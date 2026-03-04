""" mdb_types.py -- Temporary home for mdb types while debugging """

# System
from typing import Union
from collections import namedtuple
from enum import Enum

class ActionType(Enum):
    SIGNAL_INSTANCE = "SIGNAL_INSTANCE"
    EXTERNAL_EVENT = "EXTERNAL_EVENT"

class Direction(Enum):
    STIMULUS = "STIMULUS"
    RESPONSE = "RESPONSE"


Interaction = namedtuple('mdb_Interaction', 'direction action name source target parameters')
InstanceAddress = namedtuple('mdb_Interaction', 'domain class_name instance_id')
AssignerAddress = namedtuple('mdb_AssignerAddress', 'domain rel_name instance_id')
ExternalAddress = namedtuple('mdb_ExternalAddress', 'domain')
ElementAddress = Union[InstanceAddress, AssignerAddress, ExternalAddress]