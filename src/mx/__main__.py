"""
Blueprint Model Execution

"""
# System
import logging
import logging.config
import sys
import argparse
from pathlib import Path

# MX
from mx.xe import XE
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
    parser.add_argument('-s', '--system', action='store',
                        help='Name of the populated metamodel database text file *.ral produced by xuml-populate')
    parser.add_argument('-c', '--context', action='store',
                        help='Name of the starting_context *.sip file to load')
    parser.add_argument('-x', '--scenario', action='store',
                        help='Name of the scenario *.scn file to run')
    parser.add_argument('-td', '--types_dir', action='store', help='A directory of yaml files mapping '
                                                                  'user model types to system db_types. It should '
                                                                  'contain one yaml file per domain, with each name '
                                                                  'matching the domain name using underscores instead '
                                                                  'of spaces in the name.')
    parser.add_argument('-D', '--debug', action='store_true',
                        help='Debug mode'),
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
    if args.system:
        XE.initialize(populated_mmdb_filename=args.system, types_dir=Path(args.types_dir),
                      sip_file=Path(args.context), scenario_file=Path(args.scenario), debug=args.debug)

    logger.info("No problemo")  # We didn't die on an exception, basically
    print("\nNo problemo")


if __name__ == "__main__":
    main()
