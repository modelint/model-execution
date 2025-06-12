""" dispatched_event.py """

# System
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration

# MX
from mx.mxtypes import NamedValues

class DispatchedEvent:

    def __init__(self, source: [ str | None ], event_spec: str, state_model: str,
                 params: NamedValues, domain: "Domain"):
        """

        """
        self.source = source
        self.event_spec = event_spec
        self.state_model = state_model
        self.params = params
        self.domain = domain
