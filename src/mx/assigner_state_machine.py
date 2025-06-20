""" assigner_state_machine.py """

# MX
from mx.state_machine import StateMachine


class AssignerStateMachine(StateMachine):

    def __init__(self, sm_id: str, current_state: str, rnum: str, domain: str):

        super().__init__(sm_id=sm_id, current_state=current_state, state_model=rnum, domain=domain)

        self.rnum = rnum