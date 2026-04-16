""" create.py  -- execute a create action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple
from operator import itemgetter

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.relvar import Relvar
from pyral.database import Database

# MX
from mx.log_table_config import TABLE, log_table
from mx.instance_set import InstanceSet
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.exceptions import *
from mx.utility import *

_logger = logging.getLogger(__name__)


# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    create_action: str
    attr_inits: str
    explicit_attr_inits: str
    ref_attr_inits: str
    default_attr_inits: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "create_action", "attr_inits", "explicit_attr_inits",
                      "ref_attr_inits", "default_attr_inits")
    return MMRVs(*rvs)


class Create(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Create Action on a domain model.

        Args:
            action_id: The ACTN<n> value
            activity_execution: The Activity Execution object
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        mmrv = declare_mm_rvs(owner=self.owner)

        # Lookup the Action instance
        Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Create Action", svar_name=mmrv.create_action)
        # Get all Attribute Initializations required for the create
        attr_init_r = Relation.semijoin(db=mmdb, rname1=mmrv.create_action, rname2='Attribute Initialization',
                          attrs={'ID': 'Create_action', 'Activity': 'Activity', 'Domain': 'Domain'},
                          svar_name=mmrv.attr_inits)
        target_class = attr_init_r.body[0]['Class']
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.attr_inits))
        # Split out into each type of initialization and process
        initial_attr_values = {}
        ref_attr_inits_r = Relation.semijoin(db=mmdb, rname1=mmrv.attr_inits, rname2='Reference Initialization',
                                             svar_name=mmrv.ref_attr_inits)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.ref_attr_inits))
        ref_flows_out_r = Relation.project(db=mmdb, attributes=('Initial_value_flow',), relation=mmrv.ref_attr_inits)
        for t in ref_flows_out_r.body:
            output_fname = t['Initial_value_flow']
            ref_attr_vals_r = Relation.restrict(db=self.domdb,
                                                relation=self.activity_execution.flows[output_fname].value)
            # Flow value must be a tuple
            ref_attr_vals_t = ref_attr_vals_r.body[0]
            for k, v in ref_attr_vals_t.items():
                initial_attr_values[k] = v

        # TODO: Implement the other two cases when we have an example
        explicit_attr_inits_r = Relation.semijoin(db=mmdb, rname1=mmrv.attr_inits, rname2='Explicit Initialization',
                                                  svar_name=mmrv.explicit_attr_inits)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.explicit_attr_inits))
        default_attr_inits_r = Relation.semijoin(db=mmdb, rname1=mmrv.attr_inits, rname2='Default Initialization',
                                                 svar_name=mmrv.default_attr_inits)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.default_attr_inits))

        # Now create the instance
        Relvar.insert(db=self.domdb, relvar=target_class, tuples=[initial_attr_values])
        _logger.info(f"Created instance of {target_class}")
        log_table(_logger, table_msg(db=self.domdb, variable_name=target_class))

        # Also the lifecycle ID instance mapping
        # Generate an instance ID for this new Lifecycle
        if self.activity_execution.domain.lifecycles.get(target_class):
            # Add one to the maximum key value to generate an unused instance id
            self.activity_execution.new_inst_number = max(self.activity_execution.domain.lifecycles[target_class]) + 1
        # We save the new inst number as an attribute of DelegatedCreationActivity since it will be referenced
        # there when the Lifecycle state machinew is created

        # Update the _instance relation which maps int instance ids to real attribute identifiers
        new_inst_id_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name='new_inst_id')
        # Get identifier attributes of the target class
        class_id = self.activity_execution.domain.class_ids[target_class]
        # Project on that identifier and add an _instance attribute to hold the int instance id of the new instance
        Relation.project(db=self.domdb, relation=target_class, attributes=class_id, svar_name=new_inst_id_drv)
        Relation.extend(db=self.domdb, attrs={'_instance': self.activity_execution.new_inst_number}, relation=new_inst_id_drv,
                        svar_name=new_inst_id_drv)
        # Get the existing population of inst id mappings for the target class and update it with the new instance
        class_inst_id_drv = self.activity_execution.domain.sm_instance_rvs[target_class]
        Relation.union(db=self.domdb, relations=(new_inst_id_drv, class_inst_id_drv), svar_name=class_inst_id_drv)

        # Set the identifier of the newly created instance for future reference (lifecycle creation for example)
        self.activity_execution.new_inst_id = {k: initial_attr_values[k] for k in class_id if k in initial_attr_values}

        self.complete()
