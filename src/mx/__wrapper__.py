""" __wrapper__.py -- For testing mx without mdb or other driving external interface """

# Our purpose here is to ensure that the mx works as if it were being driven by the mdb (model debugger) package
# This supports factoring out mdb functionality (stepping, running scenarios, etc) from the mx

# This driver is similar to __main__.py but without taking arguments from the command line
# We'll just specify the argument values directly in this module

# Once we're happy with the refactoring, we'll just drive the mx directly from the mdb without using this test wrapper

# System
import logging
import logging.config
from pathlib import Path
import atexit
from collections import namedtuple
from enum import Enum

# Model Integration
from pyral.database import Database

# MX
import mx.log_table_config
from mx.system import System
from mx import version
from mx.mdb_types import *
from mx.mxtypes import *
from mx.db_names import mmdb, PROGRAM_NAME
from mx.utility import print_classes

_logpath = Path("mx.log")

def clean_up():
    """Normal and exception exit activities"""
    _logpath.unlink(missing_ok=True)

def get_logger():
    """Initiate the logger"""
    log_conf_path = Path(__file__).parent / 'log.conf'  # Logging configuration is in this file
    logging.config.fileConfig(fname=log_conf_path, disable_existing_loggers=False)
    return logging.getLogger(__name__)  # Create a logger for this module

def main():
    # Start logging
    logger = get_logger()


    print('---')
    print(f'{PROGRAM_NAME} version: {version}')
    print('---')
    # logger.info(f'{_progname} version: {version}')

    # Here is the path to the mmdb populated with the elevator domain models
    # Normally this is provided by the mdb
    system_path = Path("/Users/starr/SDEV/Python/PyCharm/ModelExecution/src/mx/systems/elevator")

    # Now we can try loading the system
    s = System()  # Create the singleton instance
    s.initialize(system_path=system_path, verbose=False, debug=True)

    # Try printing it out
    print_classes(db=mmdb, class_names=['Class', 'Attribute'], output_file='class.txt')

    s.load_domains(playground='one_bank_one_shaft')

    print_classes(db='EVMAN', class_names=['Cabin', 'Door'], output_file='evman_cabin_door.txt')


# Begin hard coded scenario
    actors = {
        'EVMAN:ASLEV<S1-3>': InstanceAddress(
            domain='EVMAN', class_name='Accessible Shaft Level',
            instance_id={'Shaft': 'S1', 'Floor': '3'}
        ),
        'UI': ExternalAddress(domain='UI'),
        'EVMAN:XFER<S1>': InstanceAddress(domain='EVMAN', class_name='Transfer',
                                          instance_id={'Shaft': 'S1'}),
    }

    interactions = [
        Interaction(
            direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Stop request',
            source=actors['UI'], target=actors['EVMAN:ASLEV<S1-3>'], parameters=None
        ),
        Interaction(
            direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Set destination',
            source=actors['EVMAN:XFER<S1>'], target=actors['UI'], parameters=None
        ),

    ]

    logger.info(f"Beginning scenario: {s.playground.name}")

    system_responses = s.inject(stimulus=interactions[0], responses=[interactions[1]])

    np = "\n***\nNo problemo"
    logger.info(f"Beginning scenario: {s.playground.name}")

    logger.info(np)
    print(np)  # Comment this line out before release

if __name__ == "__main__":
    main()
