""" action_execution.py -- manages Action execution """

# System
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb

_logger = logging.getLogger(__name__)

# These actions do not output a non-scalar flow and, thus, do not declare
# an output database variable to be freed up upon activity completion
no_nsflow_output_actions = {"scalarswitch", "gate", "read", "extract"}

class ActionExecution:

    def __init__(self, activity_execution: "ActivityExecution", action_id: str):
        """
        Execute an Action

        Args:
            activity_execution:
            action_id:
        """
        self.activity_execution = activity_execution
        self.action_id = action_id
        self.action_type = type(self).__name__.lower()
        _logger.info(f"\n\n    ::: STARTING {{{self.action_id}}}: {self.activity_execution.anum} ({self.action_type}) :::\n")
        # _logger.info(f"Executing action: {self.activity_execution.anum}-{action_id}({self.action_type})")

        # The domain alias is also the name of the TclRAL domain database session
        self.domdb = self.activity_execution.domain.alias  # Abbreviated access since we use it alot

        # Action owner name uses Activity owner name as its prefix
        self.owner = f"{self.activity_execution.owner_name}_{action_id}_{self.action_type}"

        # Check the Flow Dependency class for all required input Flow names
        R = f"To_action:<{action_id}>, Activity:<{self.activity_execution.anum}>, Domain:<{self.activity_execution.domain.name}>"
        dependencies_r = Relation.restrict(db=mmdb, relation="Flow Dependency", restriction=R)
        required_flow_names = [d["Flow"] for d in dependencies_r.body]
        # Check our dictionary of active flows and disable if any required input flows were not set
        if self.action_type == "gate":
            self.disabled = all(self.activity_execution.flows[f] is None for f in required_flow_names)
        else:
            self.disabled = any(self.activity_execution.flows[f] is None for f in required_flow_names)
        pass

        # To simplify the lookup of each subclass of Action, we extend the activity tuple with our action id
        # Then the action will do a semijoin to its subclass, Read Action, for example.
        Relation.declare_rv(db=mmdb, owner=self.owner, name="action_mmrv")
        Relation.extend(db=mmdb, relation=self.activity_execution.activity_rvn, attrs={'ID': self.action_id},
                        svar_name="action_mmrv")
        self.action_mmrv = "action_mmrv"

    def complete(self):
        _logger.info(f"\n\n    ::: COMPLETED {{{self.action_id}}}: {self.activity_execution.anum} ({self.action_type}) :::\n")

