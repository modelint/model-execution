""" instance_set.py -- instance set and reference management """

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb

class InstanceSet:
    """
    Instance reference management.

    An instance reference is a relation with a header corresponding to some identifier of a class.
    """

    @staticmethod
    def irefs(db: str, iset_rv: str, irefs_rv: str, class_name: str, domain_name: str, id_num: int = 1):
        """
        Project an instance set onto an identifier to produce instance references.

        Given an input instance set relation, projects on the specified identifier (ID1 by default)
        and sets the supplied irefs relation variable to the instance reference relation.

        Args:
            db: The domain database.
            iset_rv: Relation variable with the input instance set.
            irefs_rv: Relation variable set to extracted instance references.
            class_name: Name of the class.
            domain_name: Domain of this class.
            id_num: Identifier number to project on. Defaults to 1 (ID1), but any other ID
                defined on the class may be specified instead.
        """
        # Look up the class's identifier attributes and pack them into a tuple
        R = f"Identifier:<{str(id_num)}>, Class:<{class_name}>, Domain:<{domain_name}>"
        id_attr_r = Relation.restrict(db=mmdb, relation="Identifier Attribute", restriction=R)
        id_attrs = tuple(t["Attribute"] for t in id_attr_r.body)
        # Project on that tuple and assign the result to the supplied irefs relation variable
        Relation.project(db=db, relation=iset_rv, attributes=id_attrs, svar_name=irefs_rv)

    @staticmethod
    def instances(db: str, irefs_rv: str, iset_rv: str, class_name: str):
        """
        Expand instance references into a full instance set.

        Given a set of instance references as a relation variable, updates that variable to
        the value of the corresponding instance set.

        Args:
            db: The domain database.
            irefs_rv: The input set of instance references to be converted to corresponding instances.
            iset_rv: Relation variable to be set to the resulting instance set.
            class_name: The class whose instances the irefs identify.
        """
        Relation.join(db=db, rname1=irefs_rv, rname2=class_name, svar_name=iset_rv)
