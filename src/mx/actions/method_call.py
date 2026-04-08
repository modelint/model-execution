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
from mx.log_table_config import TABLE, log_table
from mx.utility import *
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
    method_info: str
    method_call_parameters: str
    method_call_output: str  # Output of the method call itself

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "method_call_action", "method_info", "method_call_parameters",
                      "method_call_output")
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
        method_call_r = Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Method Call",
                                          attrs={'ID': 'ID', 'Activity': 'Activity', 'Domain': 'Domain'},
                                          svar_name=mmrv.method_call_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.method_call_action))
        method_call_t = method_call_r.body[0]
        called_method_anum = method_call_t['Method']
        called_method_input_fname = method_call_t['Instance_flow']

        # Get the Method information so that the Method Activity can initialize its owner name without having
        # to do a query.  We will pass the rv to the Method Activity.
        # We are careful to do the semijoin using Method and Domain attributes as specified on R1225 in the model
        Relation.semijoin(db=mmdb, rname1=mmrv.method_call_action, rname2="Method",
                          attrs={'Method': 'Anum', 'Domain': 'Domain'}, svar_name=mmrv.method_info)
        Relation.rename(db=mmdb, names={'Anum': 'Activity'}, relation=mmrv.method_info, svar_name=mmrv.method_info)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.method_info))

        # Lookup the Method Call Output
        # This gives us the flow name of any output from the method (may be none)
        mcall_output_r = Relation.semijoin(db=mmdb, rname1=mmrv.method_call_action, rname2="Method Call Output",
                                           attrs={'ID': 'Method_call', 'Activity': 'Activity', 'Domain': 'Domain'},
                                           svar_name=mmrv.method_call_output)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.method_call_output))
        called_method_output_fname = None
        if mcall_output_r.body:
            called_method_output_fname = mcall_output_r.body[0]['Flow']

        # Lookup any parameters
        mcall_params_r = Relation.semijoin(
            db=mmdb, rname1=mmrv.method_call_action, rname2="Method Call Parameter",
            attrs={'ID': 'Method_call', 'Activity': 'Activity', 'Domain': 'Domain'},
            svar_name=mmrv.method_call_parameters)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.method_call_parameters))
        my_flows = self.activity_execution.flows
        mcall_param_flows: dict[str, ActiveFlow] = {
            t['Parameter']: my_flows[t['Flow']] for t in mcall_params_r.body
        }

        # We need the id of the target method's executing instance
        from mx.instance_set import InstanceSet
        target_instance_t = Relation.restrict(db=self.domdb,
                                              relation=self.activity_execution.flows[called_method_input_fname].value)
        log_table(_logger, table_msg(db=self.domdb,
                                     variable_name=self.activity_execution.flows[called_method_input_fname].value))
        target_instance_id = target_instance_t.body[0]

        # Call the method
        synch_output_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="synch_output")
        from mx.method_execution import MethodExecution
        m = MethodExecution(domain=self.activity_execution.domain, method_rv=mmrv.method_info,
                            anum=called_method_anum, instance_id=target_instance_id, parameters=mcall_param_flows,
                            synch_output_drv=synch_output_drv)
        scalar_synch_out = m.synch_scalar_output
        # If there was a method output we need to set an output flow to the scalar or non scalar value
        if called_method_output_fname:
            # We output a value
            if m.synch_scalar_output:
                self.activity_execution.flows[called_method_output_fname] = ActiveFlow(
                    value=m.synch_scalar_output, flowtype='scalar')
            else:
                self.activity_execution.flows[called_method_output_fname] = ActiveFlow(
                    value=synch_output_drv, flowtype=m.synch_ns_output_type)
        pass

        # TODO: Need to set the output flow value

        self.complete()

