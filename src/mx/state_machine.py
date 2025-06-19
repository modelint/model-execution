""" state_machine.py """

# System
import logging
import random
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relation import Relation

# MX
from mx.exceptions import *
from mx.db_names import mmdb
from mx.interaction_event import InteractionEvent
from mx.completion_event import CompletionEvent
from mx.completion_event import DispatchedEvent


class EventResponse(Enum):
    TRANSITION = 1
    IGNORE = 2
    CANT_HAPPEN = 3


_logger = logging.getLogger(__name__)

sm_id_map = {}  # Map of identifier values to state machine instances


class StateMachine:

    def __init__(self, current_state: str, state_model: str, domain: "Domain"):
        """
        Initialize a state machine with a current state

        :param current_state: The statemachine is in this state when created
        """
        self.activity_executing = False
        self.current_state = current_state
        self.interaction_events: list[InteractionEvent] = []
        self.completion_events: list[CompletionEvent] = []
        self.dest_state = None
        self.active_event = None
        self.state_model = state_model
        self.domain = domain
        self.int_processed = 0
        self.comp_processed = 0
        self.max_int_events = 0
        self.max_comp_events = 0
        self.active_event = None

    # def accept_event_from_self(self, event: DispatchedEvent):
    #     """
    #     New SelfDirected event received, queue it
    #
    #     :param event: A dispatched self-directed event
    #     """
    #     self.completion_events.append(event)

    @property
    def busy(self) -> bool:
        return self.interaction_events or self.completion_events or self.activity_executing

    def go(self, max_int_events: int = 0, max_comp_events: int = 0):
        """
        Process up to the maximum number of allowed events

        :param max_int_events: Maximum interaction events to process, 0 means no limit (all)
        :param max_comp_events: Maximum completion events to process, 0 means no limit (all)
        """

        self.max_int_events = max_int_events
        self.max_comp_events = max_comp_events
        # Reset counter
        self.comp_processed = 0
        self.int_processed = 0

        while self.completion_events or self.interaction_events:
            # Keep processing events until none are left or the max events in either cateogry is reached
            if (0 < max_int_events <= self.int_processed) or\
                    (0 < max_comp_events <= self.max_comp_events):
                return len(self.completion_events) + len(self.interaction_events)

            self.process_event()

    def process_event(self):
        self.active_event = self.select_next_event()
        if not self.active_event:
            return

        # Check for transition
        R = (f"From_state:<{self.current_state}>, Event:<{self.active_event.event_spec}>, "
             f"State_model:<{self.state_model}>, Domain:<{self.domain.name}>")
        transition_r = Relation.restrict(db=mmdb, relation="Transition", restriction=R)
        if transition_r.body:
            to_state = transition_r.body[0]["To_state"]
            pass
        pass






    def select_next_event(self) -> DispatchedEvent | None:
        """
        Returns a Dispatched Event if one is pending
        """
        return (
            self.completion_events.pop(0)
            if self.completion_events else
            self.interaction_events.pop(0)
            if self.interaction_events else
            None
        )


    def accept_interaction_event(self, event: InteractionEvent):
        """
        New NonSelfDirected event received, queue it

        :param event: A dispatched non-self-directed event
        """
        self.interaction_events.append(event)
        self.domain.events_pending = True

    def check_input(self) -> bool:
        """
        Select a pending event, if any

        :return: True if an event was selected
        """
        if self.completion_events:
            self.active_event = self.completion_events.pop(0)
            return True

        if self.interaction_events:
            self.active_event = random.choice(self.interaction_events)
            # self.active_event = self.interaction_events.pop(0) TODO: Make this an option
            return True

        return False

    def transition(self, dest_state: str):
        self.dest_state = dest_state
        # start activivity execution and wait for completion

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
