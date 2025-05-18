""" project.py  -- execute a relational project action """

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
class MMRVs(NamedTuple):
    activity_project_actions: str
    this_project_action: str
    project_table_action: str
    projected_attrs: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(db: str, owner: str) -> MMRVs:
    rvs = declare_rvs(db, owner, "activity_project_actions", "this_project_action",
                      "project_table_action", "projected_attrs")
    return MMRVs(*rvs)

class Project(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Project Action on a domain model.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)
        _rv_before_mmdb = Database.get_rv_names(db=mmdb)
        _rv_before_dom = Database.get_rv_names(db=self.domdb)

        # Get a NamedTuple with a field for each relation variable name
        mmrv = declare_mm_rvs(db=mmdb, owner=self.rvp)

        # Lookup the Action instance
        # Start with all Project Actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Project_Action",
                          svar_name=mmrv.activity_project_actions)
        # Narrow it down to this Project Action instance
        R = f"ID:<{action_id}>"
        Relation.restrict(db=mmdb, relation=mmrv.activity_project_actions, restriction=R,
                          svar_name=mmrv.this_project_action)

        # Join it with the Table Action superclass to get the input / output flows
        project_table_action_t = Relation.join(db=mmdb, rname1=mmrv.this_project_action, rname2="Table_Action",
                                              svar_name=mmrv.project_table_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.project_table_action)

        # Extract input and output flows required by the Project Action
        project_table_values = project_table_action_t.body[0]  # convenient abbreviation of the rename table action tuple body
        self.source_flow_name = project_table_values["Input_a_flow"]  # Name like F1, F2, etc
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = project_table_values["Output_flow"]
        # And the output of the Rename will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Get the attributes to project
        projected_attrs_r = Relation.semijoin(db=mmdb, rname1=mmrv.this_project_action, rname2="Projected Attribute",
                                              attrs={"ID": "Project_action", "Activity": "Activity", "Domain": "Domain"},
                                              svar_name=mmrv.projected_attrs)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=mmrv.projected_attrs)

        project_output_drv = Relation.declare_rv(db=self.domdb, owner=self.rvp, name="project_output")

        P = tuple(a["Attribute"] for a in projected_attrs_r.body)
        Relation.project(db=self.domdb, relation=self.source_flow.value, attributes=P, svar_name=project_output_drv)
        if self.activity.xe.debug:
            Relation.print(db=self.domdb, variable_name=project_output_drv)

        # Join the project action to the Relation Flow to get the type of the output
        # as a concatenated sequence of attribute type pairs delimited by underscores
        rflow_r = Relation.semijoin(db=mmdb, rname1=mmrv.project_table_action, rname2="Relation_Flow",
                                    attrs={"Output_flow":"ID", "Activity":"Activity", "Domain":"Domain"})
        output_table_type = rflow_r.body[0]["Type"]

        # Assign result to output flow
        # For a select action, the source and dest flow types must match
        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=project_output_drv,
                                                              flowtype=output_table_type)

        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)

        # Built the project phrase
        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)

