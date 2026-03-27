""" system.py -- Represents the user's entire system """

# System
import logging
from typing import TYPE_CHECKING, Optional
from pathlib import Path
from contextlib import redirect_stdout

# Model Integration
from pyral.database import Database
from pyral.relation import Relation
from pyral.relvar import Relvar

# MX
from mx.interaction_event import InteractionEvent
from mx.domain import Domain
from mx.db_names import mmdb
from mx.exceptions import *
from mx.mdb_types import *
from mx.mxtypes import ExternalAddress
from mx_logger import MXLogger

_logger = logging.getLogger(__name__)

DEFAULT_MODEL_OUTPUT_NAME = "model_out.txt"


class System:
    """
    This class represents the complete executing system
    It follows the singleton pattern to ensure only one System exists.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(System, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Avoid reinitialization if already initialized
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.path = None  # Path to the top level of all system specific files
        self.mmdb_path = None  # Path to the populated metamodel database
        self.domains: dict[str, Domain] = {}  # All modeled domains in the system
        self.name = None  # Name of the system, extracted from the populated metamodel
        self.debug = False
        self.verbose = False
        self.playground = None  # This is a set of populated domain dbs and compatible scenarios
        self.response_monitor = None
        self.mxlogger = MXLogger()

    def initialize(self, system_path: Path, verbose: bool, debug: bool):
        """
        Load the system from a populated metamodel database.
        The end result is a System with one or more modeled domains, each unpopulated

        Args:
            system_path:  Path to the system
            verbose:  If true, we may log to the console
            debug: If true, we do some diagnostic activity
        """
        _logger.info("---")
        _logger.info(f"System Initialization from path [{system_path}]")
        self.path = system_path
        self.set_mmdb_path()  # Sets self.mmdb_path

        # Load a metamodel file populated with the system as one or more modeled domains
        _logger.info(f"Loading the metamodel database from: [{self.mmdb_path.name}]")
        Database.open_session(name=mmdb)
        Database.load(db=mmdb, fname=str(self.mmdb_path))

        # Get the System name from the populated metamodel
        system_i = Relation.restrict(db=mmdb, relation='System')
        if not system_i.body:
            msg = f"System name not found in the user db"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        self.name = system_i.body[0]['Name']
        _logger.info(f"System [{self.name}] located from populated metamodel")

    def load_domains(self, playground: str):
        """
        Load each populated domain database in the selected playground

        Args:
            playground: Name of the selected playground
        """
        # Set path to the selected playground
        self.playground = self.path / 'playgrounds' / playground
        _logger.info(f"Loading modeled domains from playground: [{playground}]")

        Relation.restrict(db=mmdb, relation='Modeled Domain')
        domain_i = Relation.semijoin(db=mmdb, rname2='Domain')
        if not domain_i.body:
            msg = f"No domains defined for system in metamodel"
            _logger.exception(msg)
            raise MXUserDBException(msg)

        # Initialize modeled domains only
        self.domains = {d['Alias']: Domain(name=d['Name'], alias=d['Alias'], system=self) for d in domain_i.body}
        _logger.info("All modeled domains loaded")
        _logger.info("===")
        _logger.info("")
        pass


    def go(self):
        work_remaining = True  # Assume there is work to be done
        while work_remaining:
            for d in self.domains.values():
                _logger.info(f"Executing domain: {d.alias}")
                work_remaining = d.go()  # We'll stay in the loop as long as at least one domain reports true

    def set_mmdb_path(self):

        model_path = self.path / 'models'
        ral_files = list(model_path.glob("*.ral"))
        #
        if len(ral_files) == 0:
            print(f"Error: No .ral file found in '{self.path}'")
            return None
        elif len(ral_files) > 1:
            print(f"Error: Multiple .ral files found in '{self.path}': {[f.name for f in ral_files]}")
            return None

        self.mmdb_path = model_path / ral_files[0]

    def set_response_monitors(self, responses):
        """
        Flag any action associated with a response to be monitored so that when and if that action fires,
        it checks to see if its data matches an expected response.

        Args:
            responses: Any number of responses that should be monitored
        """
        self.response_monitor = responses
        for r in responses:
            match r.action:
                case ActionType.EXTERNAL_EVENT:
                    from mx.actions.signal import Signal
                    Signal.monitor_external = True
                    _logger.info(f"Setting MDB external event monitor")
                case ActionType.SIGNAL_INSTANCE:
                    from mx.actions.signal import Signal
                    Signal.monitor_internal = True
                    _logger.info(f"Setting MDB internal signal monitor")

    def inject(self, stimulus: Interaction, responses: list[Interaction]) -> Interaction:
        """
        Inject the supplied stimulus and set a monitor for each expected response, if any

        Args:
            stimulus:
            responses:

        Returns:
            Interaction:
        """
        # Save expected responses to be detected
        self.set_response_monitors(responses)

        # process the stimulus
        match stimulus.action:
            case ActionType.EXTERNAL_EVENT:
                pass
            case ActionType.SIGNAL_INSTANCE:
                self.process_signal_instance(stimulus)
            case _:
                pass

        # Now resume the system
        _logger.info("Transferring control from scenario to system")
        _logger.info("MDB --> SYS")
        _logger.info("---")
        suspend_status = self.go()
        # the suspend status tells us why the system stopped
        # monitor tripped, terminal condition
        # If monitor tripped, report the detected interaction and exit



        pass

    def process_signal_instance(self, s: Interaction):
        _logger.info(f"Injecting signal: {s.name}")
        if isinstance(s.source, ExternalAddress):
            _logger.info(f"{s.source.domain} >|| {s.target.domain} : {s.name} -> {s.target.class_name} <{s.target.instance_id}>")
        else:
            pass
        target_domain = self.domains[s.target.domain]
        params = s.parameters if s.parameters else {}
        ie = InteractionEvent.to_lifecycle(event_spec=s.name, source=s.source,
                                           to_instance=s.target.instance_id, to_class=s.target.class_name,
                                           params=s.parameters, domain=target_domain)
