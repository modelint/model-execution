""" instance_set.py -- instance set and reference management """

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb

class InstanceSet:
    """
    Instance reference management:
    An instance reference is a relation with a header correpsonding to some identifier of a class
    """

    @staticmethod
    def irefs(db: str, iset_rv: str, irefs_rv: str, class_name: str, domain_name: str, id_num: int = 1):
        """
        Given an input instance set relation, we project on the specified identifier (ID1) by default and set
        the supplied irefs relation variable to the instance reference relation

        :param db: The domain database
        :param iset_rv: Relation variable with the input instance set
        :param irefs_rv:  Relation variable set to extracted instance references
        :param class_name:  Name of the class
        :param domain_name:  Domain of this class
        :param id_num:  By default, ID1 is used, but any other ID defined on the class may be specified instead
        """
        # Look up the class's identifier attributes and pack them into a tuple
        R = f"Identifier:<{str(id_num)}>, Class:<{class_name}>, Domain:<{domain_name}>"
        id_attr_r = Relation.restrict(db=mmdb, relation="Identifier Attribute", restriction=R)
        id_attrs = tuple(t["Attribute"] for t in id_attr_r.body)
        # Project on that tuple and assign the result to the supplied irefs relation variable
        Relation.project(db=db, relation=iset_rv, attributes=id_attrs, svar_name=irefs_rv)

    @staticmethod
    def instances(db: str, irefs_rv: str, class_name: str):
        """
        Given a set of instance references as a relation variable, update that variable to
        the value of the correpsonding instance set.

        :param db: The domain database
        :param irefs_rv: The input set of instance references to be converted to corresponding instances
        :param class_name: The irefs refer to instances of this class
        """
        Relation.join(db=db, rname1=irefs_rv, rname2=class_name, svar_name=irefs_rv)
