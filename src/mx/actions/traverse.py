""" traverse.py  -- execute a traverse action """

# MX
from mx.actions.action import Action

# Model Integration
from pyral.relation import Relation


class Traverse(Action):

    def __init__(self, anum: str, action_id: str, input_instance_flow: str, output_instance_flow: str, path):
        """

        :param anum:
        :param action_id:
        :param input_instance_flow:
        :param output_instance_flow:
        :param path:
        """
        super().__init__(anum=anum, action_id=action_id)

        R = f"Phrase:<{phrase}>, Domain:<{cls.domain}>"
        result = Relation.restrict(db=db, relation='Perspective', restriction=R)

        pass

