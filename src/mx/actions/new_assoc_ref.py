""" new_assoc_ref.py  -- execute a new association reference action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple
from collections import defaultdict

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics
from pyral.rtypes import Attribute

# MX
from mx.log_table_config import TABLE, log_table
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.utility import *

_logger = logging.getLogger(__name__)


# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    new_assoc_ref_action: str
    init_sources: str
    attr_refs: str
    assoc_class_attrs: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "new_assoc_ref_action", "init_sources", "attr_refs", "assoc_class_attrs")
    return MMRVs(*rvs)


class NewAssocRef(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the New Associative Reference Action on a domain model.

        Args:
            action_id:  The ACTN<n> value identifying each Action instance
            activity_execution: The A<n> Activity ID
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        domain = self.activity_execution.domain  # For convenience

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        mmrv = declare_mm_rvs(db=mmdb, owner=self.owner)

        # Lookup the Action instance
        Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="New Associative Reference Action",
                          svar_name=mmrv.new_assoc_ref_action)
        Relation.join(db=mmdb, rname1=mmrv.new_assoc_ref_action, rname2='New Reference Action',
                      svar_name=mmrv.new_assoc_ref_action)
        ref_action_r = Relation.join(db=mmdb, rname1=mmrv.new_assoc_ref_action, rname2='Reference Action',
                                     svar_name=mmrv.new_assoc_ref_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.new_assoc_ref_action))
        t = ref_action_r.body[0]
        tflow_name, pflow_name, output_flow_name, rnum = \
            t['T_instance'], t['P_instance'], t['Ref_attr_values'], t['Association']

        # Get source flows from Initialization Source
        # We semijoin from the Initial Signal Action that triggered the Delegated Creation Activity
        # to obtain any number of Flows in the Activity where the creation signal was emitted mapped to
        # flows here in the Delegated Creation Activity.
        init_sources_r = Relation.semijoin(db=mmdb, rname1=self.activity_execution.signal_action_mmrv,
                                           rname2='Initialization Source',
                                           attrs={'ID': 'Signal_action', 'Activity': 'Signal_activity',
                                                  'Domain': 'Domain'},
                                           svar_name=mmrv.init_sources)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.init_sources))

        _logger.info("Flows")
        # Set the value of each local flow to its corresponding source in the creation initiator's executing
        # activity
        # TODO: generalize this to accommodate a synchronous creation source (synch create action)
        for t in init_sources_r.body:
            source_anum, source_fname, local_fname = t['Signal_activity'], t['Source_flow'], t['Local_flow']
            _logger.info(f"Copying {source_anum}-{source_fname} value -> {self.activity_execution.anum}-{local_fname}")
            source_fvalue = self.activity_execution.source_ae.flows[source_fname]
            self.activity_execution.flows[local_fname] = source_fvalue
            log_table(_logger, nsflow_msg(db=self.domdb, flow_name=local_fname, flow_dir=FlowDir.IN,
                                          flow_type=source_fvalue.flowtype,
                                          activity=self.activity_execution, rv_name=source_fvalue.value))

        # Determine the action output value.  This will be a tuple where each attribute is the name of a referential
        # Attribute of the new instance's Association Class.
        #
        # To determine the value of each referential attribute, we join the T/P instances
        # of the appropriate instance in the

        # Obtain the Attribute References
        R = f"Rnum:<{rnum}>, Domain:<{domain.name}>"
        attr_refs_r = Relation.restrict(db=mmdb, relation='Attribute Reference', restriction=R,
                                        svar_name=mmrv.attr_refs)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.attr_refs))

        # Create the output flow tuple structure
        assoc_class_attrs_r = Relation.project(db=mmdb, attributes=('From_attribute',), relation=mmrv.attr_refs)

        # Unpack from->to attribute names for the T and P references
        from_to = defaultdict(list)
        for t in attr_refs_r.body:
            from_to[t['Ref']].append({'from': t['From_attribute'], 'to': t['To_attribute']})

        output_tuple_dict = {t['From_attribute']: None for t in assoc_class_attrs_r.body}

        # T and P participating class instance relations
        tflow_value = self.activity_execution.flows[tflow_name]
        pflow_value = self.activity_execution.flows[pflow_name]

        # Process T reference
        T_to_inst_r = Relation.restrict(db=self.domdb, relation=tflow_value.value)
        T_to_inst_t = T_to_inst_r.body[0]
        for r in from_to['T']:
            output_tuple_dict[r['from']] = T_to_inst_t[r['to']]

        # Process P reference
        P_to_inst_r = Relation.restrict(db=self.domdb, relation=pflow_value.value)
        P_to_inst_t = P_to_inst_r.body[0]
        for r in from_to['P']:
            output_tuple_dict[r['from']] = P_to_inst_t[r['to']]

        # Convert output tuple dictionary into a relational tuple

        # Get the Association Class Name
        # All From_class values are the same in the attr refs relation, so we can extract the association
        # class name from the first tuple.
        # Get all attributes for this class
        assoc_class = attr_refs_r.body[0]['From_class']
        assoc_attrs_r = Relation.restrict(db=mmdb, relation='Attribute',
                                          restriction=f"Class:<{assoc_class}>, Domain:<{domain.name}>",
                                          svar_name=mmrv.assoc_class_attrs)
        # We need a list of named Attribute tuples
        attrs = [
            Attribute(name=a['Name'], type=domain.types[a['Scalar']])
            for a in assoc_attrs_r.body
            if a['Name'] in output_tuple_dict
        ]
        output_tuple_body = [tuple(output_tuple_dict[a.name] for a in attrs)]
        ref_attr_init_tuple_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="ref_attr_init_tuple")
        output_tuple_r = Relation.create(db=self.domdb, attrs=attrs, tuples=output_tuple_body, svar_name=ref_attr_init_tuple_drv)
        # Now we need to set the flowtype

        output_flow_type = "_".join(f"{a['Name']}_{a['Scalar']}" for a in assoc_attrs_r.body)

        # Set the output flow
        self.activity_execution.flows[output_flow_name] = ActiveFlow(value=ref_attr_init_tuple_drv, flowtype=output_flow_type)

        self.complete()
