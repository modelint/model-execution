""" mxtypes.py -- Named tuples to support model execution """


# System
from typing import NamedTuple, Dict, Any, TypeAlias, Union
from collections import namedtuple
from enum import Enum

InstanceAddress = namedtuple('mx_InstanceAddress', 'domain class_name instance_id')
AssignerAddress = namedtuple('mx_AssignerAddress', 'domain rel_name instance_id')
ExternalAddress = namedtuple('mx_ExternalAddress', 'domain')
ElementAddress = Union[InstanceAddress, AssignerAddress, ExternalAddress]

# Used any time we have a set of named values such as a set of identifier attribute values
# parameter values, or any other set of attribute values
NamedValues: TypeAlias = Dict[str, Any]

class StateMachineType(Enum):
    LIFECYCLE = 1
    SA = 2
    MA = 3

def snake(name: str) -> str:
    return name.replace(' ', '_')
