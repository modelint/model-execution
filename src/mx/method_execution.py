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
        instance_id_value = '_'.join(v for v in self.instance_id.values())
        owner_name = f"METHOD_{snake(self.class_name)}_{snake(self.method_name)}_{instance_id_value}"
        activity_rvn = Relation.declare_rv(db=mmdb, owner=owner_name, name="method")
        Relation.restrict(db=mmdb, relation=method_rv, svar_name=activity_rvn)

        # The name of our executing instance flow. This always ends up as "F1", but
        # just in case our Flow naming scheme changes, we check to be sure
        self.xi_flow_name = method_t["Executing_instance_flow"]

        super().__init__(domain=domain, anum=anum, owner_name=owner_name, activity_rvn=activity_rvn,
                         parameters=parameters)
        self.enable_initial_flows()
        self.execute()
        pass

    def enable_initial_flows(self):
        """
        Set the values of any initially available flows in this State Activity
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

    def enable_initial_actions(self) -> str | None:
        """
        See description in ActivityExecution abstract method
        """
        mmrv = self.mmrv
        method_action_r = Relation.semijoin(db=mmdb, rname1=self.activity_rvn, rname2='Action',
                                            attrs={'Activity': 'Activity', 'Domain': 'Domain'})
        pass

        # It is possible for a Method, like any Activity, to have no Actions
        # That said, an empty State Activity is meaningful during execution, but an empty Method
        # is nothing more than a placeholder during development.  It has no system specification utility.
        if not method_action_r.body:
            _logger.warning(f"Method {self.domain.alias}::{self.class_name}.{self.method_name} specifies no actions.")
            return None

        # Create a relation and set the execution state of each Action to (U) - unexecuted
        initial_states_rv = Relation.declare_rv(db=mmdb, owner=self.owner_name, name="initial_ma_relation")
        Relation.project(db=mmdb, attributes=("ID",))
        Relation.extend(db=mmdb, attrs={'State': 'U'}, svar_name=initial_states_rv)
        # The relvar name must be unique to each state and instance of this state machine
        # So we use the activity number, this state machine's instance specific owner name
        # The state name at the end isn't necessary since we have the anum, but aids in readability
        relvar_name = f"Method_{self.anum}_{self.owner_name}"
        Relvar.create_relvar(db=mmdb, name=relvar_name, attrs=[
            Attribute(name='ID', type='string'),
            Attribute(name='State', type='string'),
        ], ids={1: ['ID']})
        # Set the initial value of the relvar to
        Relvar.set(db=mmdb, relvar=relvar_name, relation=initial_states_rv)
        self.actions = relvar_name
        log_table(_logger, table_msg(db=mmdb, variable_name=self.actions))
        pass

        # # Get all unexecuted actions
        Relation.restrict(db=mmdb, relation=self.actions, restriction=ActionState.U)
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
            Relvar.updateone(db=mmdb, relvar_name=self.actions, id={'ID': a['ID']}, update={'State': 'E'})

        log_table(_logger, table_msg(db=mmdb, variable_name=self.actions))
        return self.actions
