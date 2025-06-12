""" dispatched_event.py """

# System
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration

# MX
from mx.dispatched_event import DispatchedEvent
from mx.mxtypes import NamedValues

class InteractionEvent(DispatchedEvent):

    def __init__(self, source: [ str | None ], event_spec: str, domain: str, params: NamedValues = {}, ):
        """

        """
        super().__init__(source=source, event_spec=event_spec, params=params, domain=domain)

        self.arrival_time = datetime.now()

    @classmethod
    def to_lifecycle(cls, ):
        # def __init__(self, source: [ str | None ], target_instance: [ NamedValues | None ], event_spec: str, state_model: str,
        #              params: NamedValues, domain: "Domain"):
        pass

    @classmethod
    def to_multiple_assigner(cls):
        pass

    @classmethod
    def to_single_assigner(cls):
        pass

