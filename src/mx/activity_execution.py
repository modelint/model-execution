""" activity_execution.py -- A metamodel Activity """

# System
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relation import Relation

# MX
from mx.actions.action_execution import ActionExecution
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
from mx.actions.signal import Signal
from mx.db_names import mmdb

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
        "gate": Gate,
        "signal": Signal,
        # "write": Write,
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
        self.ready_actions: set[str] = set()

    def next_action(self) -> str | None:
        """
        Select the next action to execute and return its action id

        Returns:
            The action ID as a string
        """
        # Check the Flow Depenency instances, are there any?
        R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
        fdep_r = Relation.restrict(db=mmdb, relation="Flow Dependency", restriction=R)
        if not fdep_r.body:
            # There are no flow dependencies, so we can just execute the actions in any order
            R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
            enabled_action_r = Relation.restrict(db=mmdb, relation="Action", restriction=R)
            # Put all actions in this Activity into the set of ready actions
            for a in enabled_action_r.body:
                self.ready_actions.add(a["ID"])
        else:
            # Process dependencies
            pass
        # All actions in the set are ready to execute, so it doesn't matter in what order we process them

        return self.ready_actions.pop() if self.ready_actions else None

    def execute(self):
        """
        Execute an Activity
        """
        # We keep executing ready actions until there are no more
        while (action_id := self.next_action()) is not None:
            # Lookup the action type
            R = (f"ID:<{action_id}>, Activity:<{self.anum}>, "
                 f"Domain:<{self.domain.name}>")
            action_r = Relation.restrict(db=mmdb, relation="Action", restriction=R)
            action_type = action_r.body[0]["Type"]
            current_x_action = ActivityExecution.execute_action[action_type](activity=self, action_id=action_id)
            pass
        pass
