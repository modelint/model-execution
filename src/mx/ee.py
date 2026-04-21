""" ee.py - External Entity """

# System
import logging
from typing import TYPE_CHECKING

# MX
from mx.actions.ext_signal import ExtSignal
if TYPE_CHECKING:
    from mx.domain import Domain

class EE:
    """
    External Entity. When we have a system in place for MX Bridge implementation, we will fit it
    to this class. For now this is a placeholder.
    """
    def __init__(self, name: str, service_domain_name: str, domain: 'Domain'):
        self.name = name
        self.service = service_domain_name
        self.domain = domain

    def process_operation(self):
        # TODO: Implement
        pass

    def process_ext_signal(self, ext_signal: ExtSignal):
        # TODO: Implement
        pass



