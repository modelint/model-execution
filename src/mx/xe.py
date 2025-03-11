""" xe.py -- Execution environment """

# System
import logging
from pathlib import Path
from typing import NamedTuple, Dict

# MX
from mx.metamodel_db import MetamodelDB
from mx.domain_model_db import DomainModelDB
from mx.context import Context
from mx.system import System
from mx.scenario import Scenario

_logger = logging.getLogger(__name__)

class XE:

    system: System = None

    @classmethod
    def initialize(cls, populated_mmdb_filename: str, types_dir: Path, sip_file: Path, scenario_file: Path,
                   debug: bool = False):
        """
        Generate a user database (udb) from the populated metamodel (mmdb) and then populate the udb with
        a population of initial instances establishing a starting context for any further execution.

        :param populated_mmdb_filename: Name of metamodel database populated with the domain model - this is a
         serialized TclRAL text file. The user model is generated from the instances in this metamodel database
        :param types_dir: Directory of files mapping model to TclRAL db_types for each domain
        :param sip_file: *.sip file specifying an initial population of user instance values for the user model
         to be generated
        :param scenario_file: Path to an *.scn file defining a scenario to run
        :param debug: Debug mode - prints schemas and other info to the console
        """
        cls.debug = debug

        # Load a metamodel file populated with a system
        MetamodelDB.initialize(filename=populated_mmdb_filename)

        # Set the system name
        cls.system = System(types_dir=types_dir)

        if debug:
            MetamodelDB.display(system_name=cls.system.name)

        cls.system.init_domains(debug=debug)

        # Create a schema for the user model database and initiate a udb database session in PyRAL
        schema = DomainModelDB(db_types=types_dir, debug=debug)

        # Populate the schema with initial user instance values
        # context = Context(sip_file=sip_file, domain=domain, dbtypes=schema.user_types)
        # cls.domains[domain] = ExecutableDomain(schema=schema, context=context)
        # Initialize the system (build the dynamic components within)

        # Run the scenario (sequence of interactions)
        pass
