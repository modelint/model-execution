"""
Blueprint MX Model Execution

"""
# System
import logging
import logging.config
import sys
import argparse
from pathlib import Path
import atexit

# MX
from mx import version
from mx.db_names import PROGRAM_NAME
from mx._mdb import MDB

_logpath = Path("mx.log")

def clean_up():
    """Normal and exception exit activities"""
    _logpath.unlink(missing_ok=True)

def get_logger():
    """Initiate the logger"""
    log_conf_path = Path(__file__).parent / 'log.conf'  # Logging configuration is in this file
    logging.config.fileConfig(fname=log_conf_path, disable_existing_loggers=False)
    return logging.getLogger(__name__)  # Create a logger for this module


# Configure the expected parameters and actions for the argparse module
def parse(cl_input):
    parser = argparse.ArgumentParser(description=PROGRAM_NAME)
    parser.add_argument('-s', '--system', action='store',
                        help='Path to the system directory')
    parser.add_argument('-L', '--log', action='store_true',
                        help='Generate a diagnostic log file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose messages')
    parser.add_argument('-V', '--version', action='store_true',
                        help='Print the current version of the model execution app')
    return parser.parse_args(cl_input)


def main():
    # Start logging
    logger = get_logger()
    print('---')
    logger.info(f'{PROGRAM_NAME} version: {version}')
    print('---')

    # Parse the command line args
    args = parse(sys.argv[1:])

    if args.version:
        # Just print the version and quit
        print(f'{PROGRAM_NAME} version: {version}')
        sys.exit(0)

    if not args.log:
        # If no log file is requested, remove the log file before termination
        atexit.register(clean_up)

    # Domain specified
    if args.system:
        mdb = MDB()  # Create the singleton instance
        spath = Path(args.system)
        mdb.initialize(sys_path=spath, verbose=args.verbose)

    print("\nNo problemo")  # Comment this line out before release
    logger.info("No problemo")  # We didn't die on an exception, basically
    if args.verbose:
        print("\nNo problemo")


if __name__ == "__main__":
    main()
