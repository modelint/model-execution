""" assigner_state_machine.py """

# System
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# MX
from mx.state_machine import StateMachine
from mx.mxtypes import StateMachineType

class AssignerStateMachine(StateMachine):

    def __init__(self, assigner_sm_id: str, current_state: str, rnum: str, sm_type: StateMachineType, domain: "Domain"):

        # Owner name is prefixed with the state machine type
        rv_owner = f"Assigner_SM_{assigner_sm_id}"

        super().__init__(sm_id=assigner_sm_id, rv_owner=rv_owner, current_state=current_state, state_model=rnum, sm_type=sm_type, domain=domain)
        self.rnum = rnum

