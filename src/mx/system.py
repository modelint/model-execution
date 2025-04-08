""" system.py -- Represents the user's entire system """

# System
import logging
from pathlib import Path

# Model Integration
from pyral.relation import Relation

# Model Execution
from mx.domain_model_db import DomainModelDB
from mx.domain import Domain
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
        self.context_dir = None  # Where the initial population *.sip files are
        self.domain_dbs = None  # Each domain's schema
        self.domains: dict[str, Domain] = {}  # Each active domain

        # Get the System name from the populated metamodel
        result = Relation.restrict(db=mmdb, relation='System')
        if not result.body:
            msg = f"System name not found in the user db"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.name = result.body[0]['Name']

    def create_domain_dbs(self):
        """
        Create a separate database for each domain in the system
        """
        # Create a dictionary of domains
        result = Relation.restrict(db=mmdb, relation='Domain')
        if not result.body:
            msg = f"No domains defined for system in metamodel"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.domain_dbs = {d['Alias']: DomainModelDB(name=d['Name'], alias=d['Alias'], system=self)
                           for d in result.body}

    def populate(self, context_dir: Path):
        """
        :param context_dir: Path to the context directory

        """
        self.context_dir = context_dir
        for name, domdb in self.domain_dbs.items():
            domdb.populate()

    def activate(self):
        for domain_name, db in self.domain_dbs.items():
            self.domains[domain_name] = Domain(name=db.domain, alias=db.alias, db=db)


