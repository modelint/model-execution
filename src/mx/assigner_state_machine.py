""" assigner_state_machine.py """

# MX
from mx.state_machine import StateMachine


class AssignerStateMachine(StateMachine):

    rnum = None
    domain = None
    instance_id = None
    class_name = None

    def __init__(self, current_state: str, rnum: str, domain: str, sm_type: StateMachineType, currnt_state: str,
                 instance_id: str = None, class_name: str = None):

        super().__init__(current_state=current_state)

        self.rnum = rnum
        self.domain = domain
        self.instance_id = instance_id
        self.class_name = class_name