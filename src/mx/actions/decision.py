""" decision.py  -- execute a decision action"""

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.relation import Database  # Diagnostic

# MX
from mx.log_table_config import TABLE, log_table
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.utility import *

_logger = logging.getLogger(__name__)

# For each python string variable that will hold the name of a temporary TclRAL relation used in this module,
# a corresponding attribute is defined. An instance of this tuple is generated with each attribute holding
# a string naming some temporary TclRAL relation variable.
# Each such variable can then be supplied in the svar_name argument
# to create the TclRAL relation. Later that same variable can be used to supply a relation argument to other
# PyRAL methods.
class MMRVs(NamedTuple):
    decision_action: str
    results: str
    enabled_result: str
    disabled_result: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "decision_action", "results", "enabled_rsult", "disabled_result")
    return MMRVs(*rvs)


def truthy_scalar(sv: int | str ) -> bool:
    """
    Evaluates a scalar value as either true or false

    Args:
        sv:  A scalar value (not an rv name) to evaluate

    Returns:
        Boolean evaluation of sv
    """
    return bool(sv) if isinstance(sv, int) else sv.upper() == 'TRUE'

class Decision(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Decision Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        Args:
            action_id: The ACTN<n> value identifying each Action instance
            activity_execution: The Activity Execution object
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        mmrv = declare_my_module_rvs(db=mmdb, owner=self.owner)

        # Lookup the Action instance
        decision_action_r = Relation.semijoin(
            db=mmdb, rname1=self.action_mmrv, rname2="Decision Action",
            svar_name=mmrv.decision_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.decision_action))
        decision_action_t = decision_action_r.body[0]

        # Get the value of this action's input flow
        self.source_flow_name = decision_action_t["Boolean_input"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]
        _logger.info(f"{self.source_flow_name}")
        _logger.info("Flows")
        if self.source_flow.flowtype == 'scalar':
            _logger.info(sflow_msg(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                   flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                   value=self.source_flow.value))
        else:  # It's nonscalar (relation) and therefore stored in a relational variable
            log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                          flow_type=self.source_flow.flowtype,
                                          activity=self.activity_execution, rv_name=self.source_flow.value))

        # Find all Result (Control Flows) that could be enabled by this Decision Action
        Relation.semijoin(db=mmdb, rname1=mmrv.decision_action, rname2="Result",
                          attrs={"ID": "Decision_action", "Activity": "Activity", "Domain": "Domain"},
                          svar_name=mmrv.results)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.results))
        # We select the output Result (Control Flow) to enable based on on our input source value
        # It is either true or false
        if self.source_flow.flowtype == 'scalar':
            # We evaluate the truthieness of a scalar value
            result = truthy_scalar(self.source_flow.value)
        else:
            source_flow_value_r = Relation.restrict(db=self.domdb, relation=self.source_flow.value)
            result = bool(len(source_flow_value_r.body))

        # And then set the value of that output flow to the result (true or false)
        enabled_result_r = Relation.restrict(db=mmdb, relation=mmrv.results, restriction=f"Decision:<{result}>",
                                             svar_name=mmrv.enabled_result)
        # The disabled result is found by subtracting the enabled result
        Relation.subtract(db=mmdb, rname1=mmrv.results, rname2=mmrv.enabled_result, svar_name=mmrv.disabled_result)

        enabled_flow_name = enabled_result_r.body[0]["Flow"]
        self.activity_execution.flows[enabled_flow_name] = ActiveFlow(value=result, flowtype="scalar")
        _logger.info("Flows")
        log_table(_logger, sflow_msg(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                     flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                     value = self.source_flow.value))
        _logger.info(sflow_msg(flow_name=enabled_flow_name, flow_dir=FlowDir.OUT, flow_type='scalar',
                               activity=self.activity_execution, value=str(result)))

        # Disable all actions from the disabled result flow
        downstream_mmrv = self.activity_execution.mmrv.downstream_actions  # Declared, but no value assigned yet
        # The Control Dependency will give us the set of downstream actions to disable
        Relation.semijoin(db=mmdb, rname1=mmrv.disabled_result, rname2='Control Dependency',
                          attrs={'Flow': 'Control_flow', 'Activity': 'Activity', 'Domain': 'Domain'},
                          svar_name=downstream_mmrv)
        Relation.project(db=mmdb, relation=downstream_mmrv, attributes=("Control_flow",), exclude=True,
                         svar_name=downstream_mmrv)
        log_table(_logger, table_msg(db=mmdb, variable_name=downstream_mmrv))
        _logger.info("Start disabling downstream actions for unmatched cases...")
        self.activity_execution.disable_downstream_actions()  # Uses the downstream_rv variable
        _logger.info("Downstream actions for unmatched cases disabled")

        self.complete()
