""" rename.py  -- execute a relational rename action """

# System
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.actions.flow import ActiveFlow
from mx.rvname import RVN


class Rename(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Traverse Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Lookup the Action instance
        # Start with all Rename actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Rename_Action")
        # Narrow it down to this Rename Action instance
        R = f"ID:<{action_id}>"
        Relation.restrict(db=mmdb, restriction=R)
        # Join it with the Table Action superclass to get the input / output flows
        rename_table_action_rv = RVN.name(db=mmdb, name="rename_table_action")
        rename_table_action_t = Relation.join(db=mmdb, rname2="Table_Action", svar_name=rename_table_action_rv)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=rename_table_action_rv)

        # Extract input and output flows required by the Traversal Action
        rename_values = rename_table_action_t.body[0]  # convenient abbreviation of the rename table action tuple body
        self.source_flow_name = rename_values["Input_a_flow"]  # Name like F1, F2, etc
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = rename_values["Output_flow"]
        # And the output of the Rename will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Rename
        rename_output_rv = RVN.name(db=mmdb, name="rename_output")
        Relation.rename(db=self.domdb, names={rename_values["From_attribute"]: rename_values["To_attribute"]},
                        relation=self.source_flow.flowtype, svar_name=rename_output_rv)
        if self.activity.xe.debug:
            Relation.print(db=self.domdb, variable_name=rename_output_rv)

        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=rename_output_rv, flowtype=rename_values["To_table"])

