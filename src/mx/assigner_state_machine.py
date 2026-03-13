""" assigner_state_machine.py """

# System
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# MX
from mx.state_machine import StateMachine
from mx.mxtypes import StateMachineType

class AssignerStateMachine(StateMachine):

    def __init__(self, sm_id: str, current_state: str, rnum: str, sm_type: StateMachineType, domain: "Domain"):

        super().__init__(sm_id=sm_id, current_state=current_state, state_model=rnum, sm_type=sm_type, domain=domain)

