""" scalar_switch.py  -- execute a scalar_switch action """

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
    scalar_switch_action: str
    cases: str
    mvals: str
    selected_case: str
    disabled_cases: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "scalar_switch_action", "cases", "mvals", "selected_case", "disabled_cases")
    return MMRVs(*rvs)

class ScalarSwitch(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Scalar Switch Action on a domain model.

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
        scalar_switch_action_r = Relation.semijoin(
            db=mmdb, rname1=self.action_mmrv, rname2="Scalar Switch Action",
            svar_name=mmrv.scalar_switch_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.scalar_switch_action))
        scalar_switch_action_t = scalar_switch_action_r.body[0]

        self.source_flow_name = scalar_switch_action_t["Scalar_input"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]  # The active content of source flow (value, type)
        _logger.info(f"{self.source_flow_name}")
        _logger.info("Flows")
        if self.source_flow.flowtype == 'scalar':
            _logger.info(sflow_msg(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                   flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                   value=self.source_flow.value))
        else:
            log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                          flow_type=self.source_flow.flowtype,
                                          activity=self.activity_execution, rv_name=self.source_flow.value))

        # Find all Case (Control Flows) that could be emitted by this Scalar Switch Action
        Relation.semijoin(db=mmdb, rname1=mmrv.scalar_switch_action, rname2="Case",
                          attrs={"ID": "Switch_action", "Activity": "Activity", "Domain": "Domain"},
                          svar_name=mmrv.cases)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.cases))
        # And join with the values that can be emitted by each of the Case (Control Flows)
        Relation.semijoin(db=mmdb, rname1=mmrv.cases, rname2="Match Value",
                          attrs={"Flow": "Case_flow", "Activity": "Activity", "Domain": "Domain"},
                          svar_name=mmrv.mvals)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.mvals))
        # We select the output Case (Control Flow) to enable based on on our input source value
        R = f"Value:<{self.source_flow.value}>"
        selected_case_r = Relation.restrict(db=mmdb, relation=mmrv.mvals, restriction=R, svar_name=mmrv.selected_case)
        unselected_cases_r = Relation.subtract(db=mmdb, rname1=mmrv.mvals, rname2=mmrv.selected_case, svar_name=mmrv.disabled_cases)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.disabled_cases))
        scase_tuple = selected_case_r.body[0]
        # And then set the value of that output flow to the selected Match Value
        self.activity_execution.flows[scase_tuple["Case_flow"]] = ActiveFlow(value=scase_tuple["Value"],
                                                                             flowtype=self.source_flow.flowtype)
        _logger.info("Flows")
        # The source flow always matches the output flow
        log_table(_logger, sflow_msg(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                     flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                     value = self.source_flow.value))

        log_table(_logger, sflow_msg( flow_name=scase_tuple["Case_flow"], flow_dir=FlowDir.OUT,
                                      flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                      value=self.activity_execution.flows[scase_tuple["Case_flow"]].value))

        # Disable all outgoing unselected case flows
        # for t in unselected_cases_r.body:
        #     self.activity_execution.flows[t['Case_flow']] = FlowState.DISABLED
        #     _logger.info(f"Disabled case control flow: {t['Case_flow']} -> x")
            # self.activity_execution.disable(flow_name=t['Case_flow'])

        downstream_rv = self.activity_execution.mmrv.downstream_actions
        Relation.semijoin(db=mmdb, rname1=mmrv.disabled_cases, rname2='Control Dependency',
                          attrs={'Case_flow': 'Control_flow', 'Activity': 'Activity', 'Domain': 'Domain'},
                          svar_name=downstream_rv)
        Relation.project(db=mmdb, relation=downstream_rv, attributes=("Control_flow",), exclude=True,
                         svar_name=downstream_rv)
        log_table(_logger, table_msg(db=mmdb, variable_name=downstream_rv))
        _logger.info("Start disabling downstream actions for unmatched cases...")
        self.activity_execution.disable_downstream_actions()
        _logger.info("Downstream actions for unmatched cases disabled")

        self.complete()
