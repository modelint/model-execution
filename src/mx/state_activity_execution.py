""" state_activity_execution.py -- A metamodel StateActivity """

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mx.state_machine import StateMachine

# Model Integration
from pyral.relation import Relation
from pyral.database import Database

# MX
from mx.activity_execution import ActivityExecution
from db_names import mmdb

class StateActivityExecution(ActivityExecution):

    def __init__(self, anum: str, state_machine: "StateMachine"):

        self.state_machine = state_machine
        super().__init__(domain=state_machine.domain, anum=anum,
                         parameters=state_machine.active_event.params)

        self.owner_name = None
        self.xi_flow = None
        from mx.lifecycle_state_machine import LifecycleStateMachine
        if isinstance(self.state_machine, LifecycleStateMachine):
            instance_id_value = '_'.join(v for v in self.state_machine.instance_id.values())
            self.owner_name = f"{self.anum}_{instance_id_value}"
            R = f"Anum:<{self.anum}>, Domain:<{self.domain.name}>"
            lifecycle_activity_r = Relation.restrict(db=mmdb, relation="Lifecycle Activity", restriction=R)
            self.xi_flow = lifecycle_activity_r.body[0]["Executing_instance_flow"]
        else:
            # TODO: Implement for assigner and multiple assigner
            pass
        self.state_rvname = Relation.declare_rv(db=mmdb, owner=self.owner_name, name="state_name")
        self.execute()
        # Relation.free_rvs(db=mmdb, owner=self.owner_name)
        # Relation.free_rvs(db=self.domain.alias, owner=self.owner_name)

        self.execute()
