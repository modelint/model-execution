""" extract.py  -- execute a relational extract action """

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
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs

# See comment in scalar_switch.py
class RVs(NamedTuple):
    activity_extract_switch_actions: str
    this_extract_action: str
    attribute: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> RVs:
    rvs = declare_rvs(db, owner, "activity_extract_actions", "this_extract_action", "attribute"
                      )
    return RVs(*rvs)

class Extract(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Extract Action on a domain model.

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
        # Start with all Rename actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Extract_Action",
                          svar_name=rv.activity_extract_switch_actions)
        # Narrow it down to this Extract Action instance
        R = f"ID:<{action_id}>"
        extract_action_r = Relation.restrict(db=mmdb, relation=rv.activity_extract_switch_actions, restriction=R,
                                             svar_name=rv.this_extract_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=rv.this_extract_action)

        extract_action_t = extract_action_r.body[0]
        self.source_flow_name = extract_action_t["Input_tuple"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        self.dest_flow_name = extract_action_t["Output_scalar"]

        self.attr = extract_action_t["Attribute"]
        input_tuple_r = Relation.project(db=self.domdb, relation=self.source_flow.value, attributes=(self.attr,))
        extracted_value = input_tuple_r.body[0][self.attr]

        self.activity.xe.mxlog.log(message=f"- Attribute: {self.attr}")
        self.activity.xe.mxlog.log(message="Flows")
        self.activity.xe.mxlog.log_nsflow(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                          flow_type=self.source_flow.flowtype, activity=self.activity,
                                          db=self.domdb, rv_name=self.source_flow.value)

        if self.activity.xe.debug:
            print(f"\nScalar value: {extracted_value} output on Flow: {self.dest_flow_name}")

        # Get attribute being read so we can look up its type
        attr_r = Relation.semijoin(db=mmdb, rname1=rv.this_extract_action, rname2="Table Attribute",
                                   attrs={"Attribute": "Name", "Table": "Table", "Domain": "Domain"},
                                   svar_name=rv.attribute)
        attr_t = attr_r.body[0]

        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=extracted_value, flowtype="scalar")
        self.activity.xe.mxlog.log_sflow(flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                         flow_type=attr_t["Scalar"], activity=self.activity)
        self.activity.xe.mxlog.log(message=f"Scalar value: [{extracted_value}]")

        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)
        # And since we are outputing a scalar flow, there is no domain rv output to preserve
        # In fact, we didn't define any domain rv's at all, so there are none to free

        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)
