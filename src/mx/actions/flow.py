""" flow.py -- Active Flow type """

# System
from typing import NamedTuple, Any

class ActiveFlow(NamedTuple):
    value: Any
    flowtype: str

