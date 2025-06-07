""" scalar_switch.py  -- execute a scalar_switch action """

# System
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.method import Method  # TODO: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation
from pyral.relation import Database  # Diagnostic

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs

# For each python string variable that will hold the name of a temporary TclRAL relation used in this module,
# a corresponding attribute is defined. An instance of this tuple is generated with each attribute holding
# a string naming some temporary TclRAL relation variable.
# Each such variable can then be supplied in the svar_name argument
# to create the TclRAL relation. Later that same variable can be used to supply a relation argument to other
# PyRAL methods.
class RVs(NamedTuple):
    activity_scalar_switch_actions: str
    this_scalar_switch_action: str
    cases: str
    mvals: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> RVs:
    rvs = declare_rvs(db, owner, "activity_scalar_switch_actions", "this_scalar_switch_action", "cases", "mvals")
    return RVs(*rvs)

class ScalarSwitch(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Scalar Switch Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        rv = declare_my_module_rvs(db=mmdb, owner=self.rvp)

        # Lookup the Action instance
        # Start with all Switch actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Scalar Switch Action",
                          svar_name=rv.activity_scalar_switch_actions)
        # Narrow it down to this Switch Action instance
        R = f"ID:<{action_id}>"
        scalar_switch_action_t = Relation.restrict(db=mmdb, relation=rv.activity_scalar_switch_actions, restriction=R,
                                                   svar_name=rv.this_scalar_switch_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=rv.this_scalar_switch_action)

        self.source_flow_name = scalar_switch_action_t.body[0]["Scalar_input"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)

        cases_r = Relation.semijoin(db=mmdb, rname1=rv.this_scalar_switch_action, rname2="Case",
                                    attrs={"ID": "Switch_action", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=rv.cases)
        mvals_r = Relation.semijoin(db=mmdb, rname1=rv.cases, rname2="Match Value",
                                    attrs={"Flow": "Case_flow", "Activity": "Activity", "Domain": "Domain"},
                                    svar_name=rv.mvals)
        R = f"Value:<{self.source_flow.value}>"
        selected_case_r = Relation.restrict(db=mmdb, relation=rv.mvals, restriction=R)
        scase_tuple = selected_case_r.body[0]
        self.activity.flows[scase_tuple["Case_flow"]] = ActiveFlow(value=scase_tuple["Value"], flowtype=self.source_flow.flowtype)

        self.activity.xe.mxlog.log(message="Flows")
        self.activity.xe.mxlog.log_sflow(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                         flow_type=self.source_flow.flowtype, activity=self.activity)
        self.activity.xe.mxlog.log(message=f"Scalar value: {scase_tuple['Value']}")
        # We don't need our mmdb relation variables
        Relation.free_rvs(db=mmdb, owner=self.rvp)
        # And since we are outputing a scalar flow, there is no domain rv output to preserve
        # In fact, we didn't define any domain rv's at all, so there are none to free

        # Diagnostic verification
        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)
