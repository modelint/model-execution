""" dispatched_event.py """

from mx.supplied_parameter_value import SuppliedParameterValue
from datetime import datetime

class DispatchedEvent:

    def __init__(self, event_spec: str, parameter_values: list[SuppliedParameterValue]):
        """

        :param event_spec:
        :param parameter_values:
        """
        self.supplied_parameter_values = parameter_values
        self.event_spec = event_spec
        self.arrival_time = datetime.now()