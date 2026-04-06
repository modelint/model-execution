""" set_action.py  -- execute a relational join, union, or subtract action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

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
    set_action: str
    set_table_action: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "set_action", "set_table_action")
    return MMRVs(*rvs)

class SetAction(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Set Action on a domain model.

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
        Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Set Action", svar_name=mmrv.set_action)

        # Join it with the Table Action superclass to get the input / output flows
        set_table_action_r = Relation.join(db=mmdb, rname1=mmrv.set_action, rname2="Table_Action",
                                           svar_name=mmrv.set_table_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.set_table_action))

        # Extract input and output flows required by the Set Action
        set_table_action_t = set_table_action_r.body[0]
        _logger.info(f"- Operation: {set_table_action_t["Operation"]}")
        _logger.info("Flows")
        # convenient abbreviation of the rename table action tuple body
        self.source_A_name = set_table_action_t["Input_a_flow"]  # Name like F1, F2, etc
        self.source_B_name = set_table_action_t["Input_b_flow"]
        self.source_A_flow = self.activity_execution.flows[self.source_A_name]
        self.source_B_flow = self.activity_execution.flows[self.source_B_name]

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_A_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_A_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_A_flow.value))
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_B_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_B_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_B_flow.value))

        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = set_table_action_t["Output_flow"]
        # And the output of the Set Action will be placed in the Activity flow dictionary
        # upon completion of this Action

        set_action_name = set_table_action_r.body[0]["Operation"]
        set_action_output_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="set_action_output")
        if set_action_name == "UNION":
            Relation.union(db=self.domdb, relations=(self.source_A_flow.value, self.source_B_flow.value),
                           svar_name=set_action_output_drv)
        elif set_action_name == "JOIN":
            Relation.join(db=self.domdb, rname1=self.source_A_flow.value, rname2=self.source_B_flow.value,
                          svar_name=set_action_output_drv)
        else:
            pass  # TODO: SUBTRACT, ...

        log_table(_logger, table_msg(db=self.domdb, variable_name=set_action_output_drv))

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity_execution.flows[self.dest_flow_name] = ActiveFlow(value=set_action_output_drv,
                                                                        flowtype=self.source_A_flow.flowtype)

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                      flow_type=self.source_A_flow.flowtype,
                                      activity=self.activity_execution, rv_name=set_action_output_drv))

        self.complete()
