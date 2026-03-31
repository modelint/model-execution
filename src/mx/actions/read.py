""" read.py  -- execute an attribute read action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

from mx.instance_set import InstanceSet

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database

# MX
from mx.log_table_config import TABLE, log_table
from mx.message import *
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.mxtypes import *

_logger = logging.getLogger(__name__)

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    this_read_action: str
    attr_read_accesses: str
    attributes: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "this_read_action", "attr_read_accesses", "attributes")
    return MMRVs(*rvs)

class Read(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Read Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

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
        read_action_r = Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Read Action",
                                          svar_name=mmrv.this_read_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.this_read_action))
        read_action_t = read_action_r.body[0]

        self.source_flow_name = read_action_t["Instance_flow"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]  # The active content of source flow (value, type)

        _logger.info("Flows")
        log_table(_logger, nsflow_msg(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                      db=self.domdb, rv_name=self.source_flow.value)
                                      )

        attribute_read_accesses_r = Relation.semijoin(db=mmdb, rname1=mmrv.this_read_action,
                                                      rname2="Attribute Read Access",
                                                      attrs={"ID": "Read_action",
                                                             "Activity": "Activity", "Domain": "Domain"},
                                                      svar_name=mmrv.attr_read_accesses)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.attr_read_accesses))

        # Get all attributes being read so we can look up each type
        attr_r = Relation.semijoin(db=mmdb, rname1=mmrv.attr_read_accesses, rname2="Attribute",
                                   attrs={"Attribute": "Name", "Class": "Class", "Domain": "Domain"},
                                   svar_name=mmrv.attributes)
        # Accessed attribute / type pairs
        atypes = {t["Name"]: t["Scalar"] for t in attr_r.body}

        # Expand irefs to instance set
        input_iset_rv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="read_input")
        InstanceSet.instances(db=self.domdb, irefs_rv=self.source_flow.value, iset_rv=input_iset_rv,
                              class_name=self.source_flow.flowtype)

        for access in attribute_read_accesses_r.body:
            attr_value_r = Relation.project(db=self.domdb, attributes=(access["Attribute"],),
                                            relation=input_iset_rv)
            attr_value = attr_value_r.body[0][snake(access["Attribute"])]
            self.activity_execution.flows[access["Output_flow"]] = ActiveFlow(value=attr_value, flowtype="scalar")
            _logger.info(f"- Attribute: {access["Attribute"]}")
            log_table(_logger, sflow_msg(db=self.domdb, flow_name=access["Output_flow"], flow_dir=FlowDir.OUT,
                                         flow_type=atypes[access["Attribute"]],
                                         activity=self.activity_execution, rv_name=self.source_flow.value))

            _logger.info(f"Scalar value: [{attr_value}]")

        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.owner)
        # And since we are outputing a scalar flow, there is no domain rv output to preserve
        # In fact, we didn't define any domain rv's at all, so there are none to free

        if __debug__:
            _rv_after_free = Database.get_all_rv_names()