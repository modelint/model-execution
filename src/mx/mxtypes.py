""" mxtypes.py -- Named tuples to support model execution """


# System
from typing import NamedTuple, Dict, Any, TypeAlias
from enum import Enum

# Used any time we have a set of named values such as a set of identifier attribute values
# parameter values, or any other set of attribute values
NamedValues: TypeAlias = Dict[str, Any]

class StateMachineType(Enum):
    LIFECYCLE = 1
    SA = 2
    MA = 3

def snake(name: str) -> str:
    return name.replace(' ', '_')
