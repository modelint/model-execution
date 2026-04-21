""" _mdb.py -- Standin for Model Debugger (mdb) module """

# Our purpose here is to ensure that the mx works as if it were being driven by the mdb (model debugger) package
# This supports factoring out mdb functionality (stepping, running scenarios, etc) from the mx

# This driver is similar to __main__.py but without taking arguments from the command line
# We'll just specify the argument values directly in this module

# Once we're happy with the refactoring, we'll just drive the mx directly from the mdb without using this test wrapper

# System
import logging
from pathlib import Path
from collections import namedtuple
from enum import Enum

# Model Integration
from pyral.database import Database

# MX
from mx.system import System
from mx.mdb_types import *
from mx.mxtypes import *
from mx.db_names import mmdb
from mx.utility import print_classes

_logger = logging.getLogger(__name__)

class MDB:
    """
    Stand in for the Model Debugger to make it easier to complete development of the MX and MDB modules.
    Goal is to run a scenario manually and make sure control is properly transfered back and forth between
    MX and MDB.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MDB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Avoid reinitialization if already initialized
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.verbose = True
        self.sys_path = None
        self.announcements = None

    def initialize(self, sys_path: Path, verbose: bool):
        self.sys_path = sys_path
        self.verbose = verbose
        # Now we can try loading the system
        s = System()  # Create the singleton instance
        s.initialize(system_path=sys_path, verbose=verbose)

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


        _logger.info(f"Beginning scenario: {s.playground.name}")

        # Set monitored response
        from mx.actions.ext_signal import ExtSignal
        ExtSignal.announce = True

        self.announcements = s.inject(stimulus=interactions[0])
        pass

    def format_announcemnts(self):
        # inst = self.ext_event_source.instance_id
        # if inst:
        #     inst_str = '<' + '-'.join([str(v) for v in inst.values()]) + '>'
        # else:
        #     inst_str = ""
        # pstrings = [f"{n}={v[0]}" for n,v in self.params.items()]
        # param_str = ', '.join(pstrings)
        # action_monitor_msg = f"{domain_name} >|| {self.ee_name} : {source}{inst_str} {self.ext_event_name}( {param_str} )"
        # # Forward report message to the enclosing Domain
        # self.activity_execution.domain.announcements.append(action_monitor_msg)
        pass