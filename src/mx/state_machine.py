""" state_machine.py """

# System
import logging
import random
from enum import Enum

# Model Integration
from pyral.relation import Relation

# MX
from mx.exceptions import *
from mx.db_names import mmdb
from mx.dispatched_event import DispatchedEvent


class EventResponse(Enum):
    TRANSITION = 1
    IGNORE = 2
    CANT_HAPPEN = 3


_logger = logging.getLogger(__name__)

sm_id_map = {}  # Map of identifier values to state machine instances


class StateMachine:

    def __init__(self, current_state: str, state_model: str, domain: str):
        """
        Initialize a state machine with a current state

        :param current_state: The statemachine is in this state when created
        """
        self.current_state = current_state
        self.non_self_directed_events: list[DispatchedEvent] = []
        self.self_directed_events: list[DispatchedEvent] = []
        self.dest_state = None
        self.active_event = None
        self.state_model = state_model
        self.domain = domain

    def accept_event_from_self(self, event: DispatchedEvent):
        """
        New SelfDirected event received, queue it

        :param event: A dispatched self-directed event
        """
        self.self_directed_events.append(event)

    def accept_event_not_from_self(self, event: DispatchedEvent):
        """
        New NonSelfDirected event received, queue it

        :param event: A dispatched non-self-directed event
        """
        self.non_self_directed_events.add(event)

    def check_input(self) -> bool:
        """
        Select a pending event, if any

        :return: True if an event was selected
        """
        if self.self_directed_events:
            self.active_event = self.self_directed_events.pop(0)
            return True

        if self.non_self_directed_events:
            self.active_event = random.choice(self.non_self_directed_events)
            # self.active_event = self.non_self_directed_events.pop(0) TODO: Make this an option
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
             f"Domain:<{self.domain}>")
        result = Relation.restrict(db=mmdb, relation='Transition', restriction=R)
        if result.body:
            # There is a transition specified
            self.transition(dest_state=result.body[0]['To_state'])
            return EventResponse.TRANSITION

        R = (f"From_state:<{self.current_state}>, Event:<{self.active_event}>, State_model:<{self.state_model}>, "
             f"Domain:<{self.domain}>")
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
