""" gate.py -- executes the Gate Action """

# System
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.method import Method

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics
from pyral.rtypes import Extent, Card

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.actions.flow import ActiveFlow
from mx.rvname import declare_rvs


# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    activity_rank_restrict_actions: str
    this_rank_restrict_action: str
    rank_restrict_table_action: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "activity_rank_restrict_actions", "this_rank_restrict_action",
                      "rank_restrict_table_action", )
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

# TODO: Copy paste from Restrict - redo for Rank Restrict
class Gate(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Gate Action on a domain model.

        :param action_id: ACTN<n> value identifying each Action instance
        :param activity: A<n> Activity ID (for Method and State Activities)
        """

        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_mm_rvs(db=mmdb, owner=self.rvp)
        mmrv = self.mmrv  # For brevity

        # Lookup the Action instance
        # Start with all Restrict actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Rank_Restrict_Action",
                          svar_name=mmrv.activity_rank_restrict_actions)
        # Narrow it down to this Restrict Action instance
        R = f"ID:<{action_id}>"
        rank_restrict_action_r = Relation.restrict(db=mmdb, relation=mmrv.activity_rank_restrict_actions,
                                                   restriction=R, svar_name=mmrv.this_rank_restrict_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.this_rank_restrict_action)

        # Join it with the Table Action superclass to get the input / output flows
        rank_restrict_table_action_r = Relation.join(db=mmdb, rname1=mmrv.this_rank_restrict_action,
                                                     rname2="Table_Action",
                                                     svar_name=mmrv.rank_restrict_table_action
                                                     )
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.rank_restrict_table_action)

        self.source_flow_name = rank_restrict_table_action_r.body[0]["Input_a_flow"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = rank_restrict_table_action_r.body[0]["Output_flow"]
        # And the output of the Restrict Action will be placed in the Activity flow dictionary
        # upon completion of this Action


        pass
        rank_restrict_output_rv = Relation.declare_rv(db=self.domdb, owner=self.rvp, name="rank_restrict_output")
        rank_restrict_action_t = rank_restrict_action_r.body[0]
        rank_attr = rank_restrict_action_t["Attribute"]
        rank_extent = Extent(rank_restrict_action_t["Extent"])
        rank_card = Card(rank_restrict_action_t["Selection_cardinality"].lower())
        Relation.rank_restrict(db=self.domdb, relation=self.source_flow.value, attr_name=rank_attr,extent=rank_extent,
                               card=rank_card, svar_name=rank_restrict_output_rv)
        if self.activity.xe.debug:
            Relation.print(db=self.domdb, variable_name=rank_restrict_output_rv)

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=rank_restrict_output_rv,
                                                              flowtype=self.source_flow.flowtype)

        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)
        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)

    def make_ranking_phrases(self) -> list[str]:
        """

        :return:
        """
        mmrv = self.mmrv
        # Look up the comparison critiera, if any
        my_comp_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Comparison_Criterion",
                                               svar_name=mmrv.my_comp_criteria)

        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.my_comp_criteria)

        criteria_rphrases: list[str] = []

        for c in my_comp_criteria_r.body:
            attr = c['Attribute'].replace(' ', '_')
            scalar_flow_name = c['Value']
            value = self.activity.flows[scalar_flow_name].value
            relop = c['Comparison']
            pyral_op = ':' if relop == '==' and isinstance(value, str) else relop
            # PyRAL specifies boolean values using ptyhon bool type, not strings
            # PyRAL uses ":" for string matches and "==" for numeric matches, so we need to determine the type
            # of the value

            phrase = f"{attr}{pyral_op}<{value}>"
            criteria_rphrases.append(phrase)
        return criteria_rphrases

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

    def make_comparison_phrases(self) -> list[str]:
        """

        :return:
        """
        mmrv = self.mmrv
        # Look up the comparison critiera, if any
        my_comp_criteria_r = Relation.semijoin(db=mmdb, rname1=mmrv.my_criteria, rname2="Comparison_Criterion",
                                               svar_name=mmrv.my_comp_criteria)

        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.my_comp_criteria)

        criteria_rphrases: list[str] = []

        for c in my_comp_criteria_r.body:
            attr = c['Attribute'].replace(' ', '_')
            scalar_flow_name = c['Value']
            value = self.activity.flows[scalar_flow_name].value
            relop = c['Comparison']
            pyral_op = ':' if relop == '==' and isinstance(value, str) else relop
            # PyRAL specifies boolean values using ptyhon bool type, not strings
            # PyRAL uses ":" for string matches and "==" for numeric matches, so we need to determine the type
            # of the value

            phrase = f"{attr}{pyral_op}<{value}>"
            criteria_rphrases.append(phrase)
        return criteria_rphrases
