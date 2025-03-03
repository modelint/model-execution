""" non_self_directed_event.py """

from mx.dispatched_event import DispatchedEvent
from typing import Any

class NonSelfDirectedEvent(DispatchedEvent):

    def __init__(self, event_spec: str, param_values: list[Any]):
        super().__init__(event_spec=event_spec, param_values=param_values)
        pass
