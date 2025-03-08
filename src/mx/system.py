""" system.py -- Represents the user's entire system """

# System
import logging

# Model Integration
from pyral.relation import Relation

# Model Execution
from mx.db_names import udb, mmdb
from mx.exceptions import *

_logger = logging.getLogger(__name__)

class System:

    def __init__(self):
        """
        Initialize the entire System
        """
        result = Relation.restrict(db=mmdb, relation='System')
        if not result.body:
            msg = f"System name not found in the user db"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.name = result.body[0]['Name']
        pass

