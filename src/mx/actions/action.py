""" action.py -- manages Action execution """

# System
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

class Action:

    def __init__(self, activity: "Method", anum: str, action_id: str):
        self.anum = anum
        self.action_id = action_id
        self.activity = activity
        # self.domdb = self.activity.domain_alias  # Easy access to the name of our domain's database

    def execute(self):
        pass
