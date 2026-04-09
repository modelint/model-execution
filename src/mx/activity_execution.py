""" activity_execution.py -- A metamodel Activity """

# System
import logging
from typing import TYPE_CHECKING, Callable, NamedTuple
from abc import ABC, abstractmethod
from collections import namedtuple

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relvar import Relvar
from pyral.relation import Relation
from pyral.database import Database
from pyral.rtypes import *

# MX
from mx.instance_set import InstanceSet
from mx.log_table_config import TABLE
from mx.message import *
from mx.actions.flow import ActiveFlow
from mx.actions.action_execution import ActionExecution
from mx.actions.traverse import Traverse
from mx.actions.rename import Rename
from mx.actions.scalar_switch import ScalarSwitch
from mx.actions.decision import Decision
from mx.actions.read import Read
from mx.actions.write import Write
from mx.actions.extract import Extract
from mx.actions.select import Select
from mx.actions.project import Project
from mx.actions.set_action import SetAction
from mx.actions.restrict import Restrict
from mx.actions.gate import Gate
from mx.actions.pass_action import PassAction  # Can't be 'Pass' since pass is a python keyword
from mx.actions.rank_restrict import RankRestrict
from mx.actions.signal import Signal
from mx.actions.method_call import MethodCall
from mx.db_names import mmdb
from mx.rvname import declare_rvs
from mx.mxtypes import ActionState, NamedValues
from mx.utility import *

_logger = logging.getLogger(__name__)

FromAction_t = namedtuple("FromAction_t", "From_action")

