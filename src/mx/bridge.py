""" bridge.py -- Named tuples to support domain interactions """

# Thank to Andrew for this idea

# System
from typing import NamedTuple, Dict, Any, TypeAlias



# Model operations
MXSignalEvent = NamedTuple('MXSignalEvent', op=str | None, source=Dict[str, Any] | None, event_spec=str,
                           state_model=str, domain=str,
                           params=Dict[str, Any], instance=Dict[str, Any])

MXCallMethod = NamedTuple('MXCallMethod', op=str | None, source=Dict[str, Any] | None, method=str,
                          class_name=str, domain=str,
                          params=Dict[str, Any], instance=Dict[str, Any])

ModeledOperation: TypeAlias = MXSignalEvent | MXCallMethod

# Bridgeable conditions
MXLifecycleStateEntered = NamedTuple('MXStateEntered', instance=Dict[str, Any], state=str, state_model=str, domain=str)

BridgeableCondition: TypeAlias = MXLifecycleStateEntered


