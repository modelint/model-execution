""" computation.py  -- execute a computation action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple
import re

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
from mx.mxtypes import SCALAR_TYPE

_logger = logging.getLogger(__name__)

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    computation_action: str
    boolean_partition: str
    general_computation: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "computation_action", "boolean_partition", "general_computation")
    return MMRVs(*rvs)

def evaluate_flow_expression(expr: str, flow_values: dict[str, int | float | str]) -> int | float | bool | str:
    """
    Evaluate an expression containing <Fn> flow markers.

    Args:
        expr: Expression string like "<F3> == <F5>" or "(<F1> + <F3>) / <F1>"
        flow_values: Dict mapping flow names to their values, e.g. {'F3': 3.14, 'F5': 3.14}

    Returns:
        Evaluated result of the expression.
    """
    # Extract all flow names referenced in the expression
    flow_names = re.findall(r'<(F\d+)>', expr)

    # Verify all referenced flows have values
    missing = [f for f in flow_names if f not in flow_values]
    if missing:
        raise KeyError(f"No value provided for flow(s): {missing}")

    # Replace each <Fn> marker with its value, quoting strings
    def replacement(match: re.Match) -> str:
        name = match.group(1)
        val = flow_values[name]
        return repr(val) if isinstance(val, str) else str(val)

    python_expr = re.sub(r'<(F\d+)>', replacement, expr)

    return eval(python_expr)


class Computation(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Computation Action on a domain model.

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
        computation_action_r = Relation.semijoin(
            db=mmdb, rname1=self.action_mmrv, rname2="Computation Action", svar_name=mmrv.computation_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.computation_action))
        computation_action_t = computation_action_r.body[0]
        self.expression = computation_action_t['Expression']

        # Gather input flows
        computation_input_r = Relation.semijoin(db=mmdb, rname1=mmrv.computation_action, rname2='Computation Input',
                                                attrs={'ID': 'Computation', 'Activity': 'Activity', 'Domain': 'Domain'})
        self.input_flow_names = [t['Input_flow'] for t in computation_input_r.body]
        # self.source_flows = {n: self.activity_execution.flows[n] for n in self.input_flow_names}

        _logger.info("Flows")
        for fname in self.input_flow_names:
            source_flow = self.activity_execution.flows[fname]
            _logger.info(f"{fname}")
            if source_flow.flowtype == 'scalar':
                _logger.info(
                    sflow_msg(flow_name=fname, flow_dir=FlowDir.IN, flow_type=source_flow.scalar,
                              activity=self.activity_execution, value=source_flow.value)
                )
                pass
            else:
                log_table(_logger, nsflow_msg(db=self.domdb, flow_name=fname, flow_dir=FlowDir.IN,
                                              flow_type=source_flow.flowtype, activity=self.activity_execution,
                                              rv_name=source_flow.value))

        # Is this a General Computation or a Boolean Paritition?
        general_computation_r = Relation.semijoin(
            db=mmdb, rname1=mmrv.computation_action, rname2='General Computation', svar_name=mmrv.general_computation)
        result_flow_name = general_computation_r.body[0]['Result_flow']
        if general_computation_r.body:
            self.process_computation(result_flow_name=result_flow_name)
            result_flow = self.activity_execution.flows[result_flow_name]
            _logger.info(
                sflow_msg(flow_name=result_flow_name, flow_dir=FlowDir.OUT, flow_type=result_flow.scalar,
                          activity=self.activity_execution, value=result_flow.value)
            )
        else:
            self.process_boolean_partition()

        self.complete()

    def process_computation(self, result_flow_name: str):
        """
        Replace flow name markers in computation with flow values and set the result value
        on the output flow.

        Args:
            result_flow_name: Flow (Fn) name of the output flow
        """
        fvals = {f: self.activity_execution.flows[f].value for f in self.input_flow_names}
        result = evaluate_flow_expression(expr=self.expression, flow_values=fvals)
        result_mx_type = SCALAR_TYPE[type(result)]
        self.activity_execution.flows[result_flow_name] = ActiveFlow(
            value=result, flowtype='scalar', scalar=result_mx_type)

    def process_boolean_partition(self):
        pass
        mmrv = self.mmrv
        boolean_partition_r = Relation.semijoin(
            db=mmdb, rname1=mmrv.computation_action, rname2='Boolean Partition', svar_name=mmrv.boolean_partition)
