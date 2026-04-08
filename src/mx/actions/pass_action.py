""" pass_action.py  -- execute a pass action """

# We need the _action suffix since pass is a python keyword!

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

from mx.instance_set import InstanceSet

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database

# MX
from mx.log_table_config import TABLE, log_table
from mx.message import *
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.mxtypes import *

_logger = logging.getLogger(__name__)

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    pass_action: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "pass_action",)
    return MMRVs(*rvs)

class PassAction(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Read Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

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
        pass_action_r = Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Pass Action",
                                          svar_name=mmrv.pass_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.pass_action))
        pass_action_t = pass_action_r.body[0]

        # Get the value in the source flow
        self.source_flow_name = pass_action_t["Input_flow"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]

        # Set the dest flow do the same value
        self.dest_flow_name = pass_action_t["Output_flow"]
        self.activity_execution.flows[self.dest_flow_name] = self.source_flow
        self.dest_flow = self.activity_execution.flows[self.dest_flow_name]

        _logger.info("Flows")
        if self.source_flow.flowtype != 'scalar':
            log_table(_logger, nsflow_msg(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                          flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                          db=self.domdb, rv_name=self.source_flow.value)
                                          )
        else:
            _logger.info(sflow_msg(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                   flow_type=self.source_flow.flowtype, activity=activity_execution,
                                   value=self.source_flow.value))

        if self.dest_flow.flowtype != 'scalar':
            log_table(_logger, nsflow_msg(flow_name=self.dest_flow_name, flow_dir=FlowDir.IN,
                                          flow_type=self.dest_flow.flowtype, activity=self.activity_execution,
                                          db=self.domdb, rv_name=self.dest_flow.value)
                      )
        else:
            _logger.info(sflow_msg(flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                   flow_type=self.dest_flow.flowtype, activity=activity_execution,
                                   value=self.dest_flow.value))

        self.complete()
