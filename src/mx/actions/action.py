""" action.py -- manages Action execution """


class Action:

    def __init__(self, anum: str, action_id: str):
        self.anum = anum
        self.action_id = action_id

    def execute(self):
        pass
