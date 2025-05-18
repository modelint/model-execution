""" select.py -- executes the Select Action """

# System
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.method import Method  # TODO: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.actions.flow import ActiveFlow
from mx.rvname import declare_rvs


# See comment in scalar_switch.py
class RVs(NamedTuple):
    activity_select_actions: str
    this_select_action: str
    my_criteria: str
    my_eq_criteria: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> RVs:
    rvs = declare_rvs(db, owner, "activity_select_actions", "this_select_action", "my_criteria",
                      "my_eq_criteria")
    return RVs(*rvs)


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


class Select(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Select Action on a domain model.

        :param action_id: ACTN<n> value identifying each Action instance
        :param activity: A<n> Activity ID (for Method and State Activities)
        """

        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_my_module_rvs(db=mmdb, owner=self.rvp)
        mmrv = self.mmrv  # For brevity

        # Lookup the Action instance
        # Start with all Select actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Select_Action",
                          svar_name=mmrv.activity_select_actions)
        # Narrow it down to this Select Action instance
        R = f"ID:<{action_id}>"
        select_action_t = Relation.restrict(db=mmdb, relation=mmrv.activity_select_actions, restriction=R,
                                            svar_name=mmrv.this_select_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.this_select_action)

        self.source_flow_name = select_action_t.body[0]["Input_flow"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        if self.activity.xe.debug:
            Relation.print(db=self.domdb, variable_name=self.source_flow.value)
        pass

        # Get the destinatin flow name
        subclass_r = Relation.semijoin(db=mmdb, rname1=mmrv.this_select_action, rname2="Single_Select")
        if not subclass_r.body:
            subclass_r = Relation.semijoin(db=mmdb, rname1=mmrv.this_select_action, rname2="Many_Select")
        self.dest_flow_name = subclass_r.body[0]["Output_flow"]

        # Get all Criteria
        my_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.this_select_action, rname2="Criterion",
                                          attrs={"ID": "Action", "Activity": "Activity", "Domain": "Domain"},
                                          svar_name=mmrv.my_criteria)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.my_criteria)


        # Make a phrase for each criterion
        # TODO: ACTN5 uses a Comparison Criterion / Factor out processing of each kind of Criterion
        # TODO: Add the other two Criterion subclasses
        # TODO: incorporate and/or/not logic

        # Equivalence criteria
        eq_phrases = self.make_eq_phrases()

        criteria_rphrases = eq_phrases

        # Perform the selection
        selection_output_rv = Relation.declare_rv(db=self.domdb, owner=self.rvp, name="selection_output")
        R = ', '.join(criteria_rphrases)  # For now we will just and them all together using commas
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

    def make_eq_phrases(self) -> list[str]:
        """

        :return:
        """
        mmrv = self.mmrv
        # Look up the equivalence critiera, if any
        my_eq_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Equivalence_Criterion",
                                             svar_name=mmrv.my_eq_criteria)

        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.my_eq_criteria)

        criteria_rphrases: list[str] = []

        for c in my_eq_criteria_r.body:
            attr = c['Attribute'].replace(' ', '_')
            value = bool(c['Value'])
            # PyRAL specifies boolean values using ptyhon bool type, not strings
            value = str_to_bool(c['Value']) if c['Scalar'] == "Boolean" else value

            phrase = f"{attr}:<{value}>"
            criteria_rphrases.append(phrase)

        return criteria_rphrases

