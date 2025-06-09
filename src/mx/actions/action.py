""" action.py -- manages Action execution """

# System
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb

# These actions do not output a non-scalar flow and, thus, do not declare
# an output database variable to be freed up upon activity completion
no_nsflow_output_actions = {"scalarswitch", "gate", "read", "extract"}

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
        self.action_type = type(self).__name__.lower()

        # Do not execute this action unless ALL input flows have been enabled.
        # The preceding Wave should have enabled all required inputs, unless some upstream condition
        # evaluated as false. If so, this action must be skipped.

        # Check the Flow Dependency class for all required input Flow names
        R = f"To_action:<{action_id}>, Activity:<{activity.anum}>, Domain:<{activity.domain}>"
        dependencies_r = Relation.restrict(db=mmdb, relation="Flow Dependency", restriction=R)
        required_flow_names = [d["Flow"] for d in dependencies_r.body]
        # Check our dictionary of active flows and disable if any required input flows were not set
        if self.action_type == "gate":
            self.disabled = all(activity.flows[f] is None for f in required_flow_names)
        else:
            self.disabled = any(activity.flows[f] is None for f in required_flow_names)

        if not self.disabled and self.action_type not in no_nsflow_output_actions:
            # Since this Action will be executed, it may produce one or more non scalar flow
            # (relation) outputs, and thus set a database variable for each. These rv variables
            # will be freed up upon completion of the Activity.
            # We can't free them up earlier since any flow content in an rv must be available while the activity
            # executes.  (Strictly speaking, we could free them up piecemeal once there are no more consumers, but
            # it's easier and less error prone to just free them all up after the activity completes.
            self.activity.executed_actions.append(self.action_id)

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

        if self.disabled:
            self.activity.xe.mxlog.log(message="DISABLED")

