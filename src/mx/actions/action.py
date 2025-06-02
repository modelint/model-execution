""" action.py -- manages Action execution """

# System
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb

class Action:

    def __init__(self, activity: "Method", anum: str, action_id: str):
        """

        :param activity:  Name of the encompassing Activity
        :param anum:  The Activity number
        :param action_id: The Action ID value unique to this Action within the Activity
        """
        self.anum = anum
        self.action_id = action_id
        self.activity = activity
        self.disabled = False

        # Do not execute this action unless ALL input flows have been enabled.
        # The preceding Wave should have enabled all required inputs, unless some upstream condition
        # evaluated as false. If so, this action must be skipped.

        # Check the Flow Dependency class for all required input Flow names
        R = f"To_action:<{action_id}>, Activity:<{activity.anum}>, Domain:<{activity.domain}>"
        dependencies_r = Relation.restrict(db=mmdb, relation="Flow Dependency", restriction=R)
        required_flow_names = [d["Flow"] for d in dependencies_r.body]
        # Check our dictionary of active flows and disable if any required input flows were not set
        # self.disabled = any(activity.flows[f] is None for f in required_flow_names)
        # Make a list of required inputs with no content set
        un_enabled_inputs = [f for f in required_flow_names if activity.flows[f] is None]
        for empty_flow in un_enabled_inputs[:]:  # Iterate over a copy since list will be mutated
            # Is it the output side of a Switched Data Flow?  If so, we need to propagate the content through the switch
            R = f"Input_flow:<{empty_flow}>, Activity:<{self.anum}>, Domain:<{self.activity.domain}>"
            result = Relation.restrict(db=mmdb, relation='Switched Data Flow', restriction=R)
            if not result.body:
                continue
            # Help: Assign switched_input_flow_name to the current empty_flow value
            un_enabled_inputs.remove(empty_flow)  # Remove from the original list
            switched_output_flow_name = empty_flow
            pass
        self.disabled = any(activity.flows[f] is None for f in required_flow_names)

        # Each subclass action should verify the disable status before attempting to execute

        # The domain alias is also the name of the TclRAL domain database session
        self.domdb = self.activity.domain_alias  # Abbreviated access since we use it alot

        # To make it possible to run Actions currently (in the future)
        # we want to ensure that the temporary relational variable names between two
        # concurrent executions of the same Activity (by different instances) do not collide.

        # So we create a naming prefix unique to this action execution instance.
        # We concatenate the anum, action id, and instance id value
        # instnace id value is the conatenation of each identifier attribute value
        instance_id_value = '_'.join(v for v in self.activity.instance.values())
        # relation variable prefix (rvp) is the full concatenation
        self.rvp = f"{self.activity.anum}_{action_id}_{instance_id_value}"
        # This value is then prepended to a descriptive name to create a relational variable name
        # used to access a relation stored inside the TclRAL db

