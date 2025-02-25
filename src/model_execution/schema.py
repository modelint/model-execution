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
from pyral.rtypes import Attribute

def load_yaml(file_path):
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)  # Load YAML content safely
    return data


class Schema:
    """
    TclRAL schema a domain's class model
    """

    def __init__(self, filename: str, domain: str, types: Path):

        self.name = "cm_schema"
        self.types_filename = str(types.name) + '.yaml'
        self.domain = domain
        self.filename = filename
        # Open a PyRAL session
        self.db = "pop_mmdb"  # Name of the populated metamodel database
        self.user = "user"
        Database.open_session(name=self.db)  # This is the metamodel db populated with the user model
        Database.open_session(name=self.user)  # User model created in this database
        self.load_metamodel()
        self.build_class_relvars()

    def load_metamodel(self):
        """ Let's load and print out the metamodel database """
        Database.load(db=self.db, fname=self.filename)

        # Print out the populated metamodel
        Relvar.printall(db=self.db)

    def build_class_relvars(self):
        """
        Create class relvars

        :return:
        """
        # Load the user to system types.yaml file
        user_types = load_yaml(self.types_filename)

        R = f"Domain:<{self.domain}>"
        Relation.restrict(db=self.db, relation='Class', restriction=R, svar_name='classes')
        result = Relation.project(db=self.db, attributes=('Name', 'Cnum'), svar_name='classes')
        classes = result.body
        for c in classes:
            cname = c['Name'].replace(" ", "_")

            # Get the identifiers
            R = f"Class:<{c['Name']}>, Domain:<{self.domain}>"
            Relation.restrict(db=self.db, relation='Identifier_Attribute', restriction=R, svar_name='idattrs')
            result = Relation.project(db=self.db, attributes=('Identifier', 'Attribute'), svar_name='idattrs')
            id_attrs = result.body
            # Go get the attributes
            R = f"Class:<{c['Name']}>, Domain:<{self.domain}>"
            Relation.restrict(db=self.db, relation='Attribute', restriction=R, svar_name='attrs')
            result = Relation.project(db=self.db, attributes=('Name', 'Scalar'), svar_name='attrs')
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


