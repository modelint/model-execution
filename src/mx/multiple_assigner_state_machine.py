""" multiple_assigner_state_machine.py """

# System
from typing import Any

# MX
from mx.assigner_state_machine import AssignerStateMachine


class MultipleAssignerStateMachine(AssignerStateMachine):

    def __init__(self, current_state: str, rnum: str, domain: str, instance_id: dict[str, Any], pclass_name: str):

        super().__init__(current_state=current_state, rnum=rnum, domain=domain)

        self.instance_id = instance_id
        self.pclass_name = pclass_name
