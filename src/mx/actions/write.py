""" write.py  -- execute an attribute write action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.relvar import Relvar
from pyral.database import Database

# MX
from mx.instance_set import InstanceSet
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.exceptions import *
from mx.utility import *

_logger = logging.getLogger(__name__)

if __debug__:
    from mx.utility import *

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    write_action: str
    attr_write_accesses: str
    attributes: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "write_action", "attr_write_accesses", "attributes")
    return MMRVs(*rvs)

class Write(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Read Action on a domain model.

        Args:
            action_id: The ACTN<n> value
            activity_execution: The Activity Execution object
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        mmrv = declare_mm_rvs(owner=self.owner)

        # Lookup the Action instance
        Relation.semijoin(db=mmdb, rname1=self.activity_execution.activity_rvn, rname2="Write Action")
        # Narrow it down to this Write Action instance
        R = f"ID:<{action_id}>"
        write_action_t = Relation.restrict(db=mmdb, restriction=R, svar_name=mmrv.write_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.write_action))

        self.source_flow_name = write_action_t.body[0]["Instance_flow"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]  # The active content of source flow (value, type)
        _logger.info(f"{self.source_flow_name}")
        _logger.info("Flows")
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        attribute_write_accesses_r = Relation.semijoin(
            db=mmdb, rname1=mmrv.write_action, rname2="Attribute Write Access",
            attrs={"ID": "Write_action", "Activity": "Activity", "Domain": "Domain"},
            svar_name=mmrv.attr_write_accesses
        )
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.attr_write_accesses))

        # Get all attributes being written so we can look up each type
        attr_r = Relation.semijoin(db=mmdb, rname1=mmrv.attr_write_accesses, rname2="Attribute",
                                   attrs={"Attribute": "Name", "Class": "Class", "Domain": "Domain"},
                                   svar_name=mmrv.attributes)

        # Expand irefs to instance set
        output_iset_rv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="output_input")
        InstanceSet.instances(db=self.domdb, irefs_rv=self.source_flow.value, iset_rv=output_iset_rv,
                              class_name=self.source_flow.flowtype)

        qty_instances_to_write = Relation.cardinality(db=self.domdb, rname=output_iset_rv)
        if qty_instances_to_write > 1:
            msg = f"Write to multiple instances not yet supported"
            raise MXException(msg)

        for access in attribute_write_accesses_r.body:
            new_value = self.activity_execution.flows[access['Input_flow']].value
            # TODO: Fix PyRAL updateone so that we don't need to convert to snake case here
            write_attr = access['Attribute'].replace(' ', '_')
            class_name = access['Class'].replace(' ', '_')
            # TODO: NOW self.source_flow.value is now an rv name, need to resolve that to id value
            source_iref_str = Relation.get_rval_string(db=self.domdb, variable_name=self.source_flow.value)
            source_iref_t_dict = Relation.make_pyrel(source_iref_str).body[0]

            Relvar.updateone(db=self.domdb, relvar_name=class_name, id=source_iref_t_dict,
                             update={write_attr: new_value})
            # # attr_value_r = Relation.project(db=self.domdb, attributes=(access["Attribute"],),
            # #                                 relation=output_iset_rv)
            # attr_value = attr_value_r.body[0][access["Attribute"]]
            # self.activity.flows[access["Output_flow"]] = ActiveFlow(value=attr_value, flowtype="scalar")
            # self.activity.xe.mxlog.log(message=f"- Attribute: {access["Attribute"]}")
            # self.activity.xe.mxlog.log_sflow(flow_name=access["Output_flow"], flow_dir=FlowDir.OUT,
            #                                  flow_type=atypes[access["Attribute"]], activity=self.activity)
            # self.activity.xe.mxlog.log(message=f"Scalar value: [{attr_value}]")
        log_table(_logger, table_msg(db=self.domdb, variable_name='Accessible Shaft Level'))
        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.owner)
        Relation.free_rvs(db=self.domdb, owner=self.owner)
        # And since we are outputing a scalar flow, there is no domain rv output to preserve
        # In fact, we didn't define any domain rv's at all, so there are none to free

        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)
        pass
