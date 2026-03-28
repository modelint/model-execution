""" state_activity_execution.py -- A metamodel StateActivity """

import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.state_machine import StateMachine

# Model Integration
from pyral.relvar import Relvar
from pyral.relation import Relation
from pyral.database import Database

# MX
from mx.actions.flow import ActiveFlow
from mx.activity_execution import ActivityExecution
from mx.mxtypes import StateMachineType
from mx.utility import *
from mx.db_names import mmdb
from mx.mxtypes import ActionState

_logger = logging.getLogger(__name__)

class StateActivityExecution(ActivityExecution):

    def __init__(self, anum: str, state_machine: "StateMachine"):
        """
        We are here to execute all of the Actions in a State Activity

        Args:
            anum:  Activity number identifying the State Activity
            state_machine:  State Machine object (instance specific) executing this State Activity
        """
        self.state_machine = state_machine  # The Lifecycle or Assigner State Machine

        # Holds a value only if this is a Lifecycle State Machine
        self.instance_id_value = None
        self.xi_flow_name = None

        # Holds a value only if this is a Multiple Assigner State Machine
        self.pi_flow_name = None
        self.pi_flow_name = None

        # Initialization specific to each type of State Machine
        match self.state_machine.sm_type:
            case StateMachineType.LIFECYCLE:
                # There is an executing instance of the State Model's Class running this State Activity
                # We flatten the instance id into a string and then use it to define this's ActivityExecution's
                # owner_name. We'll use that to name any local relational variables that are declared, used, and
                # freed up during execution of this State Activity.
                self.instance_id_value = '_'.join(v for v in self.state_machine.instance_id.values())
                # The owner_name is passed along to the superclass for initialization as a self variable
                owner_name = f"LSM_{self.state_machine.state_model}_{anum}_inst_{self.instance_id_value}"

                # Now we save our Lifecycle Activity instance for use by any executing Action
                # The activity rv_name is passed along to the superclass
                activity_rvn = Relation.declare_rv(db=mmdb, owner=owner_name, name="lifecycle_name")
                R = f"Anum:<{anum}>, Domain:<{self.state_machine.domain.name}>"
                Relation.restrict(db=mmdb, relation='Lifecycle Activity', restriction=R)
                lifecycle_activity_r = Relation.rename(db=mmdb, names={"Anum": "Activity"}, svar_name=activity_rvn)

                # The name of our executing instance flow. This always ends up as "F1", but
                # just in case our Flow naming scheme changes, we check to be sure
                self.xi_flow_name = lifecycle_activity_r.body[0]["Executing_instance_flow"]

            case StateMachineType.MA:
                # It must be a multiple assigner state machine
                # we need the rnum plus the partitioning instance

                # There is an instance of the partitioning class input to this State Activity
                # We flatten the instance id into a string and then use it to define this's ActivityExecution's
                # owner_name. We'll use that to name any local relational variables that are declared, used, and
                # freed up during execution of this State Activity.
                self.pinstance_id_value = '_'.join(v for v in self.state_machine.instance_id.values())
                # The owner_name is passed along to the superclass for initialization as a self variable
                owner_name = f"MASM_{self.state_machine.state_model}_{anum}_inst_"  # TODO: add partitioning inst id
                activity_rvn = Relation.declare_rv(db=mmdb, owner=owner_name, name="multiple_assigner_name")

                # Now we save our Multiple Assigner Activity instance for use by any executing Action
                # The activity rv_name is passed along to the superclass
                R = f"Anum:<{anum}>, Domain:<{self.state_machine.domain.name}>"
                Relation.restrict(db=mmdb, relation='Multiple Assigner Activity', restriction=R)
                ma_activity_r = Relation.rename(db=mmdb, names={"Anum": "Activity"}, svar_name=activity_rvn)

                # The name of our executing instance flow. This always ends up as "F1", but
                # just in case our Flow naming scheme changes, we check to be sure
                self.pi_flow_name = ma_activity_r.body[0]["Partitioning_instance_flow"]

            case StateMachineType.SA:
                # Single assigner is just the rnum
                owner_name = f"SASM_{self.state_machine.state_model}_{anum}"
                activity_rvn = Relation.declare_rv(db=mmdb, owner=owner_name, name="single_assigner_name")

        super().__init__(domain=state_machine.domain, anum=anum, owner_name=owner_name, activity_rvn=activity_rvn,
                         parameters=state_machine.active_event.params)
        self.enable_initial_flows()
        self.execute()
        if __debug__:
            print(Database.get_all_rv_names())
        Relation.free_rvs(db=mmdb, owner=self.owner_name)
        Relation.free_rvs(db=self.domain.alias, owner=self.owner_name)
        pass

    def enable_initial_actions(self) -> str | None:
        """
        See description in ActivityExecution abstract method
        """
        mmrv = self.mmrv
        action_states = self.state_machine.actions[self.anum]
        if not action_states:
            return None

        # Get all unexecuted actions
        Relation.restrict(db=mmdb, relation=action_states, restriction=ActionState.U)
        Relation.project(db=mmdb, attributes=("ID",), svar_name=mmrv.unexecuted_actions)

        # Determine which actions have their flows available initially and enable them
        #
        # Find all the actions that are dependent on flows from other actions
        # Subtract these dependent actions from our set of unexecuted (U) actions
        # and we get have set of non-dependent actions to enable (E)

        # Join the unexecuted actions with Flow Dependency on the To_action (flow destination)
        # to obtain all dependent actions
        R = f"Activity:<{self.anum}>, Domain:<{self.domain.name}>"
        Relation.restrict(db=mmdb, relation="Action", restriction=R)
        Relation.semijoin(db=mmdb, rname2='Flow Dependency',
                          attrs={'ID': 'To_action', 'Activity': 'Activity', 'Domain': 'Domain'},
                          svar_name=mmrv.flow_deps)  # We use this later to choose actions to enable
        # And now we just take the To_action column and rename it to ID to get something we can subtract
        Relation.project(db=mmdb, attributes=("To_action",))
        Relation.rename(db=mmdb, names={"To_action": "ID"})
        # We subtract these from the set of unexecuted actions to obtain those we need to enable
        enable_r = Relation.subtract(db=mmdb, rname1=mmrv.unexecuted_actions)
        # For each action to enable, we change its state from U (unexecuted) to E (enabled)
        for a in enable_r.body:
            Relvar.updateone(db=mmdb, relvar_name=action_states, id={'ID': a['ID']}, update={'State': 'E'})

        if __debug__:
            Relation.print(db=mmdb, variable_name=action_states)
        pass
        return action_states

    def enable_initial_flows(self):
        """
        Set the values of any initially available flows in this State Activity
        """
        # Executing instance flow (if this is a Lifecycle state activity)
        _logger.info(f"Enabling initial flows")
        domdb = self.state_machine.domain.alias
        if self.xi_flow_name:
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
            logtable(logger=_logger, db=domdb, variable_name=xi_flow_value_rv, table_name=self.owner_name)
        elif self.pi_flow_name:
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

        # Any Scalar Value (constant) flows
        # These are flows whose value is specified in the activity such as 'Stop requested = TRUE'
        scalar_value_r = Relation.semijoin(db=mmdb, rname1=self.activity_rvn, rname2="Scalar Value")
        if scalar_value_r.body:
            sflow_r = Relation.join(db=mmdb, rname2="Scalar Flow")
            for sv_i in sflow_r.body:
                sv_flow_name = sv_i['ID']
                sval = sv_i['Name']
                sval_type = sv_i['Type']
                self.flows[sv_flow_name] = ActiveFlow(value=sval, flowtype=sval_type)
                _logger.info(f"initial Scalar Value Flow {sv_flow_name} set to value {sval} type {sval_type}")
                pass

        # All input parameter flows
        # TODO: Set these by referencing method_execution.py file
