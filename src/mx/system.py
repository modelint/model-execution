""" system.py -- Represents the user's entire system """

# System
import logging
from pathlib import Path

# Model Integration
from pyral.relation import Relation

# Model Execution
from mx.domain import Domain
from mx.db_names import mmdb
from mx.exceptions import *

_logger = logging.getLogger(__name__)


class System:

    def __init__(self):
        """
        Set the system name
        """
        self.context_dir = None  # Where the initial population *.sip files are
        self.domain_dbs = None  # Each domain's schema
        self.domains: dict[str, Domain] = {}  # Each active domain

        # Get the System name from the populated metamodel
        system_i = Relation.restrict(db=mmdb, relation='System')
        if not system_i.body:
            msg = f"System name not found in the user db"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.name = system_i.body[0]['Name']

    # def create_domain_dbs(self):
    #     """
    #     Create a separate database for each domain in the system
    #     """
    #     # Create a dictionary of domains
    #     result = Relation.restrict(db=mmdb, relation='Domain')
    #     if not result.body:
    #         msg = f"No domains defined for system in metamodel"
    #         _logger.exception(msg)
    #         raise MXUserDBException(msg)
    #
    #     self.domain_dbs = {d['Alias']: DomainModelDB(name=d['Name'], alias=d['Alias'], system=self)
    #                        for d in result.body}
    #
    # def populate(self, context_dir: Path):
    #     """
    #     :param context_dir: Path to the context directory
    #
    #     """
    #     self.context_dir = context_dir
    #     for name, domdb in self.domain_dbs.items():
    #         domdb.populate()

    def activate(self):
        for domain_name, db in self.domain_dbs.items():
            self.domains[domain_name] = Domain(name=db.domain, alias=db.alias, db=db)


