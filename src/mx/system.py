""" system.py -- Represents the user's entire system """

# System
import logging
from typing import TYPE_CHECKING, Optional
from pathlib import Path
from contextlib import redirect_stdout

# Model Integration
from pyral.database import Database
from pyral.relation import Relation
from pyral.relvar import Relvar

# MX
from mx.domain import Domain
from mx.db_names import mmdb
from mx.rvname import RVN
from mx.exceptions import *
# from mx.mx_logger import MXLogger

_logger = logging.getLogger(__name__)

DEFAULT_MODEL_OUTPUT_NAME = "model_out.txt"


class System:
    """
    This class represents the complete executing system
    It follows the singleton pattern to ensure only one System exists.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(System, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Avoid reinitialization if already initialized
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.mmdb_path = None
        self.domains: dict[str, Domain] = {}
        self.name = None
        self.debug = False
        self.verbose = False
        # self.mxlog = MXLogger()


    def initialize(self, mmdb_path: Path, verbose: bool, debug: bool):
        """

        Args:
            mmdb_path:
            verbose:
            debug:

        Returns:

        """
        self.mmdb_path = mmdb_path

        # Load a metamodel file populated with the system as one or more modeled domains
        _logger.info(f"Loading the metamodel database from: [{self.mmdb_path}]")
        Database.open_session(name=mmdb)
        Database.load(db=mmdb, fname=str(self.mmdb_path))

        # Initialize the variable name counter
        RVN.init_for_db(db=mmdb)
        # Get the System name from the populated metamodel
        system_i = Relation.restrict(db=mmdb, relation='System')
        if not system_i.body:
            msg = f"System name not found in the user db"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.name = system_i.body[0]['Name']

    @classmethod
    def print_models(cls, class_names=None, output_file=DEFAULT_MODEL_OUTPUT_NAME, display=False, save=True):
        with open(output_file, 'w') as f:
            with redirect_stdout(f):
                if not class_names:
                    Relvar.printall(db=mmdb)
                else:
                    for c in class_names:
                        Relation.print(db=mmdb, variable_name=c)

    def load_domains(self):
        """
        Load and create a session for each domain database
        """
        Relation.restrict(db=mmdb, relation='Modeled Domain')
        domain_i = Relation.semijoin(db=mmdb, rname2='Domain')
        if not domain_i.body:
            msg = f"No domains defined for system in metamodel"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        # Initialize modeled domains only
        self.domains = {d['Alias']: Domain(name=d['Name'], alias=d['Alias'], system=self) for d in domain_i.body}

    def go(self):
        work_remaining = True  # Assume there is work to be done
        while work_remaining:
            for d in self.domains.values():
                work_remaining = d.go()  # We'll stay in the loop as long as at least one domain reports true
