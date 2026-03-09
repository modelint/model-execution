""" signal_action.py -- Executes a Signal Action as defined in the SM Metamodel """

# System
from typing import TYPE_CHECKING, NamedTuple

from mx.mxtypes import StateMachineType

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics

# MX
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow
from mx.completion_event import CompletionEvent
from mx.mxtypes import *

class Signal(ActionExecution):

    monitor_external = False
    monitor_internal = False

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        send_signal_action_rv = Relation.declare_rv(db=mmdb, owner=self.rvp, name="send_signal_action")
        # Determine the type of signal to be generated
        send_signal_r = Relation.semijoin(db=mmdb, rname1=self.activity_execution.rv_name, rname2="Send Signal Action",
                                          svar_name=send_signal_action_rv)
        if send_signal_r.body:
            # Get the parameters
            # TODO: Process signal with parameters when we have an example
            # supplied_parameter_value_r = Relation.semijoin(db=mmdb, rname1=send_signal_action_rv,
            #                                                rname2="Supplied Parameter Value")
            supplied_params = {}  # TODO: Placeholder for above
            # Send the signal
            signal_completion_action_r = Relation.join(db=mmdb, rname1=send_signal_action_rv,
                                                       rname2="Signal Completion Action")
            if signal_completion_action_r.body:
                # This is a signal completion action
                event_spec=signal_completion_action_r.body[0]["Event_spec"]
                CompletionEvent(sm_type=self.activity_execution.state_machine.sm_type,
                                event_spec=event_spec, params=supplied_params,
                                domain=self.activity_execution.domain,
                                source=InstanceAddress(
                                    domain=self.activity_execution.domain.name,
                                    class_name=activity_execution.state_machine.state_model,
                                    instance_id=self.activity_execution.state_machine.instance_id)
                                )
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