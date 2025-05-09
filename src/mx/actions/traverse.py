""" traverse.py  -- execute a traverse action """

# System
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.rvname import RVN
from mx.actions.flow import ActiveFlow


class Traverse(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Traverse Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # We define a distinct method to trace each subclass of Hop
        execute_hop: dict[str, Callable[..., str]] = {  # The only type hint that seems to work with PyCharm
            "straight": self.straight_hop,
            "to association class": self.to_association_class_hop,
            "from asymmetric assocation": self.from_asymmetric_association_class_hop,
        }


        # Lookup the Action instance
        # Start with all Traverse actions in this Activity
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Traverse_Action")
        # Narrow it down to this Traverse Action instance
        R = f"ID:<{action_id}>"
        traverse_action_rv = RVN.name(db=mmdb, name="traverse_action")
        traverse_action_t = Relation.restrict(db=mmdb, restriction=R, svar_name=traverse_action_rv)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=traverse_action_rv)

        # Extract input and output flows required by the Traversal Action
        self.source_flow_name = traverse_action_t.body[0]["Source_flow"]  # Name like F1, F2, etc
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        self.hop_from_class = self.source_flow.flowtype  # Starts at source class and updates on each hop
        # Just the name of the destination flow since it isn't enabled until after the Traversal Action executes
        self.dest_flow_name = traverse_action_t.body[0]["Destination_flow"]
        # And the output of the Traversal will be placed in the Activity flow dictionary
        # upon completion of this Action

        # Now gather all of the Hops in the Path
        all_hops_rv = RVN.name(db=self.domdb, name="all_hops")
        hops_r = Relation.semijoin(db=mmdb, rname1=traverse_action_rv, rname2="Hop", svar_name=all_hops_rv)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=all_hops_rv)

        # Sort them by hop number so that we proceed 1, 2, ...
        hops = hops_r.body
        hops.sort(key=lambda d: int(d['Number']))  # Sorts in place

        # Initial hop starts at the source flow instance set
        hop_from_rv = self.source_flow.value

        for h in hops:
            # Create relation variable for this hop
            R = f"Number:<{h["Number"]}>"
            hop_rv = RVN.name(db=mmdb, name="this_hop")
            Relation.restrict(db=mmdb, relation=all_hops_rv, restriction=R, svar_name=hop_rv)
            if self.activity.xe.debug:
                Relation.print(db=mmdb, variable_name=hop_rv)

            if self.activity.xe.debug:
                print("\nHop from this input flow:")
                Relation.print(db=self.domdb, variable_name=hop_from_rv)

            # Determine its type
            hop_type = self.find_hop_type(hop_rv=hop_rv)

            # Execute the hop and set input to next hop as output from this hop
            hop_from_rv = execute_hop[hop_type](hop_t=h, hop_rv=hop_rv, hop_from_rv=hop_from_rv)

        self.activity.flows[self.dest_flow_name] = ActiveFlow(value=hop_from_rv, flowtype=self.hop_from_class)


        pass  # All hops completed

    def from_asymmetric_association_class_hop(self, hop_t: dict[str, str], hop_rv: str, hop_from_rv: str) -> str:
        """
        Traverse a From Assymetric Association Class Hop - (from association to participating class)

        :param hop_t: Hop tuple as a dictionary
        :param hop_rv: The relational variable for the hop
        :param hop_from_rv: The relational variable of the instance set we are hopping from
        :return: The output instance set as a relational variable name
        """
        # Get the referential attributes, source and target classes
        Relation.semijoin(db=mmdb, rname1=hop_rv, rname2="Attribute_Reference",
                          attrs={"Domain": "Domain", "Class_step": "From_class", "Rnum": "Rnum"})
        # Select out the To_class matching Class_step for this hop
        R = f"To_class:<{self.hop_from_class}>"
        hop_attr_refs_r = Relation.restrict(db=mmdb, restriction=R)

        if self.activity.xe.debug:
            print("\nExecuting a To Association Class Hop")
            Relation.print(db=mmdb, table_name="hop_attr_refs")



        # Convert each attribute reference to a join pair
        join_pairs = {aref["To_attribute"]: aref["From_attribute"] for aref in hop_attr_refs_r.body}

        hopped_rv = RVN.name(db=self.domdb, name=f"hop_number_{hop_t["Number"]}")
        hop_to_class = hop_t["Class_step"].replace(' ', '_')
        Relation.semijoin(db=self.domdb, rname2=hop_to_class, rname1=hop_from_rv,
                          attrs=join_pairs, svar_name=hopped_rv)
        if self.activity.xe.debug:
            print("\nTo Association Class Hop output")
            Relation.print(db=self.domdb, variable_name=hopped_rv)
        self.hop_from_class = hop_to_class # TODO: Check
        return hopped_rv
    def to_association_class_hop(self, hop_t: dict[str, str], hop_rv: str, hop_from_rv: str) -> str:
        """
        Traverse a To Association Class Hop - (from participating to association class)

        :param hop_t: Hop tuple as a dictionary
        :param hop_rv: The relational variable for the hop
        :param hop_from_rv: The relational variable of the instance set we are hopping from
        :return: The output instance set as a relational variable name
        """
        # Get the referential attributes, source and target classes
        Relation.semijoin(db=mmdb, rname1=hop_rv, rname2="Attribute_Reference",
                                          attrs={"Domain": "Domain", "Class_step": "From_class", "Rnum": "Rnum"})
        # Select out the To_class matching Class_step for this hop
        R = f"To_class:<{self.hop_from_class}>"
        hop_attr_refs_r = Relation.restrict(db=mmdb, restriction=R)

        if self.activity.xe.debug:
            print("\nExecuting a To Association Class Hop")
            Relation.print(db=mmdb, table_name="hop_attr_refs")



        # Convert each attribute reference to a join pair
        join_pairs = {aref["To_attribute"]: aref["From_attribute"] for aref in hop_attr_refs_r.body}

        hopped_rv = RVN.name(db=self.domdb, name=f"hop_number_{hop_t["Number"]}")
        hop_to_class = hop_t["Class_step"].replace(' ', '_')
        Relation.semijoin(db=self.domdb, rname2=hop_to_class, rname1=hop_from_rv,
                          attrs=join_pairs, svar_name=hopped_rv)
        if self.activity.xe.debug:
            print("\nTo Association Class Hop output")
            Relation.print(db=self.domdb, variable_name=hopped_rv)
        self.hop_from_class = hop_to_class # TODO: Check
        return hopped_rv

    def straight_hop(self, hop_t: dict[str, str], hop_rv: str, hop_from_rv: str) -> str:
        """
        Traverse a Straight Hop - (from class to class across non-associative binary association)

        :param hop_t: Hop tuple as a dictionary
        :param hop_rv: The relational variable for the hop
        :param hop_from_rv: The relational variable of the instance set we are hopping from
        :return: The output instance set as a relational variable name
        """
        # Get the referential attributes, source and target classes
        hop_attr_refs_r = Relation.semijoin(db=mmdb, rname1=hop_rv, rname2="Attribute_Reference",
                                            attrs={"Domain": "Domain", "Class_step": "To_class", "Rnum": "Rnum"})
        if self.activity.xe.debug:
            print("\nExecuting a Straight Hop")
            Relation.print(db=mmdb, table_name="hop_attr_refs")

        # Compose a semijoin on the domain with the source flow ## step class on Ref attrs

        # Convert each attribute reference to a join pair
        join_pairs = {aref["From_attribute"]: aref["To_attribute"] for aref in hop_attr_refs_r.body}

        hopped_rv = RVN.name(db=self.domdb, name=f"hop_number_{hop_t["Number"]}")
        hop_to_class = hop_t["Class_step"].replace(' ', '_')
        Relation.semijoin(db=self.domdb, rname1=hop_from_rv, rname2=hop_to_class,
                          attrs=join_pairs, svar_name=hopped_rv)
        if self.activity.xe.debug:
            print("\nStraight Hop output")
            Relation.print(db=self.domdb, variable_name=hopped_rv)
        self.hop_from_class = hop_to_class
        return hopped_rv

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
        result = Relation.join(db=mmdb, rname1=hop_rv, rname2="Association_Class_Hop")
        if result.body:
            # It's an Association Class Hop, but which direction?
            result = Relation.join(db=mmdb, rname2="To_Association_Class_Hop")
            if result.body:
                return "to association class"
            result = Relation.join(db=mmdb, rname2="From_Asymmetric_Associaton_Class_Hop")
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
        pass
