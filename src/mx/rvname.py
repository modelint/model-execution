""" rvname.py -- Relation variable name assigner """

# System
from typing import Any
from collections import namedtuple

# Model Integration
from pyral.relation import Relation

def declare_rvs(db: str, owner: str, *names: str) -> Any:
    """
    Declare multiple relation variables and return them as a dynamically named NamedTuple.
    The field names will be the declared names with '_rv' appended.
    """
    fields = [f"{name}" for name in names]
    values = [Relation.declare_rv(db=db, owner=owner, name=name) for name in names]

    RVDynamic = namedtuple("RVDynamic", fields)
    return RVDynamic(*values)