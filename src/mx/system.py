""" system.py -- Represents the user's entire system """

# System
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.xe import XE

# Model Integration
from pyral.relation import Relation

# Model Execution
from mx.domain import Domain
from mx.db_names import mmdb
from mx.exceptions import *

_logger = logging.getLogger(__name__)


class System:

    def __init__(self, xe: "XE"):
        """
        Set the system name
        """
        self.xe = xe
        self.domains: dict[str, Domain] = {}

        # Get the System name from the populated metamodel
        system_i = Relation.restrict(db=mmdb, relation='System')
        if not system_i.body:
            msg = f"System name not found in the user db"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.name = system_i.body[0]['Name']

        self.load_domains()

    def load_domains(self):
        """
        Load and create a session for each domain database
        """
        # Create a dictionary of domains
        domain_i = Relation.restrict(db=mmdb, relation='Domain')
        if not domain_i.body:
            msg = f"No domains defined for system in metamodel"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.domains = {d['Alias']: Domain(name=d['Name'], alias=d['Alias'], system=self) for d in domain_i.body}

    def activate(self):
        for d in self.domains.values():
            d.activate()
