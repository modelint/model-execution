"""
exceptions.py – Model Execution exceptions
"""

class MXException(Exception):
    """ Top level Model Execution exception """
    pass

class MXScenarioException(MXException):
    """ Error in scenario specification """
    pass

class MXInitialInstanceReferenceException(MXScenarioException):
    """ Error processing initial instance reference in scenario specification """
    pass

class MXScalarException(MXScenarioException):
    """ Error processing initial instance user type in scenario specification """
    pass
