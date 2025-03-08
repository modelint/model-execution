""" xe.py -- Execution environment """

# System
import logging
from pathlib import Path
from typing import NamedTuple, Dict

# MX
from mx.schema import Schema
from mx.scenario import Scenario

_logger = logging.getLogger(__name__)

class ExecutableDomain(NamedTuple):
    schema: Schema
    scenario: Scenario

class XE:

    domains: Dict[str, ExecutableDomain] = {}  # Each domain loaded into this environment

    @classmethod
    def initialize_domain(cls, populated_mmdb_filename: str, domain: str, user_tcl_type_map: Path,
                          starting_context: Path):
        """
        Generate a user database (udb) from the populated metamodel (mmdb) and then populate the udb with
        a population of initial instances establishing a starting context for any further execution.

        :param populated_mmdb_filename: Name of metamodel database populated with the domain model - this is a
         serialized TclRAL text file. The user model is generated from the instances in this metamodel database
        :param domain: Name of the domain to be initialized
        :param user_tcl_type_map: Mapping of model to TclRAL types defined for this domain
        :param starting_context: An initial population of user instance values for the user model to be generated
        :return:
        """

        # Create a schema for the user model database and initiate a udb database session in PyRAL
        schema = Schema(filename=populated_mmdb_filename, domain=domain, types=user_tcl_type_map,
                        starting_context=starting_context)
        # Populate the schema with initial user instance values
        scenario = Scenario(scenario_file=starting_context, domain=domain)
        cls.domains[domain] = ExecutableDomain(schema=schema, scenario=scenario)
        # Build the duyanmic components of the system

        # Run the scenario (sequence of interactions)
        pass
