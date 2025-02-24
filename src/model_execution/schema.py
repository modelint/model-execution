""" schema.py -- Build a TclRAL schema from a populated SM Metamodel """

# System
import logging

# Model Integration
from pyral.database import Database
from pyral.relvar import Relvar

class Schema:
    """
    TclRAL schema a domain's class model
    """

    def __init__(self, filename: str):

        self.name = "cm_schema"
        self.filename = filename
        # Open a PyRAL session
        self.db = "pop_mmdb"  # Name of the populated metamodel database
        Database.open_session(name=self.db)
        self.load_metamodel()


    def load_metamodel(self):
        """ Let's load and print out the metamodel database """
        Database.load(db=self.db, fname=self.filename)

        # Print out the populated metamodel
        Relvar.printall(db=self.db)
        pass