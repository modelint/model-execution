""" dispatched_event.py """

# System
from datetime import datetime

# Model Integration
from pyral.relation import Relation

# MX
from mx.bridge import *

class DispatchedEvent:

    def __init__(self, signal: MXSignalEvent):
        """

        """
        # self.supplied_parameter_values = parameter_values
        # self.event_spec = event_spec
        self.arrival_time = datetime.now()
        pass