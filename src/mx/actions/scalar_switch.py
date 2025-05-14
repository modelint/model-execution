""" scalar_switch.py  -- execute a scalar_switch action """

# System
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.actions.flow import ActiveFlow
from mx.rvname import RVN, declare_rvs

class RVs(NamedTuple):
    activity_scalar_switch_actions: str
    this_scalar_switch_action: str
    cases: str
    mvals: str

# def declare_rvs(db: str, owner: str, *names: str) -> RVs:
#     rv_map = {
#         f"{name}": Relation.declare_rv(db=db, owner=owner, name=name)
#         for name in names
#     }
#     return RVs(**rv_map)

class ScalarSwitch(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Scalar Switch Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        rv = declare_rvs(mmdb, self.rvp, "activity_scalar_switch_actions",
                         "this_scalar_switch_action", "cases", "mvals")

        # Lookup the Action instance
        # Start with all Switch actions in this Activity
        # activity_scalar_switch_actions_rv = f"{self.rvp}activity_scalar_switch_actions"
        # activity_scalar_switch_actions_rv = Relation.declare_rv(db=mmdb, owner=self.rvp,
        #                                                         name="activity_scalar_switch_actions")
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Scalar Switch Action",
                          svar_name=rv.activity_scalar_switch_actions)
        # Narrow it down to this Switch Action instance
        # this_scalar_switch_action_rv = Relation.declare_rv(db=mmdb, owner=self.rvp,
        #                                                    name="this_scalar_switch_action")
        R = f"ID:<{action_id}>"
        scalar_switch_action_t = Relation.restrict(db=mmdb, relation=rv.activity_scalar_switch_actions, restriction=R,
                                                   svar_name=rv.this_scalar_switch_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=rv.this_scalar_switch_action)

        self.source_flow_name = scalar_switch_action_t.body[0]["Scalar_input"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)

        # cases_rv = Relation.declare_rv(db=mmdb, owner=self.rvp, name="cases")
        cases_r = Relation.semijoin(db=mmdb, rname1=rv.this_scalar_switch_action, rname2="Case",
                                    attrs={"ID": "Switch_action", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=rv.cases)
        # mvals_rv = Relation.declare_rv(db=mmdb, owner=self.rvp, name="mvals")
        mvals_r = Relation.semijoin(db=mmdb, rname1=rv.cases, rname2="Match Value",
                                    attrs={"Flow": "Case_flow", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=rv.mvals)
        R = f"Value:<{self.source_flow.value}>"
        selected_case_r = Relation.restrict(db=mmdb, relation=rv.mvals, restriction=R)
        scase_tuple = selected_case_r.body[0]
        self.activity.flows[scase_tuple["Case_flow"]] = ActiveFlow(value=scase_tuple["Value"], flowtype=self.source_flow.flowtype)

        Relation.free_rvs(db=mmdb, owner=self.rvp)

        pass