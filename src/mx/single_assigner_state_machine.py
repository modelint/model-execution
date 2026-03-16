""" single_assigner_state_machine.py """

# System
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# MX
from mx.assigner_state_machine import AssignerStateMachine
from mx.mxtypes import StateMachineType


class SingleAssignerStateMachine(AssignerStateMachine):

    def __init__(self, sa_sm_id: int, current_state: str, rnum: str, domain: "Domain"):

        super().__init__(assigner_sm_id=f"sa_{sa_sm_id}", current_state=current_state, rnum=rnum,
                         sm_type=StateMachineType.SA, domain=domain)
