""" life_cycle_state_machine.py """

# System
from typing import Any

# MX
from mx.state_machine import StateMachine


class LifecycleStateMachine(StateMachine):

    instance_id = None
    class_name = None
    domain = None

    def __init__(self, current_state: str, instance_id: dict[str, Any], class_name: str, domain: str):
        super().__init__(current_state=current_state, state_model=class_name, domain=domain)

        self.instance_id = instance_id
        self.class_name = class_name
        pass
