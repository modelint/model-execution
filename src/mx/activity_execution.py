""" activity_execution.py -- A metamodel Activity """

# System
from typing import TYPE_CHECKING, Callable
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relation import Relation

# MX
from mx.actions.flow import ActiveFlow
from mx.actions.action_execution import ActionExecution
from mx.deprecated.bridge import NamedValues
from mx.actions.traverse import Traverse
from mx.actions.rename import Rename
from mx.actions.scalar_switch import ScalarSwitch
from mx.actions.read import Read
from mx.actions.write import Write
from mx.actions.extract import Extract
from mx.actions.select import Select
from mx.actions.project import Project
from mx.actions.set_action import SetAction
from mx.actions.restrict import Restrict
from mx.actions.gate import Gate
from mx.actions.rank_restrict import RankRestrict
from mx.actions.signal import Signal
from mx.db_names import mmdb

class ActivityExecution(ABC):

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
        "write": Write,
    }

    def __init__(self, domain: 'Domain', anum: str, owner_name: str, rv_name: str, parameters: NamedValues):
        """

        Args:
            domain: The local domain object
            anum: This activity's identifier
            owner_name: String that uniquely identifies this activity and executing instance or rnum
            rv_name: Relational variable name holding this activity's metamodel data
            parameters: Possibly an empty dictionary of parameter values conforming to the Activity's signature
        """
        self.domain = domain
        self.system = domain.system
        self.anum = anum
        self.parameters = parameters
        self.ready_actions: set[str] = set()
        self.flows: dict[str, ActiveFlow | None] = {}
        self.owner_name = owner_name
        self.rv_name = rv_name

        R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
        action_r = Relation.restrict(db=mmdb, relation="Action", restriction=R)
        self.unexecuted_actions = {t['ID'] for t in action_r.body}
        self.enabled_actions = None

    def next_action(self) -> str | None:
        """
        Select the next action to execute and return its action id

        Returns:
            The action ID as a string
        """
        # Step 1: Create current set of enabled actions
        # Check the Flow Dependency instances, are there any?
        R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
        fdep_r = Relation.restrict(db=mmdb, relation="Flow Dependency", restriction=R)
        if not fdep_r.body:
            self.enabled_actions = {a for a in self.unexecuted_actions}
        else:
            # Process dependencies
            pass
        # All actions in the set are ready to execute, so it doesn't matter in what order we process them

        # Step 2: Select one enabled action and remove it from the set of unexecuted actions
        next_action = self.enabled_actions.pop()
        self.unexecuted_actions.discard(next_action)

        return next_action if self.enabled_actions else None

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
            current_x_action = ActivityExecution.execute_action[action_type](activity_execution=self, action_id=action_id)
            pass
        pass
