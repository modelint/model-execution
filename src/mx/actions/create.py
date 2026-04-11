""" create.py  -- execute a create action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

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

_logger = logging.getLogger(__name__)


# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    create_action: str
    init_sources: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "create_action", "init_sources")
    return MMRVs(*rvs)


class Create(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Create Action on a domain model.

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
        create_action_r = Relation.semijoin(
            db=mmdb, rname1=self.action_mmrv, rname2="Create Action", svar_name=mmrv.create_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.create_action))
        create_action_t = create_action_r.body[0]

        # Get source flows from Initialization Source
        init_sources_r = Relation.semijoin(db=mmdb, rname1=self.activity_execution.signal_action_mmrv,
                                           rname2='Initialization Source',
                                           attrs={'ID': 'Signal_action', 'Activity': 'Signal_activity',
                                                  'Domain': 'Domain'},
                                           svar_name=mmrv.init_sources)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.init_sources))

        self.source_flow_name = create_action_t["Instance_flow"]
        self.source_flow = self.activity_execution.flows[
            self.source_flow_name]  # The active content of source flow (value, type)
        _logger.info(f"{self.source_flow_name}")
        _logger.info("Flows")
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        self.complete()
