""" completion_event.py """

# System
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration

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
        super().__init__(source=source, event_spec=event_spec, state_model=sm, sm_type=sm_type,
                         to_instance=to_instance,
                         partitioning_class=partitioning_class, partitioning_instance=partitioning_instance,
                         params=params, domain=domain)
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
    def to_lifecycle(cls, event_spec: str, to_instance: NamedValues, to_class: str,
                     params: NamedValues, domain: "Domain"):
        # For Completion Event the source and destination are the same, so we define the
        # source by extracting the elements out of the destination params
        source = InstanceAddress(domain=domain.name, class_name=to_class, instance_id=to_instance)
        return cls(sm_type=StateMachineType.LIFECYCLE, event_spec=event_spec, params=params, domain=domain,
                   source=source, to_instance=to_instance, to_class=to_class)

    @classmethod
    def to_multiple_assigner(cls):
        pass

    @classmethod
    def to_single_assigner(cls):
        pass

