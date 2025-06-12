""" instance.py -- Generate and manage instance id's for state machines """

from mx.mxtypes import NamedValues

def generate_key(id_attr_value: NamedValues) -> str:
    """
    Concatenate all id values with an underscore character
    :param id_attr_value:
    :return: The generated key
    """
    return '_'.join([str(v) for v in id_attr_value.values()])

