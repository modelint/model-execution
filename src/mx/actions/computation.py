""" computation.py  -- execute a computation action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

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
    computation_action: str
    boolean_partition: str
    general_computation: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "computation_action", "boolean_partition", "general_computation")
    return MMRVs(*rvs)

class Computation(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Computation Action on a domain model.

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
        computation_action_r = Relation.semijoin(
            db=mmdb, rname1=self.action_mmrv, rname2="Computation Action", svar_name=mmrv.computation_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.computation_action))
        computation_action_t = computation_action_r.body[0]
        self.expression = computation_action_t['Expression']

        # Gather input flows
        computation_input_r = Relation.semijoin(db=mmdb, rname1=mmrv.computation_action, rname2='Computation Input',
                                                attrs={'ID': 'Computation', 'Activity': 'Activity', 'Domain': 'Domain'})
        self.input_flow_names = [t['Input_flow'] for t in computation_input_r.body]
        # self.source_flows = {n: self.activity_execution.flows[n] for n in self.input_flow_names}

        _logger.info("Flows")
        for fname in self.input_flow_names:
            source_flow = self.activity_execution.flows[fname]
            _logger.info(f"{fname}")
            if source_flow.flowtype == 'scalar':
                # TODO: We need to extend the Flow structure to include the scalar type name
                pass
                # _logger.info(
                #     sflow_msg(flow_name=fname, flow_dir=FlowDir.IN, flow_type=attr_t["Scalar"],
                #               activity=self.activity_execution, value=source_flow.vaue)
                # )
            else:
                log_table(_logger, nsflow_msg(db=self.domdb, flow_name=fname, flow_dir=FlowDir.IN,
                                              flow_type=source_flow.flowtype, activity=self.activity_execution,
                                              rv_name=source_flow.value))

        # Is this a General Computation or a Boolean Paritition?
        general_computation_r = Relation.semijoin(
            db=mmdb, rname1=mmrv.computation_action, rname2='General Computation', svar_name=mmrv.general_computation)
        if general_computation_r.body:
            self.process_computation(result_flow_name=general_computation_r.body[0]['Result_flow'])
        else:
            self.process_boolean_partition()


        attribute_write_accesses_r = Relation.semijoin(
            db=mmdb, rname1=mmrv.write_action, rname2="Attribute Write Access",
            attrs={"ID": "Write_action", "Activity": "Activity", "Domain": "Domain"},
            svar_name=mmrv.attr_write_accesses
        )
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.attr_write_accesses))

        # Get all attributes being written so we can look up each type
        attr_r = Relation.semijoin(db=mmdb, rname1=mmrv.attr_write_accesses, rname2="Attribute",
                                   attrs={"Attribute": "Name", "Class": "Class", "Domain": "Domain"},
                                   svar_name=mmrv.attributes)

        # Expand irefs to instance set
        output_iset_rv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="output_input")
        InstanceSet.instances(db=self.domdb, irefs_rv=self.source_flow.value, iset_rv=output_iset_rv,
                              class_name=self.source_flow.flowtype)

        qty_instances_to_write = Relation.cardinality(db=self.domdb, rname=output_iset_rv)
        if qty_instances_to_write > 1:
            msg = f"Write to multiple instances not yet supported"
            raise MXException(msg)

        for access in attribute_write_accesses_r.body:
            new_value = self.activity_execution.flows[access['Input_flow']].value
            write_attr = access['Attribute'].replace(' ', '_')
            class_name = access['Class'].replace(' ', '_')
            # TODO: NOW self.source_flow.value is now an rv name, need to resolve that to id value
            source_iref_str = Relation.get_rval_string(db=self.domdb, variable_name=self.source_flow.value)
            source_iref_t_dict = Relation.make_pyrel(source_iref_str).body[0]

            Relvar.updateone(db=self.domdb, relvar_name=class_name, id=source_iref_t_dict,
                             update={write_attr: new_value})

        log_table(_logger, table_msg(db=self.domdb, variable_name='Accessible Shaft Level'))

        self.complete()

    def process_computation(self, result_flow_name: str):
        pass

    def process_boolean_partition(self):
        mmrv = self.mmrv
        boolean_partition_r = Relation.semijoin(
            db=mmdb, rname1=mmrv.computation_action, rname2='Boolean Partition', svar_name=mmrv.boolean_partition)
