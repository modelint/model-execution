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
import sys
import atexit

# MX
from mx.system import System
from mx import version

_logpath = Path("mx.log")
_progname = 'Blueprint Model Execution'

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
    logger.info(f'{_progname} version: {version}')

    # Here is the path to the mmdb populated with the elevator domain models
    # Normally this is provided by the mdb
    system_path = Path("/Users/starr/SDEV/Python/PyCharm/ModelExecution/src/mx/systems/elevator")

    # Now we can try loading the system
    the_System = System()  # Create the singleton instance
    the_System.initialize(system_path=system_path, verbose=False, debug=True)

    # Try printing it out
    the_System.print_models(class_names=['Class', 'Attribute'], output_file='class.txt')

    the_System.load_domains(playground='one_bank_one_shaft')
    print("\nNo problemo")  # Comment this line out before release


if __name__ == "__main__":
    main()
