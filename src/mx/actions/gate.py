""" gate.py -- executes the Gate Action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

from mx.exceptions import MXActionException

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics
from pyral.rtypes import Extent, Card

# MX
from mx.db_names import mmdb
from mx.log_table_config import TABLE, log_table
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import FlowDir
from mx.rvname import declare_rvs
from mx.utility import *

_logger = logging.getLogger(__name__)

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    gate_action: str
    gate_flow_deps: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "gate_action", "gate_flow_deps")
    return MMRVs(*rvs)

class Gate(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Gate Action on a domain model.

        Args:
            action_id:  The ACTN<n> value identifying each Action instance
            activity_execution: The A<n> Activity ID
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_mm_rvs(db=mmdb, owner=self.owner)
        mmrv = self.mmrv  # For brevity

        # Lookup the Action instance
        gate_action_r = Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Gate Action",
                                          svar_name=mmrv.gate_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.gate_action))

        _logger.info("Flows")

        # Lookup the Action flow dependency
        gate_flow_deps_r = Relation.semijoin(db=mmdb, rname1=mmrv.gate_action, rname2="Flow Dependency",
                                             attrs={"ID": "To_action", "Activity": "Activity", "Domain": "Domain"},
                                             svar_name=mmrv.gate_flow_deps)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.gate_flow_deps))

        gate_action_t = gate_action_r.body[0]
        output_flow_name = gate_action_t["Output_flow"]
        input_flow_names = [t["Flow"] for t in gate_flow_deps_r.body]

        # From all inputs to the gate, only the enabled flow will appear in the activity execution flows dictionary
        # So we verify the f flow name is a key in the dictionary so that we don't get a KeyError
        input_values = {f: v for f in input_flow_names
                        if (v := activity_execution.flows.get(f))}

        if len(input_values) > 1:
            msg = f"Multiple enabled flows input to Gate Action: {self.activity_execution.anum}-{self.action_id}"
            _logger.error(msg)
            raise MXActionException(msg)

        input_flow_name, activity_execution.flows[output_flow_name] = next(iter(input_values.items()))
        _logger.info(f"\nGate: {self.action_id} passing Flow: {input_flow_name} to Flow: {output_flow_name}")

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=input_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=activity_execution.flows[input_flow_name].flowtype,
                                      activity=self.activity_execution,
                                      rv_name=activity_execution.flows[input_flow_name].value))

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=output_flow_name, flow_dir=FlowDir.OUT,
                                      flow_type=activity_execution.flows[output_flow_name].flowtype,
                                      activity=self.activity_execution,
                                      rv_name=activity_execution.flows[output_flow_name].value))

        self.complete()
