""" state_activity.py -- A metamodel StateActivity """

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.state_machine import StateMachine

# MX
from mx.activity import Activity


class StateActivity(Activity):

    # def __init__(self, state: str, state_model: str, domain: str):
    def __init__(self, anum: str, state_machine: "StateMachine"):

        self.state_machine = state_machine
        super().__init__(xe=state_machine.domain.system.xe, domain=state_machine.domain.name, anum=anum,
                         parameters=state_machine.active_event.params)
        pass

    def execute(self):
        pass
