""" xe.py -- Execution environment """

# System
import logging
from pathlib import Path

# MX
from mx.metamodel_db import MetamodelDB
from mx.system import System
from mx.scenarios.scenario_ping import Scenario

_logger = logging.getLogger(__name__)

class XE:

    system: System = None

    @classmethod
    def initialize(cls, system_dir: Path, context_dir: Path, scenario_file: Path, debug: bool = False):
        """
        Generate a user database (udb) from the populated metamodel (mmdb) and then populate the udb with
        a population of initial instances establishing a starting context for any further execution and then
        run the specified scenario against it.

        :param system_dir: Directory containing a populated metamodel as a TclRAL text file and one user to
        db type mapping yaml file per domain
        :param context_dir: Directory containing one initial instance population *.sip file per domain
        :param scenario_file: Path to an *.scn file defining a scenario to run
        :param debug: Debug mode - prints schemas and other info to the console if true
        """
        cls.debug = debug
        cls.system_dir = system_dir

        # Load a metamodel file populated with a system
        MetamodelDB.initialize(system_dir=cls.system_dir)

        # Set the system name
        cls.system = System(system_dir=cls.system_dir, debug=debug)

        if debug:
            MetamodelDB.print()

        # Create a database schema for each domain
        cls.system.create_domain_dbs()

        # Populate each of these schemas with the corresponding *.sip file found in the context_dir
        cls.system.populate(context_dir=context_dir)

        # Activate the system (build the dynamic components within)
        cls.system.activate()

        # The system is now ready to react to external input

        # Run the scenario (sequence of interactions)
        Scenario.run(sys_domains=cls.system.domains)
        pass