# Tuple generator and rv class for Metamodel Database (mmdb)
class MMRVs(NamedTuple):
    unexecuted_actions: str  # Unexecuted actions projected on ID
    unenabled_actions: str  # Remaining actions that are unenabled (U)
    flow_deps: str  # This activity's flow dependencies
    params: str
    activity_inputs: str
    disabled_flow: str
    downstream_actions: str
    gate_check: str
    newly_disabled: str
    gate_actions: str
    gate_upstream: str
    enabled_gate: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner,
                      "unexecuted_actions", "unenabled_actions", "flow_deps", "params", "activity_inputs",
                      "disabled_flow", "downstream_actions", "gatecheck", "newly_disabled", "gate_actions",
                      "gate_upstream", "enabled_gate"
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
        "pass": PassAction,
        "signal": Signal,
        "write": Write,
        "method call": MethodCall,
        "decision": Decision,
    }

    def __init__(self, domain: 'Domain', activity_label: str, anum: str, owner_name: str, activity_rvn: str,
                 signum: str, parameters: NamedValues):
        """

        Args:
            domain: The local domain object
            anum: This activity's identifier
            owner_name: String that uniquely identifies this activity and executing instance or rnum
            activity_rvn: Relational variable name holding this activity's metamodel data
            signum: The Activity's signature number (SIGnum)
            parameters: Possibly an empty dictionary of parameter values conforming to the Activity's signature
        """
        self.domain = domain
        self.system = domain.system
        self.label = activity_label
        self.anum = anum
        self.signum = signum
        self.parameters = parameters
        self.ready_actions: set[str] = set()

        # Flow content during this execution
        #   None - Flow has not been assigned a value yet
        #   ActiveFlow - Is the type ane value conveyed in the flow
        self.flows: dict[str, ActiveFlow | None] = {}
        # self.flows: dict[str, ActiveFlow | FlowState | None] = {}

        self.owner_name = owner_name
        self.mmrv = declare_mm_rvs(owner=self.owner_name)
        self.activity_rvn = activity_rvn
        log_table(_logger, table_msg(db=mmdb, variable_name=self.activity_rvn))

        # Here we create a temporary relvar in PyRAL to track the execution state of this Activity's Actions
        # during execution
        # We set the name of this relvar so we can access and update the relvar content
        self.action_states = Relation.declare_rv(db=mmdb, owner=self.owner_name, name="_Action_States")
        # And here we define the empty relvar in PyRAL
        Relvar.create_relvar(db=mmdb, name=self.action_states, attrs=[
            Attribute(name='ID', type='string'),
            Attribute(name='State', type='string'),
        ], ids={1: ['ID']})

        _logger.info(f"\n\n    vvv ({self.anum}) {self.label} Executing vvv \n")

        # Set the initial value of the relvar so that all actions, if any, are unenabled (U)
        if self.initialize_action_states():
            # Set any initially executable actions to enabled (E)
            self.enable_initial_actions()
            self.enable_initial_flows()
            self.execute()
        # Relation.free_rvs(db=mmdb, owner=self.owner_name)
        Relation.free_rvs(db=self.domain.alias, owner=snake(self.owner_name))
        r = Database.get_all_rv_names()
        # for k in r[self.domain.alias].keys():
        #     if k.startswith(snake(self.owner_name)):
        #         Relation.free_rvs(db=self.domain.alias, owner=k)
        #     pass
        q = Database.get_all_rv_names()
        _logger.info(f"\n\n    ^^^ ({self.anum}) {self.label} Complete ^^^ \n")
        pass

    @abstractmethod
    def initialize_action_states(self) -> bool:
        """
        Actions are looked up differently for each type of Activity (State, Method, ...)

        Returns:
            False if no actions are defined in the Activity
        """
        pass

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

        Returns:
            Name of the relvar showing the state of each of this Activity's Actions
        """
        mmrv = self.mmrv

        # Get all unexecuted actions
        Relation.restrict(db=mmdb, relation=self.action_states, restriction=ActionState.U)
        Relation.project(db=mmdb, attributes=("ID",), svar_name=mmrv.unexecuted_actions)

        # Determine which actions have their flows available initially and enable them
        #
        # Find all the actions that are dependent on flows from other actions
        # Subtract these dependent actions from our set of unexecuted (U) actions
        # and we get have set of non-dependent actions to enable (E)

        # Join the unexecuted actions with Flow Dependency on the To_action (flow destination)
        # to obtain all dependent actions
        R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
        Relation.restrict(db=mmdb, relation="Action", restriction=R)
        Relation.semijoin(db=mmdb, rname2='Flow Dependency',
                          attrs={'ID': 'To_action', 'Activity': 'Activity', 'Domain': 'Domain'},
                          svar_name=mmrv.flow_deps)  # We use this later to choose actions to enable
        # And now we just take the To_action column and rename it to ID to get something we can subtract
        Relation.project(db=mmdb, attributes=("To_action",))
        Relation.rename(db=mmdb, names={"To_action": "ID"})
        # We subtract these from the set of unexecuted actions to obtain those we need to enable
        enable_r = Relation.subtract(db=mmdb, rname1=mmrv.unexecuted_actions)
        # For each action to enable, we change its state from U (unexecuted) to E (enabled)
        for a in enable_r.body:
            Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': a['ID']}, update={'State': 'E'})

        log_table(_logger, table_msg(db=mmdb, variable_name=self.action_states))

    @abstractmethod
    def enable_xi_flow(self):
        pass

    def enable_initial_flows(self):
        """
        Set the value and type of each flow that is initially available (Executing instance, input parameter, etc)
        Initial flows such as executing instance, partitioning instance

        Returns:

        """
        _logger.info(f"Enabling initial flows")
        mmrv = self.mmrv
        domdb = self.domain.alias
        self.enable_xi_flow()

        # Any Scalar Value (constant) flows
        # These are flows whose value is specified in the activity such as 'Stop requested = TRUE'
        scalar_value_r = Relation.semijoin(db=mmdb, rname1=self.activity_rvn, rname2="Scalar Value")
        if scalar_value_r.body:
            sflow_r = Relation.join(db=mmdb, rname2="Scalar Flow")
            for sv_i in sflow_r.body:
                sv_flow_name = sv_i['ID']
                sval = sv_i['Name']
                sval_type = sv_i['Type']
                self.flows[sv_flow_name] = ActiveFlow(value=sval, flowtype=sval_type)
                _logger.info(f"initial Scalar Value Flow {sv_flow_name} set to value {sval} type {sval_type}")
                pass

        # All input parameter flows
        # We do a restrict using the signum to get the Activity's input params
        R = f"Signature:<{self.signum}>, Domain:<{self.domain.name}>"
        Relation.restrict(db=mmdb, relation='Parameter', restriction=R, svar_name=mmrv.params)
        # We do a join instead of a semijoin so we retain the Parameter.Type attribute in the result
        activity_input_r = Relation.join(db=mmdb, rname1=mmrv.params, rname2='Activity Input',
                                         attrs={'Name': 'Parameter', 'Signature': 'Signature', 'Domain': 'Domain'},
                                         svar_name=mmrv.activity_inputs)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.activity_inputs))

        # Enable input flow value
        _logger.info("Enabling input parameter flows...")
        for t in activity_input_r.body:
            pflow_name = t['Input_flow']
            param_name = t['Name']
            ptype = t['Type']
            self.flows[pflow_name] = self.parameters[param_name]
            if self.flows[pflow_name].flowtype == 'scalar':
                _logger.info(sflow_msg(flow_name=pflow_name, flow_dir=FlowDir.IN, flow_type=ptype, activity=self,
                                       value=self.flows[pflow_name].value))
            else:
                log_table(_logger, nsflow_msg(db=domdb, flow_name=pflow_name, flow_dir=FlowDir.IN, flow_type=ptype,
                                              activity=self, rv_name=self.flows[pflow_name].value))

        # Now check for any class accessor and set each such flow to the name of the accessed class
        class_accessor_r = Relation.semijoin(db=mmdb, rname1=self.activity_rvn, rname2="Class Accessor",
                                             attrs={'Activity': 'Activity', 'Domain': 'Domain'})
        for t in class_accessor_r.body:
            class_name = t["Class"]  # Class accessor is defined on this class
            # Declare an rv owned by the method to hold the class irefs
            # Note that the rv cannot have any spaces in its name
            class_accessor_drv = Relation.declare_rv(db=domdb, owner=self.owner_name,
                                                     name=f"{class_name.replace(' ', '_')}_class_accessor")
            # set it to an iref per instance in the class
            InstanceSet.irefs(db=domdb, iset_rv=class_name, irefs_rv=class_accessor_drv,
                              class_name=class_name, domain_name=self.domain.name)
            # Make it the value of the class accessor output flow
            self.flows[t["Output_flow"]] = ActiveFlow(value=class_accessor_drv, flowtype=class_name)

    def next_action(self) -> str | None:
        """
        Select the next action to execute and return its action id

        Returns:
            The action ID as a string
        """
        # Enabled actions are all actions in (E) state
        enabled_actions_r = Relation.restrict(db=mmdb, relation=self.action_states, restriction=ActionState.E)
        if not len(enabled_actions_r.body):
            # There are no more enabled actions to execute
            return None

        # There is at least one enabled action ready to go, chose any of them
        next_action_r = Relation.rank_restrict(db=mmdb, attr_name='ID', extent=Extent.LEAST, card=Card.ONE)
        next_action = next_action_r.body[0]["ID"]
        # Now change that action's status to X (executing)
        Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': next_action}, update={'State': 'X'})
        _logger.info(f"Next action selected")
        log_table(_logger, table_msg(db=mmdb, variable_name=self.action_states))
        return next_action

    def update_enabled_actions(self):
        """
        Having executed some action, check flow dependencies to determine if there are any
        actions that now have all of their required inputs enabled and add them to the set of
        enabled actions.
        """
        mmrv = self.mmrv

        # We change the state of the executed action to completed
        x_action_r = Relation.restrict(db=mmdb, relation=self.action_states, restriction=ActionState.X)
        x_action = x_action_r.body[0]['ID']
        Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': x_action}, update={'State': 'C'})
        log_table(_logger, table_msg(db=mmdb, variable_name=self.action_states))

        # Now we select any remaining unenabled actions to see if we can enable them
        Relation.restrict(db=mmdb, relation=self.action_states, restriction=ActionState.U,
                          svar_name=mmrv.unenabled_actions)

        if not Relation.cardinality(db=mmdb, rname=mmrv.unenabled_actions):
            # There are none, so we just proceed with activity execution
            return

        # For each U (uenabled action), get the set of From_actions from the Flow Dependency relvar.
        # If each of these actions has reached the C (completed) state, the unenabled action moves to the
        # E (enabled) state.

        # We only need the from and to actions from our flow dependencies for this Activity
        Relation.project(db=mmdb, relation=mmrv.flow_deps, attributes=("From_action", "To_action",),
                         svar_name=mmrv.flow_deps)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.unenabled_actions))
        # log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.flow_deps))

        # This is the summarize expression which defines a sequence of relational operations
        # that will be applied per each unenabled action id
        sum_expr = Relation.build_expr(commands=[
            # Summarize creates the "s" tuple to represent the current unenabled action
            # and we join it as the To action in the flow dep
            JoinCmd(rname1="s", rname2=mmrv.flow_deps, attrs={'ID': 'To_action'}),
            # We join the resulting relation to get all From actions that "s" is dependent on
            SemiJoinCmd(rname1=None, rname2=self.action_states, attrs={'From_action': 'ID'}),
            # We look through the resulting relation for any of these that have NOT completed execution
            RestrictCmd(relation=None, restriction="NOT State:C"),
            # We then take the cardinality of that output relation
            # 0 cardinality means that there are no uncompleted From Actions
            CardinalityCmd(rname=None)
        ])

        # For each unenabled action id, summarize extends our relation with a new "Complete" column
        # with the sum_expr output which will be the integer result of the cardinality operation
        Relation.summarize(db=mmdb, relation=mmrv.unenabled_actions, per_attrs=("ID",),
                           summaries=(SumExpr(attr=Attribute(name="Complete", type="int"), expr=sum_expr),))
        # Each unenabled action with 0 unexecuted From Actions, can be advanced to the E (enabled) state
        completed_from_actions_r = Relation.restrict(db=mmdb, restriction=f"Complete:<0>")
        for unenabled_action in completed_from_actions_r.body:
            # Mark it as enabled
            Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': unenabled_action["ID"]},
                             update={'State': 'E'})

        # The above process won't always enable a Gate Action
        # Get all unenabled gate actions
        # For each check to see if any upstream From action has completed
        # If so, enable the Gate Action
        Relation.extend(db=mmdb, relation=mmrv.unenabled_actions,
                        attrs={'Activity': self.anum, 'Domain':self.domain.name}, svar_name=mmrv.unenabled_actions)
        gate_actions_r = Relation.semijoin(db=mmdb, rname1=mmrv.unenabled_actions, rname2='Gate Action', svar_name=mmrv.gate_actions)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.gate_actions))

        for t in gate_actions_r.body:
            R = f"To_action:<{t['ID']}>"
            Relation.restrict(db=mmdb, relation=mmrv.flow_deps, restriction=R, svar_name=mmrv.gate_upstream)
            Relation.semijoin(db=mmdb, rname1=mmrv.gate_upstream, rname2=self.action_states,
                              attrs={'From_action': 'ID'}, svar_name=mmrv.gate_upstream)
            Relation.restrict(db=mmdb, relation=mmrv.gate_upstream, restriction=f"State:<C>",
                              svar_name=mmrv.enabled_gate)
            if Relation.cardinality(db=mmdb, rname=mmrv.enabled_gate):
                # Mark it as enabled
                Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': t['ID']},
                                 update={'State': 'E'})

        # And now the our action_states relvar has been updated with the latest newly enabled actions
        log_table(_logger, table_msg(db=mmdb, variable_name=self.action_states))

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
            ActivityExecution.execute_action[action_type](activity_execution=self, action_id=action_id)
            self.update_enabled_actions()
            pass
        pass

    def all_upstream_disabled(self, action_id: str) -> bool:
        """
        Return true if all upstream actions have been disabled.
        This is useful when deciding whether or not to disable a Gate Action.

        Args:
            action_id: Check upstream from this Action

        Returns:
            True if all upstream actions are disabled
        """
        mmrv = self.mmrv
        # Get all upstream actions
        Relation.restrict(db=mmdb, relation=mmrv.flow_deps, restriction=f"To_action:<{action_id}>",
                          svar_name=mmrv.gate_check)
        # log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.gate_check))
        # Obtain current action states for each
        Relation.semijoin(db=mmdb, rname1=mmrv.gate_check, rname2=self.action_states, attrs={"From_action": "ID"},
                          svar_name=mmrv.gate_check)
        # log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.gate_check))
        # Get all upstream action ids that are not disabled
        Relation.restrict(db=mmdb, relation=mmrv.gate_check, restriction="NOT State:<D>", svar_name=mmrv.gate_check)
        _logger.info(f"Gate should be disabled if ALL upstream Actions have been disabled")
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.gate_check, table_name="Non-disabled upstream Actions"))
        card = Relation.cardinality(db=mmdb, rname=mmrv.gate_check)
        # If there aren't any, it means they are all disabled
        # card 0 = False (all disabled) so we report True
        # card > 0 = True At least one not disabled, report False
        all_upstream_disabled = not bool(card)
        ua_msg = "upstream actions are disabled - "
        log_msg = f"All {ua_msg} disable the Gate Action" if all_upstream_disabled \
            else f"Not all {ua_msg} don't disable Gate Action"
        _logger.info(f"{log_msg} ")
        return all_upstream_disabled

    def disable_downstream_actions(self):
        """
        Disable all downstream actions.  These are available in the
        mmrv.downstream_actions relational variable
        """
        mmrv = self.mmrv

        # log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.downstream_actions))
        # Join with Action to obtain the type of each Action.  We'll be interested in Gate Actions later
        ds_actions_r = Relation.join(db=mmdb, rname1=mmrv.downstream_actions, rname2='Action',
                                     attrs={'Action': 'ID', 'Activity': 'Activity', 'Domain': 'Domain'},
                                     svar_name=mmrv.downstream_actions)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.downstream_actions))
        # log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.flow_deps))
        newly_disabled : list[FromAction_t] = []
        for t in ds_actions_r.body:
            if t['Type'] != 'gate' or t['Type'] == 'gate' and self.all_upstream_disabled(t['Action']):
                Relvar.updateone(db=mmdb, relvar_name=self.action_states, id={'ID': t['Action']}, update={'State': 'D'})
                newly_disabled.append(FromAction_t(From_action=t['Action']))

        Relation.create(db=mmdb, attrs=[Attribute(name="From_action", type="string")], tuples=newly_disabled,
                        svar_name=mmrv.newly_disabled)
        Relation.join(db=mmdb, rname1=mmrv.newly_disabled, rname2=mmrv.flow_deps, svar_name=mmrv.newly_disabled)
        Relation.extend(db=mmdb, attrs={'Activity': self.anum, 'Domain': self.domain.name},
                        relation=mmrv.newly_disabled, svar_name=mmrv.downstream_actions)
        Relation.rename(db=mmdb, relation=mmrv.downstream_actions, names={'To_action': 'Action'},
                        svar_name=mmrv.downstream_actions)
        Relation.project(db=mmdb, relation=mmrv.downstream_actions, attributes=("From_action",), exclude=True,
                         svar_name=mmrv.downstream_actions)
        # log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.downstream_actions))

        # Check recursion limit and return if there are no more downstream actions to disable
        if not Relation.cardinality(db=mmdb, rname=mmrv.downstream_actions):
            return

        self.disable_downstream_actions()