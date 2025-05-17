""" read.py  -- execute a relational read action """

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
    activity_read_switch_actions: str
    this_read_action: str
    attr_read_accesses: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> RVs:
    rvs = declare_rvs(db, owner, "activity_read_switch_actions", "this_read_action",
                      "attr_read_accesses",)
    return RVs(*rvs)

class Read(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Read Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Get a NamedTuple with a field for each relation variable name
        rv = declare_my_module_rvs(db=mmdb, owner=self.rvp)

        # Lookup the Action instance
        # Start with all Rename actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Read_Action",
                          svar_name=rv.activity_read_switch_actions)
        # Narrow it down to this Read Action instance
        R = f"ID:<{action_id}>"
        read_action_t = Relation.restrict(db=mmdb, relation=rv.activity_read_switch_actions, restriction=R,
                                          svar_name=rv.this_read_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=rv.this_read_action)

        self.source_flow_name = read_action_t.body[0]["Instance_flow"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)

        attribute_read_accesses_r = Relation.semijoin(db=mmdb, rname1=rv.this_read_action,
                                                      rname2="Attribute Read Access",
                                                      attrs={"ID": "Read_action",
                                                             "Activity": "Activity", "Domain": "Domain"},
                                                      svar_name=rv.attr_read_accesses)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=rv.attr_read_accesses)

        for access in attribute_read_accesses_r.body:
            attr_value_t = Relation.project(db=self.domdb, attributes=(access["Attribute"],),
                                            relation=self.source_flow.value)
            attr_value = attr_value_t.body[0][access["Attribute"]]
            self.activity.flows[access["Output_flow"]] = ActiveFlow(value=attr_value, flowtype="scalar")

        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)
        # And since we are outputing a scalar flow, there is no domain rv output to preserve
        # In fact, we didn't define any domain rv's at all, so there are none to free

        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)
