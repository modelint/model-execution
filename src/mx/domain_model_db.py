""" domain_model_db.py -- Build a TclRAL schema for a modeled domain from a populated SM Metamodel """

# System
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, NamedTuple
from contextlib import redirect_stdout

if TYPE_CHECKING:
    from mx.system import System

# Model Integration
from pyral.database import Database
from pyral.relvar import Relvar
from pyral.relation import Relation
from pyral.rtypes import Attribute, Mult

# Model Execution
from mx.db_names import mmdb, types_dir_name
from mx.context import Context
from mx.exceptions import *

_logger = logging.getLogger(__name__)

MultipleAssigner = NamedTuple("MultipleAssigner", rnum=str, pclass=str)

class DomainModelDB:
    """
    TclRAL schema for a user domain model extracted from a populated SM metamodel
    """

    def __init__(self, name: str, alias: str, system: 'System'):
        """
        Create the db schema and optionally print it out

        :param name: Name of this domain
        :param alias: Alias for this domain (used for the database name)
        :param system: The system object
        """
        self.system = system
        self.domain = name
        self.alias = alias
        self.prefixes = None
        self.ordinal_rnums = None
        self.gen_rnums = None
        self.non_assoc_rnums = None
        self.assoc_rnums = None
        self.user_types = None
        self.context = None
        self.lifecycles: dict[str, list[str]] = {}
        self.pclasses: dict[str, list[str]] = {}
        self.single_assigners = None
        self.methods = None
        MultAssignerPartition = NamedTuple('MultAssignerPartion', pclass=str, id_attrs=dict[str, list[str]])
        self.mult_assigners: dict[str, MultAssignerPartition] = {}

        Database.open_session(name=self.alias)  # User models created in this database

        self.find_lifecycles()
        self.find_single_assigners()
        self.find_mult_assigners()
        pass

    def display(self):
        """
        Display the user domain schema on the console
        """
        print(f"\nvvv Unpopulated [{self.domain}] Domain Model vvv ")
        Relvar.printall(db=self.alias)
        print(f"^^^ Unpopulated [{self.domain}] Domain Model ^^^ ")

    def print(self):
        """
        Print out the user domain schema
        """
        with open(f"{self.alias.lower()}.txt", 'w') as f:
            with redirect_stdout(f):
                Relvar.printall(db=self.alias)

    def find_lifecycles(self):
        """
        Find each class with a lifecycle defined and save its name and I1 identifier.
        We use this information later when we populate the initial state of each lifecycle statemachine.
        """
        # Get the names of each class in this domain with a lifecycle defined
        R = f"Domain:<{self.domain}>"
        lcyc_result = Relation.restrict(db=mmdb, relation='Lifecycle', restriction=R)
        class_names = [t['Class'] for t in lcyc_result.body]

        # Now get the identifier attributes of all of these classes
        R = f"Domain:<{self.domain}>, Identifier:<1>"
        Relation.join(db=mmdb, rname2='Identifier_Attribute', rname1='Lifecycle', svar_name='id_all')
        # id_all relation has all identifier attributes for all classes with lifecycles

        # Save the primary identifier for each class with a lifecycle
        for c in class_names:
            R = f"Class:<{c}>"
            id_result = Relation.restrict(db=mmdb, restriction=R, relation='id_all')
            c_id_attrs = [t['Attribute'] for t in id_result.body]  # id attributes for the current class
            self.lifecycles[c] = c_id_attrs

    def find_single_assigners(self):
        """
        For each relationship that uses one, create a single assigner
        """
        R = f"Domain:<{self.domain}>"
        result = Relation.restrict(db=mmdb, relation='Single_Assigner', restriction=R)
        self.single_assigners = [t['rnum'] for t in result.body]

    def find_mult_assigners(self):
        """
        For each
        """
        # Get the names of each partitioning class in this domain
        R = f"Domain:<{self.domain}>"
        p_result = Relation.restrict(db=mmdb, relation='Multiple_Assigner', restriction=R)
        pclass_names = [t['Partitioning_class'] for t in p_result.body]

        # Now get the identifier attributes of all of these classes
        R = f"Domain:<{self.domain}>, Identifier:<1>"
        Relation.join(db=mmdb, rname2='Identifier_Attribute', rname1='Multiple_Assigner',
                      attrs={'Partitioning_class': 'Class', 'Domain':'Domain'}, svar_name='id_pall')
        # id_pall relation has all identifier attributes for all partitioning classes

        # Save the primary identifier for each partitioning class
        for c in pclass_names:
            R = f"Partitioning_class:<{c}>"
            id_result = Relation.restrict(db=mmdb, restriction=R, relation='id_pall')
            c_id_attrs = [t['Attribute'] for t in id_result.body]  # id attributes for the current class
            self.pclasses[c] = c_id_attrs

        R = f"Domain:<{self.domain}>"
        result = Relation.restrict(db=mmdb, relation='Multiple_Assigner', restriction=R)
        self.mult_assigners = [MultipleAssigner(rnum=t['Rnum'], pclass=t['Partitioning_class'])
                               for t in result.body]

