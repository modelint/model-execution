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


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "new_assoc_ref_action", "init_sources", "attr_refs")
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
        R = f"Rnum:<{rnum}>, Domain:<{self.activity_execution.domain.name}>"
        attr_refs_r = Relation.restrict(db=mmdb, relation='Attribute Reference', restriction=R,
                                        svar_name=mmrv.attr_refs)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.attr_refs))

        # Create the output flow tuple structure
        assoc_class_attrs_r = Relation.project(db=mmdb, attributes=('From_attribute',), relation=mmrv.attr_refs)

        # Unpack from->to attribute names for the T and P references
        from_to = defaultdict(list)
        for t in attr_refs_r.body:
            from_to[t['Ref']].append({'from': t['From_attribute'], 'to': t['To_attribute']})

        output_tuple = {t['From_attribute']: None for t in assoc_class_attrs_r.body}

        # T and P participating class instance relations
        tflow_value = self.activity_execution.flows[tflow_name]
        pflow_value = self.activity_execution.flows[pflow_name]

        # Process T reference
        T_to_inst_r = Relation.restrict(db=self.domdb, relation=tflow_value.value)
        T_to_inst_t = T_to_inst_r.body[0]
        for r in from_to['T']:
            output_tuple[r['from']] = T_to_inst_t[r['to']]

        # Process P reference
        P_to_inst_r = Relation.restrict(db=self.domdb, relation=pflow_value.value)
        P_to_inst_t = P_to_inst_r.body[0]
        for r in from_to['P']:
            output_tuple[r['from']] = P_to_inst_t[r['to']]
        pass

        self.complete()
