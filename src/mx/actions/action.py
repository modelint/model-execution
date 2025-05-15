""" action.py -- manages Action execution """

# System
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

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

