""" method.py -- class method """

# System
import logging

# Model Integration
from pyral.relation import Relation

# MX
from mx.activity import Activity
from mx.bridge import NamedValues
from db_names import mmdb
from exceptions import *

_logger = logging.getLogger(__name__)

class Method(Activity):

    def __init__(self, name: str, class_name: str, domain_name: str,
                 instance_id: NamedValues, parameters: NamedValues):
        """

        :param name:
        :param class_name:
        :param domain_name:
        :param instance_id:
        :param parameters:
        """
        self.name = name
        self.instance = instance_id
        self.class_name = class_name
        self.xi_flow = None

        R = f"Name:<{self.name}>, Class:<{self.class_name}>, Domain:<{domain_name}>"
        result = Relation.restrict(db=mmdb, relation='Method', restriction=R)
        if not result.body:
            msg = f"Method [{domain_name}:{self.class_name}.{self.name}] not found in metamodel db"
            _logger.error(msg)
            raise MXMetamodelDBException(msg)

        anum = result.body[0]['Anum']
        self.xi_flow = result.body[0]['Executing_instance_flow']

        super().__init__(domain=domain_name, anum=anum, parameters=parameters)

        pass