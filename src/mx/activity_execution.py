""" activity_execution.py -- A metamodel Activity """

# System
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from mx.domain import Domain

# MX
from mx.deprecated.bridge import NamedValues
from mx.actions.traverse import Traverse
from mx.actions.rename import Rename
from mx.actions.scalar_switch import ScalarSwitch
from mx.actions.read import Read
from mx.actions.extract import Extract
from mx.actions.select import Select
from mx.actions.project import Project
from mx.actions.set_action import SetAction
from mx.actions.restrict import Restrict
from mx.actions.gate import Gate
from mx.actions.rank_restrict import RankRestrict

class ActivityExecution:

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
        "rank restrict": RankRestrict,
        "extract": Extract,
        "gate": Gate
    }

    def __init__(self, domain: 'Domain', anum: str, parameters: NamedValues):
        """

        Args:
            domain:
            anum:
            parameters:
        """
        self.domain = domain
        self.system = domain.system
        self.anum = anum
        self.parameters = parameters

    def next_action(self) -> str:
        """
        Select the next action to execute and return its action id

        Returns:
            The action ID as a string
        """
        # instance_id_value = '_'.join(v for v in self.instance.values())
        # self.owner_name = f"{class_name}_{name}_{instance_id_value}"
        #
        # self.method_rvname = Relation.declare_rv(db=mmdb, owner=self.owner_name, name="method_name")
        pass

    def execute(self):
        """
        Each type of Activity (Method, State) overrides this method
        :return:
        """
        # TODO: Look for commonality to promote
        pass
