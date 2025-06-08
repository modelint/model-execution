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
from mx.actions.flow import ActiveFlow, FlowDir
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

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

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
        set_table_action_r = Relation.join(db=mmdb, rname1=mmrv.this_set_action, rname2="Table_Action",
                                           svar_name=mmrv.set_table_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.set_table_action)

        # Extract input and output flows required by the Union Action
        set_table_action_t = set_table_action_r.body[0]
        self.activity.xe.mxlog.log(message=f"- Operation: {set_table_action_t["Operation"]}")
        self.activity.xe.mxlog.log(message="Flows")
        # convenient abbreviation of the rename table action tuple body
        self.source_A_name = set_table_action_t["Input_a_flow"]  # Name like F1, F2, etc
        self.source_B_name = set_table_action_t["Input_b_flow"]
        self.source_A_flow = self.activity.flows[self.source_A_name]  # The active content of source flow (value, type)
        self.source_B_flow = self.activity.flows[self.source_B_name]  # The active content of source flow (value, type)
        self.activity.xe.mxlog.log_nsflow(flow_name=self.source_A_name, flow_dir=FlowDir.IN,
                                          flow_type=self.source_A_flow.flowtype, activity=self.activity,
                                          db=self.domdb, rv_name=self.source_A_flow.value)
        self.activity.xe.mxlog.log_nsflow(flow_name=self.source_B_name, flow_dir=FlowDir.IN,
                                          flow_type=self.source_B_flow.flowtype, activity=self.activity,
                                          db=self.domdb, rv_name=self.source_B_flow.value)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = set_table_action_t["Output_flow"]
        # And the output of the Set Action will be placed in the Activity flow dictionary
        # upon completion of this Action

        set_action_name = set_table_action_r.body[0]["Operation"]
        set_action_output_drv = Relation.declare_rv(db=self.domdb, owner=self.rvp, name="set_action_output")
        if set_action_name == "UNION":
            Relation.union(db=self.domdb, relations=(self.source_A_flow.value, self.source_B_flow.value),
                           svar_name=set_action_output_drv)
        elif set_action_name == "JOIN":
            Relation.join(db=self.domdb, rname1=self.source_A_flow.value, rname2=self.source_B_flow.value,
                          svar_name=set_action_output_drv)
        else:
            pass  # TODO: SUBTRACT, ...
        pass
        if self.activity.xe.debug:
            Relation.print(db=self.domdb, variable_name=set_action_output_drv)

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=set_action_output_drv,
                                                              flowtype=self.source_A_flow.flowtype)

        self.activity.xe.mxlog.log_nsflow(flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                          flow_type=self.source_A_flow.flowtype, activity=self.activity,
                                          db=self.domdb, rv_name=set_action_output_drv)
        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)

        # Built the project phrase
        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)

