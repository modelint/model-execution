""" method.py -- class method """

# System

# Model Integration
from pyral.relation import Relation

# MX
from mx.activity import Activity
from mx.bridge import NamedValues
from db_names import mmdb
from exceptions import *


class Method(Activity):

    def __init__(self, name: str, class_name: str, domain_alias: str,
                 instance_id: NamedValues, parameters: NamedValues):
        """

        :param name:
        :param class_name:
        :param domain_alias:
        :param instance_id:
        :param parameters:
        """
        self.name = name
        self.instance = instance_id
        self.class_name = class_name
        self.xi_flow = None

        # Get the domain name from the alias
        R = f"Alias:<{domain_alias}>"
        result = Relation.restrict(db=mmdb, relation='Domain', restriction=R)
        if len(result.body) != 1:
            pass
        domain_name = result.body[0]['Name']

        R = f"Name:<{self.name}>, Class:<{self.class_name}>, Domain:<{domain_name}>"
        result = Relation.restrict(db=mmdb, relation='Method', restriction=R)
        if len(result.body) != 1:
            pass
        anum = result.body[0]['Anum']
        self.xi_flow = result.body[0]['Executing_instance_flow']

        super().__init__(domain=domain_name, anum=anum, parameters=parameters)

        pass