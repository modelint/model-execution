""" signal_action.py -- Executes a Signal Action as defined in the SM Metamodel """

# System
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics

# MX
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow

class Signal(ActionExecution):

    monitor_external = False
    monitor_internal = False

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Determine the type of signal to be gennerated
        send_signal_action_rv = Relation.declare_rv(db=self.domdb, owner=self.rvp, name="read_input")
        Relation.semijoin(db=mmdb, rname1=self.activity_execution.rv_name, rname2="Send Signal Action",
                          svar_name=send_signal_action_rv)
        signal_completion_action_r = Relation.semijoin(db=mmdb, rname2="Signal Completion Action")
        if signal_completion_action_r.body:
            # This is a signal completion action
            pass
        pass
        # R = f"ID:<{self.action_id}>, Activity:<{anum}>, Domain:<{domain}>"
        # labeled_flow_r = Relation.restrict(db=mmdb, relation="Labeled Flow", restriction=R)
        # if not flow_r.body:
        #     msg = f"Flow {fid} in {anum}:{domain} not found"
        #     _logger.error(msg)
        # raise FlowException(msg)

        # Determine the signal type
        # Is it a Send Signal Action?
        #   If so, is it a Signal Completion Action?
        # Else Canceled Delayed Signal Action

        # for Signal Completion Action case
        # We know it will be queued for the xi (if lifecycle)
        # Send Signal Action has the ev spec

        pass