""" metamodel_db.py -- Loads a metamodel database populated with a system of one or more modeled domains """

# System
import logging
from pathlib import Path
from contextlib import redirect_stdout

# Model Integration
from pyral.database import Database
from pyral.relvar import Relvar

# Model Execution
from mx.db_names import mmdb, dbfile_ext
from mx.exceptions import *

_logger = logging.getLogger(__name__)

class MetamodelDB:

    filename = None

    @classmethod
    def initialize(cls, system_dir: Path):
        """ Let's load and print out the metamodel database """

        # There should be a single *.ral or *.txt TclRAL database file in this directory
        found_files = list(system_dir.glob("*.txt")) + list(system_dir.glob(f"*{dbfile_ext}"))
        if len(found_files) == 0:
            raise MXFileException(f"No TclRAL database found in: {system_dir.resolve()}")
        if len(found_files) > 1:
            raise MXFileException(f"Multiple possible TclRAL database files found in: {system_dir.resolve()}")

        # Found the metamodel database TclRAL file
        cls.filename = found_files[0]

        _logger.info(f"Loading the metamodel database from: [{cls.filename}]")
        Database.open_session(name=mmdb)
        Database.load(db=mmdb, fname=cls.filename)

    @classmethod
    def print(cls):
        """
        Print out the populated metamodel
        """
        with open("mmdb.txt", 'w') as f:
            with redirect_stdout(f):
                Relvar.printall(db=mmdb)

    @classmethod
    def display(cls, system_name: str):
        # Print out the populated metamodel
        msg = f"Metamodel populated with {system_name} System"
        print(f"*** {msg} ***")
        Relvar.printall(db=mmdb)
        print(f"^^^ {msg} ^^^")
