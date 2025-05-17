""" rename.py  -- execute a relational rename action """

# System
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.actions.flow import ActiveFlow

class Rename(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Rename Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Lookup the Action instance
        # Start with all Rename actions in this Activity
        activity_rename_actions_mrv = Relation.declare_rv(db=mmdb, owner=self.rvp, name="activity_rename_action")
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Rename_Action",
                          svar_name=activity_rename_actions_mrv)

        # Narrow it down to this Rename Action instance
        R = f"ID:<{action_id}>"
        this_rename_action_mrv = Relation.declare_rv(db=mmdb, owner=self.rvp, name="this_rename_action")
        Relation.restrict(db=mmdb, relation=activity_rename_actions_mrv, restriction=R, svar_name=this_rename_action_mrv)
        # Join it with the Table Action superclass to get the input / output flows
        rename_table_action_mrv = Relation.declare_rv(db=mmdb, owner=self.rvp, name="rename_table_action")
        rename_table_action_t = Relation.join(db=mmdb, rname1=this_rename_action_mrv, rname2="Table_Action",
                                              svar_name=rename_table_action_mrv)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=rename_table_action_mrv)

        # Extract input and output flows required by the Traversal Action
        rename_values = rename_table_action_t.body[0]  # convenient abbreviation of the rename table action tuple body
        self.source_flow_name = rename_values["Input_a_flow"]  # Name like F1, F2, etc
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = rename_values["Output_flow"]
        # And the output of the Rename will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Rename
        rename_output_drv = Relation.declare_rv(db=self.domdb, owner=self.rvp, name="rename_output")
        Relation.rename(db=self.domdb, names={rename_values["From_attribute"]: rename_values["To_attribute"]},
                        relation=self.source_flow.flowtype, svar_name=rename_output_drv)
        if self.activity.xe.debug:
            Relation.print(db=self.domdb, variable_name=rename_output_drv)

        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=rename_output_drv, flowtype=rename_values["To_table"])
        # The domain rv above is retained since it is an output flow, so we don't free it until the Activity completes

        # This action's mmdb rvs are no longer needed)
        Relation.free_rvs(db=mmdb, owner=self.rvp)

        _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
        _rv_after_dom_free = Database.get_rv_names(db=self.domdb)
        pass
