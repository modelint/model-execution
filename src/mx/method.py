""" method.py -- class method """

# System
import logging
from typing import Optional, Any

# Model Integration
from pyral.relation import Relation

# MX
from mx.activity import Activity, ActiveFlow
from mx.bridge import NamedValues
from db_names import mmdb
from exceptions import *

_logger = logging.getLogger(__name__)

class Method(Activity):

    rname = "this_method"

    def __init__(self, name: str, class_name: str, domain_name: str, instance_id: NamedValues, parameters: NamedValues):
        """
        Lookup the Method and execute it

        :param name:  Method name
        :param class_name:  Method is defined on this class
        :param domain_name:  Method is defined on class in this domain
        :param instance_id:  Method is invoked on this instance, specified by identifier attribute value pairs
        :param parameters:  Parameters and values for this Method's Signature
        """
        self.name = name
        self.instance = instance_id
        self.parameters = parameters
        self.class_name = class_name
        self.xi_flow = None
        self.current_wave = 1
        self.wave_action_ids = None
        self.flows : dict[str, Optional[ActiveFlow] ] = {}

        # Get the method attribute values (anum, xi_flow)
        R = f"Name:<{self.name}>, Class:<{self.class_name}>, Domain:<{domain_name}>"
        method_i = Relation.restrict(db=mmdb, relation='Method', restriction=R, svar_name=Method.rname)
        if not method_i.body:
            msg = f"Method [{domain_name}:{self.class_name}.{self.name}] not found in metamodel db"
            _logger.error(msg)
            raise MXMetamodelDBException(msg)

        anum = method_i.body[0]['Anum']
        self.xi_flow = method_i.body[0]['Executing_instance_flow']

        # Create all flows with empty content
        Relation.join(db=mmdb, rname1=Method.rname, rname2="Flow", attrs={"Anum": "Activity", "Domain": "Domain"})
        flow_ids_r = Relation.project(db=mmdb, attributes=("ID",))
        self.flows = {t["ID"]: None for t in flow_ids_r.body}

        super().__init__(domain=domain_name, anum=anum, parameters=parameters)

        self.execute()

    def enable_initial_flows(self):
        # Set the values of all initial flows

        # Set the xi flow value to a single instance reference for the executing instance
        self.flows[self.xi_flow] = ActiveFlow(value=self.instance, flowtype=self.class_name)

        # Set the input parameter flows
        Relation.rename(db=mmdb, relation="Parameter", names={"Name": "Pname"})
        p = Relation.join(db=mmdb, rname2=Method.rname, attrs={"Activity": "Anum", "Domain": "Domain"}, svar_name="my_params")
        param_r = Relation.project(db=mmdb, attributes=("Pname", "Input_flow", "Type"))
        for t in param_r.body:
            self.flows[t["Input_flow"]] = ActiveFlow(value=self.parameters[t["Pname"]], flowtype=t["Type"])

        # Now check for any class accessor and set each such flow to the name of the accessed class
        Relation.rename(db=mmdb, relation=Method.rname, names={"Class": "MethodClass"})
        Relation.join(db=mmdb, rname2="Class_Accessor", attrs={"Anum": "Activity", "Domain": "Domain"})
        ca_flows_r = Relation.project(db=mmdb, attributes=("Class", "Output_flow",))
        for t in ca_flows_r.body:
            self.flows[t["Output_flow"]] = ActiveFlow(value=None, flowtype=t["Class"])

    def execute(self):
        """
        Execute the method actions
        :return:
        """
        self.enable_initial_flows()

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