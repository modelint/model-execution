""" single_assigner_state_machine.py """

# MX
from mx.assigner_state_machine import AssignerStateMachine


class SingleAssignerStateMachine(AssignerStateMachine):

    def __init__(self, current_state: str, rnum: str, domain: str):

        super().__init__(current_state=current_state, domain=domain)

        self.state_model = rnum