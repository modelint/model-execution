""" activity.py -- A metamodel Activity """

# System
from typing import TYPE_CHECKING, NamedTuple, Optional, Any

if TYPE_CHECKING:
    from mx.xe import XE

# MX
from mx.bridge import NamedValues

class ActiveFlow(NamedTuple):
    value: Any
    flowtype: str

class Activity:

    def __init__(self, xe: "XE", domain: str, anum: str, parameters: NamedValues):
        """

        :param domain:
        :param anum:
        :param parameters:
        """
        self.xe = xe
        self.anum = anum
        self.parameters = parameters
        self.domain = domain

    def execute(self):
        pass
