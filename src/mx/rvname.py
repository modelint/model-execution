""" rvname.py -- Relation variable name assigner """

# System
from typing import NamedTuple
from collections import namedtuple

# Model Integration
from pyral.relation import Relation

def declare_rvs(db: str, owner: str, *names: str) -> NamedTuple:
    """
    Declare multiple relation variables and return them as a dynamically named NamedTuple.
    The field names will be the declared names with '_rv' appended.
    """
    fields = [f"{name}" for name in names]
    values = [Relation.declare_rv(db=db, owner=owner, name=name) for name in names]

    RVDynamic = namedtuple("RVDynamic", fields)
    return RVDynamic(*values)


class RVN:
    """
    Relational Variable Name
    """

    _db_counter : dict[str, int] = {}

    @classmethod
    def init_for_db(cls, db: str):
        cls._db_counter[db] = 0

    @classmethod
    def name(cls, db: str, name: str = ""):
        suffix = "" if not name else f"_{name}"
        cls._db_counter[db] += 1
        unique_name = f"rvn_{cls._db_counter[db]}{suffix}"
        return unique_name