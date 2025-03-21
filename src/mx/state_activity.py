""" state_activity.py -- A metamodel StateActivity """

class StateActivity:

    def __init__(self, state: str, state_model: str, domain: str):

        self.state = state
        self.state_model = state_model
        self.domain = domain


    def execute(self):
        pass
