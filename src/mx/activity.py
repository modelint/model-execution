""" activity.py -- A metamodel Activity """

# MX
from mx.bridge import NamedValues

class Activity:

    def __init__(self, domain: str, anum: str, parameters: NamedValues):
        """

        :param domain:
        :param anum:
        :param parameters:
        """
        self.anum = anum
        self.parameters = parameters
        self.domain = domain

    def execute(self):
        pass
