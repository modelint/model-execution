""" restrict.py -- executes the Restrict Action """

# System
from typing import TYPE_CHECKING, NamedTuple
import re

if TYPE_CHECKING:
    from mx.method import Method

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.actions.flow import ActiveFlow
from mx.rvname import declare_rvs


# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    activity_restrict_actions: str
    this_restrict_action: str
    restrict_table_action: str
    restriction_condition: str
    my_criteria: str
    my_eq_criteria: str
    my_comp_criteria: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "activity_restrict_actions", "this_restrict_action",
                      "restrict_table_action",
                      "restriction_condition", "my_criteria", "my_eq_criteria", "my_comp_criteria")
    return MMRVs(*rvs)


def str_to_bool(s: str) -> bool:
    """
    :param s: "True" or "true" or "False" or "false"
    :return: Corresponding Python bool value
    """
    tf = s.strip().lower()
    if tf == "true":
        return True
    elif tf == "false":
        return False
    else:
        raise ValueError(f"Invalid boolean string: {s}")

class Restrict(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Restrict Action on a domain model.

        :param action_id: ACTN<n> value identifying each Action instance
        :param activity: A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        #



        self.criteria : dict[int, str] = {}

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_mm_rvs(db=mmdb, owner=self.rvp)
        mmrv = self.mmrv  # For brevity

        # Lookup the Action instance
        # Start with all Restrict actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Restrict_Action",
                          svar_name=mmrv.activity_restrict_actions)
        # Narrow it down to this Restrict Action instance
        R = f"ID:<{action_id}>"
        restrict_action_t = Relation.restrict(db=mmdb, relation=mmrv.activity_restrict_actions, restriction=R,
                                              svar_name=mmrv.this_restrict_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.this_restrict_action)

        # Join it with the Table Action superclass to get the input / output flows
        restrict_table_action_t = Relation.join(db=mmdb, rname1=mmrv.this_restrict_action, rname2="Table_Action",
                                                svar_name=mmrv.restrict_table_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.restrict_table_action)

        self.source_flow_name = restrict_table_action_t.body[0]["Input_a_flow"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = restrict_table_action_t.body[0]["Output_flow"]
        # And the output of the Restrict Action will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Get the Restriction Condition
        rcond_r = Relation.semijoin(db=mmdb, rname1=mmrv.this_restrict_action, rname2="Restriction Condition",
                                    attrs={"ID": "Action", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=mmrv.restriction_condition)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.restriction_condition)

        # The supplied expression helps us define any complex boolean logic
        # in the restriction phrase to be created.
        self.predicate_str = rcond_r.body[0]["Expression"]  # TODO: Use this when we have a more interesting example

        # Get all Criteria
        Relation.semijoin(db=mmdb, rname1=mmrv.restriction_condition, rname2="Criterion", svar_name=mmrv.my_criteria)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.my_criteria)

        # Make a phrase for each criterion
        # TODO: incorporate and/or/not logic

        # Equivalence criteria
        self.make_eq_phrases()
        self.make_comparison_phrases()

        # Perform the selection
        selection_output_rv = Relation.declare_rv(db=self.domdb, owner=self.rvp, name="selection_output")
        R = self.make_rphrase()

        Relation.restrict(db=self.domdb, relation=self.source_flow.value, restriction=R.strip(),
                          svar_name=selection_output_rv)

        if self.activity.xe.debug:
            Relation.print(db=self.domdb, variable_name=selection_output_rv)

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=selection_output_rv,
                                                              flowtype=self.source_flow.flowtype)

        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)
        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)
        pass

    def make_eq_phrases(self):
        """
        """
        mmrv = self.mmrv
        # Look up the equivalence critiera, if any
        my_eq_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Equivalence_Criterion",
                                             svar_name=mmrv.my_eq_criteria)

        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.my_eq_criteria)

        for c in my_eq_criteria_r.body:
            cid = int(c["ID"])
            attr = c['Attribute'].replace(' ', '_')
            value = bool(c['Value'])
            # PyRAL specifies boolean values using ptyhon bool type, not strings
            value = str_to_bool(c['Value']) if c['Scalar'] == "Boolean" else value
            value = f"<{value}>" if ' ' in value else value

            phrase = f"{attr}:{value}"
            self.criteria[cid] = phrase

    def make_comparison_phrases(self):
        """
        """
        mmrv = self.mmrv
        # Look up the comparison critiera, if any
        my_comp_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Comparison_Criterion",
                                               svar_name=mmrv.my_comp_criteria)

        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.my_comp_criteria)

        for c in my_comp_criteria_r.body:
            cid = int(c["ID"])
            attr = c['Attribute'].replace(' ', '_')
            scalar_flow_name = c['Value']
            value = self.activity.flows[scalar_flow_name].value
            relop = c['Comparison']
            pyral_op = ':' if relop == '==' and isinstance(value, str) else relop
            # PyRAL specifies boolean values using ptyhon bool type, not strings
            # PyRAL uses ":" for string matches and "==" for numeric matches, so we need to determine the type
            # of the value
            value = f"<{value}>" if ' ' in value else value

            phrase = f"{attr}{pyral_op}{value}"
            self.criteria[cid] = phrase
        pass

    def make_rphrase(self) -> str:
        def replace_match(match):
            key = int(match.group())
            try:
                return f"{self.criteria[key]}"
            except KeyError:
                raise ValueError(f"No replacement found for key: {key}")

        return re.sub(r'\b\d+\b', replace_match, self.predicate_str)