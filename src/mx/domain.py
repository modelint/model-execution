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

    def __init__(self, name: str, alias: str, db:'DomainModelDB'):
        """
        Instantiate the domain

        :param name: The name of the domain, used for indexing into the mmdb
        :param alias: The domain alias serves as the name of the corresponding domain database
        """
        self.name = name
        self.alias = alias  # Now we have access to both the mmdb and this domain's schema
        self.db = db
        self.lifecycles: dict[str, LifecycleStateMachine] = {}
        # self.assigners: dict[str, AssignerStateMachine] = {}
        self.initiate_lifecycles()  # Create a lifecycle statemachine for each class with a lifecycle
        self.initiate_assigners()  # Create an assigner statemachine for each relationship managed by an assigner

    def initiate_lifecycles(self):
        """
        Create a state machine for each class with a lifecycle
        """
        # Get the names of each class in this domain with a lifecycle defined
        R = f"Domain:<{self.name}>"
        l_result = Relation.restrict(db=mmdb, relation='Lifecycle', restriction=R)
        class_names = [t['Class'] for t in l_result.body]

        # Now get the identifier attributes of all of these classes
        R = f"Domain:<{self.name}>, Identifier:<1>"
        Relation.join(db=mmdb, rname2='Identifier_Attribute', rname1='Lifecycle', svar_name='id_all')
        # id_all relation has all identifier attributes for all classes with lifecycles

        for c in class_names:
            R = f"Class:<{c}>"
            i_result = Relation.restrict(db=mmdb, restriction=R, relation='id_all')
            c_id_attrs = [t['Attribute'] for t in i_result.body]  # id attributes for the current class

            inst_result = Relation.restrict(db=self.alias, relation=f"{c}")
            for i in inst_result.body:
                # create identifier value
                inst_id = {ia:i[ia] for ia in c_id_attrs}
                self.lifecycles[c] = LifecycleStateMachine(current_state='IDLE', instance_id=inst_id,
                                                           class_name=c, domain=self.name)
                pass


            pass




        # for row in class_result.body:
        #     class_name = row.value()
        #     pass
        #     R = f"Class:<>, Domain:<{self.name}>"
        #     id_result =
        #     dom_result = Relation.restrict(db=self.alias, relation=lifecycle_result['Class'])
        #     for instance in dom_result.body:
        #         pass
        #         self.lifecycles[lifecycle['Name']] = LifecycleStateMachine()
        # pass

    def initiate_assigners(self):
        """

        :param self:
        """
        R = f"Domain:<{self.name}>"
        result = Relation.restrict(db=mmdb, relation='Lifecycle', restriction=R)
        pass
