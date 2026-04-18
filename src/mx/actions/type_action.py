""" type_action.py  -- execute a type action """
# We suffix _action to avoid any potential platform conflict with 'type'

# System
import logging
from typing import TYPE_CHECKING, NamedTuple
import re

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.relvar import Relvar
from pyral.database import Database

# MX
from mx.log_table_config import TABLE, log_table
from mx.instance_set import InstanceSet
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.exceptions import *
from mx.utility import *
from mx.mxtypes import SCALAR_TYPE
from mx.usertypes import *

_logger = logging.getLogger(__name__)

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    type_action: str
    type_operation: str
    selector: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "type_action", "type_operation", "selector")
    return MMRVs(*rvs)

class TypeAction(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Type Action on a domain model.

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
        type_action_r = Relation.semijoin(
            db=mmdb, rname1=self.action_mmrv, rname2="Type Action", svar_name=mmrv.type_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.type_action))
        type_action_t = type_action_r.body[0]
        self.output_flow_name, self.scalar_name = type_action_t['Output_flow'], type_action_t['Scalar']
        pass

        # This is either a Type or Selector operation, process accordingly
        type_operation_r = Relation.semijoin(
            db=mmdb, rname1=mmrv.type_action, rname2='Type Operation', svar_name=mmrv.type_operation)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.type_operation))
        if type_operation_r.body:
            t = type_operation_r.body[0]
            op_name, input_flow_name = t['Name'], t['Input_flow']
            # Process input flow (there are non for a selector)
            # This type operation is invoked on this input scalar value
            _logger.info("Flows")
            source_flow = self.activity_execution.flows[input_flow_name]
            _logger.info(f"{input_flow_name}")
            _logger.info(
                sflow_msg(flow_name=input_flow_name, flow_dir=FlowDir.IN, flow_type=source_flow.scalar,
                          activity=self.activity_execution, value=source_flow.value)
            )
            output_value = self.process_type_operation(type_op=op_name, input_flow=input_flow_name)
            output_flow = ActiveFlow(value=output_value, flowtype='scalar', scalar=self.scalar_name)
            self.activity_execution.flows[self.output_flow_name] = output_flow
            _logger.info(
                sflow_msg(flow_name=self.output_flow_name, flow_dir=FlowDir.OUT, flow_type=output_flow.scalar,
                          activity=self.activity_execution, value=output_flow.value)
            )
        else:
            output_value = self.process_selector()

        self.complete()

    def process_selector(self) -> str | bool | int | float:
        """
        Type selector operation. We simply output the selected value.
        """
        pass

    def process_type_operation(self, type_op: str, input_flow: str) -> str | bool | int | float:
        """
        Type Operation. We execute the defined operation which may or may not
        yield an output.

        Args:
            type_op: Name of the Type Operation

        Returns:
            The value produced by the type op function
        """

        # TODO: Support parameter input to type ops
        output_value = type_ops[self.scalar_name][type_op]()
        return output_value