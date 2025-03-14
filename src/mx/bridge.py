""" bridge.py -- Named tuples to support domain interactions """

# System
from typing import NamedTuple, Dict, Any

# Bridge operations
MXSignalEvent = NamedTuple('MXSignalEvent', op=str | None, source=Dict[str, Any] | None, event_spec=str,
                           state_model=str, domain=str,
                           params=Dict[str, Any], instance=Dict[str, Any])

# Bridgeable conditions
MXLifecycleStateEntered = NamedTuple('MXStateEntered', instance=Dict[str, Any], state=str, state_model=str, domain=str)

