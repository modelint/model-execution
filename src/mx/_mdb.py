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
        self.announcements: list[str] = []

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
            'EVMAN:Cabin<S1>': InstanceAddress(domain='EVMAN', class_name='Cabin',
                                               instance_id={'Shaft': 'S1'}),
            'TRANS': ExternalAddress(domain='TRANS'),
        }

        interactions = {
            1: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Stop request',
                source=actors['UI'], target=actors['EVMAN:ASLEV<S1-3>'], parameters=None
            ),
            2: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Set destination',
                source=actors['EVMAN:XFER<S1>'], target=actors['UI'], parameters=None
            ),
            3: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Go to floor',
                source=actors['EVMAN:Cabin<S1>'], target=actors['TRANS'], parameters={'dest floor': 3}
            ),
            # Passing floors
            4: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Passing floor',
                source=actors['TRANS'], target=actors['EVMAN:Cabin<S1>'], parameters={'floor': 1}
            ),
            5: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Passing floor',
                source=actors['EVMAN:Cabin<S1>'], target=actors['UI'], parameters={'floor': 1}
            ),
            6: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Passing floor',
                source=actors['TRANS'], target=actors['EVMAN:Cabin<S1>'], parameters={'floor': 2}
            ),
            7: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Passing floor',
                source=actors['EVMAN:Cabin<S1>'], target=actors['UI'], parameters={'floor': 2}
            ),
            8: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Passing floor',
                source=actors['TRANS'], target=actors['EVMAN:Cabin<S1>'], parameters={'floor': 3}
            ),
            9: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Passing floor',
                source=actors['EVMAN:Cabin<S1>'], target=actors['UI'], parameters={'floor': 3}
            ),
            10: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Arrived at floor',
                source=actors['TRANS'], target=actors['EVMAN:Cabin<S1>'], parameters=None
            ),

        }


        _logger.info(f"Beginning scenario: {s.playground.name}")

        # Set monitored response
        from mx.actions.ext_signal import ExtSignal
        ExtSignal.announce = True

        self.format_interaction(interactions[1])
        s.inject(stimulus=interactions[1])  # 1 Stop request -> ASLEV
        self.format_announcements(announcement_tuples=s.announcements)  # 2 Set destination >|| UI
        s.go()
        self.format_announcements(announcement_tuples=s.announcements)  # 3 Go to floor >|| TRANS
        self.format_interaction(interactions[4])
        s.inject(stimulus=interactions[4])  # 4 Passing floor 1 -> Cabin
        self.format_announcements(announcement_tuples=s.announcements)  # 5 Passing floor 1 >|| UI
        pass

    def format_interaction(self, i: Interaction):
        pass
        if i.action == ActionType.SIGNAL_INSTANCE:
            inst_str = '<' + '-'.join([str(v) for v in i.target.instance_id.values()]) + '>'
            formatted_i = f"{i.source.domain} >|| {i.target.domain} : {i.name} -> {i.target.class_name} <{inst_str}>"
        else:
            formatted_i = "Unimplemented Acton Type"
        print(formatted_i)

    def format_announcements(self, announcement_tuples: list[Announcement]):
        for a in announcement_tuples:
            if isinstance(a, ExternalEvent_Announcement):
                if a.inst:
                    inst_str = '<' + '-'.join([str(v) for v in a.inst.values()]) + '>'
                else:
                    inst_str = ""
                pstrings = [f"{n}={v[0]}" for n,v in a.params.items()]
                param_str = ', '.join(pstrings)
                formatted_a = f"{a.domain} >|| {a.ee} : {a.source}{inst_str} {a.event}( {param_str} )"
                print(formatted_a)
                self.announcements.append(formatted_a)