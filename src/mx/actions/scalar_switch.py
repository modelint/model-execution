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


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "scalar_switch_action", "cases", "mvals")
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
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        cases_r = Relation.semijoin(db=mmdb, rname1=mmrv.scalar_switch_action, rname2="Case",
                                    attrs={"ID": "Switch_action", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=mmrv.cases)
        mvals_r = Relation.semijoin(db=mmdb, rname1=mmrv.cases, rname2="Match Value",
                                    attrs={"Flow": "Case_flow", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=mmrv.mvals)
        R = f"Value:<{self.source_flow.value}>"
        selected_case_r = Relation.restrict(db=mmdb, relation=mmrv.mvals, restriction=R)
        scase_tuple = selected_case_r.body[0]
        self.activity_execution.flows[scase_tuple["Case_flow"]] = ActiveFlow(value=scase_tuple["Value"],
                                                                             flowtype=self.source_flow.flowtype)

        _logger.info("Flows")
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))
        _logger.info(f"Scalar value: [{scase_tuple['Value']}]")
        log_table(_logger, sflow_msg(db=self.domdb, flow_name=scase_tuple["Case_flow"], flow_dir=FlowDir.OUT,
                                     flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                     rv_name=self.source_flow.value))

        self.complete()
