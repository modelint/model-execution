""" select.py -- executes the Select Action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics
from pyral.rtypes import TAG

# MX
from mx.log_table_config import TABLE, log_table
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.instance_set import InstanceSet
from mx.utility import *

_logger = logging.getLogger(__name__)

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    select_action: str
    restriction_condition: str
    my_criteria: str
    my_eq_criteria: str
    my_comp_criteria: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "select_action", "restriction_condition",
                      "my_criteria", "my_eq_criteria", "my_comp_criteria")
    return MMRVs(*rvs)

class Select(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Select Action on a domain model.

        Args:
            action_id:  The ACTN<n> value identifying each Action instance
            activity_execution: The A<n> Activity ID
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_my_module_rvs(db=mmdb, owner=self.owner)
        mmrv = self.mmrv

        # Lookup the Action instance
        select_action_r = Relation.semijoin(
            db=mmdb, rname1=self.action_mmrv, rname2="Select Action", svar_name=mmrv.select_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.select_action))
        select_action_t = select_action_r.body[0]

        self.source_flow_name = select_action_t["Input_flow"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]  # The active content of source flow (value, type)
        _logger.info(f"{self.source_flow_name}")
        _logger.info("Flows")
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        # Get the destination flow name
        subclass_r = Relation.semijoin(db=mmdb, rname1=mmrv.select_action, rname2="Single Select")
        if not subclass_r.body:
            subclass_r = Relation.semijoin(db=mmdb, rname1=mmrv.select_action, rname2="Many Select")
        self.dest_flow_name = subclass_r.body[0]["Output_flow"]

        # Check for a Select None, in which case we skip any Restriction Condition processing
        select_none_r = Relation.semijoin(db=mmdb, rname1=mmrv.select_action, rname2='Select None')
        if select_none_r.body:
            self.card = 'NONE'  # For other Select Action subclasses, cardinality is in the restriction condition
            criteria_phrases = []
        else:
            # Process the restriction condition (if any)
            self.card, criteria_phrases = self.process_restriction_condition()

        # Convert input irefs to instances and save in same rv
        input_iset_rv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="selection_input")
        InstanceSet.instances(db=self.domdb, irefs_rv=self.source_flow.value, iset_rv=input_iset_rv,
                              class_name=self.source_flow.flowtype)
        log_table(_logger, table_msg(db=self.domdb, variable_name=input_iset_rv))

        # Perform the selection and apply any cardinality
        selection_output_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="selection_output")
        if self.card == 'NONE':
            # We don't actually do a restrict, we just produce an empty relation
            Relation.emptyof(db=self.domdb, relation=input_iset_rv, svar_name=selection_output_drv)
        else:
            R = ', '.join(criteria_phrases)  # For now we will just and them all together using commas
            Relation.restrict(db=self.domdb, relation=input_iset_rv, restriction=R.strip(),
                              svar_name=selection_output_drv)
            if self.card == 'ONE':
                tuple_qty = Relation.cardinality(db=self.domdb, rname=selection_output_drv) > 1
                if tuple_qty > 1:
                    # We need to reduce the cardinality to a single tuple
                    # Tag each tuple with a number
                    Relation.tag(db=self.domdb, relation=selection_output_drv, svar_name=selection_output_drv)
                    # Choose a random tag value within the tuple_qty and restrict on it
                    import random
                    rselect_tag = random.randrange(tuple_qty)
                    Relation.restrict(db=self.domdb, relation=selection_output_drv,
                                      restriction=f"{TAG}:<{rselect_tag}>", svar_name=selection_output_drv)
                    # Project out the tag attr
                    Relation.project(db=self.domdb, attributes=[TAG], relation=selection_output_drv,
                                     exclude=True, svar_name=selection_output_drv)

        log_table(_logger, table_msg(db=self.domdb, variable_name=selection_output_drv))

        # Extract irefs for output
        InstanceSet.irefs(db=self.domdb, iset_rv=selection_output_drv, irefs_rv=selection_output_drv,
                          class_name=self.source_flow.flowtype,
                          domain_name=self.activity_execution.domain.name)

        log_table(_logger, table_msg(db=self.domdb, variable_name=selection_output_drv))

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity_execution.flows[self.dest_flow_name] = ActiveFlow(
            value=selection_output_drv, flowtype=self.source_flow.flowtype)

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=selection_output_drv))

        self.complete()

    def process_restriction_condition(self) -> tuple[str, list[str]]:

        mmrv = self.mmrv
        # Get the Restriction Condition
        rcond_r = Relation.semijoin(db=mmdb, rname1=mmrv.select_action, rname2="Restriction Condition",
                                    attrs={"ID": "Action", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=mmrv.restriction_condition)
        if not rcond_r.body:
            return 'ALL', []  # With no restriction condition, we assume the least restrictive cardinality

        rc_card = rcond_r.body[0]["Selection_cardinality"]
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.restriction_condition))
        _logger.info(f"- Restriction Condition cardinality: {rc_card}")

        # The supplied expression helps us define any complex boolean logic
        # in the restriction phrase to be created.
        predicate_str = rcond_r.body[0]["Expression"]  # TODO: Use this when we have a more interesting example

        # Get all Criteria
        Relation.semijoin(db=mmdb, rname1=mmrv.restriction_condition, rname2="Criterion", svar_name=mmrv.my_criteria)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.my_criteria))

        # Make a phrase for each criterion
        # TODO: incorporate and/or/not logic

        # Equivalence criteria
        eq_phrases = self.make_eq_phrases()
        comp_phrases = self.make_comparison_phrases()
        criteria_phrases = eq_phrases + comp_phrases
        _logger.info(f"- Criteria: {criteria_phrases}")
        _logger.info("Flows")

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))
        return rc_card, criteria_phrases

    def make_eq_phrases(self) -> list[str]:
        """

        :return:
        """
        mmrv = self.mmrv
        # Look up the equivalence critiera, if any
        my_eq_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Equivalence Criterion",
                                             svar_name=mmrv.my_eq_criteria)

        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.my_eq_criteria))

        criteria_rphrases: list[str] = []

        for c in my_eq_criteria_r.body:
            attr = c['Attribute'].replace(' ', '_')
            value = c['Value'].upper()  # This will be either TRUE or FALSE

            phrase = f"{attr}:<{value}>"
            criteria_rphrases.append(phrase)

        return criteria_rphrases

    def make_comparison_phrases(self) -> list[str]:
        """

        :return:
        """
        # TODO: This method under construction
        mmrv = self.mmrv
        # Look up the comparison critiera, if any
        my_comp_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Comparison_Criterion",
                                               svar_name=mmrv.my_comp_criteria)

        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.my_comp_criteria))

        criteria_rphrases: list[str] = []

        for c in my_comp_criteria_r.body:
            attr = c['Attribute'].replace(' ', '_')
            scalar_flow_name = c['Value']
            value = self.activity_execution.flows[scalar_flow_name].value
            relop = c['Comparison']
            if isinstance(value, str):
                pyral_op = ':' if relop == '==' else relop
                value = f"<{value}>"
            else:
                # TODO: This case does not currently work
                _logger.warning("Make comparison for non-string value in selection action not fully implemented")
                # Test this case out in PyRAL: x == 12
                pyral_op = f" {relop} "
                # PyRAL specifies boolean values using ptyhon bool type, not strings
                # PyRAL uses ":" for string matches and "==" for numeric matches, so we need to determine the type
                # of the value

            phrase = f"{attr}{pyral_op}{value}"
            criteria_rphrases.append(phrase)
        return criteria_rphrases

