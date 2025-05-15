""" rename.py  -- execute a relational rename action """

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
from mx.rvname import declare_rvs

# See comment in scalar_switch.py
class RVs(NamedTuple):
    rename_table_action: str
    rename_output: str

# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_my_module_rvs(db: str, owner: str) -> RVs:
    rvs = declare_rvs(db, owner, "rename_table_action", "rename_output", )
    return RVs(*rvs)


class Rename(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Rename Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Get a NamedTuple with a field for each relation variable name
        rv = declare_my_module_rvs(db=mmdb, owner=self.rvp)

        # Lookup the Action instance
        # Start with all Rename actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Rename_Action")
        # Narrow it down to this Rename Action instance
        R = f"ID:<{action_id}>"
        Relation.restrict(db=mmdb, restriction=R)
        # Join it with the Table Action superclass to get the input / output flows
        rename_table_action_t = Relation.join(db=mmdb, rname2="Table_Action", svar_name=rv.rename_table_action)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=rv.rename_table_action)

        # Extract input and output flows required by the Traversal Action
        rename_values = rename_table_action_t.body[0]  # convenient abbreviation of the rename table action tuple body
        self.source_flow_name = rename_values["Input_a_flow"]  # Name like F1, F2, etc
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = rename_values["Output_flow"]
        # And the output of the Rename will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Rename
        Relation.rename(db=self.domdb, names={rename_values["From_attribute"]: rename_values["To_attribute"]},
                        relation=self.source_flow.flowtype, svar_name=rv.rename_output)
        if self.activity.xe.debug:
            Relation.print(db=self.domdb, variable_name=rv.rename_output)

        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=rv.rename_output, flowtype=rename_values["To_table"])

