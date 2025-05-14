""" select_action.py -- executes the Select Action """

from mx.actions.single_select import SingleSelect


class ZeroOneCardinalitySelect(SingleSelect):

    def __init__(self, non_scalar_flow):
        super.__init__()

    def execute(self):
        pass
