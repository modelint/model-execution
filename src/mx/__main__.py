"""
Blueprint Model Execution

"""
# System
import logging
import logging.config
import sys
import argparse
from pathlib import Path
import atexit

# MX
from mx.xe import XE
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


# Configure the expected parameters and actions for the argparse module
def parse(cl_input):
    parser = argparse.ArgumentParser(description=_progname)
    parser.add_argument('-s', '--system', action='store',
                        help='Name of the metamodel TclRAL database *.ral file populated with one or more domains')
    parser.add_argument('-c', '--context', action='store',
                        help='Name of the context directory specifying the initialized domain dbs and a *.sip file')
    parser.add_argument('-x', '--scenario', action='store',
                        help='Name of the scenario *.yaml file to run against the populated system')
    parser.add_argument('-D', '--debug', action='store_true',
                        help='Debug mode'),
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
    logger.info(f'{_progname} version: {version}')

    # Parse the command line args
    args = parse(sys.argv[1:])

    if args.version:
        # Just print the version and quit
        print(f'{_progname} version: {version}')
        sys.exit(0)

    if not args.log:
        # If no log file is requested, remove the log file before termination
        atexit.register(clean_up)

    # Domain specified
    if args.system:
        xe = XE()  # Create the singleton instance
        xe.initialize(mmdb_path=Path(args.system), context_dir=Path(args.context),
                      scenario_path=Path(args.scenario), verbose=args.verbose, debug=args.debug)

    print("\nNo problemo")  # Comment this line out before release
    logger.info("No problemo")  # We didn't die on an exception, basically
    if args.verbose or args.debug:
        print("\nNo problemo")


if __name__ == "__main__":
    main()
