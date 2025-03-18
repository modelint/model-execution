""" assigner_state_machine.py """

# MX
from mx.state_machine import StateMachine


class AssignerStateMachine(StateMachine):

    def __init__(self, current_state: str, rnum: str, domain: str):

        super().__init__(current_state=current_state, state_model=rnum, domain=domain)

        self.rnum = rnum