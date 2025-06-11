""" initial_states.py -- Extract initial states for all lifecycles and assigners from scenario (.sip) file """

# System
from pathlib import Path
from collections import namedtuple
import logging
from typing import NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from sip_parser.parser import SIParser

# Model Execution
from mx.exceptions import *

MultipleAssignerInitialState = NamedTuple('MultipleAssignerInitialState', pclass=str, state=str)

_logger = logging.getLogger(__name__)

tcl_to_python = { 'string': str, 'boolean': bool, 'double': float, 'int': int }

pop_scenario = 'pop'  # Name of transaction that loads the schema

class InitialStateContext:

    def __init__(self, domain: "Domain"):
        """
        We see that there is an R1 ref.  We need to find the target attributes and class
        The metamodel gives us Shaft.Bank -> Bank.Name

        We proceed for each instance of Shaft taking the R1 ref (L, P, or F)
        And go find the Bank population
        We find the L instance
        Now we grab the Name value and add it to our Shaft table by adding a key.
        And, at this point, we are building the relation.create command
        When we get all the values, we commit and move on to the next instance

        :param domain:  The subject matter domain being populated
        """
        self.lifecycle_istates: dict[str, str] = {}
        self.ma_istates: dict[str, MultipleAssignerInitialState] = {}

        context_dir = domain.system.xe.context_dir
        sip_files = list(context_dir.glob("*.sip"))

        if len(sip_files) == 0:
            raise MXFileException(f"No .sip file found for domain [{self.domain.name}] in: {context_dir.resolve()}")
        if len(sip_files) > 1:
            raise RuntimeError("Multiple .sip files found in directory.")

        sip_file = sip_files[0]

        # Parse the starting_context's initial population file (*.sip file)
        _logger.info(f"Parsing sip: [{sip_file}]")
        parse_result = SIParser.parse_file(file_input=sip_file, debug=False)
        self.name = parse_result.name  # Name of this starting_context
        self.pop = parse_result.classes  # Dictionary of initial instance populations keyed by class name
        self.relations = dict()  # The set of relations keyed by relvar name ready for insertion into the user db

        _logger.info(f"Sip parsed, loading initial instance population into user db")
        # Process each class (c) and its initial instance specification (i)
        for class_name, i_spec in self.pop.items():
            for irow in i_spec.population:
                # save any initial states for classes and multiple assigners
                # TODO: Support single assigners (after SIP support added)
                for s in irow['initial_state']:
                    if len(s) == 1:
                        # save initial state for this class
                        self.lifecycle_istates[class_name] = s[0]
                    if len(s) == 2:
                        # index by rnum and save partitioning class and initial state
                        self.ma_istates[s[0]] = MultipleAssignerInitialState(pclass=class_name, state=s[1])
        pass

