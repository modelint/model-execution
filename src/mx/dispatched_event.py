""" dispatched_event.py """

# System
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration

# MX
from mx.mxtypes import NamedValues, StateMachineType

class DispatchedEvent:

    def __init__(self, source: Optional[str], event_spec: str, state_model: str,
                 sm_type: StateMachineType, to_instance: Optional[NamedValues], partitioning_class: Optional[str],
                 partitioning_instance: Optional[NamedValues], params: NamedValues, domain: "Domain"):
        """

        """
        self.source = source  # If None, from outside the domain
        self.sm_type = sm_type
        self.event_spec = event_spec
        self.state_model = state_model
        self.params = params  # Might be empty {}
        self.domain = domain

        # Any or all of these may be None depending on sm_type
        # (the all case is the single assigner)
        self.to_instance = to_instance
        self.partitioning_class = partitioning_class
        self.partitioning_instance = partitioning_instance

    def dispatch(self):
        pass  # Overriden by subclasses