""" state_activity_execution.py -- A metamodel StateActivity """

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.state_machine import StateMachine

# MX
from mx.activity_execution import ActivityExecution


class StateActivityExecution(ActivityExecution):

    def __init__(self, anum: str, state_machine: "StateMachine"):

        self.state_machine = state_machine
        super().__init__(domain=state_machine.domain, anum=anum,
                         parameters=state_machine.active_event.params)

        pass
        self.execute()

    def execute(self):
        a = self.next_action()
        pass
