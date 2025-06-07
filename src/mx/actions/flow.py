""" flow.py -- Active Flow type """

# System
from typing import TYPE_CHECKING, NamedTuple, Any

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb
if TYPE_CHECKING:
    from mx.activity import Activity


class ActiveFlow(NamedTuple):
    value: Any
    flowtype: str

def label(name: str, activity: "Activity") -> str:
    R = f"ID:<{name}>, Activity:<{activity.anum}>, Domain:<{activity.domain}>"
    labeled_flow_r = Relation.restrict(db=mmdb, relation='Labeled Flow', restriction=R)
    if labeled_flow_r.body:
        return labeled_flow_r.body[0]["Name"]
    else:
        return ""




