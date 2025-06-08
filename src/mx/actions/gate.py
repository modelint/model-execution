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
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs

# See comment in scalar_switch.py
class MMRVs(NamedTuple):
    activity_gate_actions: str
    this_gate_action: str
    flow_deps: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "activity_gate_actions", "this_gate_action", "flow_deps")
    return MMRVs(*rvs)

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

        self.activity.xe.mxlog.log(message="Flows")
        # Lookup the Action instance
        # Start with all Gate actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Gate Action",
                          svar_name=mmrv.activity_gate_actions)

        # Narrow it down to this Restrict Action instance
        R = f"ID:<{action_id}>"
        gate_action_r = Relation.restrict(db=mmdb, relation=mmrv.activity_gate_actions, restriction=R,
                                          svar_name=mmrv.this_gate_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.this_gate_action)

        # Lookup the Action flow dependency
        flow_deps_r = Relation.semijoin(db=mmdb, rname1=mmrv.this_gate_action, rname2="Flow Dependency",
                                        attrs={"ID": "To_action", "Activity": "Activity", "Domain": "Domain"},
                                        svar_name=mmrv.flow_deps)

        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.flow_deps)

        gate_action_t = gate_action_r.body[0]
        output_flow_name = gate_action_t["Output_flow"]
        input_flow_names = [t["Flow"] for t in flow_deps_r.body]
        input_values = {n: activity.flows[n] for n in input_flow_names if activity.flows[n]}
        if len(input_values) > 1:
            pass
        assert(len(input_values) == 1)
        input_flow_name, activity.flows[output_flow_name] = next(iter(input_values.items()))
        if self.activity.xe.debug:
            print(f"\nGate: {self.action_id} passing Flow: {input_flow_name} to Flow: {output_flow_name}")
            Relation.print(db=self.domdb, variable_name=activity.flows[output_flow_name].value)

        self.activity.xe.mxlog.log_nsflow(flow_name=input_flow_name, flow_dir=FlowDir.IN,
                                          flow_type=activity.flows[input_flow_name].flowtype, activity=self.activity,
                                          db=self.domdb, rv_name=activity.flows[input_flow_name].value)
        self.activity.xe.mxlog.log_nsflow(flow_name=output_flow_name, flow_dir=FlowDir.OUT,
                                          flow_type=activity.flows[output_flow_name].flowtype, activity=self.activity,
                                          db=self.domdb, rv_name=activity.flows[output_flow_name].value)

        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)
        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)
