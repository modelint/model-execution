""" completion_event.py """

# System
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration

# MX
from mx.dispatched_event import DispatchedEvent
from mx.mxtypes import NamedValues

class CompletionEvent(DispatchedEvent):

    def __init__(self, source: [ str | None ], event_spec: str, params: NamedValues = {}, ):
        """

        """
        pass

        # dest_instance = None
        # dest_rnum = None
        # if isinstance(target, str):
        #     dest_rnum = target  # Target is a single assigner rnum
        #     return
        # else:
        #     dest_instance = target  # Target value is an instance
        #     return

    @classmethod
    def to_lifecycle(cls, ):
        pass

    @classmethod
    def to_multiple_assigner(cls):
        pass

    @classmethod
    def to_single_assigner(cls):
        pass

