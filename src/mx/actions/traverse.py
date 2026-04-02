""" traverse.py  -- execute a traverse action """

# System
from typing import TYPE_CHECKING, Callable, NamedTuple

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation, _relation
from pyral.database import Database  # For diagnostics

# MX
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow, FlowDir
from mx.rvname import declare_rvs
from mx.instance_set import InstanceSet
from mx.exceptions import *

if __debug__:
    from mx.utility import *

_logger = logging.getLogger(__name__)


# Tuple generator and rv class for Metamodel Database (mmdb)
class MMRVs(NamedTuple):
    activity_traverse_actions: str  # All traverse actions defined in this activity
    this_traverse_action: str  # This traverse action
    all_hops: str
    this_hop: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner, "activity_traverse_actions", "this_traverse_action",
                      "all_hops", "this_hop")
    return MMRVs(*rvs)


# Tuple generator and rv class for Domain Database (dom)
class DomRVs(NamedTuple):
    hopped: str
    output_irefs: str


def declare_dom_rvs(db: str, owner: str) -> DomRVs:
    rvs = declare_rvs(db, owner, "hopped", "output_irefs")
    return DomRVs(*rvs)


class Traverse(ActionExecution):

    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        """
        Perform the Traverse Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        Args:
            action_id: The ACTN<n> value identifying each Action instance
            activity_execution:  The Activity Execution object
        """
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        if __debug__:
            _rv_before = Database.get_all_rv_names()

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_mm_rvs(owner=self.owner)
        self.domrv = declare_dom_rvs(db=self.domdb, owner=self.owner)
        mmrv = self.mmrv
        domrv = self.domrv

        if __debug__:
            _rv_before = Database.get_all_rv_names()

        # We define a distinct method to trace each subclass of Hop
        execute_hop: dict[str, Callable[..., str]] = {  # The only type hint that seems to work with PyCharm
            "straight": self.straight_hop,
            "to association class": self.to_association_class_hop,
            "from asymmetric association class": self.from_asymmetric_association_class_hop,
            # TODO: Several more to come (generalization, ordinal, etc)
        }

        # Lookup this Action instance
        traverse_action_r = Relation.semijoin(db=mmdb, rname1=self.action_mmrv,
                                              rname2="Traverse Action",
                                              svar_name=mmrv.this_traverse_action)
        if not traverse_action_r.body:
            msg = f"Traverse action {self.activity_execution.anum}-{self.action_id} not found in metamodel"
            _logger.error(msg)
            raise MXMetamodelDBException(msg)

        traverse_action_t = traverse_action_r.body[0]

        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.this_traverse_action))
        _logger.info(f"- Path: {traverse_action_t['Path']}")
        _logger.info("Flows")

        # Extract input and output flows required by the Traversal Action
        # ---
        # Get the name of the input flow (F1, F2, etc)
        self.source_flow_name = traverse_action_t["Source_flow"]
        # Save the content of that flow (value, type)
        self.source_flow = self.activity_execution.flows[self.source_flow_name]
        log_table(_logger, nsflow_msg(db=self.domdb, flow_name=self.source_flow_name, flow_dir=FlowDir.IN,
                                      flow_type=self.source_flow.flowtype, activity=self.activity_execution,
                                      rv_name=self.source_flow.value))
        # The name of the class we are currently hopping from, we will update as we hop
        # Initialize it on the class (type) of the source flow
        self.hop_from_class = self.source_flow.flowtype
        # Save the name of the currently empty output (destination) flow
        # We'll set its value after we complete all hops in this traversal
        self.dest_flow_name = traverse_action_t["Destination_flow"]

        # Join our Traverse Action to the Hop class to gather all of the Hops in the Path
        hops_r = Relation.semijoin(db=mmdb, rname1=mmrv.this_traverse_action, rname2="Hop", svar_name=mmrv.all_hops)
        log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.all_hops))
        # For traversal we need to order these in the numbered hop sequence, 1, 2, ...
        hops = hops_r.body
        hops.sort(key=lambda d: int(d['Number']))  # Sorts in place

        # Initial hop starts at the source flow instance set
        hop_from_rv = self.source_flow.value

        # Execute each hop in sequence until we reach the end of the traversal
        for h in hops:
            # Create relation variable for this hop
            R = f"Number:<{h["Number"]}>"
            Relation.restrict(db=mmdb, relation=mmrv.all_hops, restriction=R, svar_name=mmrv.this_hop)
            log_table(_logger, table_msg(db=mmdb, variable_name=mmrv.this_hop))
            _logger.info("Hop from this input flow:")
            log_table(_logger, table_msg(db=self.domdb, variable_name=hop_from_rv))

            # Determine its type
            hop_type = self.find_hop_type(hop_rv=mmrv.this_hop)

            # Execute the hop and set input to next hop as output from this hop
            hop_from_rv = execute_hop[hop_type](hop_t=h, hop_rv=mmrv.this_hop, hop_from_rv=hop_from_rv)

            log_table(_logger, table_msg(db=self.domdb, variable_name=hop_from_rv))

        # Extract instance references
        InstanceSet.irefs(db=self.domdb, iset_rv=hop_from_rv, irefs_rv=domrv.output_irefs,
                          class_name=self.hop_from_class, domain_name=self.activity_execution.domain.name)

        output_flow_content = ActiveFlow(value=domrv.output_irefs, flowtype=self.hop_from_class)
        self.activity_execution.flows[self.dest_flow_name] = output_flow_content
        log_table(_logger, nsflow_msg(
            flow_name=self.dest_flow_name, flow_dir=FlowDir.OUT,
            flow_type=self.hop_from_class, activity=self.activity_execution,
            db=self.domdb, rv_name=domrv.output_irefs
        ))
        log_table(_logger, table_msg(db=self.domdb, variable_name=domrv.output_irefs))
        Relation.free_rvs(db=mmdb, owner=self.owner)

        if __debug__:
            _rv_after_mmdb_free = Database.get_rv_names(db=mmdb)
            _rv_after_dom_free = Database.get_rv_names(db=self.domdb)

        self.complete()

    def from_asymmetric_association_class_hop(self, hop_t: dict[str, str], hop_rv: str, hop_from_rv: str) -> str:
        """
        Traverse a From Assymetric Association Class Hop - (from association to participating class)

        :param hop_t: Hop tuple as a dictionary
        :param hop_rv: The relational variable for the hop
        :param hop_from_rv: The relational variable of the instance set we are hopping from
        :return: The output instance set as a relational variable name
        """
        drv = self.domrv
        # Get the referential attributes, source and target classes
        ref_attrs_rv = Relation.declare_rv(db=mmdb, owner=self.owner, name="ref_attrs")
        hop_attr_refs_r = Relation.semijoin(db=mmdb, rname1=hop_rv, rname2="Attribute_Reference",
                                            attrs={"Domain": "Domain", "Class_step": "To_class", "Rnum": "Rnum"},
                                            svar_name=ref_attrs_rv)

        _logger.info("Executing a From Asymmetric Association Class Hop")
        log_table(_logger, table_msg(db=mmdb, variable_name=ref_attrs_rv))

        # Convert each attribute reference to a join pair
        join_pairs = {aref["From_attribute"]: aref["To_attribute"] for aref in hop_attr_refs_r.body}

        hop_to_class = hop_t["Class_step"]
        Relation.semijoin(db=self.domdb, rname2=hop_to_class, rname1=hop_from_rv,
                          attrs=join_pairs, svar_name=drv.hopped)
        _logger.info("From Asymmetric Association Class Hop output")
        log_table(_logger, table_msg(db=self.domdb, variable_name=drv.hopped))
        self.hop_from_class = hop_to_class
        Relation.free_rvs(db=mmdb, owner=self.owner, names=("ref_attrs",))
        return drv.hopped

    def to_association_class_hop(self, hop_t: dict[str, str], hop_rv: str, hop_from_rv: str) -> str:
        """
        Traverse a To Association Class Hop - (from participating to association class)

        :param hop_t: Hop tuple as a dictionary
        :param hop_rv: The relational variable for the hop
        :param hop_from_rv: The relational variable of the instance set we are hopping from
        :return: The output instance set as a relational variable name
        """
        drv = self.domrv
        mrv = self.mmrv
        # Get the referential attributes, source and target classes
        ref_attrs_rv = Relation.declare_rv(db=mmdb, owner=self.owner, name="ref_attrs")
        Relation.semijoin(db=mmdb, rname1=mrv.this_hop, rname2="Attribute_Reference",
                          attrs={"Domain": "Domain", "Class_step": "From_class", "Rnum": "Rnum"},
                          svar_name=ref_attrs_rv)
        _logger.info("Ref attrs for this hop")
        log_table(_logger, table_msg(db=mmdb, variable_name=ref_attrs_rv))
        # Select out the To_class matching Class_step for this hop
        R = f"To_class:<{self.hop_from_class}>"
        hop_attr_refs_r = Relation.restrict(db=mmdb, relation=ref_attrs_rv, restriction=R)

        _logger.info("Executing a To Association Class Hop")
        log_table(_logger, table_msg(db=mmdb, variable_name=_relation, table_name="hop_attr_refs"))

        # Convert each attribute reference to a join pair
        join_pairs = {aref["To_attribute"]: aref["From_attribute"] for aref in hop_attr_refs_r.body}

        hop_to_class = hop_t["Class_step"]
        Relation.semijoin(db=self.domdb, rname2=hop_to_class, rname1=hop_from_rv,
                          attrs=join_pairs, svar_name=drv.hopped)
        _logger.info("To Association Class Hop output")
        log_table(_logger, table_msg(db=self.domdb, variable_name=drv.hopped))
        self.hop_from_class = hop_to_class
        Relation.free_rvs(db=mmdb, owner=self.owner, names=("ref_attrs",))
        return drv.hopped

    def straight_hop(self, hop_t: dict[str, str], hop_rv: str, hop_from_rv: str) -> str:
        """
        Traverse a Straight Hop - (from class to class across non-associative binary association)

        :param hop_t: Hop tuple as a dictionary
        :param hop_rv: The relational variable for the hop
        :param hop_from_rv: The relational variable of the instance set we are hopping from
        :return: The output instance set as a relational variable name
        """
        # Shorter names
        drv = self.domrv

        # Get the referential attributes, source and target classes
        hop_attr_refs_r = Relation.semijoin(db=mmdb, rname1=hop_rv, rname2="Attribute_Reference",
                                            attrs={"Domain": "Domain", "Class_step": "To_class", "Rnum": "Rnum"})
        _logger.info("Executing a Straight Hop")
        log_table(_logger, table_msg(db=mmdb, variable_name=_relation, table_name="hop_attr_refs"))

        # Convert each attribute reference to a join pair
        join_pairs = {aref["From_attribute"]: aref["To_attribute"] for aref in hop_attr_refs_r.body}

        source_inst_rv = Relation.declare_rv(db=self.domdb, owner=self.owner, name="source_inst")
        Relation.join(db=self.domdb, rname1=hop_from_rv, rname2=self.hop_from_class, svar_name=source_inst_rv)
        _logger.info("Hopping from instances:")
        log_table(_logger, table_msg(db=self.domdb, variable_name=source_inst_rv))

        hop_to_class = hop_t["Class_step"]
        Relation.semijoin(db=self.domdb, rname1=source_inst_rv, rname2=hop_to_class,
                          attrs=join_pairs, svar_name=drv.hopped)
        _logger.info("Straight Hop output")
        log_table(_logger, table_msg(db=self.domdb, variable_name=drv.hopped))
        self.hop_from_class = hop_to_class
        Relation.free_rvs(db=self.domdb, owner=self.owner, names=("source_inst",))
        return drv.hopped

    def find_hop_type(self, hop_rv: str) -> str:
        """
        Determine the metamodel subclass of this Hop tuple

        :param hop_rv:  A relational variable holding a single tuple representing the Hop instance
        :return: Name of the subclass (hop type)
        """
        # Let's rule out (or in) Generalization first since the logic is simple
        result = Relation.join(db=mmdb, rname1=hop_rv, rname2="Generalization")
        if result.body:
            result = Relation.join(db=mmdb, rname2="To_Superclass_Hop")  # Note we can join the previous result
            if result.body:
                return "to superclass"
            else:
                return "to subclass"

        # It's an Association Hop
        # We proceed from the most likely to the least likely cases
        # Is it a straight, nonassociation class hop
        result = Relation.join(db=mmdb, rname1=hop_rv, rname2="Straight_Hop")
        if result.body:
            return "straight"

        # Now it's either an Association Class or Circular Hop
        result = Relation.join(db=mmdb, rname1=hop_rv, rname2="Association_Class_Hop", svar_name="assoc_class_hop")
        if result.body:
            # It's an Association Class Hop, but which direction?
            result = Relation.join(db=mmdb, rname2="To_Association_Class_Hop")
            if result.body:
                return "to association class"
            result = Relation.join(db=mmdb, rname1="assoc_class_hop", rname2="From_Asymmetric_Association_Class_Hop")
            if result.body:
                return "from asymmetric association class"
            else:
                return "from symmetric association class"

        # It's a Circular Hop, but what kind?
        result = Relation.join(db=mmdb, rname1=hop_rv, rname2="Symmetric_Hop")
        if result:
            return "symmetric"
        result = Relation.join(db=mmdb, rname2="Asymmetric_Circular_Hop")
        if result:
            return "asymmetric circular"
        else:
            return "ordinal"

        # TODO: Use PyRAL relation create to convert hop to an rv
