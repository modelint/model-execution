""" dc_creation_activity.py -- A metamodel Delegated Creation Activity """
import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relvar import Relvar
from pyral.relation import Relation
from pyral.database import Database

# MX
from mx.log_table_config import TABLE
from mx.message import *
from mx.actions.flow import ActiveFlow
from mx.activity_execution import ActivityExecution
from mx.lifecycle_state_machine import LifecycleStateMachine
from mx.mxtypes import StateMachineType
from mx.utility import *
from mx.db_names import mmdb
from mx.mxtypes import NamedValues

_logger = logging.getLogger(__name__)

class DelegatedCreationActivity(ActivityExecution):

    def __init__(self, anum: str,  ip_state_name: str, class_name: str, domain: 'Domain',
                 parameters: NamedValues):
        """
        Here we execute a Delegated Creation Activity to create a new instance with a Lifecycle State Machine

        Args:
            anum: Activity number identifying the Delegated Creation Activity
            ip_state_name: All initial pseudo states have the same name, but we pass it in here from the mmdb
            class_name:  Name of the Class with a Lifecycle, effectively our state model name
            domain: Domain object
        """
        dca_label = f"{class_name}[{ip_state_name}]"  # For display in log messages

        # Execute the creation activity to create the class instance
        # Later we can obtain the identifier value of that new instance to create a lifecycle state machine

        # We assume there are no lifecycles at the moment so we can just make the id 0
        instance_id = 0  # Default assumption is that there are no lifey
        if domain.lifecycles.get(class_name):
            # Add one to the maximum key value to generate an unused instance id
            instance_id = max(domain.lifecycles[class_name]) + 1

        pass


        # We need to generate an instance_id and create a lifecycle state machine for this new instance
        # Then we need to execute the activity to populate the instance

        self.lifecycles.setdefault(class_name, {})[i["_instance"]] = LifecycleStateMachine(
            lifecycle_sm_id=instance_id,
            current_state=ip_state_name,
            instance_id=inst_id,
            class_name=class_name,
            domain=domain
        )

        self.instance_id_value = None
        self.xi_flow_name = None

        # Set signum
        # R = f"State_model:<{class_name}>, Domain:<{domain.name}>"
        state_sig_r = Relation.restrict(db=mmdb, relation="State Signature", restriction=R)
        signum = state_sig_r.body[0]['SIGnum']

        # We need to create a new lifecycle instance

        # There is an executing instance of the State Model's Class running this State Activity
        # We flatten the instance id into a string and then use it to define this's ActivityExecution's
        # owner_name. We'll use that to name any local relational variables that are declared, used, and
        # freed up during execution of this State Activity.
        self.instance_id_value = '_'.join(v for v in self.state_machine.instance_id.values())
        # The owner_name is passed along to the superclass for initialization as a self variable
        owner_name = f"LSM_{class_name}__{'initial_pseudo_state'}_{anum}_inst_{self.instance_id_value}"

        # Now we save our Lifecycle Activity instance for use by any executing Action
        # The activity rv_name is passed along to the superclass
        activity_rvn = Relation.declare_rv(db=mmdb, owner=owner_name, name="lifecycle_name")
        R = f"Anum:<{anum}>, Domain:<{self.state_machine.domain.name}>"
        Relation.restrict(db=mmdb, relation='Lifecycle Activity', restriction=R)
        lifecycle_activity_r = Relation.rename(db=mmdb, names={"Anum": "Activity"}, svar_name=activity_rvn)

        # The name of our executing instance flow. This always ends up as "F1", but
        # just in case our Flow naming scheme changes, we check to be sure
        self.xi_flow_name = lifecycle_activity_r.body[0]["Executing_instance_flow"]


        super().__init__(domain=domain, activity_label=dca_label, anum=anum, owner_name=owner_name,
                         activity_rvn=activity_rvn,
                         signum=signum, parameters=parameters)

    def initialize_action_states(self) -> bool:
        """
        Initialize value of action_states relvar for the executing instance's Real State

        Returns:
            False if there are no Actions defined in this Real State
        """
        _logger.info("Initializing this instance's executing State action states to U (unenabled)")
        # We declare a temporary relation to build the relvar value
        action_init_mmrv = Relation.declare_rv(db=mmdb, owner=self.owner_name, name="action_init")

        # Get all Actions in this State Activity, if any
        R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
        state_action_r = Relation.restrict(db=mmdb, relation="Action", restriction=R, svar_name=action_init_mmrv)
        if not state_action_r.body:
            _logger.info(f"No actions defined in [{self.state}]")
            return False

        # There are actions in this Real State
        # Create a relation and set the execution state of each Action to (U) - unexecuted
        Relation.project(db=mmdb, attributes=("ID",), svar_name=action_init_mmrv)
        Relation.extend(db=mmdb, attrs={'State': 'U'}, svar_name=action_init_mmrv)
        # Now we set the relvar to initial action states
        Relvar.set(db=mmdb, relvar=self.action_states, relation=action_init_mmrv)
        # And free up the temporary relation variable
        Relation.free_rvs(db=mmdb, owner=self.owner_name, names=(action_init_mmrv,))
        _logger.info("Actions states initialized")
        return True

    def enable_xi_flow(self):
        """
        An executing instance (xi) is the instance progressing through a Lifecycle
        State Machine. We set the value of this Flow (F1) in that case.

        If this is a Multiple Assigner State Machine, there will be a partitioning
        instance (pi) as F1 instead.

        Otherwise, this must be a Single Assigner State Machine which is defined
        on an Association and there is no associated instance and no flow value to
        set.
        """
        domdb = self.state_machine.domain.alias

        if self.xi_flow_name:
            # This must be a Lifecycle State Machine
            class_name = self.state_machine.state_model
            instance_id = self.state_machine.instance_id
            xi_flow_value_rv = Relation.declare_rv(
                db=domdb, owner=self.owner_name, name="xi_flow_value"
            )
            # Convert identifier to a restriction phrase
            R = ", ".join(f"{k}:<{v}>" for k, v in instance_id.items())
            # Set a relation variable name for the xi flow value
            Relation.restrict(db=domdb, relation=class_name, restriction=R)
            id_attr_names = tuple(k for k in instance_id.keys())
            Relation.project(db=domdb, attributes=id_attr_names, svar_name=xi_flow_value_rv)

            # Set the xi flow value to a relation variable holding a single instance reference for the xi
            self.flows[self.xi_flow_name] = ActiveFlow(value=xi_flow_value_rv, flowtype=class_name)
            _logger.info(f"{self.xi_flow_name} set to executing instance")
            log_table(_logger, table_msg(db=domdb, variable_name=xi_flow_value_rv, table_name=self.owner_name))

        elif self.pi_flow_name:
            # This must be a Multiple Assigner State Machine
            pclass_name = self.state_machine.pclass_name
            pinstance_id = self.state_machine.instance_id
            pi_flow_value_rv = Relation.declare_rv(
                db=domdb, owner=self.owner_name, name="pi_flow_value"
            )
            # Convert identifier to a restriction phrase
            R = ", ".join(f"{k}:<{v}>" for k, v in pinstance_id.items())
            # Set a relation variable name for the pi flow value
            Relation.restrict(db=domdb, relation=pclass_name, restriction=R)
            id_attr_names = tuple(k for k in pinstance_id.keys())
            Relation.project(db=domdb, attributes=id_attr_names, svar_name=pi_flow_value_rv)

            # Set the xi flow value to a relation variable holding a single instance reference for the xi
            self.flows[self.pi_flow_name] = ActiveFlow(value=pi_flow_value_rv, flowtype=pclass_name)
            pass

        # Neither case executes if this is an Single Assigner