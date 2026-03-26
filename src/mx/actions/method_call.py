""" method_call.py  -- execute a method_call action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

from mx.instance_set import InstanceSet

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.relvar import Relvar
from pyral.database import Database  # Diagnostics

# MX
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.exceptions import *

_logger = logging.getLogger(__name__)

if __debug__:
    from mx.utility import *

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    method_call_action: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "method_call_action",)
    return MMRVs(*rvs)

class MethodCall(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Method Call Action on a domain model.

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

        # Lookup the Method Call Action
        # This gives us the Method's anum and input instance flow number
        Relation.extend(db=mmdb, relation=self.activity_execution.activity_rvn, attrs={'ID': self.action_id})
        method_call_t = Relation.semijoin(db=mmdb, rname2="Method Call", svar_name=mmrv.method_call_action)
        called_method_anum = method_call_t.body[0]['Method']
        called_method_input_fname = method_call_t.body[0]['Instance_flow']

        # Lookup the Method Call Output
        # This gives us the flow name of any output from the method (may be none)
        mcall_output_t = Relation.semijoin(db=mmdb, rname1=mmrv.method_call_action, rname2="Method Call Output")
        called_method_output_fname = None
        if mcall_output_t.body:
            called_method_output_fname = mcall_output_t.body[0]['Flow']

        # Lookup any parameters
        mcall_params_r = Relation.semijoin(db=mmdb, rname1=mmrv.method_call_action, rname2="Method Call Parameter")
        mcall_param_flow_names = {}
        if mcall_params_r.body:
            mcall_param_flow_names = {t['Parameter']: t['Flow'] for t in mcall_params_r.body}
        pass

        # Call the method

