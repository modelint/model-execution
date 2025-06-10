""" xe.py -- Execution environment """

# System
import logging
import yaml
from pathlib import Path
from typing import Any

# Model Integration
from pyral.database import Database
from pyral.relvar import Relvar

# MX
from mx.system import System
from mx.scenario import Scenario
from mx.db_names import mmdb
from mx.rvname import RVN
from mx.mx_logger import MXLogger

_logger = logging.getLogger(__name__)


def load_scenario(path: str | Path) -> dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class XE:
    """
    This class represents the overall model execution environment.
    It follows the singleton pattern to ensure only one XE exists.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XE, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Avoid reinitialization if already initialized
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.mmdb_path = None
        self.context_dir = None
        self.scenario = None
        self.system = None
        self.debug = False
        self.verbose = False
        self.mxlog = None

    def initialize(self, mmdb_path: Path, context_dir: Path, scenario_path: Path, verbose:bool, debug: bool):
        """
        Generate a user database (udb) from the populated metamodel (mmdb) and then populate the udb with
        a population of initial instances establishing a starting context for any further execution and then
        run the specified scenario against it.

        :param mmdb_path: Path to the system (all domains) populated into the metamodel *.ral TclRAL
        :param context_dir: Directory containing one initial instance population *.sip file per domain
        :param scenario_path: Path to an *.scn file defining a scenario to run
        :param verbose: Verbose mode
        :param debug: Debug mode - prints schemas and other info to the console if true
        """
        self.mmdb_path = mmdb_path
        self.context_dir = context_dir
        self.verbose = verbose  # Print db schemas, etc to console
        self.debug = debug  # Print intermediate tables and values to console

        # Load the scenario
        self.scenario = load_scenario(path=scenario_path)

        # Initialize model execution logger for scenario specific output
        log_file_name = self.scenario["scenario"].get("name", "unnamed_scenario")
        self.mxlog = MXLogger(scenario_name=log_file_name)
        pass


        # Load a metamodel file populated with the system as one or more modeled domains
        _logger.info(f"Loading the metamodel database from: [{self.mmdb_path}]")
        Database.open_session(name=mmdb)
        Database.load(db=mmdb, fname=str(self.mmdb_path))

        # Initialize the variable name counter
        RVN.init_for_db(db=mmdb)

        # Create the System and get each domain ready to execute
        self.system = System(xe=self)

        if self.verbose:
            # Display the populated metamodel
            msg = f"Metamodel populated with the {self.system.name} system"
            print(f"\n*** {msg} ***\n")
            Relvar.printall(db=mmdb)
            print(f"\n^^^ {msg} ^^^\n")

        # Activate the system (build the dynamic components within)
        self.system.activate()

        # Run the scenario
        s = Scenario(xe=self)
        s.run()

        # Close the mx logger
        self.mxlog.close()

        # Run the scenario (sequence of interactions)
        # Scenario.run(sys_domains=self.system.domains)

