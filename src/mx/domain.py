""" domain.py -- Represents a modeled domain defined in the metamodel """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple, Optional
from collections import defaultdict
from contextlib import redirect_stdout

if TYPE_CHECKING:
    from mx.system import System

# Model Integration
from pyral.relation import Relation
from pyral.database import Database
from pyral.relvar import Relvar

# Model Execution
# from domain_model_db import MultipleAssigner
# from mx.single_assigner_state_machine import SingleAssignerStateMachine
from mx.method_execution import MethodExecution
from mx.multiple_assigner_state_machine import MultipleAssignerStateMachine
from mx.assigner_state_machine import AssignerStateMachine
from mx.lifecycle_state_machine import LifecycleStateMachine
from mx.db_names import mmdb
from mx.initial_states import InitialStateContext
# from mx.exceptions import *
from mx.mxtypes import snake


_logger = logging.getLogger(__name__)

MultipleAssigner = NamedTuple("MultipleAssigner", rnum=str, pclass=str)
MAPartitionClassID = NamedTuple('MAPartitionClassID', pclass=str, id_attrs=list[str])


class Domain:
    """
    A Domain is an active component that can respond to external input
    """

    def __init__(self, name: str, alias: str, system: 'System'):
        """
        Initiate a database session for this domain and load it from its database file.

        Gather data of interest for the domain's execution from the database and prep the domain
        for execution.

        When execution begins, manage execution of this domain.

        Args:
            name: The name of the domain, used for indexing into the mmdb
            alias: The domain alias serves as the name of the corresponding domain database
            system: Reference to the single System object.
        """
        self.events_pending = False  # Initially, there is no work to do
        self.activity_executing = False  # Initially, no Activity is executing

        self.name = name
        self.alias = alias  # Now we have access to both the mmdb and this domain's schema
        self.system = system
        self.single_assigners = None
        self.lifecycles: dict[str, dict[ str, LifecycleStateMachine]] = {}
        self.mult_assigners: dict[str, dict[ str, MultipleAssignerStateMachine]] = {}
        # self.mult_assigners: dict[str, list[MultipleAssignerStateMachine]] = {}  # TODO: match lifecycle dict
        self.lifecycle_ids: dict[str, list[str]] = {}
        self.pclasses: dict[str, list[str]] = {}
        self.methods = None
        # self.flows = activity: flow id, flow type(scalar, inst1, instM, table, tuple), data type(scalar, table, class)
        self.ma_partitions: dict[str, MAPartitionClassID] = {}

        self.file_path = self.system.playground / 'population' / f"{self.alias}.ral"  # Path to the domain database file

        # Load the sip file and save all specified initial states
        is_context = InitialStateContext(domain=self)
        self.lifecycle_initial_states = is_context.lifecycle_istates
        self.massigner_initial_states = is_context.ma_istates
        # TODO: Single assigner initial states not yet specified in the sip file syntax

        # Load the domain database
        Database.open_session(name=self.alias)
        Database.load(db=self.alias, fname=str(self.file_path))
        if self.system.verbose:
            self.display()
        self.find_lifecycles()
        self.find_single_assigners()
        self.find_mult_assigners()
        pass

        # self.lifecycles: dict[str, list[LifecycleStateMachine]] = {}
        # self.assigners: dict[str, list[AssignerStateMachine]] = {}
        self.initiate_lifecycles()  # Create a lifecycle statemachine for each class with a lifecycle
        pass
        self.initiate_assigners()  # Create an assigner statemachine for each relationship managed by an assigner
        # self.initiate_methods()

    @property
    def busy(self) -> bool:
        return self.events_pending or self.activity_executing

    def go(self) -> bool:
        """
        Run all state machines

        :return:
        """
        for class_name, instance in self.lifecycles.items():
            for inst_id, sm in instance.items():
                if sm.busy:
                    sm.go()  # Operating at thread granularity 0, 0 max events
        return self.busy

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
            R = f"Class:<{c}>, Identifier:<{1}>"
            id_result = Relation.restrict(db=mmdb, restriction=R, relation='id_all')
            c_id_attrs = [t['Attribute'] for t in id_result.body]  # id attributes for the current class
            self.lifecycle_ids[c] = c_id_attrs

    def find_single_assigners(self):
        """
        For each relationship that uses one, create a single assigner
        """
        R = f"Domain:<{self.name}>"
        single_assigner_r = Relation.restrict(db=mmdb, relation='Single_Assigner', restriction=R)
        self.single_assigners = [t['rnum'] for t in single_assigner_r.body]

    def find_mult_assigners(self):
        """
        For each multiple assigner, record the rnum, partitioning class, and the identifier attributes
        of the partitioning class primary identifier
        """
        # Get all of the multiple assigners in this domain
        R = f"Domain:<{self.name}>"
        multiple_assigner_r = Relation.restrict(db=mmdb, relation='Multiple Assigner', restriction=R)

        # Map each rnum -> partitioning class name
        pclass_by_rnum: dict[str, str] = {
            ma_t['Rnum']: ma_t['Partitioning_class']
            for ma_t in multiple_assigner_r.body
        }

        # Collect identifier attributes of the primary identifier of each partitioning class
        R = f"Domain:<{self.name}>, Identifier:<1>"
        Relation.restrict(db=mmdb, restriction=R, relation='Identifier Attribute')
        ma__idattrs = Relation.join(db=mmdb, rname2='Multiple Assigner',
                                    attrs={'Class': 'Partitioning_class', 'Domain': 'Domain'})

        # We just need the rnum and the list of identifying attributes of the partitioning class
        id_attrs_by_rnum: dict[str, list[str]] = defaultdict(list)
        for t in ma__idattrs.body:
            id_attrs_by_rnum[t['Rnum']].append(t['Attribute'])

        # Now we can arrange the partitioning class name and identifier attributes in a named tuple
        # mapped to the rnum key
        self.ma_partitions = {
            rnum: MAPartitionClassID(pclass=pclass, id_attrs=id_attrs_by_rnum[rnum])
            for rnum, pclass in pclass_by_rnum.items()
        }

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

            # Tag the class relvar so that each instance has an arbitrary integer id 0..n
            class_i_rv = f"{snake(class_name)}_i"
            # We can use the above formula to obtain this relation variable later for any given class name
            Relation.tag(db=self.alias, tag_attr_name="_instance", relation=class_name)
            # Project on id attrs + the tagged _instance attr to yield the class_i_rv value
            P = tuple(id_attrs + ['_instance'])
            instance_r = Relation.project(db=self.alias, attributes=P, svar_name=class_i_rv)

            # Create a lifecycle statemachine for each instance and index it to its instance id
            for i in instance_r.body:
                # Create the lifecycle
                # Create identifier value for this instance
                inst_id = {attr: i[attr] for attr in id_attrs}
                # Get the initial state for this instance from the context
                istate = istates[class_name]
                # Now use the instance id in the inner dictionary (local to class_name)
                # Ensure the inner dictionary exists for the class_name
                self.lifecycles.setdefault(class_name, {})[i["_instance"]] = LifecycleStateMachine(
                    lifecycle_sm_id=i["_instance"],
                    current_state=istate,
                    instance_id=inst_id,
                    class_name=class_name,
                    domain=self
                )

    def initiate_assigners(self):
        """
        Initiates any single and multiple assigner state machines
        """
        pass
        # for ma in self.mult_assigner_partitions:
        #     pclass_id = self.pclasses[ma.pclass]
        #     result = Relation.restrict(db=self.alias, relation=ma.pclass)
        #     for t in result.body:
        #         # build the id
        #         id_val = {attr: t[attr] for attr in pclass_id}
        #         istate = self.massigner_initial_states[ma.rnum].state
        #         self.mult_assigners.setdefault(ma, {})[MultipleAssignerStateMachine(
        #             ma_sm_id=, current_state=istate, rnum=ma.rnum, pclass_name=ma.pclass, instance_id=id_val, domain=self.name))
        return
    #
    #     for sa in self.db.single_assigners:
    #         # TODO: Support single assigners
    #         # self.assigners[sa] = SingleAssignerStateMachine(current_state="None", rnum=sa.rnum, domain=self.name)
    #         pass
