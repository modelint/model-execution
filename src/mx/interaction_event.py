""" dispatched_event.py """

# System
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration

# MX
from mx.dispatched_event import DispatchedEvent
from mx.mxtypes import NamedValues, StateMachineType


class InteractionEvent(DispatchedEvent):

    def __init__(self, sm_type: StateMachineType, event_spec, params, domain, source=None, to_instance=None,
                 to_class=None, partitioning_instance=None, partitioning_class=None, to_rnum=None):
        """

        """
        # Validate target state machine type
        sm = None
        match sm_type:
            case StateMachineType.LIFECYCLE:
                sm = to_class
                if not (to_instance and to_class):
                    pass # TODO: Raise exception
            case StateMachineType.SA:
                sm = to_rnum
                if not to_rnum:
                    pass  # TODO: Raise exception
            case StateMachineType.MA:
                sm = to_rnum
                if not (to_rnum and partitioning_class and partitioning_instance):
                    pass  # TODO: Raise exception
            case _:
                pass  # TODO: Raise exception

        super().__init__(source=source, event_spec=event_spec, state_model=sm, sm_type=sm_type,
                         to_instance=to_instance,
                         partitioning_class=partitioning_class, partitioning_instance=partitioning_instance,
                         params=params, domain=domain)

        self.arrival_time = datetime.now()
        self.dispatch()

    def dispatch(self):
        pass

    @classmethod
    def to_lifecycle(cls, source: [ str | None ], event_spec: str, to_instance: NamedValues, to_class: str,
                     params: NamedValues, domain: "Domain"):
        return cls(sm_type=StateMachineType.LIFECYCLE, event_spec=event_spec, params=params, domain=domain,
                   source=source, to_instance=to_instance, to_class=to_class)

    @classmethod
    def to_single_assigner(cls, source: [ str | None ],  event_spec: str, to_rnum: str,
                           params: NamedValues, domain: "Domain"):
        return cls(sm_type=StateMachineType.SA, event_spec=event_spec, params=params, domain=domain,
                   source=source, to_rnum=to_rnum)

    @classmethod
    def to_multiple_assigner(cls, source: [ str | None ],  event_spec: str, paritioning_instance: NamedValues,
                             partitioning_class: str, to_rnum: str, params: NamedValues, domain: "Domain"):
        return cls(sm_type=StateMachineType.MA, event_spec=event_spec, params=params, domain=domain, source=source,
                   partitioning_instance=paritioning_instance, partitioning_class=partitioning_class, to_rnum=to_rnum)

