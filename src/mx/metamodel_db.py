""" metamodel_db.py -- Loads a metamodel database populated with a system of one or more modeled domains """

# System
import logging

# Model Integration
from pyral.database import Database
from pyral.relvar import Relvar

# Model Execution
from mx.db_names import mmdb, dbfile_ext

_logger = logging.getLogger(__name__)

class MetamodelDB:

    filename = None

    @classmethod
    def initialize(cls, filename: str):
        """ Let's load and print out the metamodel database """

        cls.filename = filename if filename.endswith(dbfile_ext) else filename + dbfile_ext

        _logger.info(f"Loading the metamodel database from: [{cls.filename}]")
        Database.open_session(name=mmdb)
        Database.load(db=mmdb, fname=cls.filename)

    @classmethod
    def display(cls, system_name: str):
        # Print out the populated metamodel
        msg = f"Metamodel populated with {system_name} System"
        print(f"*** {msg} ***")
        Relvar.printall(db=mmdb)
        print(f"^^^ {msg} ^^^")
