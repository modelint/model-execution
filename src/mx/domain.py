""" domain.py -- Represents a modeled domain defined in the metamodel """

# System
import logging

# Model Integration
from pyral.relation import Relation

# Model Execution
from mx.db_names import udb, mmdb
from mx.exceptions import *

_logger = logging.getLogger(__name__)


class Domain:

    def __init__(self, name:str):


def initiate_lifecycles(self):
    """

    :param self:
    :return:
    """
    R = f"Domain:<{domain}>"
    result = Relation.restrict(db=mmdb, relation='Lifecycle', restriction=R)

