""" rank_restrict.py -- executes the Rank Restrict Action """

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
class RankRestrict(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Rank Restrict Action on a domain model.

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

        rank_restrict_table_action_t = rank_restrict_table_action_r.body[0]
        self.activity.xe.mxlog.log(message=f"- Attribute: {rank_restrict_table_action_t["Attribute"]}")
        self.activity.xe.mxlog.log(message=f"- Extent: {rank_restrict_table_action_t["Extent"]}")
        self.activity.xe.mxlog.log(message=f"- Card: {rank_restrict_table_action_t["Selection_cardinality"]}")
        self.activity.xe.mxlog.log(message="Flows")

        self.source_flow_name = rank_restrict_table_action_t["Input_a_flow"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        self.activity.xe.mxlog.log_nsflow(flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                          flow_type=self.source_flow.flowtype, activity=self.activity,
                                          db=self.domdb, rv_name=self.source_flow.value)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = rank_restrict_table_action_t["Output_flow"]
        # And the output of the Restrict Action will be placed in the Activity flow dictionary
        # upon completion of this Action

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

        self.activity.xe.mxlog.log_nsflow(flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
                                          flow_type=self.source_flow.flowtype, activity=self.activity,
                                          db=self.domdb, rv_name=rank_restrict_output_rv)
        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)
        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)