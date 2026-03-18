""" activity_execution.py -- A metamodel Activity """

# System
import logging
from typing import TYPE_CHECKING, Callable, NamedTuple
from abc import ABC, abstractmethod


if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relation import Relation
from pyral.database import Database
from pyral.rtypes import *

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
from mx.rvname import declare_rvs

_logger = logging.getLogger(__name__)

# Tuple generator and rv class for Metamodel Database (mmdb)
class MMRVs(NamedTuple):
    unexecuted_actions_full: str  # All unexecuted actions with full header
    unexecuted_actions: str  # Unexecuted actions projected on ID
    enabled_actions: str  # Actions that can be executed
    dependent_actions: str  # Actions dependent on some unexecuted action
    unenabled_actions: str  # Unexecuted actions that are not yet enabled


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "unexecuted_actions_full", "unexecuted_actions",
                      "enabled_actions", "dependent_actions", "unenabled_actions")
    return MMRVs(*rvs)

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
        self.mmrv = declare_mm_rvs(owner=self.owner_name)
        self.rv_name = rv_name
        _logger.info(f"owner: {self.owner_name}")
        _logger.info(f"rv_name: {self.rv_name}")
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
        mmrv = self.mmrv

        # First let's mark all actions as unexecuted
        R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
        action_r = Relation.restrict(db=mmdb, relation="Action", restriction=R, svar_name=mmrv.unexecuted_actions_full)
        self.unexecuted_actions = {t['ID'] for t in action_r.body}
        # And save as a relational value as well
        Relation.project(db=mmdb, attributes=("ID",), svar_name=mmrv.unexecuted_actions)
        pass

        # Subtract the set of actions dependent on action flows from the set of unexecuted actions to
        # obtain the set of non dependent actions which we can mark as enabled (immediately executable)

        # Join the unexecuted actions with Flow Dependency on the To_action (flow destination)
        # to obtain all dependent actions
        dependent_action_r = Relation.semijoin(db=mmdb, rname1=mmrv.unexecuted_actions_full, rname2='Flow Dependency',
                                               attrs={'ID': 'To_action', 'Activity': 'Activity', 'Domain': 'Domain'})
        Relation.project(db=mmdb, attributes=("To_action",))
        Relation.rename(db=mmdb, names={"To_action": "ID"}, svar_name=mmrv.dependent_actions)
        Relation.subtract(db=mmdb, rname1=mmrv.unexecuted_actions, rname2=mmrv.dependent_actions,
                          svar_name=mmrv.enabled_actions)
        dependent_actions = {t['To_action'] for t in dependent_action_r.body}
        self.enabled_actions = self.unexecuted_actions - dependent_actions
        if __debug__:
            Relation.print(db=mmdb, variable_name=mmrv.unexecuted_actions)
            Relation.print(db=mmdb, variable_name=mmrv.dependent_actions)
            Relation.print(db=mmdb, variable_name=mmrv.enabled_actions)
        pass

    def next_action(self) -> str | None:
        """
        Select the next action to execute and return its action id

        Returns:
            The action ID as a string
        """
        mmrv = self.mmrv

        if self.enabled_actions:
            next_action = self.enabled_actions.pop()  # Any enabled action will do

            # Get the corresponding relation for that next action so we can subtract it
            R = f"ID:<{next_action}>"
            Relation.restrict(db=mmdb, relation=mmrv.unexecuted_actions, restriction=R)

            # Subtract it
            self.unexecuted_actions.discard(next_action)  # Unmark it as unexecuted
            Relation.subtract(db=mmdb, rname1=mmrv.unexecuted_actions, svar_name=mmrv.unexecuted_actions)
            return next_action

        return None  # None were enabled, so we must be done

    def update_enabled_actions(self):
        """
        Having executed some action, check flow dependencies to determine if there are any
        actions that now have all of their required inputs enabled and add them to the set of
        enabled actions.
        """
        mmrv = self.mmrv

        # If the current set of enabled actions equals the set of unexecuted actions
        # there are no more actions to enable
        if self.enabled_actions == self.unexecuted_actions:
            return

        unenabled_actions = self.unexecuted_actions - self.enabled_actions
        # Relation.subtract(db=mmdb, rname1=mmrv.unexecuted_actions, rname2=mmrv.enabled_actions,
        #                   svar_name=mmrv.unenabled_actions)
        if __debug__:
            Relation.print(db=mmdb, variable_name=mmrv.unexecuted_actions)
            Relation.print(db=mmdb, variable_name=mmrv.enabled_actions)
            # Relation.print(db=mmdb, variable_name=mmrv.unenabled_actions)
        pass
        # Per each a in unabled_actions
        # Get the set of from_actions
        # if all of the from_actions are a subset of self.executed_actions
        # add that a to the set of self.enabled_actions and remove it from
        # the set of self.unexecuted actions

        # --- Copied from old wave computation in xuml_populate ---
        # Proceeding from the Actions completed in the prior Wave,
        # enable the set of Flows output from those Actions
        # and make those the new wave_enabled_flows (replacing the prior set of flows)
        # self.enable_action_outputs(source_action_relation="executable_actions")

        # The total set of enabled flows becomes the new wave_enabled_flows relation value added to
        # all earlier enabled flows in the enabled_flows relation value
        # Relation.union(db=mmdb, relations=("enabled_flows", "wave_enabled_flows"),
        #                svar_name="enabled_flows")
        # Relation.print(db=mmdb, variable_name="enabled_flows")

        # Now for the fun part:
        # For each unexecuted Action, see if its total set of required input Flows is a subset
        # of the currently enabled Flows. If so, this Action can execute and be assigned to the current Wave.

        # We use the summarize command to do the relational magic.
        # The idea is to go through the unexecuted_actions relation value and, for each Action ID
        # execute the sum_expr (summarization expression) yielding a true or false result.
        # Either the Action can or cannot execute. The unexecuted_actions relation is extended with an extra
        # column that holds this boolean result.
        # Then we'll restrict that table to find only the true results and throw away the extra column
        # in the process so that we just end up with a new set of executable_actions (replacing the previous
        # relation value of the same name).

        # Taking it step by step, here we build the sum_expr
        # sum_expr = Relation.build_expr(commands=[
            # the temproary s (summarize) relation represents the current unexecuted action
            # We join it with the Flow Dependencies for this Activity as the To_action
            # to obtain the set of action generated inputs it requires.
            # (we don't care about the non-action generated initial_pseudo_state flows since we know these are always
            # available)
        #     JoinCmd(rname1="s", rname2="fd", attrs={"ID": "To_action"}),
        #     ProjectCmd(attributes=("Flow",), relation=None),
        #     # And here we see if those flows are a subset of the enabled flows (true or false)
        #     SetCompareCmd(rname2="enabled_flows", op=SetOp.subset, rname1=None)
        # ])
        # Now we embed the sum_expr in our summarize command
        # Relation.summarize(db=mmdb, relation="unexecuted_actions", per_attrs=("ID",),
        #                    summaries=(
        #                        SumExpr(attr=Attribute(name="Can_execute", type="boolean"), expr=sum_expr),), )
        # R = f"Can_execute:<{1}>"  # True is 1, False is 0 in TclRAL and we just want the 1's
        # Relation.restrict(db=mmdb, restriction=R)
        # Just take the ID attributes.  After the restrict we don't need the extra boolean attribute anymore
        # xactions = Relation.project(db=mmdb, attributes=("ID",), svar_name="executable_actions")
        # Relation.print(db=mmdb, variable_name="executable_actions")
        # And here we replace the set of completed_actions with our new batch of executable_actions
        # Relation.restrict(db=mmdb, relation="executable_actions", svar_name="completed_actions")

    # Having processed either the initial_pseudo_state or subsequent waves, we do the same work
    # Add all Action IDs in the executable_actions relation into the current Wave, and increment the counter
    # self.waves[self.wave_ctr] = [t['ID'] for t in xactions.body]
    # self.wave_ctr += 1
    # print(f"Wave --- [{self.wave_ctr}] ---")
    # Finally, remove the latest completed actions from the set of unexecuted_actions
    # unex_actions = Relation.subtract(db=mmdb, rname1="unexecuted_actions", rname2="completed_actions",
    #                                  svar_name="unexecuted_actions")

    # Relation.print(db=mmdb, variable_name="unexecuted_actions")
    # Rinse and repeat until all the actions are completed
    # ^^^ Copied from old wave computation in xuml_populate ^^^

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
