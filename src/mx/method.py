""" method.py -- class method """

# System
import logging
from typing import Optional, Any

# Model Integration
from pyral.relation import Relation

# MX
from mx.activity import Activity, FlowType
from mx.bridge import NamedValues
from db_names import mmdb
from exceptions import *

_logger = logging.getLogger(__name__)

class Method(Activity):

    def __init__(self, name: str, class_name: str, domain_name: str,
                 instance_id: NamedValues, parameters: NamedValues):
        """

        :param name:
        :param class_name:
        :param domain_name:
        :param instance_id:
        :param parameters:
        """
        self.name = name
        self.instance = instance_id
        self.class_name = class_name
        self.xi_flow = None
        self.current_wave = 1
        self.wave_action_ids = None
        self.flows : dict[str, Optional[Any] ] = {}

        R = f"Name:<{self.name}>, Class:<{self.class_name}>, Domain:<{domain_name}>"
        method_i = Relation.restrict(db=mmdb, relation='Method', restriction=R, svar_name="this_method")
        if not method_i.body:
            msg = f"Method [{domain_name}:{self.class_name}.{self.name}] not found in metamodel db"
            _logger.error(msg)
            raise MXMetamodelDBException(msg)

        anum = method_i.body[0]['Anum']
        self.xi_flow = method_i.body[0]['Executing_instance_flow']

        # Create flows
        Relation.join(db=mmdb, rname1="this_method", rname2="Flow", attrs={"Anum": "Activity", "Domain": "Domain"})
        flow_ids_r = Relation.project(db=mmdb, attributes=("ID",))
        self.flows = {t["ID"]: None for t in flow_ids_r.body}

        # Set the xi flow value
        self.flows[self.xi_flow] = instance_id

        # Set the parameter flows
        Relation.rename(db=mmdb, relation="Parameter", names={"Name": "Label"}, svar_name="label")
        p = Relation.join(db=mmdb, rname1="this_method", rname2="label", attrs={"Anum": "Activity", "Domain": "Domain"}, svar_name="my_params")
        param_r = Relation.project(db=mmdb, attributes=("Label", "Input_flow"))
        for t in param_r.body:
            # Determine Flow type based on parameter
            Relation.rename(db=mmdb, relation="my_params", names={"Anum": "Activity"}, svar_name="my_params_rn")
            s = Relation.join(db=mmdb, rname2="Scalar_Flow")
            if s.body:
                ftype = FlowType.S
            else:
                i = Relation.join(db=mmdb, rname1="my_params_rn", rname2="Instance_Flow")

            self.flows[t["Input_flow"]] = parameters[t["Label"]]
            pass

        # Now check for any class accessors
        Relation.rename(db=mmdb, relation="this_method", names={"Class": "MethodClass"})
        Relation.join(db=mmdb, rname2="Class_Accessor", attrs={"Anum": "Activity", "Domain": "Domain"})
        ca_flows_r = Relation.project(db=mmdb, attributes=("Class", "Output_flow",))
        for t in ca_flows_r.body:
            self.flows[t["Output_flow"]] = t["Class"]
        pass



        super().__init__(domain=domain_name, anum=anum, parameters=parameters)

        self.execute()


    def execute(self):
        """
        Execute the method actions
        :return:
        """
        while True:
            R = f"Activity:<{self.anum}>, Wave:<{self.current_wave}>, Domain:<{self.domain}>"
            wave_assignment_i = Relation.restrict(db=mmdb, relation='Wave_Assignment', restriction=R)
            if not wave_assignment_i.body:
                return
            wave_actions_r = Relation.project(db=mmdb, attributes=("Action",))
            self.wave_action_ids = [a['Action'] for a in wave_actions_r.body]
            self.process_wave()
            self.current_wave += 1

    def process_wave(self):
        for action in self.wave_action_ids:
            pass
        pass