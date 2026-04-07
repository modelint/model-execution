""" rank_restrict.py -- executes the Rank Restrict Action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics
from pyral.rtypes import Extent, Card

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
    rank_restrict_action: str
    rank_restrict_table_action: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "rank_restrict_action", "rank_restrict_table_action", )
    return MMRVs(*rvs)

class RankRestrict(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Rank Restrict Action on a domain model.

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
        rank_restrict_action_r = Relation.semijoin(db=mmdb,
                                                   rname1=self.action_mmrv, rname2="Rank Restrict Action",
                                                   svar_name=mmrv.rank_restrict_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.rank_restrict_action))

        # Join it with the Table Action superclass to get the input / output flows
        rank_restrict_table_action_r = Relation.join(db=mmdb, rname1=mmrv.rank_restrict_action,
                                                     rname2="Table_Action",
                                                     svar_name=mmrv.rank_restrict_table_action
                                                     )
        Relation.print(db=mmdb, variable_name=mmrv.rank_restrict_table_action)

        rank_restrict_table_action_t = rank_restrict_table_action_r.body[0]
        _logger.info(f"- Attribute: {rank_restrict_table_action_t["Attribute"]}")
        _logger.info(f"- Extent: {rank_restrict_table_action_t["Extent"]}")
        _logger.info(f"- Card: {rank_restrict_table_action_t["Selection_cardinality"]}")
        _logger.info("Flows")

        self.source_flow_name = rank_restrict_table_action_t["Input_a_flow"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        self.dest_flow_name = rank_restrict_table_action_t["Output_flow"]
        # And the output of the Restrict Action will be placed in the Activity flow dictionary
        # upon completion of this Action

        rank_restrict_output_rv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="rank_restrict_output")
        rank_restrict_action_t = rank_restrict_action_r.body[0]
        rank_attr = rank_restrict_action_t["Attribute"]
        rank_extent = Extent(rank_restrict_action_t["Extent"])
        rank_card = Card(rank_restrict_action_t["Selection_cardinality"].lower())
        Relation.rank_restrict(db=self.domdb, relation=self.source_flow.value, attr_name=rank_attr, extent=rank_extent,
                               card=rank_card, svar_name=rank_restrict_output_rv)

        log_table(_logger, table_msg(db=self.domdb, variable_name=rank_restrict_output_rv))

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity_execution.flows[self.dest_flow_name] = ActiveFlow(value=rank_restrict_output_rv,
                                                                        flowtype=self.source_flow.flowtype)

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=rank_restrict_output_rv))

        self.complete()
