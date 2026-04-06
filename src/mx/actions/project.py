""" project.py  -- execute a relational project action """

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
    project_action: str
    project_table_action: str
    projected_attrs: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "project_action", "project_table_action", "projected_attrs")
    return MMRVs(*rvs)

class Project(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Project Action on a domain model.

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
        Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Project Action", svar_name=mmrv.project_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.project_action))

        # Join it with the Table Action superclass to get the input / output flows
        project_table_action_r = Relation.join(db=mmdb, rname1=mmrv.project_action, rname2="Table_Action",
                                               svar_name=mmrv.project_table_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.project_table_action))

        # Extract input and output flows required by the Project Action
        project_table_action_t = project_table_action_r.body[0]
        # convenient abbreviation of the rename table action tuple body
        self.source_flow_name = project_table_action_t["Input_a_flow"]  # Name like F1, F2, etc
        self.source_flow = self.activity_execution.flows[self.source_flow_name]  # The active content of source flow (value, type)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = project_table_action_t["Output_flow"]
        # And the output of the Union will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Get the attributes to project
        projected_attrs_r = Relation.semijoin(db=mmdb, rname1=mmrv.project_action, rname2="Projected Attribute",
                                              attrs={"ID": "Project_action", "Activity": "Activity", "Domain": "Domain"},
                                              svar_name=mmrv.projected_attrs)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.projected_attrs))

        attr_names = [t["Attribute"] for t in projected_attrs_r.body]
        _logger.info(f"- Attributes: {', '.join(attr_names)}")
        _logger.info("Flows")
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        project_output_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="project_output")

        P = tuple(a["Attribute"] for a in projected_attrs_r.body)
        Relation.project(db=self.domdb, relation=self.source_flow.value, attributes=P, svar_name=project_output_drv)
        log_table(_logger, table_msg(db=self.domdb, variable_name=project_output_drv))

        # Join the project action to the Relation Flow to get the type of the output
        # as a concatenated sequence of attribute type pairs delimited by underscores
        rflow_r = Relation.semijoin(db=mmdb, rname1=mmrv.project_table_action, rname2="Relation_Flow",
                                    attrs={"Output_flow": "ID", "Activity": "Activity", "Domain": "Domain"})
        output_table_type = rflow_r.body[0]["Type"]

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity_execution.flows[self.dest_flow_name] = ActiveFlow(value=project_output_drv,
                                                                        flowtype=output_table_type)

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=project_output_drv))

        self.complete()
