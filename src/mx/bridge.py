""" bridge.py -- Named tuples to support domain interactions """

# Thank to Andrew for this idea

# System
from typing import NamedTuple, Dict, Any, TypeAlias

# Used any time we have a set of named values such as a set of identifier attribute values
# parameter values, or any other set of attribute values
NamedValues: TypeAlias = Dict[str, Any]


# Model operations
class MXSignalEvent(NamedTuple):
    ee: str | None
    source: NamedValues | None
    event_spec: str
    state_model: str
    params: NamedValues
    instance: NamedValues


class MXCallMethod(NamedTuple):
    ee: str | None  # Name of target EE if called from outside the domain
    source: NamedValues | None
    method: str
    class_name: str
    params: NamedValues
    instance: NamedValues


ModeledOperation: TypeAlias = MXSignalEvent | MXCallMethod


# Bridgeable conditions
class MXLifecycleStateEntered(NamedTuple):
    instance: NamedValues
    state: str
    state_model: str


BridgeableCondition: TypeAlias = MXLifecycleStateEntered
