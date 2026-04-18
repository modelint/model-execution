""" extract.py  -- execute a relational extract action """

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
    extract_action: str
    attribute: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "extract_action", "attribute")
    return MMRVs(*rvs)

class Extract(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Extract Action on a domain model.

        Args:
            action_id:  The ACTN<n> value identifying each Action instance
            activity_execution: The A<n> Activity ID
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        mmrv = declare_my_module_rvs(db=mmdb, owner=self.owner)

        # Lookup the Action instance
        extract_action_r = Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Extract Action",
                                             svar_name=mmrv.extract_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.extract_action))

        extract_action_t = extract_action_r.body[0]
        self.source_flow_name = extract_action_t["Input_tuple"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]  # The active content of source flow (value, type)
        self.dest_flow_name = extract_action_t["Output_scalar"]

        self.attr = extract_action_t["Attribute"]
        input_tuple_r = Relation.project(db=self.domdb, relation=self.source_flow.value, attributes=(self.attr,))
        extracted_value = input_tuple_r.body[0][self.attr]

        _logger.info(f"- Attribute: {self.attr}")
        _logger.info("Flows")
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        _logger.info(f"\nScalar value: {extracted_value} output on Flow: {self.dest_flow_name}")

        # Get attribute being read so we can look up its type
        attr_r = Relation.semijoin(db=mmdb, rname1=mmrv.extract_action, rname2="Table Attribute",
                                   attrs={"Attribute": "Name", "Table": "Table", "Domain": "Domain"},
                                   svar_name=mmrv.attribute)
        attr_t = attr_r.body[0]

        self.activity_execution.flows[self.dest_flow_name] = ActiveFlow(value=extracted_value, flowtype="scalar", scalar=attr_t['Scalar'])

        _logger.info(
            sflow_msg(flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT, flow_type=attr_t["Scalar"],
                      activity=self.activity_execution, value=extracted_value)
        )

        self.complete()
