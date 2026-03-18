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
from mx.method_execution import MethodExecution
from mx.multiple_assigner_state_machine import MultipleAssignerStateMachine
from mx.single_assigner_state_machine import SingleAssignerStateMachine
from mx.assigner_state_machine import AssignerStateMachine
from mx.lifecycle_state_machine import LifecycleStateMachine
from mx.db_names import mmdb
from mx.initial_states import InitialStateContext
from mx.exceptions import *
from mx.mxtypes import snake
from mx.utility import *

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
        self.lifecycle_ids: dict[str, list[str]] = {}
        self.ma_partitions: dict[str, MAPartitionClassID] = {}
        self.methods = None
        self.rv_owner = f"_{alias}_domain"

        self.file_path = self.system.playground / 'population' / f"{self.alias}.ral"  # Path to the domain database file

        # Load the sip file and save all specified initial states
        is_context = InitialStateContext(domain=self)
        self.lifecycle_initial_states = is_context.lifecycle_istates
        self.ma_initial_states = is_context.ma_istates
        # TODO: Single assigner initial states not yet specified in the sip file syntax

        # Load the domain database
        _logger.info(f"---")
        _logger.info(f"Loading {self.alias} domain database")
        Database.open_session(name=self.alias)
        Database.load(db=self.alias, fname=str(self.file_path))
        if self.system.verbose:
            print_classes(db=self.alias, name=self.name)
        self.find_lifecycles()
        self.find_single_assigners()
        self.find_mult_assigners()

        self.initiate_lifecycles()
        self.initiate_ma_state_machines()
        # self.initiate_sa_state_machines()
        # self.initiate_methods()

        # Clear out any mmdb rvs defined by this domain during initialization
        _logger.info(f"Clearing out metamodel rvs for {self.rv_owner}...")
        _logger.info(f"    Before: {Database.get_rv_names(db=mmdb)}")
        Relation.free_rvs(db=mmdb, owner=self.rv_owner)
        _logger.info(f"    After: {Database.get_rv_names(db=mmdb)}")
        _logger.info(f"---")
        pass

    @property
    def busy(self) -> bool:
        return self.events_pending or self.activity_executing

    def go(self) -> bool:
        """
        Run all state machines

        Returns:
            True if there is still work remaining (unprocessed events)
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
        _logger.info(f"Gathering lifecycle info")
        # Get the names of each class in this domain with a lifecycle defined
        R = f"Domain:<{self.name}>"
        lifecycle_i = Relation.restrict(db=mmdb, relation='Lifecycle', restriction=R)
        class_names = [t['Class'] for t in lifecycle_i.body]

        # Now get the identifier attributes of all of these classes
        rv_id_all = Relation.declare_rv(db=mmdb, owner=self.rv_owner, name="id_all")
        R = f"Domain:<{self.name}>, Identifier:<1>"
        Relation.join(db=mmdb, rname2='Identifier_Attribute', rname1='Lifecycle', svar_name=rv_id_all)
        # id_all relation has all identifier attributes for all classes with lifecycles

        # Save the primary identifier for each class with a lifecycle
        for c in class_names:
            R = f"Class:<{c}>, Identifier:<{1}>"
            id_result = Relation.restrict(db=mmdb, restriction=R, relation=rv_id_all)
            c_id_attrs = [t['Attribute'] for t in id_result.body]  # id attributes for the current class
            self.lifecycle_ids[c] = c_id_attrs
            _logger.info(f"    Setting {c} id to {c_id_attrs}")


    def find_single_assigners(self):
        """
        For each relationship that uses one, create a single assigner
        """
        _logger.info(f"Gathering single assigner info")
        R = f"Domain:<{self.name}>"
        single_assigner_r = Relation.restrict(db=mmdb, relation='Single_Assigner', restriction=R)
        self.single_assigners = [t['rnum'] for t in single_assigner_r.body]

    def find_mult_assigners(self):
        """
        For each multiple assigner, record the rnum, partitioning class, and the identifier attributes
        of the partitioning class primary identifier
        """
        _logger.info(f"Gathering multiple assigner info")
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
        _logger.info(f"    {self.ma_partitions}")

    def initiate_lifecycles(self):
        """
        Create a State Machine for each Instance of a Class with a modeled Lifecycle
        """
        _logger.info(f"Initiating lifecycles...")
        istates = self.lifecycle_initial_states

        # Get each class_name and its primary id for each lifecycle
        for class_name, id_attrs in self.lifecycle_ids.items():

            _logger.info(f"    Lifecycles for: {class_name}")

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
                _logger.info(f"       sm id: {i["_instance"]} current state: [{istate}] inst id: {inst_id}")

    def initiate_ma_state_machines(self):
        """
        Create a State Machine for each Instance of a Multiple Assigner partitioning Class
        """
        _logger.info(f"Initiating multiple assigners...")
        istates = self.ma_initial_states

        # Get each class_name and its primary id for each lifecycle
        for rnum, partition in self.ma_partitions.items():

            _logger.info(f"    {rnum} paritioned by: {partition}")

            id_attrs = partition.id_attrs
            class_name = partition.pclass

            # Tag the class relvar so that each instance has an arbitrary integer id 0..n
            class_i_rv = f"{snake(class_name)}_i"
            # We can use the above formula to obtain this relation variable later for any given class name
            Relation.tag(db=self.alias, tag_attr_name="_instance", relation=class_name)
            # Project on id attrs + the tagged _instance attr to yield the class_i_rv value
            P = tuple(id_attrs + ['_instance'])
            instance_r = Relation.project(db=self.alias, attributes=P, svar_name=class_i_rv)

            # Create a Multiple Assigner State Machine for each Instance and index it to its instance id
            for i in instance_r.body:
                # Create the Multipel Assigner State Machine
                # Create identifier value for this instance
                inst_id = {attr: i[attr] for attr in id_attrs}
                # Get the initial state for this instance from the context
                istate = istates[rnum]
                # Now use the instance id in the inner dictionary (local to class_name)
                # Ensure the inner dictionary exists for the class_name
                pass
                self.mult_assigners.setdefault(class_name, {})[i["_instance"]] = MultipleAssignerStateMachine(
                    ma_sm_id=i["_instance"],
                    current_state=istate,
                    rnum=rnum,
                    domain=self,
                    instance_id=inst_id,
                    pclass_name=class_name
                )
                _logger.info(f"       sm id: {i["_instance"]} current state: [{istate}] inst id: {inst_id}")

    def initiate_sa_assigners(self):
        """
        Initiates any Single Assigner State Machines
        """
        for sa in self.db.single_assigners:
            # TODO: Support single assigners
            # self.assigners[sa] = SingleAssignerStateMachine(current_state="None", rnum=sa.rnum, domain=self.name)
            pass
