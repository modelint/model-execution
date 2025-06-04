""" method.py -- class method """

# System
import logging
from typing import TYPE_CHECKING, Optional, NamedTuple

if TYPE_CHECKING:
    from mx.xe import XE

# Model Integration
from pyral.relation import Relation
from pyral.database import Database

# MX
from mx.actions.flow import ActiveFlow
from mx.activity import Activity
from mx.bridge import NamedValues
from db_names import mmdb
from exceptions import *

_logger = logging.getLogger(__name__)

class Method(Activity):

    def __init__(self, xe: "XE", name: str, class_name: str, domain_name: str, domain_alias: str,
                 instance_id: NamedValues, parameters: NamedValues):
        """
        Lookup the Method and execute it

        :param xe: For access to environment settings (debug, verbose, etc)
        :param name:  Method name
        :param class_name:  Method is defined on this class
        :param domain_name:  Method is defined on class in this domain
        :param instance_id:  Method is invoked on this instance, specified by identifier attribute value pairs
        :param parameters:  Parameters and values for this Method's Signature
        """
        self.name = name
        self.domain_name = domain_name
        self.domain_alias = domain_alias
        self.instance = instance_id
        self.parameters = parameters
        self.class_name = class_name
        self.xi_flow = None
        self.current_wave = 1
        self.wave_action_ids = None
        self.flows: dict[str, Optional[ActiveFlow]] = {}
        self.executed_actions : list[str] = []  # List of action names executed in sequence so rvs can be freed later

        instance_id_value = '_'.join(v for v in self.instance.values())
        self.owner_name = f"{class_name}_{name}_{instance_id_value}"

        self.method_rvname = Relation.declare_rv(db=mmdb, owner=self.owner_name, name="method_name")

        # Get the method attribute values (anum, xi_flow)
        R = f"Name:<{self.name}>, Class:<{self.class_name}>, Domain:<{self.domain_name}>"
        Relation.restrict(db=mmdb, relation='Method', restriction=R)

        method_i = Relation.rename(db=mmdb, names={"Anum": "Activity"}, svar_name=self.method_rvname)
        if not method_i.body:
            msg = f"Method [{domain_name}:{self.class_name}.{self.name}] not found in metamodel db"
            _logger.error(msg)
            raise MXMetamodelDBException(msg)

        anum = method_i.body[0]['Activity']
        self.xi_flow = method_i.body[0]['Executing_instance_flow']

        # Create all flows with empty content
        Relation.join(db=mmdb, rname1=self.method_rvname, rname2="Flow")
        flow_ids_r = Relation.project(db=mmdb, attributes=("ID",))
        self.flows = {t["ID"]: None for t in flow_ids_r.body}

        super().__init__(xe=xe, domain=domain_name, anum=anum, parameters=parameters)

        self.execute()

        # Diagnostic check for in use database variables
        _rv_before_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_before_dom_free = Database.get_rv_names(db=self.domain_alias)

        Relation.free_rvs(db=mmdb, owner=self.owner_name)
        Relation.free_rvs(db=domain_alias, owner=self.owner_name)
        for a in self.executed_actions:
            action_owner = f"{self.anum}_{a}_{instance_id_value}"
            Relation.free_rvs(db=domain_alias, owner=action_owner)

        # Diagnostic check to ensure all db variables freed up (returning empty sets)
        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domain_alias)

    def enable_initial_flows(self):
        # Set the values of all initial flows
        xi_flow_value_rv = Relation.declare_rv(db=self.domain_alias, owner=self.owner_name, name="xi_flow_value")
        # Convert identifier to a restriction phrase
        R = ", ".join(f"{k}:<{v}>" for k, v in self.instance.items())
        # Set a relation variable name for the xi flow value
        Relation.restrict(db=self.domain_alias, relation=self.class_name, restriction=R)
        id_attr_names = tuple(k for k in self.instance.keys())
        Relation.project(db=self.domain_alias, attributes=id_attr_names, svar_name=xi_flow_value_rv)
        Relation.print(db=self.domain_alias, variable_name=xi_flow_value_rv)

        # Set the xi flow value to a relation variable holding a single instance reference for the executing instance
        self.flows[self.xi_flow] = ActiveFlow(value=xi_flow_value_rv, flowtype=self.class_name)

        # Set the input parameter flows
        Relation.rename(db=mmdb, relation="Parameter", names={"Name": "Pname"})
        p = Relation.join(db=mmdb, rname2=self.method_rvname)
        param_r = Relation.project(db=mmdb, attributes=("Pname", "Input_flow", "Type"))
        for t in param_r.body:
            self.flows[t["Input_flow"]] = ActiveFlow(value=self.parameters[t["Pname"]], flowtype=t["Type"])

        # Now check for any class accessor and set each such flow to the name of the accessed class
        Relation.rename(db=mmdb, relation=self.method_rvname, names={"Class": "MethodClass"})
        Relation.join(db=mmdb, rname2="Class_Accessor")
        ca_flows_r = Relation.project(db=mmdb, attributes=("Class", "Output_flow",))
        for t in ca_flows_r.body:
            self.flows[t["Output_flow"]] = ActiveFlow(value=t["Class"], flowtype=t["Class"])

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
            _dbm = Database.get_rv_names(db=mmdb)
            _dbd = Database.get_rv_names(db=self.domain_alias)
            self.process_wave()
            self.current_wave += 1

    def process_wave(self):
        for action in self.wave_action_ids:

            # Get the Action relation
            Relation.join(db=mmdb, rname1="Action", rname2=self.method_rvname)
            R = f"ID:<{action}>"
            Relation.restrict(db=mmdb, restriction=R)

            # Get the action type
            atype_r = Relation.project(db=mmdb, attributes=("Type",))
            action_type = atype_r.body[0]["Type"]

            # Execute the appropriate action
            # We do this by instantiating the class defined for the action_type
            # Using the Activity's action execution dispatch dictionary
            current_x_action = Method.execute_action[action_type](activity=self, action_id=action)
            pass

        pass
