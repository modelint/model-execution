""" system.py -- Represents the user's entire system """

# System
import logging
from pathlib import Path
from typing import NamedTuple, Dict

# Model Integration
from pyral.relation import Relation
from pyral.database import Database

# Model Execution
from mx.domain_model_db import DomainModelDB
from mx.context import Context
from mx.db_names import udb, mmdb
from mx.exceptions import *

ExecutableDomain = NamedTuple('ExecutableDomain', schema=DomainModelDB, context=Context)

_logger = logging.getLogger(__name__)

class System:

    def __init__(self, types_dir: Path):
        """
        Set the system name

        :param types_dir: Directory containing type mapping files
        """
        # Get the System name from the populated metamodel
        result = Relation.restrict(db=mmdb, relation='System')
        if not result.body:
            msg = f"System name not found in the user db"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.name = result.body[0]['Name']
        self.domains: Dict[str, ExecutableDomain] = {}  # Each domain loaded into this environment
        self.types_dir = types_dir

    def init_domains(self, debug: bool = False):
        """
        Create a database containing all user model domains in the system.

        :param debug:
        :return:
        """
        Database.open_session(name=udb)  # User models created in this database

        result = Relation.restrict(db=mmdb, relation='Domain')
        for d in result.body:
            filename = d['Name'].replace(' ', '_')+".yaml"
            db_types = self.types_dir / filename
            domain_db = DomainModelDB(domain=d['Name'], db_types=db_types, debug=debug)
            pass

    def populate_domains(self):
        pass


