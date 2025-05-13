""" scalar_switch.py  -- execute a scalar_switch action """

# System
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.method import Method  # TOOD: Replace with Activity after refactoring State/Assigner Activities

# Model Integration
from pyral.relation import Relation

# MX
from mx.db_names import mmdb
from mx.actions.action import Action
from mx.actions.flow import ActiveFlow
from mx.rvname import RVN


class ScalarSwitch(Action):

    def __init__(self, action_id: str, activity: "Method"):
        """
        Perform the Traverse Action on a domain model.

        Note: For now we are only handling Methods, but State Activities will be incorporated eventually.

        :param action_id:  The ACTN<n> value identifying each Action instance
        :param activity: The A<n> Activity ID (for Method and State Activities)
        """
        super().__init__(activity=activity, anum=activity.anum, action_id=action_id)

        # Lookup the Action instance
        # Start with all Switch actions in this Activity
        activity_scalar_switch_actions_rv = RVN.name(db=mmdb, name="activity_scalar_switch_actions")
        Relation.semijoin(db=mmdb, rname1=activity.method_rvname, rname2="Scalar Switch Action",
                          svar_name=activity_scalar_switch_actions_rv)
        # Narrow it down to this Switch Action instance
        this_scalar_switch_action_rv = RVN.name(db=mmdb, name="this_scalar_switch_action")
        R = f"ID:<{action_id}>"
        scalar_switch_action_t = Relation.restrict(db=mmdb, relation=activity_scalar_switch_actions_rv, restriction=R,
                          svar_name=this_scalar_switch_action_rv)
        if self.activity.xe.debug:
            Relation.print(db=mmdb, variable_name=this_scalar_switch_action_rv)

        self.source_flow_name = scalar_switch_action_t.body[0]["Scalar_input"]
        self.source_flow = self.activity.flows[self.source_flow_name]  # The active content of source flow (value, type)
        pass