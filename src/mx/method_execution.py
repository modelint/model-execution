""" method_execution.py -- class method """

# System
import logging
from typing import TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relvar import Relvar
from pyral.relation import Relation
from pyral.database import Database
from pyral.rtypes import *

# MX
from mx.log_table_config import TABLE, log_table
from mx.message import *
from mx.actions.flow import ActiveFlow
from mx.activity_execution import ActivityExecution
from mx.deprecated.bridge import NamedValues
from mx.instance_set import InstanceSet
from db_names import mmdb
from exceptions import *
from mx.mxtypes import *

_logger = logging.getLogger(__name__)

class MethodExecution(ActivityExecution):

    def __init__(self, anum: str, domain: "Domain", method_rv: str, instance_id: NamedValues, parameters: NamedValues):
        """
        A Method is invoked by a Method Call action

        Args:
            anum: The activity number of the method to execute
            method_rv: relational variable with the method information
            domain: In this domain (object)
            instance_id: Method is invoked on this instance, specified by identifier attribute value pairs
            parameters: Parameters and values for this Method's Signature
        """
        self.instance_id = instance_id
        self.actions = None  # Here we will maintain the execution state of each action in this Method

        method_r = Relation.restrict(db=mmdb, relation=method_rv)
        method_t = method_r.body[0]
        self.class_name = method_t['Class']
        self.method_name = method_t['Name']
        self.label = f"{self.class_name}.{self.method_name}"  # For display in log messages
        instance_id_value = '_'.join(v for v in self.instance_id.values())
        owner_name = f"METHOD_{snake(self.class_name)}_{snake(self.method_name)}_{instance_id_value}"
        activity_rvn = Relation.declare_rv(db=mmdb, owner=owner_name, name="method")
        Relation.restrict(db=mmdb, relation=method_rv, svar_name=activity_rvn)

        # The name of our executing instance flow. This always ends up as "F1", but
        # just in case our Flow naming scheme changes, we check to be sure
        self.xi_flow_name = method_t["Executing_instance_flow"]

        # Set the signature
        method_sig_r = Relation.semijoin(db=mmdb, rname1=method_rv, rname2="Method Signature",
                                         attrs={'Name': 'Method', 'Class': 'Class', 'Domain': 'Domain'})
        signum = method_sig_r.body[0]['SIGnum']

        super().__init__(domain=domain, anum=anum, owner_name=owner_name, activity_rvn=activity_rvn,
                         signum=signum, parameters=parameters)

    def enable_xi_flow(self):
        """
        A Method is executed by some instance and we flow that value into the Method
        as the executing instance (xi) flow.  Here we set the value of that flow.
        """
        domdb = self.domain.alias

        # Set the xi flow value to a relation variable holding a single instance reference for the xi
        xi_flow_value_rv = Relation.declare_rv(
            db=domdb, owner=self.owner_name, name="xi_flow_value"
        )

        # Convert identifier to a restriction phrase
        R = ", ".join(f"{k}:<{v}>" for k, v in self.instance_id.items())
        # Set a relation variable name for the xi flow value
        Relation.restrict(db=domdb, relation=self.class_name, restriction=R)
        id_attr_names = tuple(k for k in self.instance_id.keys())
        Relation.project(db=domdb, attributes=id_attr_names, svar_name=xi_flow_value_rv)
        Relation.print(db=domdb, variable_name=xi_flow_value_rv)

        self.flows[self.xi_flow_name] = ActiveFlow(value=xi_flow_value_rv, flowtype=self.class_name)
        pass

    def initialize_action_states(self) -> bool:

        """
        Initialize value of action_states relvar for the executing instance's Method

        Returns:
            False if there are no Actions defined in this Method
        """
        _logger.info("Initializing this instance's executing Method action states to U (unenabled)")

        action_init_mmrv = Relation.declare_rv(db=mmdb, owner=self.owner_name, name="action_init")

        # Get all Actions in this Method, if any
        method_action_r = Relation.semijoin(db=mmdb, rname1=self.activity_rvn, rname2='Action',
                                            attrs={'Activity': 'Activity', 'Domain': 'Domain'},
                                            svar_name=action_init_mmrv)

        # It is possible for a Method, like any Activity, to have no Actions
        # That said, an empty State Activity is meaningful during execution, but an empty Method
        # is nothing more than a placeholder during development.  It has no system specification utility.
        if not method_action_r.body:
            _logger.warning(f"Method {self.domain.alias}::{self.class_name}.{self.method_name} specifies no actions.")
            return False

        # Create a relation and set the execution state of each Action to (U) - unexecuted
        Relation.project(db=mmdb, attributes=("ID",), svar_name=action_init_mmrv)
        Relation.extend(db=mmdb, attrs={'State': 'U'}, svar_name=action_init_mmrv)

        # Now we set the relvar to initial action states
        Relvar.set(db=mmdb, relvar=self.action_states, relation=action_init_mmrv)
        # And free up the temporary relation variable
        Relation.free_rvs(db=mmdb, owner=self.owner_name, names=(action_init_mmrv,))
        _logger.info("Actions states initialized")
        return True

