""" restrict.py -- executes the Restrict Action """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple
import re

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics

# MX
from mx.log_table_config import TABLE, log_table
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.utility import *

_logger = logging.getLogger(__name__)

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    restrict_action: str
    restrict_table_action: str
    restriction_condition: str
    my_criteria: str
    my_eq_criteria: str
    my_comp_criteria: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "restrict_action", "restrict_table_action",
                      "restriction_condition", "my_criteria", "my_eq_criteria", "my_comp_criteria")
    return MMRVs(*rvs)

class Restrict(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Restrict Action on a domain model.

        Args:
            action_id:  The ACTN<n> value identifying each Action instance
            activity_execution: The A<n> Activity ID
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        self.criteria: dict[int, str] = {}

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_mm_rvs(db=mmdb, owner=self.owner)
        mmrv = self.mmrv  # For brevity

        # Lookup the Action instance
        Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="Restrict Action", svar_name=mmrv.restrict_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.restrict_action))

        # Join it with the Table Action superclass to get the input / output flows
        restrict_table_action_t = Relation.join(db=mmdb, rname1=mmrv.restrict_action, rname2="Table Action",
                                                svar_name=mmrv.restrict_table_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.restrict_table_action))

        self.source_flow_name = restrict_table_action_t.body[0]["Input_a_flow"]
        self.source_flow = self.activity_execution.flows[self.source_flow_name]

        self.dest_flow_name = restrict_table_action_t.body[0]["Output_flow"]
        # And the output of the Restrict Action will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Get the Restriction Condition
        rcond_r = Relation.semijoin(db=mmdb, rname1=mmrv.restrict_action, rname2="Restriction Condition",
                                    attrs={"ID": "Action", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=mmrv.restriction_condition)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.restriction_condition))

        # The supplied expression helps us define any complex boolean logic
        # in the restriction phrase to be created.
        self.predicate_str = rcond_r.body[0]["Expression"]  # TODO: Use this when we have a more interesting example

        # Get all Criteria
        Relation.semijoin(db=mmdb, rname1=mmrv.restriction_condition, rname2="Criterion", svar_name=mmrv.my_criteria)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.my_criteria))

        _logger.info(f"- Card: {rcond_r.body[0]["Selection_cardinality"]}")

        # Make a phrase for each criterion
        # TODO: incorporate and/or/not logic

        # Equivalence criteria
        self.make_eq_phrases()
        self.make_comparison_phrases()

        # Perform the selection
        selection_output_drv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="selection_output")
        R = self.make_rphrase()

        Relation.restrict(db=self.domdb, relation=self.source_flow.value, restriction=R.strip(),
                          svar_name=selection_output_drv)

        _logger.info(f"- Criteria: {R}")
        _logger.info("Flows")

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=self.source_flow.value))

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity_execution.flows[self.dest_flow_name] = ActiveFlow(value=selection_output_drv,
                                                                        flowtype=self.source_flow.flowtype)

        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                      flow_type=self.source_flow.flowtype,
                                      activity=self.activity_execution, rv_name=selection_output_drv))

        self.complete()

    def make_eq_phrases(self):
        """
        """
        mmrv = self.mmrv
        # Look up the equivalence criteria, if any
        my_eq_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Equivalence_Criterion",
                                             svar_name=mmrv.my_eq_criteria)

        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.my_eq_criteria))

        for c in my_eq_criteria_r.body:
            cid = int(c["ID"])
            attr = c['Attribute'].replace(' ', '_')
            value = bool(c['Value'])
            value = c['Value'].upper() if c['Scalar'] == "Boolean" else value  # TRUE or FALSE if boolean
            value = f"<{value}>" if ' ' in value else value

            phrase = f"{attr}:{value}"
            self.criteria[cid] = phrase

    def make_comparison_phrases(self):
        """
        """
        mmrv = self.mmrv
        # Look up the comparison critiera, if any
        my_comp_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Comparison Criterion",
                                               svar_name=mmrv.my_comp_criteria)

        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.my_comp_criteria))

        for c in my_comp_criteria_r.body:
            cid = int(c["ID"])
            attr = c['Attribute'].replace(' ', '_')
            scalar_flow_name = c['Value']
            value = self.activity_execution.flows[scalar_flow_name].value
            relop = c['Comparison']
            pyral_op = ':' if relop == '==' and isinstance(value, str) else relop
            # PyRAL specifies boolean values using ptyhon bool type, not strings
            # PyRAL uses ":" for string matches and "==" for numeric matches, so we need to determine the type
            # of the value
            value = f"<{value}>" if ' ' in value else value

            phrase = f"{attr}{pyral_op}{value}"
            self.criteria[cid] = phrase

    def make_rphrase(self) -> str:
        def replace_match(match):
            key = int(match.group())
            try:
                return f"{self.criteria[key]}"
            except KeyError:
                raise ValueError(f"No replacement found for key: {key}")

        return re.sub(r'\b\d+\b', replace_match, self.predicate_str)