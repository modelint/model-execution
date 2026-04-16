""" completion_event.py """

# System
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relation import Relation

# MX
from mx.dispatched_event import DispatchedEvent
from mx.mxtypes import *

class CompletionEvent(DispatchedEvent):

    def __init__(self, sm_type: StateMachineType, event_spec: str, params: NamedValues,
                 domain: "Domain",
                 source: ElementAddress,
                 to_instance: NamedValues = None,
                 to_class: str = None, partitioning_instance: NamedValues = None,
                 partitioning_class: str = None, to_rnum: str = None):
        """

        """
        state_model = None
        match sm_type:
            case StateMachineType.LIFECYCLE:
                state_model = source.class_name
            case StateMachineType.SA:
                state_model = source.rel_name
            case StateMachineType.MA:
                state_model = source.rel_name
        super().__init__(source=source, event_spec=event_spec, state_model=state_model, sm_type=sm_type,
                         to_instance=to_instance,
                         partitioning_class=partitioning_class, partitioning_instance=partitioning_instance,
                         params=params, domain=domain)
        self.dispatch()

    def dispatch(self):
        # Look up the target state machine and set the completion event
        match self.sm_type:
            case StateMachineType.LIFECYCLE:
                # We need the instance id generated for the executing instance of this lifecycle
                # Since this is a completion event, we can just use the source instance id
                # So we restrict based on the identifier attr/value pairs
                R = ", ".join([f"{a}:<{v}>" for a, v in self.source.instance_id.items()])
                inst_id_r = Relation.restrict(db=self.domain.alias, relation=f"{self.domain.owner}__{self.state_model}_i", restriction=R)
                target_inst_id = int(inst_id_r.body[0]["_instance"])
                # Now we grab the lifecycle state machine instance
                sm = self.domain.lifecycles[self.state_model][target_inst_id]
                # And tell it to set this completion event
                # Note that only one completion event may be active at a time, so unlike an interaction event
                # We don't queue it or put it in a set. We just make it the one and only pending completion event.
                sm.accept_completion_event(event=self)
            case StateMachineType.MA:
                pass
            case StateMachineType.SA:
                pass


