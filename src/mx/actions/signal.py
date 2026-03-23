""" signal_action.py -- Executes a Signal Action as defined in the SM Metamodel """

# System
import logging
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
from mx.interaction_event import InteractionEvent
from mx.rvname import declare_rvs
from mx.mxtypes import *

_logger = logging.getLogger(__name__)

class MMRVs(NamedTuple):
    send_signal_action_rv : str
    signal_assigner_action_rv : str
    signal_instance_action_rv : str
    initial_signal_action_rv : str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner,
                      "send_signal_action",
                      "signal_assigner_action",
                      "signal_instance_action",
                      "initial_signal_action",
                      )
    return MMRVs(*rvs)

class Signal(ActionExecution):
    """
    See the Signal Action subsystem class model to find all referenced classes in the comments
    in this python module.
    """
    # Default model debugger monitoring options
    monitor_external = False
    monitor_internal = False

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_mm_rvs(owner=self.owner)

        if __debug__:
            _logger.info(f"    RVS begin signal action:")
            _logger.info(f"    {Database.get_all_rv_names()}")

        self.supplied_params: NamedValues = {}

        self.process_signal()

        Relation.free_rvs(db=mmdb, owner=self.owner)

    def process_signal(self):
        """
        Determine whether this Signal Action actually sends a signal or if it is cancelling a delayed event.
        """
        mmrv = self.mmrv

        # Determine the type of signal to be generated
        # and extend our activity with our action id to semijoin to the our action only
        Relation.extend(db=mmdb, relation=self.activity_execution.activity_rvn, attrs={'ID': self.action_id})
        send_signal_t = Relation.semijoin(db=mmdb, rname2="Send Signal Action", svar_name=mmrv.send_signal_action_rv)
        if send_signal_t.body:
            self.process_send_signal()
        else:
            self.process_cancel_delay()

    def process_send_signal(self):
        """
        Here we determine the type of destination and process accordingly.
        Each subclass of Send Signal Action defines a possible destination.
        """
        mmrv = self.mmrv

        # Get any supplied parameters
        self.set_supplied_params()

        # Mutually exclusive destination cases

        # Signal Completion Action (self)
        signal_completion_action_r = Relation.join(db=mmdb, rname1=mmrv.send_signal_action_rv,
                                                   rname2="Signal Completion Action")
        if signal_completion_action_r.body:
            self.signal_completion(
                event_spec_name=signal_completion_action_r.body[0]["Event_spec"],
            )
            return

        # Signal Instance
        signal_instance_action_r = Relation.join(
            db=mmdb, rname1=mmrv.send_signal_action_rv, rname2="Signal Instance Action",
            svar_name=mmrv.signal_instance_action_rv
        )
        if signal_instance_action_r.body:
            self.signal_assigner()
            return

        # Signal Assigner State Machine (single or multiple)
        signal_assigner_action_r = Relation.join(
            db=mmdb, rname1=mmrv.send_signal_action_rv, rname2="Signal Assigner Action",
            svar_name=mmrv.signal_assigner_action_rv
        )
        if signal_assigner_action_r.body:
            self.signal_assigner()
            return

        # Initial Signal
        initial_signal_action_r = Relation.join(
            db=mmdb, rname1=mmrv.send_signal_action_rv, rname2="Initial Signal Action",
            svar_name=mmrv.initial_signal_action_rv
        )
        if signal_instance_action_r.body:
            self.signal_assigner()
            return


    def signal_instance(self):
        pass

    def initial_signal(self):
        pass

    def signal_assigner(self):
        mmrv = self.mmrv
        pass
        signal_assigner_action_t = Relation.semijoin(db=mmdb, rname1=mmrv.signal_assigner_action_rv, rname2="Signal Assigner Action")
        rnum = signal_assigner_action_t.body[0]['Association']
        ma_partition_instance_t = Relation.semijoin(db=mmdb, rname2="Multiple Assigner Partition Instance")
        partition_flow = None if not ma_partition_instance_t.body else ma_partition_instance_t.body[0]["Partition"]
        pinst_id = None
        pclass = None
        if partition_flow:
            pflow_value = self.activity_execution.flows[partition_flow].value
            pclass = self.activity_execution.flows[partition_flow].flowtype
            pflow_t = Relation.restrict(db=self.domdb, relation=pflow_value)
            pinst_id = pflow_t.body[0]
            pass
        send_signal_action_t = Relation.restrict(db=mmdb, relation=mmrv.send_signal_action_rv)
        InteractionEvent(
            sm_type=StateMachineType.MA if partition_flow else StateMachineType.SA,
            event_spec=send_signal_action_t.body[0]["Event_spec"],
            params=self.supplied_params,
            domain=self.activity_execution.domain,
            source=InstanceAddress(
                domain=self.activity_execution.domain.name,
                class_name=self.activity_execution.state_machine.state_model,
                instance_id=self.activity_execution.state_machine.instance_id),
            to_instance=None,
            to_class=None,
            partitioning_instance=pinst_id,
            partitioning_class=pclass,
            to_rnum=rnum
        )

        pass

    def signal_completion(self, event_spec_name: str):
        CompletionEvent(sm_type=self.activity_execution.state_machine.sm_type,
                        event_spec=event_spec_name, params=self.supplied_params,
                        domain=self.activity_execution.domain,
                        source=InstanceAddress(
                            domain=self.activity_execution.domain.name,
                            class_name=self.activity_execution.state_machine.state_model,
                            instance_id=self.activity_execution.state_machine.instance_id)
                        )

    def process_cancel_delay(self):
        pass

    def set_supplied_params(self):
        # Get the parameters
        # TODO: Process signal with parameters when we have an example
        # supplied_parameter_value_r = Relation.semijoin(db=mmdb, rname1=send_signal_action_rv,
        #                                                rname2="Supplied Parameter Value")

        pass
