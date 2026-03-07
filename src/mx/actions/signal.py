""" signal_action.py -- Executes a Signal Action as defined in the SM Metamodel """

# System
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.database import Database  # Diagnostics

# MX
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow

class Signal(ActionExecution):

    monitor_external = False
    monitor_internal = False

    def __init__(self, action_id: str, activity: "ActivityExecution"):
        super().__init__(activity_execution=activity, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        pass