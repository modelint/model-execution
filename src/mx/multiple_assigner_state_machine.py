""" multiple_assigner_state_machine.py """

# System
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relation import Relation

# MX
from mx.assigner_state_machine import AssignerStateMachine
from mx.mxtypes import StateMachineType


class MultipleAssignerStateMachine(AssignerStateMachine):

    def __init__(self, ma_sm_id: int, current_state: str, rnum: str, domain: "Domain", instance_id: dict[str, Any],
                 pclass_name: str):

        super().__init__(sm_id=f"ma_{ma_sm_id}", current_state=current_state, rnum=rnum, sm_type=StateMachineType.MA,
                         domain=domain)

        self.instance_id = instance_id
        self.pclass_name = pclass_name
