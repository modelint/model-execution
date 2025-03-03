""" life_cycle_state_machine.py """

# MX
from mx.state_machine import StateMachine


class LifecycleStateMachine(StateMachine):

    instance_id = None
    class_name = None
    domain = None

    def __init__(self, current_state: str, instance_id: str, class_name: str, domain: str):
        super().__init__(current_state=current_state)

        self.instance_id = instance_id
        self.class_name = class_name
        self.domain = domain
