""" operation.py -- Bridgeable operation """

# System
from typing import Any
import logging

# Model Integration
from pyral.relation import Relation

# Model Execution
from mx.db_names import udb, mmdb
from mx.exceptions import *

_logger = logging.getLogger(__name__)

class Operation:
    """
    Andrew's notes on implicit bridging define a set of bridging operations that may be invoked in a terminal domain
    as a consequence of a bridgeable condition occuring in an originating domain.

    Each method on this class defines one of those possible operations such as:
        signal_event, update_attribute, migrate_class, etc.
    """

    @classmethod
    def signal_event(cls, event_spec: str, domain:str, class_name:str, instance_id: dict[str, Any], params: dict[str, Any]):
        """
        Ex: Floor_call

        Create an imminent event and put it in the proper queue

        :param event_spec:
        :param domain:
        :param class_name:
        :param instance_id:
        :param params:
        """
        # Lookup instance in populated metamodel and fail if it does not exist
        R = f"Name:<{event_spec}>, State_model:<{class_name}>, Domain:<{domain}>"
        result = Relation.restrict(db=mmdb, relation='Event_Specification', restriction=R)

        # Lookup state machine object using the instance_id and the state_machine sm_id_map dict
        #   And fail if the state machine does not exist

        # Create an instance of non-self-directed dispatched event for that state machine



        pass

