""" state_activity_execution.py -- A metamodel StateActivity """

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.state_machine import StateMachine

# Model Integration
from pyral.relation import Relation
from pyral.database import Database

# MX
from mx.actions.flow import ActiveFlow
from mx.activity_execution import ActivityExecution
from mx.mxtypes import StateMachineType
from mx.utility import snake
from db_names import mmdb

_logger = logging.getLogger(__name__)

class StateActivityExecution(ActivityExecution):

    def __init__(self, anum: str, state_machine: "StateMachine"):

        self.state_machine = state_machine
        self.xi_flow_name = None
        from mx.lifecycle_state_machine import LifecycleStateMachine
        from mx.assigner_state_machine import AssignerStateMachine
        match self.state_machine.sm_type:
            case StateMachineType.LIFECYCLE:
                self.instance_id_value = '_'.join(v for v in self.state_machine.instance_id.values())
                owner_name = f"LSM_{self.state_machine.state_model}_{anum}_inst_{self.instance_id_value}"
                rv_name = Relation.declare_rv(db=mmdb, owner=owner_name, name="lifecycle_name")
                R = f"Anum:<{anum}>, Domain:<{self.state_machine.domain.name}>"
                Relation.restrict(db=mmdb, relation='Lifecycle Activity', restriction=R)
                lifecycle_activity_r = Relation.rename(db=mmdb, names={"Anum": "Activity"}, svar_name=rv_name)
                self.xi_flow_name = lifecycle_activity_r.body[0]["Executing_instance_flow"]
                pass
                _logger.info(f"Executing activity: {anum} with xi flow {self.xi_flow_name}")
                # if not method_i.body:
                #     msg = f"Method [{domain_name}:{self.class_name}.{self.name}] not found in metamodel db"
                #     _logger.error(msg)
                #     raise MXMetamodelDBException(msg)
            case StateMachineType.SA:
                # Single assigner is just the rnum
                owner_name = f"SASM_{self.state_machine.state_model}_{anum}"
                rv_name = Relation.declare_rv(db=mmdb, owner=owner_name, name="single_assigner_name")
            case StateMachineType.MA:
                # It must be a multiple assigner state machine
                # we need the rnum plus the partitioning instance
                owner_name = f"MASM_{self.state_machine.state_model}_{anum}_inst_"  # TODO: add partitioning inst id
                rv_name = Relation.declare_rv(db=mmdb, owner=owner_name, name="multiple_assigner_name")

        super().__init__(domain=state_machine.domain, anum=anum, owner_name=owner_name, rv_name=rv_name,
                         parameters=state_machine.active_event.params)
        self.enable_initial_flows()
        self.execute()
        if __debug__:
            print(Database.get_all_rv_names())
        Relation.free_rvs(db=mmdb, owner=self.owner_name)
        Relation.free_rvs(db=self.domain.alias, owner=self.owner_name)
        pass

    def enable_initial_flows(self):
        """
        Set the values of any initially available flows in this State Activity
        """
        # Executing instance flow (if this is a Lifecycle state activity)
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

        # Any Scalar Value (constant) flows
        # These are flows whose value is specified in the activity such as 'Stop requested = TRUE'
        scalar_value_r = Relation.semijoin(db=mmdb, rname1=self.rv_name, rname2="Scalar Value")
        if scalar_value_r.body:
            sflow_r = Relation.join(db=mmdb, rname2="Scalar Flow")
            for sv_i in sflow_r.body:
                sv_flow_name = sv_i['ID']
                sval = sv_i['Name']
                sval_type = sv_i['Type']
                self.flows[sv_flow_name] = ActiveFlow(value=sval, flowtype=sval_type)
                pass

        # All input parameter flows
        # TODO: Set these by referencing method_execution.py file
