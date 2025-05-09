""" activity.py -- A metamodel Activity """

# System
from typing import TYPE_CHECKING, NamedTuple, Callable, Any

if TYPE_CHECKING:
    from mx.xe import XE

# MX
from mx.bridge import NamedValues
from mx.actions.traverse import Traverse
from mx.actions.rename import Rename

class Activity:

    execute_action: dict[str, Callable[..., None]] = {
        "traverse": Traverse,
        "rename" : Rename
    }

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
