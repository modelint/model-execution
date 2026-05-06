""" system.py -- Represents the user's entire system """

# System
import sys
import logging
from pathlib import Path
from contextlib import redirect_stdout

# Model Integration
from pyral.database import Database
from pyral.relation import Relation
from pyral.relvar import Relvar

# MX
from mx import version
from mx.interaction_event import InteractionEvent
from mx.domain import Domain
from mx.db_names import mmdb, PROGRAM_NAME
from mx.exceptions import *
from mx.mxtypes import *
from mx.actions.flow import ActiveFlow
# from mx.log_table_config import ConsoleTableFilter, ConsoleWarningFilter

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
        self.verbose = False
        # Model components such as actions will make announcements to if they are being monitored
        # These can be reviewed and processed by a monitoring process such as the model debugger
        self.announcements: list[Announcement] = []
        self.suspend = False  # When set to True, we will return control to the monitoring process
        self.time_override = False  # When set to True, the monitoring process will manage all delayed event timing
        self.playground = None

    @staticmethod
    def set_announce_triggers(triggers: list[str]):
        """
        An external service such as the model debugger can set a trigger on certain actions
        that will transfer control back to the service when the associated action type completes.
        For now, we only support setting it on external signals, but this is ripe for expansion to
        other action types and perhaps non-action behaviors.

        Args:
            triggers: A list of strings each defining a known trigger type named after an action type
        """
        # TODO: expand this to handle other trigger types
        for t in triggers:
            match t:
                case "external signal":
                    from mx.actions.ext_signal import ExtSignal
                    ExtSignal.announce = True
                case _:
                    pass

    def initialize(self, system_path: Path, verbose: bool):
        """
        Load the system from a populated metamodel database.
        The end result is a System with one or more modeled domains, each unpopulated

        Args:
            system_path:  Path to the system
            verbose:  If true, we may log to the console
        """
        # for handler in logging.getLogger().handlers:
        #     if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
        #         if handler.stream is sys.stdout:
        #             handler.addFilter(ConsoleTableFilter())
        #         elif handler.stream is sys.stderr:
        #             handler.addFilter(ConsoleWarningFilter())

        _logger.info(f'{PROGRAM_NAME} version: {version}')
        _logger.info("---")
        _logger.info(f"System Initialization from path [{system_path}]")
        self.path = system_path
        self.set_mmdb_path()  # Sets self.mmdb_path
        self.verbose = verbose

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
        if self.verbose:
            print(f"System [{self.name}] located from populated metamodel")

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
        """
        This is the main system run loop
        """
        work_remaining = True  # Assume there is work to be done
        self.announcements = []  # Clear any prior announcments
        self.suspend = False  # Reset the susupend status

        while work_remaining and not self.suspend:
            for d in self.domains.values():
                _logger.info(f"Executing domain: {d.alias}")
                _logger.info("---")
                work_remaining = d.go()  # We'll stay in the loop as long as at least one domain reports true
                if self.suspend:
                    return

    @property
    def playgrounds(self) -> list[str]:
        """
        Names of playground subdirectories, if any

        Returns:
            List of subdirectory names (possibly empty), or None if playground is unset.
        """
        return [d.name for d in (self.path / 'playgrounds').iterdir() if d.is_dir()]

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

    def set_announcements(self, responses):
        """
        Flag any action associated with a response to be monitored so that when and if that action fires,
        it checks to see if its data matches an expected response.

        Args:
            responses: Any number of responses that should be monitored
        """
        self.announcements = responses
        for r in responses:
            match r.action:
                case ActionType.EXTERNAL_EVENT:
                    from mx.actions.ext_signal import ExtSignal
                    ExtSignal.announce = True
                    _logger.info(f"Setting MDB external event monitor")
                # case ActionType.SIGNAL_INSTANCE:
                #     from mx.actions.signal import Signal
                #     Signal.monitor_internal = True
                #     _logger.info(f"Setting MDB internal signal monitor")

    def inject(self, stimulus: Interaction):
        """
        Inject the supplied stimulus and set a monitor for each expected response, if any

        Args:
            stimulus:
        """
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
        self.go()
        pass
        # the suspend status tells us why the system stopped
        # monitor tripped, terminal condition
        # If monitor tripped, report the detected interaction and exit

    def process_signal_instance(self, s: Interaction):
        _logger.info(f"Injecting signal: {s.name}")
        if isinstance(s.source, ExternalAddress):
            _logger.info(f"{s.source.domain} >|| {s.target.domain} : {s.name} -> {s.target.class_name} <{s.target.instance_id}>")
        else:
            pass
        target_domain = self.domains[s.target.domain]
        params = s.parameters if s.parameters is not None else {}
        pflows = {}
        if params:
            event_spec_name = s.name
            domain_alias = s.target.domain
            domain_name = self.domains[domain_alias].name
            class_name = s.target.class_name
            R = f"Name:<{event_spec_name}>, State_model:<{class_name}>, Domain:<{domain_name}>"
            Relation.restrict(db=mmdb, relation='Event Specification', restriction=R)
            sig_param_r = Relation.semijoin(db=mmdb, rname2='Parameter', attrs={'State_signature': 'Signature', 'Domain': 'Domain'})
            ptypes = {t['Name'] : t['Type'] for t in sig_param_r.body}
            # Get the signature and ptypes
            pflows = {}
            for name, value in params.items():
                # Get the type and determine whether or not it is a scalar
                ptype = ptypes[name]
                R = f"Name:<{ptype}>, Domain:<{domain_name}>"
                scalar_r = Relation.restrict(db=mmdb, relation='Scalar', restriction=R)
                if scalar_r.body:
                    pflows[name] = ActiveFlow(value=value, flowtype='scalar', scalar=ptype)
                else:
                    pflows[name] = ActiveFlow(value=value, flowtype='ptype', scalar=None)
        ie = InteractionEvent.to_lifecycle(event_spec=s.name, source=s.source,
                                           to_instance=s.target.instance_id, to_class=s.target.class_name,
                                           params=pflows, domain=target_domain)

def get() -> System:
    if System._instance is None:
        raise RuntimeError("System has not been initialized")
    return System._instance

