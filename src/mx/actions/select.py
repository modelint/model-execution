""" select.py -- executes the Select Action """

from mx.actions.action import Action

class Select(Action):

    def __init__(self, non_scalar_flow):
        super().__init__()

    def create(self):
        """
        Determine which subclass object to create

        :return:
        """
        pass

    def execute(self):
        pass
