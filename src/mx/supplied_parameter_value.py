""" supplied_parameter_value.py """

from typing import Any

class SuppliedParameterValue:

    def __init__(self, value:Any, type_name:str):
        """

        :param value:
        :param type_name:
        """

        self.value = value
        self.type_name = type_name
