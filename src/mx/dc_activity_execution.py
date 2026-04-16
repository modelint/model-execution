""" dc_creation_activity.py -- A metamodel Delegated Creation Activity """
import logging
from typing import TYPE_CHECKING, NamedTuple
from operator import itemgetter

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

    def __init__(self, ips_rv: str, parameters: NamedValues, domain: "Domain", signal_action_mmrv: str,
                 source_activity_execution: ActivityExecution):
        """
        Execute a Delegated Creation Activity to create a new instance with a Lifecycle State Machine

        Args:
            ips_rv: Initial Pseudo State relational variable name
            parameters: Supplied parameter values for the Creation Signature
            domain: The Domain object
            signal_action_mmrv: The initial signal action triggering this dc activity
            source_activity_execution: The executing activity that triggerd this dc activity
        """
        self.source_ae = source_activity_execution
        self.signal_action_mmrv = signal_action_mmrv
        self.new_inst_id: NamedValues = {} # The delegated creation activity will set this to the id of the new instance
        self.new_inst_number = 0  # We use this if the target class is not populated with any instances
        dc_activity_r = Relation.join(db=mmdb, rname1=ips_rv, rname2='Delegated Creation Activity',
                                      attrs={'Creation_activity': 'Anum', 'Domain': 'Domain', }, svar_name=ips_rv
                                      )
        log_table(_logger, table_msg(db=mmdb, variable_name=ips_rv))
        dca_t = dc_activity_r.body[0]

        anum, class_name, ip_state, csig = itemgetter(
            'Creation_activity', 'Class', 'Name', 'Signature')(dca_t)

        dca_label = f"{class_name}[{ip_state}]"  # For display in log messages

        # The owner_name is passed along to the superclass for initialization as a self variable
        owner_name = f"LSM_{class_name}__{'creation'}_{anum}"

        # Set the activity rv name
        activity_rvn = Relation.declare_rv(db=mmdb, owner=owner_name, name="dc_activity")
        R = f"Anum:<{anum}>, Domain:<{domain.name}>"
        Relation.restrict(db=mmdb, relation='Delegated Creation Activity', restriction=R, svar_name=activity_rvn)
        Relation.rename(db=mmdb, names={"Anum": "Activity"}, svar_name=activity_rvn)

        # Execute the creation activity to create the class instance
        # Later we can obtain the identifier value of that new instance to create a lifecycle state machine
        super().__init__(domain=domain, activity_label=dca_label, anum=anum, owner_name=owner_name,
                         activity_rvn=activity_rvn,
                         signum=csig, parameters=parameters)

        # Create a lifeycle state machine for this instance and add it to the domain lifecycle dictionary
        self.lsm = LifecycleStateMachine(
            lifecycle_sm_id=self.new_inst_number,
            current_state=ip_state,
            instance_id=self.new_inst_id,
            class_name=class_name,
            domain=domain
        )
        self.domain.lifecycles.setdefault(class_name, {})[self.new_inst_number] = self.lsm
        self.cleanup()


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
        No instance has been created yet, so we have no executing instance flow
        in a Delegated Creation Activity.

        So no flow value to set.
        """
        return
