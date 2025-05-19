""" activity.py -- A metamodel Activity """

# System
from typing import TYPE_CHECKING, NamedTuple, Callable, Any

if TYPE_CHECKING:
    from mx.xe import XE

# MX
from mx.bridge import NamedValues
from mx.actions.traverse import Traverse
from mx.actions.rename import Rename
from mx.actions.scalar_switch import ScalarSwitch
from mx.actions.read import Read
from mx.actions.select import Select
from mx.actions.project import Project
from mx.actions.set_action import SetAction
from mx.actions.restrict import Restrict

class Activity:

    # This is a dispatch table mapping action names to the python classes that execute these actions
    execute_action: dict[str, Callable[..., None]] = {
        "traverse": Traverse,
        "rename": Rename,
        "scalar switch": ScalarSwitch,
        "read": Read,
        "select": Select,
        "project": Project,
        "set": SetAction,
        "restrict": Restrict,
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
        """
        Each type of Activity (Method, State) overrides this method
        :return:
        """
        # TODO: Look for commonality to promote
        pass
