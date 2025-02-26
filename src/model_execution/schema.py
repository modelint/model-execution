""" schema.py -- Build a TclRAL schema from a populated SM Metamodel """

# System
import logging
import yaml
from pathlib import Path
from collections import defaultdict

# Model Integration
from pyral.database import Database
from pyral.relvar import Relvar
from pyral.relation import Relation
from pyral.rtypes import Attribute, Mult

# Model Execution
from model_execution.scenario import Scenario

# Here is a mapping from metamodel multiplcity notation to that used by the target TclRAL tclral
# When interacting with PyRAL we must supply the tclral specific value
mult_tclral = {
    'M': Mult.AT_LEAST_ONE,
    '1': Mult.EXACTLY_ONE,
    'Mc': Mult.ZERO_ONE_OR_MANY,
    '1c': Mult.ZERO_OR_ONE
}

def load_yaml(file_path):
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)  # Load YAML content safely
    return data


class Schema:
    """
    TclRAL schema a domain's class model
    """

    def __init__(self, filename: str, domain: str, types: Path, scenario: Path):

        self.ordinal_rnums = None
        self.gen_rnums = None
        self.non_assoc_rnums = None
        self.assoc_rnums = None

        self.name = "cm_schema"
        self.types_filename = str(types.name) + '.yaml'
        self.domain = domain
        self.filename = filename
        # Open a PyRAL session
        self.mmdb = "pop_mmdb"  # Name of the populated metamodel database
        self.user = "user"
        Database.open_session(name=self.mmdb)  # This is the metamodel mmdb populated with the user model
        Database.open_session(name=self.user)  # User model created in this database
        self.load_metamodel()
        self.build_class_relvars()
        self.sort_rels()
        self.build_simple_assocs()
        self.build_associative_rels()
        self.build_gen_rels()
        s = Scenario(scenario_file=scenario)
        pass

    def build_gen_rels(self):
        """
        Create referential constraints for each generalization relationship
            name: 'R14'
            superclass_name: 'Subsystem Element'
            super_attrs: ['Label', 'Domain']
            subs: {'Relationship': ['Rnum', 'Domain'], 'Class':['Cnum', 'Domain']}
        """
        for g in self.gen_rnums:
            # Get the name of the superclass
            R = f"Rnum:<{g}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Generalization', restriction=R)
            superclass = result.body[0]['Superclass']

            # Get the superclass referenced identifier attributes
            # This is the same for each subclass attribute reference, so we just take one
            # of them and grab the To Attributes in the reference
            result = Relation.restrict(db=self.mmdb, relation='Attribute_Reference', restriction=R)
            one_subclass = result.body[0]['From_class']
            R = f"Rnum:<{g}>, From_class:<{one_subclass}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Attribute_Reference', restriction=R)
            superclass_attrs = [ref['To_attribute'].replace(' ', '_') for ref in result.body]

            # Create a dictionary of subclass names and to attrs from each
            # First get a list of subclasses
            R = f"Rnum:<{g}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Subclass', restriction=R)
            subclass_names = [s['Class'] for s in result.body]
            # Now create a dictionary with list of referring attributes keyed by each subclass name
            subclasses = dict()
            for sub_name in subclass_names:
                R = f"Rnum:<{g}>, From_class:<{sub_name}>, Domain:<{self.domain}>"
                result = Relation.restrict(db=self.mmdb, relation='Attribute_Reference', restriction=R)
                subclasses[sub_name.replace(' ','_')] = [ref['From_attribute'].replace(' ', '_') for ref in result.body]

            # Create the generalization constraint
            Relvar.create_partition(db=self.user, name=g, superclass_name=superclass.replace(' ','_'),
                                    super_attrs=superclass_attrs, subs=subclasses)

    def build_associative_rels(self):
        """
        Create referential constraints for each association formalized by an association class
        """
        for a in self.assoc_rnums:
            # Get the name of the association class
            R = f"Rnum:<{a}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Association_Class', restriction=R)
            assoc_class = result.body[0]['Class']

            # Get the mult/cond of each participating class (referenced from the association class)
            result = Relation.restrict(db=self.mmdb, relation='Perspective', restriction=R)
            ref1_class = result.body[0]['Viewed_class']
            conditional = 'c' if result.body[0]['Conditional'] == 'True' else ''
            ref1_mult = result.body[0]['Multiplicity'] + conditional
            ref2_class = result.body[1]['Viewed_class']
            conditional = 'c' if result.body[1]['Conditional'] == 'True' else ''
            ref2_mult = result.body[1]['Multiplicity'] + conditional

            # Get the from/to attrs for ref1
            R = f"To_class:<{ref1_class}>, Rnum:<{a}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Attribute_Reference', restriction=R)
            ref1_from_attrs = [rc['From_attribute'].replace(' ', '_') for rc in result.body]
            ref1_to_attrs = [rc['To_attribute'].replace(' ', '_') for rc in result.body]

            # Get the from/to attrs for ref2
            R = f"To_class:<{ref2_class}>, Rnum:<{a}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Attribute_Reference', restriction=R)
            ref2_from_attrs = [rc['From_attribute'].replace(' ', '_') for rc in result.body]
            ref2_to_attrs = [rc['To_attribute'].replace(' ', '_') for rc in result.body]

            Relvar.create_correlation(db=self.user, name=a, correlation_relvar=assoc_class.replace(' ', '_'),
                                      correl_a_attrs=ref1_from_attrs, a_mult=mult_tclral[ref1_mult],
                                      a_relvar=ref1_class.replace(' ', '_'), a_ref_attrs=ref1_to_attrs,
                                      correl_b_attrs=ref2_from_attrs, b_mult=mult_tclral[ref2_mult],
                                      b_relvar=ref2_class.replace(' ', '_'), b_ref_attrs=ref2_to_attrs,
                                      )

    def build_simple_assocs(self):
        """
        Create referential constraints for each non-associative association
        i.e. Associations not formalized by an association class
        """
        for a in self.non_assoc_rnums:
            R = f"Rnum:<{a}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Attribute_Reference', restriction=R)
            from_class = result.body[0]['From_class']
            to_class = result.body[0]['To_class']
            from_attrs = [ref['From_attribute'].replace(" ", "_") for ref in result.body]
            to_attrs = [ref['To_attribute'].replace(" ", "_") for ref in result.body]
            R = f"Viewed_class:<{from_class}>, Rnum:<{a}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Perspective', restriction=R)
            conditional = 'c' if result.body[0]['Conditional'] == 'True' else ''
            from_mult = result.body[0]['Multiplicity'] + conditional
            R = f"Viewed_class:<{to_class}>, Rnum:<{a}>, Domain:<{self.domain}>"
            result = Relation.restrict(db=self.mmdb, relation='Perspective', restriction=R)
            conditional = 'c' if result.body[0]['Conditional'] == 'True' else ''
            to_mult = result.body[0]['Multiplicity'] + conditional
            Relvar.create_association(db=self.user, name=a,
                                      from_relvar=from_class.replace(" ", "_"), from_attrs=from_attrs, from_mult=mult_tclral[from_mult],
                                      to_relvar=to_class.replace(" ", "_"), to_attrs=to_attrs, to_mult=mult_tclral[to_mult],
                                      )

    def load_metamodel(self):
        """ Let's load and print out the metamodel database """
        Database.load(db=self.mmdb, fname=self.filename)

        # Print out the populated metamodel
        Relvar.printall(db=self.mmdb)

    def sort_rels(self):
        """
        Sort all of the domain's rnums into non associative, associative, and generalization relationships
        """
        # Simple associations
        # Get rnums from Association class
        # Subtract from all rnums in Association
        R = f"Domain:<{self.domain}>"
        Relation.restrict(db=self.mmdb, relation='Association', restriction=R, svar_name='assocs')
        Relation.project(db=self.mmdb, attributes=('Rnum',), svar_name='assocs')
        Relation.restrict(db=self.mmdb, relation='Association_Class', restriction=R, svar_name='aclasses')
        result = Relation.project(db=self.mmdb, attributes=('Rnum',), svar_name='aclasses')
        self.assoc_rnums = [r['Rnum'] for r in result.body]
        result = Relation.subtract(db=self.mmdb, rname2='aclasses', rname1='assocs')
        self.non_assoc_rnums = [r['Rnum'] for r in result.body]
        result = Relation.restrict(db=self.mmdb, relation='Generalization', restriction=R)
        self.gen_rnums = [r['Rnum'] for r in result.body]
        result = Relation.restrict(db=self.mmdb, relation='Ordinal_Relationship', restriction=R)
        self.ordinal_rnums = [r['Rnum'] for r in result.body]


    def build_class_relvars(self):
        """
        Create class relvars
        """
        # Load the user to system types.yaml file
        user_types = load_yaml(self.types_filename)

        R = f"Domain:<{self.domain}>"
        Relation.restrict(db=self.mmdb, relation='Class', restriction=R, svar_name='classes')
        result = Relation.project(db=self.mmdb, attributes=('Name', 'Cnum'), svar_name='classes')
        classes = result.body
        for c in classes:
            cname = c['Name'].replace(" ", "_")

            # Get the identifiers
            R = f"Class:<{c['Name']}>, Domain:<{self.domain}>"
            Relation.restrict(db=self.mmdb, relation='Identifier_Attribute', restriction=R, svar_name='idattrs')
            result = Relation.project(db=self.mmdb, attributes=('Identifier', 'Attribute'), svar_name='idattrs')
            id_attrs = result.body
            # Go get the attributes
            R = f"Class:<{c['Name']}>, Domain:<{self.domain}>"
            Relation.restrict(db=self.mmdb, relation='Attribute', restriction=R, svar_name='attrs')
            result = Relation.project(db=self.mmdb, attributes=('Name', 'Scalar'), svar_name='attrs')
            attrs = result.body

            attr_list = [Attribute(name=a['Name'], type=user_types[a['Scalar']]) for a in attrs]


            # attr_list = [a['Name'].replace(" ", "_") for a in attrs]
            id_dict = defaultdict(list)

            for i in id_attrs:
                key = int(i['Identifier'])  # Convert Identifier to int if needed
                id_dict[key].append(i['Attribute'].replace(" ", "_"))
            ids = dict(id_dict)

            Relvar.create_relvar(db=self.user, name=cname, attrs=attr_list, ids=ids)

        # Print out the populated metamodel
        print("\nUser model\n-----")
        Relvar.printall(db=self.user)
        pass


