""" usertypes.py -- Stub for user and system type operations """

# Eventually we will import a type system package that will provide
# both system and user types and operators. But with the focus on MX
# and the model debugger, this will do for now.  Just add any
# and type operation implementations here.

# System
from enum import Enum

# Here we define what C.J. Date calls type selector operations
# for each base type supported by our MX
selectors = { 'Boolean': { 'TRUE': True, 'FALSE': False} }
""" Type selector operations defined for each Scalar type """

# And these are implementations of type operations
def mx_set() -> bool:
    return True

def mx_unset() -> bool:
    return False


# Here we map the name of each type operation to a corresponding impementation
type_ops = {'Boolean': {'set': mx_set, 'unset': mx_unset}, }
