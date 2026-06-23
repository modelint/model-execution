""" mxtypes.py -- Named tuples to support model execution """

# System
from typing import NamedTuple, Dict, Any, TypeAlias, Union
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum, StrEnum

SM_State = namedtuple('SM_State', 'state_model instance state')
SM_Pending = namedtuple('SM_Pending', 'instance interaction completion')
SM_Interactive = namedtuple('SM_Interactive', 'source event_name params arrival_time')
SM_Completion = namedtuple('SM_Completion', 'event_name params arrival_time')

class ActionType(Enum):
    SIGNAL_INSTANCE = "signal instance"
    EXTERNAL_EVENT = "external event"

class Direction(Enum):
    STIMULUS = "stimulus"
    RESPONSE = "response"

class SuspendStatus(Enum):
    """
    Reasons why the system has stopped running
    """
    MONITOR_TRIPPED = "monitor tripped"  # An monitored condition or response was detected
    TERMINAL_CONDITION = "terminal condition"  # The system has entered a terminal state

# Map python to MX base scalar types
SCALAR_TYPE = {
    bool: 'Boolean',
    int: 'Integer',
    float: 'Float',
    str: 'String'
}

class ActionState(StrEnum):
    U = "State:U"  # Unexecuted action
    E = "State:E"  # Enabled action
    X = "State:X"  # Executing action
    C = "State:C"  # Completed action
    D = "State:D"  # Disabled action


InstanceAddress = namedtuple('mx_InstanceAddress', 'domain class_name instance_id')
AssignerAddress = namedtuple('mx_AssignerAddress', 'domain rel_name instance_id')
ExternalAddress = namedtuple('mx_ExternalAddress', 'domain')
ElementAddress = Union[InstanceAddress, AssignerAddress, ExternalAddress]

# Announcements
ExternalEvent_Announcement = namedtuple('mx_ExternalEvent_Announcement', 'domain ee source inst event params')
InteractionSignal_Announcement = namedtuple('mx_InteractionSignal_Announcement', 'domain sm inst event params')
Announcement = Union[ExternalEvent_Announcement, InteractionSignal_Announcement]

# Used any time we have a set of named values such as a set of identifier attribute values
# parameter values, or any other set of attribute values
NamedValues: TypeAlias = Dict[str, Any]

@dataclass(frozen=True)
class Interaction:
    """
    We use this to package up stimulus and response data loaded from a yaml scenario file
    for interaction with the MX.
    """
    description: str            # User friendly purpose or context of the interaction
    delay: float                # Wait before triggering this Stimulus (ignored for responses)
    direction: Direction        # Stimulus or Response (input or output) with respect to the MX
    action: ActionType          # MX action that injects or reports the interaction
    name: str                   # Name of the specific action (event name, domain operation, etc)
    source: ElementAddress      # Model address of any emitter/receiver:  instance, domain, assigner, etc
    source_actor: str           # ID used by mdb to name the source for formatted output
    target: ElementAddress      # Same as source field
    target_actor: str           # ID used by mdb to name the source for formatted output
    parameters: NamedValues     # Parameters, empty if none or not relevant to the acion type

class StateMachineType(Enum):
    LIFECYCLE = 1
    SA = 2
    MA = 3


def snake(name: str) -> str:
    return name.replace(' ', '_')
