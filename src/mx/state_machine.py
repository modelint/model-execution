""" state_machine.py """

# System
import logging
import random
from collections import defaultdict
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relvar import Relvar
from pyral.relation import Relation
from pyral.database import Database
from pyral.rtypes import *

# MX
from mx.exceptions import *
from mx.db_names import mmdb
from mx.interaction_event import InteractionEvent
from mx.completion_event import CompletionEvent
from mx.dispatched_event import DispatchedEvent
from mx.state_activity_execution import StateActivityExecution
from mx.mxtypes import StateMachineType
from mx.message import *


class EventResponse(Enum):
    TRANSITION = 1
    IGNORE = 2
    CANT_HAPPEN = 3


_logger = logging.getLogger(__name__)

sm_id_map = {}  # Map of identifier values to state machine instances


class StateMachine:

    def __init__(self, sm_id: str, rv_owner: str, current_state: str, state_model: str, sm_type: StateMachineType, domain: "Domain"):
        """
        Initialize a state machine with a current state

        Args:
            sm_id:
            current_state: The statemachine is in this state when created
            state_model:
            domain:
        """
        self.sm_id = sm_id  # State machine id (unique across all state machine types in this domain)
        self.rv_owner = rv_owner
        self.sm_type = sm_type
        self.activity_executing = False
        self.current_state = current_state
        self.interaction_events: list[InteractionEvent] = []
        self.completion_event: CompletionEvent | None = None
        self.active_event = None
        self.state_model = state_model
        self.domain = domain
        self.int_processed = 0
        self.comp_processed = 0
        self.max_int_events = 0
        self.max_comp_events = 0
        self.active_event = None
        self.actions = defaultdict(str)

        # Define an action_states relvar per Real State

        # Find all Real States for this State Machine's State Model
        # Only (Real States) execute Actions
        R = f"State_model:<{self.state_model}>, Domain:<{self.domain.name}>"
        real_state_r = Relation.restrict(db=mmdb, relation="Real State", restriction=R)
        initial_states_rv = Relation.declare_rv(db=mmdb, owner=self.rv_owner, name="initial_sa_relation")
        for s in real_state_r.body:
            state_anum = s["Activity"]
            state_name = s["Name"]
            # Get all Actions in this State Activity, if any
            R = f"Activity:<{state_anum}>, Domain:<{self.domain.name}>"
            state_action_r = Relation.restrict(db=mmdb, relation="Action", restriction=R, svar_name="actions")
            if state_action_r.body:
                # There are actions in this Real State
                # Create a relation and set the execution state of each Action to (U) - unexecuted
                Relation.project(db=mmdb, attributes=("ID",))
                Relation.extend(db=mmdb, attrs={'State': 'U'}, svar_name=initial_states_rv)
                # The relvar name must be unique to each state and instance of this state machine
                # So we use the activity number, this state machine's instance specific owner name
                # The state name at the end isn't necessary since we have the anum, but aids in readability
                relvar_name = f"Activity_{state_anum}_{self.rv_owner}_{state_name}"
                Relvar.create_relvar(db=mmdb, name=relvar_name, attrs=[
                    Attribute(name='ID', type='string'),
                    Attribute(name='State', type='string'),
                ], ids={1: ['ID']})
                # Set the initial value of the relvar to
                Relvar.set(db=mmdb, relvar=relvar_name, relation=initial_states_rv)
                self.actions[state_anum] = relvar_name
        Relation.free_rvs(db=mmdb, owner=rv_owner, names=("initial_sa_relation",))

    def accept_completion_event(self, event: CompletionEvent):
        """
        New Completion event received. Only one may be pending at a time,
        so we throw an exception if we already have one.

        Args:
            event: A dispatched completion event
        """
        pass
        if self.completion_event:
            msg = f"Completion event dispatch while completion event already pending for state machine"
            _logger.error(msg)
            raise MXStateMachineException(msg)

        # Otherwise, accept the completion event
        self.completion_event = event
        pass

    @property
    def busy(self) -> bool:
        return self.interaction_events or self.completion_event or self.activity_executing

    def go(self, max_int_events: int = 0, max_comp_events: int = 0):
        """
        Process up to the maximum number of allowed events

        Args:
            max_int_events: Maximum interaction events to process, 0 means no limit (all)
            max_comp_events: Maximum completion events to process, 0 means no limit (all)

        Returns:

        """
        match self.sm_type:
            case StateMachineType.LIFECYCLE:
                sm_info = f"{self.sm_type.name}: {self.state_model} [{self.current_state}] <{self.instance_id}>"
            case StateMachineType.MA:
                sm_info = f"{self.sm_type.name}: {self.state_model} [{self.current_state}] P<{self.instance_id}>"
            case StateMachineType.SA:
                sm_info = f"{self.sm_type.name}: {self.state_model} [{self.current_state}]"

        _logger.info(f"{sm_info} checking events")

        self.max_int_events = max_int_events
        self.max_comp_events = max_comp_events
        # Reset counter
        self.comp_processed = 0
        self.int_processed = 0

        while self.completion_event or self.interaction_events:
            # Keep processing events until none are left or the max events in either cateogry is reached
            if (0 < max_int_events <= self.int_processed) or (0 < max_comp_events <= self.max_comp_events):
                comp_event = 1 if self.completion_event else 0
                return len(self.interaction_events) + comp_event
            self.process_event()

    def process_event(self):
        self.active_event = self.select_next_event()
        if not self.active_event:
            return

        _logger.info(f"Active event: {self.active_event.event_spec}")

        # Check for transition
        transition_rv = Relation.declare_rv(db=mmdb, owner=self.rv_owner, name="transition")
        R = (f"From_state:<{self.current_state}>, Event:<{self.active_event.event_spec}>, "
             f"State_model:<{self.state_model}>, Domain:<{self.domain.name}>")
        transition_r = Relation.restrict(db=mmdb, relation="Transition", restriction=R,
                                         svar_name=transition_rv)
        if transition_r.body:
            self.transition(transition_rv=transition_rv)
        else:
            # Process non-transition
            R = (f"State:<{self.current_state}>, Event:<{self.active_event.event_spec}>, "
                 f"State_model:<{self.state_model}>, Domain:<{self.domain.name}>")
            non_transition_r = Relation.restrict(db=mmdb, relation="Transition", restriction=R)
            if not non_transition_r:
                pass  # TODO: This is an exception, bad mmdb_elevator data

            # TODO: Process ignore or can't happen behavior
            pass

        # Delete Active Event
        self.active_event = None
        pass

    def select_next_event(self) -> DispatchedEvent | None:
        """
        Select the next Active Event to process.
        Always select the Completion Event if one is pending.
        Otherwise, any pending Interaction Event may be selected.

        Returns:
            Dispatched Event if one is pending, otherwise None
        """
        if self.completion_event:
            active_event = self.completion_event
            self.completion_event = None
            return active_event

        if self.interaction_events:
            return self.interaction_events.pop(0)

    def accept_interaction_event(self, event: InteractionEvent):
        """
        New NonSelfDirected event received, queue it

        :param event: A dispatched non-self-directed event
        """
        _logger.info(f"Event {event.event_spec} dispatched to <{self.instance_id}>")
        self.interaction_events.append(event)
        _logger.info(f"Interaction events pending: {len(self.interaction_events)}")
        self.domain.events_pending = True

    def transition(self, transition_rv: str):
        dest_real_state_r = Relation.semijoin(db=mmdb, rname1=transition_rv, rname2="Real State",
                                              attrs= {"To_state": "Name", "State_model": "State_model",
                                                      "Domain": "Domain"})
        Relation.free_rvs(db=mmdb, owner=self.rv_owner, names=("transition",))
        dest_real_state_t = dest_real_state_r.body[0]
        self.current_state = dest_real_state_t["Name"]
        msg = f"transitioning to [{self.current_state}]"
        _logger.info(msg)
        StateActivityExecution(anum=dest_real_state_t["Activity"], state_machine=self)
        pass
        # start activity execution and wait for completion

    def ignore(self):
        """
        Process an ignore event response
        """
        pass

    def cant_happen(self):
        """
        Process a cant happen event response
        """
        pass

    def process_active_event(self) -> EventResponse:
        """
        For the active event, determine the response: Transition, Ignore, or Can't Happen
        and invoke the corresponding method

        :return:
        """
        # Look up the response in the mmdb
        R = (f"From_state:<{self.current_state}>, Event:<{self.active_event}>, State_model:<{self.state_model}>, "
             f"Domain:<{self.domain.name}>")
        result = Relation.restrict(db=mmdb, relation='Transition', restriction=R)
        if result.body:
            # There is a transition specified
            self.transition(dest_state=result.body[0]['To_state'])
            return EventResponse.TRANSITION

        R = (f"From_state:<{self.current_state}>, Event:<{self.active_event}>, State_model:<{self.state_model}>, "
             f"Domain:<{self.domain.name}>")
        result = Relation.restrict(db=mmdb, relation='Non_Transition', restriction=R)
        if not result.body:
            # There must be a response defined for every event defined on a statemodel
            msg = (f"No event response defined for event [{self.active_event.event_spec}] received in "
                   f"state [{self.current_state}] while executing state machine [{self.state_model}")
            _logger.exception(msg)
            raise MXStateMachineException(msg)

        nt_response = result.body[0]['Behavior']
        if nt_response == 'ignore':
            self.ignore()
            return EventResponse.IGNORE

        if nt_response == 'cant happen':
            self.cant_happen()
            return EventResponse.CANT_HAPPEN

        msg = (f"Behavior specifed by Non Transition in metamodel is neither ignore or can't happen for "
               f"state [{self.current_state}] while executing state machine [{self.state_model}")
        _logger.exception(msg)
        raise MXStateMachineException(msg)
