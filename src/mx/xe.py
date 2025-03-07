""" xe.py -- Execution environment """

# System
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

class XE:

    @classmethod
    def initialize_domain(cls, populated_mmdb_filename:str, domain: str, types: Path, starting_context: Path):
        """
        Generate a user database (udb) from the populated metamodel (mmdb) and then populate the udb with
        a population of initial instances establishing a starting context for any further execution.

        :param populated_mmdb_filename: Name of metamodel database populated with the domain model - this is a
         serialized TclRAL text file. The user model is generated from the instances in this metamodel database
        :param domain: Name of the domain to be initialized
        :param types: Mapping of model to TclRAL types defined for this domain
        :param starting_context: An initial population of user instance values for the user model to be generated
        :return:
        """
        pass
