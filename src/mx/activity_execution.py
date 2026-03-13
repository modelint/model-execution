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
        self.unexecuted_actions: set[str] | None = None

        self.enabled_actions = None
        self.enable_initial_actions()

    def enable_initial_actions(self):
        """
        Produce the set of actions that are initially executable.

        These will be any actions that do not require input from another action, but may receive
        one or more inputs that are initially available when execution begins.

        Cases:
           Rare: Action takes no input at all (random number generator)

           Or takes immediately available input:

           1. Class Accessor flow (reads attribute values from one or more classes)
           2. The executing (lifecycle) or partitioning (multiple assigner) instance flow
           3. Input parameter flow
           4. Scalar Value (flow with literal value specified in action language)
        """
        # First let's mark all actions as unexecuted
        R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
        action_r = Relation.restrict(db=mmdb, relation="Action", restriction=R)
        self.unexecuted_actions = {t['ID'] for t in action_r.body}

        # Subtract the set of actions dependent on action flows from the set of unexecuted actions to
        # obtain the set of non dependent actions which we can mark as enabled (immediately executable)

        # Join the unexecuted actions with Flow Dependency on the To_action (flow destination)
        # to obtain all dependent actions
        dependent_action_r = Relation.semijoin(db=mmdb, rname2='Flow Dependency',
                                               attrs={'ID': 'To_action', 'Activity': 'Activity', 'Domain': 'Domain'})
        dependent_actions = {t['To_action'] for t in dependent_action_r.body}
        self.enabled_actions = self.unexecuted_actions - dependent_actions

    def next_action(self) -> str | None:
        """
        Select the next action to execute and return its action id

        Returns:
            The action ID as a string
        """
        if self.enabled_actions:
            next_action = self.enabled_actions.pop()  # Any enabled action will do
            self.unexecuted_actions.discard(next_action)  # Unmark it as unexecuted
            return next_action

        return None  # None were enabled, so we must be done

    def update_enabled_actions(self):
        """
        Having executed some action, check flow dependencies to determine if there are any
        actions that now have all of their required inputs enabled and add them to the set of
        enabled actions.
        """
        # If the current set of enabled actions equals the set of unexecuted actions
        # there are no more actions to enable
        if self.enabled_actions == self.unexecuted_actions:
            return

        # TODO: When we get to a more interesting Activity, expand the logic

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
            current_x_action = ActivityExecution.execute_action[action_type](activity_execution=self,
                                                                             action_id=action_id)
            self.update_enabled_actions()
            pass
        pass
