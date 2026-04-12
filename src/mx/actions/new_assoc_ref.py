""" new_assoc_ref.py  -- execute a new association reference action """

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
    new_assoc_ref_action: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "rename_action", "rename_table_action")
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
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.new_assoc_ref_action))

        Relation.join(db=mmdb, rname1=mmrv.new_assoc_ref_action, rname2='New Reference Action',
                      svar_name=mmrv.new_assoc_ref_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.new_assoc_ref_action))
        pass






        # Join it with the Table Action superclass to get the input / output flows
        rename_table_action_r = Relation.join(db=mmdb, rname1=mmrv.rename_action, rname2="Table Action",
                                              svar_name=mmrv.rename_table_action)
        rename_table_action_t = rename_table_action_r.body[0]

        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.rename_table_action))

        _logger.info(f"- {rename_table_action_t["From_attribute"]} >> {rename_table_action_t["To_attribute"]}")
        _logger.info("Flows")

        # Extract input and output flows required by the Rename Action
        self.source_flow_name = rename_table_action_t["Input_a_flow"]  # Name like F1, F2, etc
        self.source_flow = self.activity_execution.flows[self.source_flow_name]  # The active content of source flow (value, type)
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        self.dest_flow_name = rename_table_action_t["Output_flow"]
        # And the output of the Rename will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Rename
        rename_output_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="rename_output")
        Relation.rename(db=self.domdb,
                        names={rename_table_action_t["From_attribute"]: rename_table_action_t["To_attribute"]},
                        relation=self.source_flow.flowtype, svar_name=rename_output_drv)
        log_table(_logger, table_msg(db=self.domdb, variable_name=rename_output_drv))

        self.activity_execution.flows[self.dest_flow_name] = ActiveFlow(value=rename_output_drv,
                                                                        flowtype=rename_table_action_t["To_table"])
        # The domain rv above is retained since it is an output flow, so we don't free it until the Activity completes
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                      flow_type=rename_table_action_t["To_table"],
                                      activity=self.activity_execution, rv_name=rename_output_drv))

        self.complete()
