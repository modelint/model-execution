"""
Blueprint Model Execution

"""
import logging
import logging.config
import sys
import argparse
from pathlib import Path
from mx.schema import Schema
from mx import version

_logpath = Path("mx.log")
_progname = 'Blueprint Model Execution'


def get_logger():
    """Initiate the logger"""
    log_conf_path = Path(__file__).parent / 'log.conf'  # Logging configuration is in this file
    logging.config.fileConfig(fname=log_conf_path, disable_existing_loggers=False)
    return logging.getLogger(__name__)  # Create a logger for this module


# Configure the expected parameters and actions for the argparse module
def parse(cl_input):
    parser = argparse.ArgumentParser(description=_progname)
    parser.add_argument('-db', '--database', action='store',
                        help='Name of the populated metamodel database text file produced by xuml-populate')
    parser.add_argument('-dom', '--domain', action='store',
                        help='Name of the domain to build')
    parser.add_argument('-s', '--scenario', action='store',
                        help='Name of the scenario *.sip file to load')
    parser.add_argument('-types', action='store', help='This yaml file maps user model attribute types '
                                                       'to system types. No need to specify .yaml extension')
    # parser.add_argument('-D', '--debug', action='store_true',
    #                     help='Debug mode'),
    # parser.add_argument('-A', '--actions', action='store_true',
    #                     help='Parse actions'),
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

    # Domain specified
    if args.database:
        domain_schema = Schema(filename=args.database, domain=args.domain, types=Path(args.types), scenario=args.scenario)

    logger.info("No problemo")  # We didn't die on an exception, basically
    print("\nNo problemo")


if __name__ == "__main__":
    main()
