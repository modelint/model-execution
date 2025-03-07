""" ee.py -- External Entity """

from typing import Any

class EE:
    """
    An External Entity (EE) as defined in the SM Metamodel

    Defines a set of operations that correspond to bridging conditions in an external domain.

    Each operation will take the input data, identify the target instance and perform its function.

    We presume that the relevant target instances have been wired up accordingly.
    """

    def __init__(self, name:str, class_name:str):
        """
        We create one of these per instance of External Entity defined in the populated metamodel
        :param name: The all caps EE External Entity (EE) name such as CABIN, SHAFT, DOOR, etc.
        :param class_name: The EE is a proxy for this Class: Cabin, Shaft, Door, etc.
        """
        self.name = name
        self.class_name = class_name

    def signal(self, class_name:str, instance_id: dict[str, Any], event_spec: str, params: dict[str, Any]):
        """
        Create an event and put it in the proper queque

        :param event_spec:
        :param class_name:
        :param instance_id:
        :param operation:
        :param params:
        :return:
        """
        # Lookup instance in populated metamodel and fail if it does not exist

        # Lookup state machine object using the instance_id and the state_machine sm_id_map dict
        #   And fail if the state machine does not exist

        # Create an instance of non-self-directed dispatched event for that state machine



        pass

