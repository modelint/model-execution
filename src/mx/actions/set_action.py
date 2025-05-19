""" set_action.py  -- execute a relational join, union, or subtract action """

# System
from typing import TYPE_CHECKING, NamedTuple

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
    activity_set_actions: str
    this_set_action: str
    set_table_action: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "activity_set_actions", "this_union_action",
                      "set_table_action")
    return MMRVs(*rvs)

class SetAction(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Set Action on a domain model.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)
        _rv_before_mmdb = Database.get_rv_names(db=mmdb)
        _rv_before_dom = Database.get_rv_names(db=self.domdb)

        # Get a NamedTuple with a field for each relation variable name
        mmrv = declare_mm_rvs(db=mmdb, owner=self.rvp)

        # Lookup the Action instance
        # Start with all Set Actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Set_Action",
                          svar_name=mmrv.activity_set_actions)
        # Narrow it down to this Set Action instance
        R = f"ID:<{action_id}>"
        Relation.restrict(db=mmdb, relation=mmrv.activity_set_actions, restriction=R,
                          svar_name=mmrv.this_set_action)

        # Join it with the Table Action superclass to get the input / output flows
        set_table_action_t = Relation.join(db=mmdb, rname1=mmrv.this_set_action, rname2="Table_Action",
                                              svar_name=mmrv.set_table_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.set_table_action)

        # Extract input and output flows required by the Union Action
        union_table_values = union_table_action_t.body[0]  # convenient abbreviation of the rename table action tuple body
        self.source_flow_name = union_table_values["Input_a_flow"]  # Name like F1, F2, etc
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = union_table_values["Output_flow"]
        # And the output of the Union will be placed in the Activity flow dictionary
        # upon completion of this Action

