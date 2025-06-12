""" domain.py -- Represents a modeled domain defined in the metamodel """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple
from collections import defaultdict

if TYPE_CHECKING:
    from mx.system import System

# Model Integration
from pyral.relation import Relation
from pyral.database import Database
from pyral.relvar import Relvar

# Model Execution
# from domain_model_db import MultipleAssigner
# from mx.single_assigner_state_machine import SingleAssignerStateMachine
from mx.method import Method
from mx.multiple_assigner_state_machine import MultipleAssignerStateMachine
from mx.assigner_state_machine import AssignerStateMachine
from mx.lifecycle_state_machine import LifecycleStateMachine
from mx.db_names import mmdb
from mx.initial_states import InitialStateContext
# from mx.exceptions import *
from mx.rvname import RVN
from mx.instance import generate_key

_logger = logging.getLogger(__name__)

MultipleAssigner = NamedTuple("MultipleAssigner", rnum=str, pclass=str)


class Domain:
    """
    An Domain is an active component that can respond to external input
    """

    def __init__(self, name: str, alias: str, system: 'System'):
        """
        Initiate a database session for this domain and load it from its databae file.

        Gather data of interest for the domain's execution from the database and prep the domain
        for execution.

        When execution begins, manage execution of this domain.

        :param name: The name of the domain, used for indexing into the mmdb
        :param alias: The domain alias serves as the name of the corresponding domain database
        :param system: Reference to the single System object.
        """
        self.name = name
        self.alias = alias  # Now we have access to both the mmdb and this domain's schema
        self.system = system
        self.single_assigners = None
        self.lifecycles: dict[str, dict[ str, LifecycleStateMachine]] = {}
        self.mult_assigners: dict[str, list[MultipleAssignerStateMachine]] = {}  # TODO: match lifecycle dict
        self.lifecycle_ids: dict[str, list[str]] = {}
        self.pclasses: dict[str, list[str]] = {}
        self.single_assigners = None
        self.methods = None
        # self.flows = activity: flow id, flow type(scalar, inst1, instM, table, tuple), data type(scalar, table, class)
        MultAssignerPartition = NamedTuple('MultAssignerPartion', pclass=str, id_attrs=dict[str, list[str]])
        self.mult_assigner_partitions: dict[str, MultAssignerPartition] = {}

        self.file_path = self.system.xe.context_dir / f"{self.alias}.ral"  # Path to the domain database file

        # Load the sip file and save all specified initial states
        is_context = InitialStateContext(domain=self)
        self.lifecycle_initial_states = is_context.lifecycle_istates
        self.massigner_initial_states = is_context.ma_istates
        # TODO: Single assigner initial states not yet specified in the sip file syntax

        # Initialize the variable name counter
        RVN.init_for_db(db=self.alias)

        # Load the domain database
        Database.open_session(name=self.alias)
        Database.load(db=self.alias, fname=str(self.file_path))
        if self.system.xe.verbose:
            self.display()
        self.find_lifecycles()
        self.find_single_assigners()
        self.find_mult_assigners()
        pass

        # self.lifecycles: dict[str, list[LifecycleStateMachine]] = {}
        # self.assigners: dict[str, list[AssignerStateMachine]] = {}
        self.initiate_lifecycles()  # Create a lifecycle statemachine for each class with a lifecycle
        self.initiate_assigners()  # Create an assigner statemachine for each relationship managed by an assigner
        # self.initiate_methods()

    def activate(self):
        """
        Create any elements necessary before scenario execution begins

        :return:
        """
        # At this point we are only testing method execution, so there's nothing to be done.  Just return.
        return

    def find_lifecycles(self):
        """
        Find each class with a lifecycle defined and save its name and I1 identifier.
        We use this information later when we populate the initial state of each lifecycle statemachine.
        """
        # Get the names of each class in this domain with a lifecycle defined
        R = f"Domain:<{self.name}>"
        lifecycle_i = Relation.restrict(db=mmdb, relation='Lifecycle', restriction=R)
        class_names = [t['Class'] for t in lifecycle_i.body]

        # Now get the identifier attributes of all of these classes
        R = f"Domain:<{self.name}>, Identifier:<1>"
        Relation.join(db=mmdb, rname2='Identifier_Attribute', rname1='Lifecycle', svar_name='id_all')
        # id_all relation has all identifier attributes for all classes with lifecycles

        # Save the primary identifier for each class with a lifecycle
        for c in class_names:
            R = f"Class:<{c}>"
            id_result = Relation.restrict(db=mmdb, restriction=R, relation='id_all')
            c_id_attrs = [t['Attribute'] for t in id_result.body]  # id attributes for the current class
            self.lifecycle_ids[c] = c_id_attrs

    def find_single_assigners(self):
        """
        For each relationship that uses one, create a single assigner
        """
        R = f"Domain:<{self.name}>"
        result = Relation.restrict(db=mmdb, relation='Single_Assigner', restriction=R)
        self.single_assigners = [t['rnum'] for t in result.body]

    def find_mult_assigners(self):
        """
        For each
        """
        # Get the names of each partitioning class in this domain
        R = f"Domain:<{self.name}>"
        p_result = Relation.restrict(db=mmdb, relation='Multiple_Assigner', restriction=R)
        pclass_names = [t['Partitioning_class'] for t in p_result.body]

        # Now get the identifier attributes of all of these classes
        R = f"Domain:<{self.name}>, Identifier:<1>"
        Relation.join(db=mmdb, rname2='Identifier_Attribute', rname1='Multiple_Assigner',
                      attrs={'Partitioning_class': 'Class', 'Domain': 'Domain'}, svar_name='id_pall')
        # id_pall relation has all identifier attributes for all partitioning classes

        # Save the primary identifier for each partitioning class
        for c in pclass_names:
            R = f"Partitioning_class:<{c}>"
            id_result = Relation.restrict(db=mmdb, restriction=R, relation='id_pall')
            c_id_attrs = [t['Attribute'] for t in id_result.body]  # id attributes for the current class
            self.pclasses[c] = c_id_attrs

        R = f"Domain:<{self.name}>"
        result = Relation.restrict(db=mmdb, relation='Multiple_Assigner', restriction=R)
        self.mult_assigner_partitions = [MultipleAssigner(rnum=t['Rnum'], pclass=t['Partitioning_class'])
                                         for t in result.body]

    def display(self):
        """
        Display the user domain schema on the console
        """
        print(f"\nvvv {self.name} domain model vvv\n")
        Relvar.printall(db=self.alias)
        print(f"\n^^^ {self.name} domain model ^^^\n")

    def initiate_lifecycles(self):
        """
        Create a state machine for each class with a lifecycle
        """
        istates = self.lifecycle_initial_states

        # Get each class_name and its primary id for each lifecycle
        for class_name, id_attrs in self.lifecycle_ids.items():
            # Get all the instances from the user model for that class
            inst_result = Relation.restrict(db=self.alias, relation=f"{class_name.replace(' ', '_')}")
            # Create a lifecycle statemachine for each instance
            for i in inst_result.body:
                # Create identifier value for this instance
                inst_id = {attr: i[attr] for attr in id_attrs}
                # Get a key
                inst_key = generate_key(id_attr_value=inst_id)
                # Get the initial state for this instance from the context
                istate = istates[class_name]
                # Ensure the inner dictionary exists for the class_name
                self.lifecycles.setdefault(class_name, {})[inst_key] = LifecycleStateMachine(
                    current_state=istate,
                    instance_id=inst_id,
                    class_name=class_name,
                    domain=self.name
                )
                pass

            pass
        pass

    def initiate_assigners(self):
        """
        Initiates any single and multiple assigner state machines
        """
        for ma in self.mult_assigner_partitions:
            pclass_id = self.pclasses[ma.pclass]
            result = Relation.restrict(db=self.alias, relation=ma.pclass)
            for t in result.body:
                # build the id
                id_val = {attr: t[attr] for attr in pclass_id}
                istate = self.massigner_initial_states[ma.rnum].state
                self.mult_assigners.setdefault(ma, []).append(MultipleAssignerStateMachine(
                    current_state=istate, rnum=ma.rnum, pclass_name=ma.pclass, instance_id=id_val, domain=self.name))
    #
    #     for sa in self.db.single_assigners:
    #         # TODO: Support single assigners
    #         # self.assigners[sa] = SingleAssignerStateMachine(current_state="None", rnum=sa.rnum, domain=self.name)
    #         pass
