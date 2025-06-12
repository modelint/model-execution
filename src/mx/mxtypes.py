""" mxtypes.py -- Named tuples to support model execution """


# System
from typing import NamedTuple, Dict, Any, TypeAlias

# Used any time we have a set of named values such as a set of identifier attribute values
# parameter values, or any other set of attribute values
NamedValues: TypeAlias = Dict[str, Any]
