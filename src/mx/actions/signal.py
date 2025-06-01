""" signal_action.py -- Executes a Signal Action as defined in the SM Metamodel """

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

class SignalAction(Action):

    def __init__(self, action_id: str, activity: "Method"):
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        pass