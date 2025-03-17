""" domain.py -- Represents a modeled domain defined in the metamodel """

# System
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain_model_db import DomainModelDB

# Model Integration
from pyral.relation import Relation

# Model Execution
# from mx.assigner_state_machine import AssignerStateMachine
from mx.lifecycle_state_machine import LifecycleStateMachine
from mx.db_names import mmdb
from mx.exceptions import *

_logger = logging.getLogger(__name__)


class Domain:
    """
    An Domain is an active component that can respond to external input
    """

    def __init__(self, name: str, alias: str, db: 'DomainModelDB'):
        """
        Instantiate the domain

        :param name: The name of the domain, used for indexing into the mmdb
        :param alias: The domain alias serves as the name of the corresponding domain database
        """
        self.name = name
        self.alias = alias  # Now we have access to both the mmdb and this domain's schema
        self.db = db
        self.lifecycles: dict[str, list[LifecycleStateMachine]] = {}
        # self.assigners: dict[str, AssignerStateMachine] = {}
        self.initiate_lifecycles()  # Create a lifecycle statemachine for each class with a lifecycle
        self.initiate_assigners()  # Create an assigner statemachine for each relationship managed by an assigner

    def initiate_lifecycles(self):
        """
        Create a state machine for each class with a lifecycle
        """
        for class_name, id_attrs in self.db.lifecycles.items():
            inst_result = Relation.restrict(db=self.alias, relation=f"{class_name.replace(' ', '_')}")
            for i in inst_result.body:
                # Get initial state
                istates = self.db.context.lifecycle_istates
                # create identifier value
                inst_id = {attr: i[attr] for attr in id_attrs}
                istate = istates[class_name]
                self.lifecycles.setdefault(class_name, []).append(
                    LifecycleStateMachine(current_state=istate, instance_id=inst_id,
                                          class_name=class_name, domain=self.name)
                )
                pass

            pass
        pass

    def initiate_assigners(self):
        """
        Initiates any single and multiple assigner state machines

        :param self:
        """
        R = f"Domain:<{self.name}>"
        ma_result = Relation.restrict(db=mmdb, relation='Multiple_Assigner', restriction=R)
        if ma_result.body:
            pass
        sa_result = Relation.restrict(db=mmdb, relation='Single_Assigner', restriction=R)
        if sa_result.body:
            pass
        pass
