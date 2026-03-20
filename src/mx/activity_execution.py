""" activity_execution.py -- A metamodel Activity """

# System
import logging
from typing import TYPE_CHECKING, Callable, NamedTuple
from abc import ABC, abstractmethod


if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relvar import Relvar
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
    unexecuted_actions: str  # Unexecuted actions projected on ID
    unenabled_actions: str  # Remaining actions that are unenabled (U)
    flow_deps: str  # This activity's flow dependencies
    # action_states: str # All actions with execution status
    # actions_to_enable: str  # Actions that are to be enabled
    # next_action: str  # Next action to be enabled
    # executed_actions: str  # These actions have been executed
    # unchanged_actions: str  # Actions unaffected by state change
    # change_actions: str  # These Actions will change state to E, X, or D


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner,
                      "unexecuted_actions", "unenabled_actions", "flow_deps"
                      # "action_states",
                      # "next_action", "executed_actions", "unchanged_actions", "change_actions"
                      )
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

    def __init__(self, domain: 'Domain', anum: str, owner_name: str, activity_rvn: str, parameters: NamedValues):
        """

        Args:
            domain: The local domain object
            anum: This activity's identifier
            owner_name: String that uniquely identifies this activity and executing instance or rnum
            activity_rvn: Relational variable name holding this activity's metamodel data
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
        _logger.info(f"d Declared rvs: {Database.get_all_rv_names()}")
        self.activity_rvn = activity_rvn
        # Here we create a temporary relvar in PyRAL to track the execution state of this Activity's Actions
        # during execution
        # We set the name of this relvar so we can access and update the relvar content
        self.action_states = f"{self.owner_name}_Action_States"
        # And here we define the empty relvar in PyRAL
        Relvar.create_relvar(db=mmdb, name=self.action_states, attrs=[
            Attribute(name='ID', type='string'),
            Attribute(name='State', type='string'),
        ], ids={1: ['ID']})
        # TODO: Remember to unset this relvar after the Activity completes execution
        self.action_states = self.enable_initial_actions()

    @abstractmethod
    def enable_initial_actions(self) -> str:
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

        Returns:
            Name of the relvar showing the state of each of this Activity's Actions
        """
        pass

    def next_action(self) -> str | None:
        """
        Select the next action to execute and return its action id

        Returns:
            The action ID as a string
        """
        # Enabled actions are all actions in (E) state
        R = f"State:E"
        enabled_actions_r = Relation.restrict(db=mmdb, relation=self.action_states, restriction=R)
        if not len(enabled_actions_r.body):
            # There are no more enabled actions to execute
            return None

        # There is at least one enabled action ready to go, chose any of them
        next_action_r = Relation.rank_restrict(db=mmdb, attr_name='ID', extent=Extent.LEAST, card=Card.ONE)
        next_action = next_action_r.body[0]["ID"]
        # Now change that action's status to X (executing)
        Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': next_action}, update={'State': 'X'})
        if __debug__:
            Relation.print(db=mmdb, variable_name=self.action_states)
        return next_action

    def update_enabled_actions(self):
        """
        Having executed some action, check flow dependencies to determine if there are any
        actions that now have all of their required inputs enabled and add them to the set of
        enabled actions.
        """
        mmrv = self.mmrv

        # We change the state of the executed action to completed
        R = f"State:X"
        x_action_r = Relation.restrict(db=mmdb, relation=self.action_states, restriction=R)
        x_action = x_action_r.body[0]['ID']
        Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': x_action}, update={'State': 'C'})
        if __debug__:
            Relation.print(db=mmdb, variable_name=self.action_states)
        pass

        # Now we select any remaining unenabled actions to see if we can enable them
        R = f"State:U"
        unenabled_actions_r = Relation.restrict(db=mmdb, relation=self.action_states, restriction=R, svar_name=mmrv.unenabled_actions)

        if not Relation.cardinality(db=mmdb, rname=mmrv.unenabled_actions):
            # There are none, so we just proceed with activity execution
            return

        # For each U (uenabled action), get the set of From_actions from the Flow Dependency relvar.
        # If each of these actions has reached the C (completed) state, the unenabled action moves to the
        # E (enabled) state.

        Relation.project(db=mmdb, relation=mmrv.flow_deps, attributes=("From_action", "To_action",),
                         svar_name=mmrv.flow_deps)
        Relation.print(db=mmdb, variable_name=mmrv.unenabled_actions)
        Relation.print(db=mmdb, variable_name=mmrv.flow_deps)

        # Test to derive sum_expr expr
        # Get the to actions for the unabled action
        Relation.join(db=mmdb, rname1=mmrv.unenabled_actions, rname2=mmrv.flow_deps, attrs={'ID': 'To_action'})
        Relation.print(db=mmdb, table_name="Join1: Get From")
        # Get the action states entry for the to actions
        Relation.print(db=mmdb, variable_name=self.action_states)
        Relation.semijoin(db=mmdb, rname2=self.action_states, attrs={'From_action': 'ID'})
        Relation.print(db=mmdb, table_name="Join2: Get status")
        # Make sure they are all C
        R = f"NOT State:C"
        Relation.restrict(db=mmdb, restriction=R)
        Relation.print(db=mmdb, table_name="Not completed")
        pass

        sum_expr = Relation.build_expr(commands=[
            JoinCmd(rname1="s", rname2=mmrv.flow_deps, attrs={'ID': 'To_action'}),
            SemiJoinCmd(rname1=None, rname2=self.action_states, attrs={'From_action': 'ID'}),
            RestrictCmd(relation=None, restriction="NOT State:C"),
            CardinalityCmd(rname=None)
        ])

        Relation.summarize(db=mmdb, relation=mmrv.unenabled_actions, per_attrs=("ID",),
                               summaries=(SumExpr(attr=Attribute(name="Complete", type="int"), expr=sum_expr),),
                               svar_name="solution")


        Relation.print(db=mmdb, table_name="solution")
        R = f"Complete:<0>"
        e_r = Relation.restrict(db=mmdb, restriction=R)
        for a in e_r.body:
            aid = a["ID"]
            Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': aid}, update={'State':'E'})
        Relation.print(db=mmdb, variable_name=self.action_states)
        pass



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
            # the temporary s (summarize) relation represents the current unexecuted action
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
        _logger.info(f"Executing activity {self.anum} actions")
        while (action_id := self.next_action()) is not None:
            # Lookup the action type
            R = (f"ID:<{action_id}>, Activity:<{self.anum}>, "
                 f"Domain:<{self.domain.name}>")
            action_r = Relation.restrict(db=mmdb, relation="Action", restriction=R)
            action_type = action_r.body[0]["Type"]
            _logger.info(f"Executing action {action_id}-{action_type}")
            current_x_action = ActivityExecution.execute_action[action_type](activity_execution=self,
                                                                             action_id=action_id)
            self.update_enabled_actions()
            pass
        pass
