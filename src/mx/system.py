""" system.py -- Represents the user's entire system """

# System
import logging
from pathlib import Path

# Model Integration
from pyral.relation import Relation

# Model Execution
from mx.domain_model_db import DomainModelDB
from mx.db_names import mmdb
from mx.exceptions import *

_logger = logging.getLogger(__name__)

class System:

    def __init__(self, system_dir: Path, debug: bool = False):
        """
        Set the system name

        :param system_dir: Directory containing system and type mapping files
        :param debug:
        """
        self.debug = debug
        self.system_dir = system_dir
        self.context_dir = None
        self.domains = None

        # Get the System name from the populated metamodel
        result = Relation.restrict(db=mmdb, relation='System')
        if not result.body:
            msg = f"System name not found in the user db"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.name = result.body[0]['Name']

        # Create a dictionary of domain names
        result = Relation.restrict(db=mmdb, relation='Domain')
        if not result.body:
            msg = f"No domains defined for system in metamodel"
            _logger.exception(msg)
            raise MXUserDBException(msg)

    def init_domains(self):
        """
        Create a database containing all user model domains in the system.

        :param debug:
        :return:
        """
        # Create a dictionary of domains
        result = Relation.restrict(db=mmdb, relation='Domain')
        if not result.body:
            msg = f"No domains defined for system in metamodel"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.domains = {d['Name']: DomainModelDB(name=d['Name'], alias=d['Alias'], system=self)
                        for d in result.body}

    def populate(self, context_dir: Path):
        """
        :param context_dir: Path to the context directory

        """
        self.context_dir = context_dir
        for name, domdb in self.domains.items():
            domdb.populate()


