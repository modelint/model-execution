"""
exceptions.py – Model Execution exceptions
"""

class MXException(Exception):
    """ Top level Model Execution exception """
    pass

class MXUserDBException(MXException):
    """ Errors accessing data in the User DB """

class MXScenarioException(MXException):
    """ Error in starting_context specification """
    pass

class MXStateMachineException(MXException):
    """ Error while executing state machine"""
    pass

class MXInitialInstanceReferenceException(MXScenarioException):
    """ Error processing initial instance reference in starting_context specification """
    pass

class MXScalarException(MXScenarioException):
    """ Error processing initial instance user type in starting_context specification """
    pass

class MXNoEventResponseException(MXStateMachineException):
    """ Metamodel does not specify any kind of response for an specific event received in a givent state """
    pass

class MXUserDBMissingData(MXUserDBException):
    """ Errors finding specific data in the User DB """
