""" domain.py -- Represents a modeled domain defined in the metamodel """

# System
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain_model_db import DomainModelDB

# Model Integration
from pyral.relation import Relation

# Model Execution
# from domain_model_db import MultipleAssigner
# from mx.single_assigner_state_machine import SingleAssignerStateMachine
from mx.multiple_assigner_state_machine import MultipleAssignerStateMachine
from mx.assigner_state_machine import AssignerStateMachine
from mx.lifecycle_state_machine import LifecycleStateMachine
# from mx.db_names import mmdb
# from mx.exceptions import *

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
        self.assigners: dict[str, list[AssignerStateMachine]] = {}
        self.initiate_lifecycles()  # Create a lifecycle statemachine for each class with a lifecycle
        self.initiate_assigners()  # Create an assigner statemachine for each relationship managed by an assigner

    def initiate_lifecycles(self):
        """
        Create a state machine for each class with a lifecycle
        """
        # Get each class_name and its primary id for each lifecycle
        for class_name, id_attrs in self.db.lifecycles.items():
            # Get all the instances from the user model for that class
            inst_result = Relation.restrict(db=self.alias, relation=f"{class_name.replace(' ', '_')}")
            # Create a lifecycle statemachine for each instance
            for i in inst_result.body:
                # Get initial state from the context
                istates = self.db.context.lifecycle_istates
                # Create identifier value for this instance
                inst_id = {attr: i[attr] for attr in id_attrs}
                # Get the initial state for this instance from the context
                istate = istates[class_name]
                # Create the lifecycle and add it to our dictionary of lifecycles keyed by class name
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
        """
        for ma in self.db.mult_assigners:
            pclass_id = self.db.pclasses[ma.pclass]
            result = Relation.restrict(db=self.alias, relation=ma.pclass)
            for t in result.body:
                # build the id
                id_val = {attr: t[attr] for attr in pclass_id}
                istate = self.db.context.ma_istates[ma.rnum].state
                self.assigners.setdefault(ma, []).append(MultipleAssignerStateMachine(current_state=istate,
                                                              rnum=ma.rnum, pclass_name=ma.pclass,
                                                              instance_id=id_val,
                                                              domain=self.name))

        for sa in self.db.single_assigners:
            # TODO: Support single assigners
            # self.assigners[sa] = SingleAssignerStateMachine(current_state="None", rnum=sa.rnum, domain=self.name)
            pass

