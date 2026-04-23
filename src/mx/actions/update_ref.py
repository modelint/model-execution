""" update_ref.py  -- execute an Update Reference Action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple
from collections import defaultdict

from mx.instance_set import InstanceSet

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics
from pyral.rtypes import Attribute

# MX
from mx.log_table_config import TABLE, log_table
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.instance_set import InstanceSet
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.utility import *

_logger = logging.getLogger(__name__)


# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    update_ref_action: str
    attr_refs: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "update_ref_action", "attr_refs")
    return MMRVs(*rvs)


class UpdateReference(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Update Reference Action on a domain model.

        Args:
            action_id:  The ACTN<n> value identifying each Action instance
            activity_execution: The A<n> Activity ID
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        domain = self.activity_execution.domain  # For convenience

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        mmrv = declare_mm_rvs(db=mmdb, owner=self.owner)

        # Lookup the Action instance
        Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Update Reference Action",
                          svar_name=mmrv.update_ref_action)
        update_ref_action_r = Relation.join(db=mmdb, rname1=mmrv.update_ref_action, rname2='Reference Action',
                                            svar_name=mmrv.update_ref_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.update_ref_action))
        t = update_ref_action_r.body[0]
        from_inst_fname, to_inst_fname, rnum = t['From_instance'], t['To_instance'], t['Association']
        to_flow = self.activity_execution.flows[to_inst_fname]
        from_flow = self.activity_execution.flows[from_inst_fname]

        _logger.info("Flows")
        _logger.info("From flow")
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=from_inst_fname, flow_dir=FlowDir.IN,
                                      flow_type=from_flow.flowtype,
                                      activity=self.activity_execution, rv_name=from_flow.value))
        _logger.info("To flow")
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=to_inst_fname, flow_dir=FlowDir.IN,
                                      flow_type=to_flow.flowtype,
                                      activity=self.activity_execution, rv_name=to_flow.value))

        # Obtain the Attribute References
        R = f"Rnum:<{rnum}>, Domain:<{domain.name}>"
        attr_refs_r = Relation.restrict(db=mmdb, relation='Attribute Reference', restriction=R,
                                        svar_name=mmrv.attr_refs)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.attr_refs))

        # Unpack from->to attribute names for the Reference
        attr_ref = {}
        for t in attr_refs_r.body:
            attr_ref[t['From_attribute']] = t['To_attribute']

        # Get the from instance values (expanding from iref)
        inst_to_update_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="inst_to_update")
        InstanceSet.instances(db=self.domdb, irefs_rv=from_flow.value, iset_rv=inst_to_update_drv, class_name=from_flow.flowtype)
        log_table(_logger, table_msg(db=self.domdb, variable_name=inst_to_update_drv))

        # Build the update one tuple
        # First we need the id dict of the instance to be updated (available in the from flow input to this action)
        # Body of an instance reference is an id dict we can supply to the update command
        from_inst_id = Relation.restrict(db=self.domdb, relation=from_flow.value).body[0]
        to_inst_t = Relation.restrict(db=self.domdb, relation=to_flow.value).body[0]
        # Now we need a dict to express the values to update
        update_attrs = {}
        for from_attr, to_attr in attr_ref.items():
            update_attrs[from_attr] = to_inst_t[to_attr]
        Relvar.updateone(db=self.domdb, relvar_name=from_flow.flowtype, id=from_inst_id, update=update_attrs)
        log_table(_logger, table_msg(db=self.domdb, variable_name=from_flow.flowtype))

        # This action has no output flows, so just complete
        self.complete()
