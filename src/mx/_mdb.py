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
            'SIO': ExternalAddress(domain='SIO'),
            'EVMAN:Door<S1>': InstanceAddress(domain='EVMAN', class_name='Door',
                                              instance_id={'Shaft': 'S1'}),
        }

        interactions = {
            # Send the initial stop request to ASLEV S1-3
            1: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Stop request',
                source=actors['UI'], target=actors['EVMAN:ASLEV<S1-3>'], parameters=None
            ),
            # UI updated with request
            2: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Set destination',
                source=actors['EVMAN:XFER<S1>'], target=actors['UI'], parameters=None
            ),

            # Cabin S1 requests transport from TRANS
            3: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Go to floor',
                source=actors['EVMAN:Cabin<S1>'], target=actors['TRANS'], parameters={'dest floor': '3'}
            ),

            # Passing floors TRANS reports passing floor, UI notified
            # Floor 1
            4: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Passing floor',
                source=actors['TRANS'], target=actors['EVMAN:Cabin<S1>'], parameters={'floor': '1'}
            ),
            5: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Passing floor',
                source=actors['EVMAN:Cabin<S1>'], target=actors['UI'], parameters={'floor': '1'}
            ),

            # Floor 2
            6: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Passing floor',
                source=actors['TRANS'], target=actors['EVMAN:Cabin<S1>'], parameters={'floor': '2'}
            ),
            7: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Passing floor',
                source=actors['EVMAN:Cabin<S1>'], target=actors['UI'], parameters={'floor': '2'}
            ),

            # Floor 3 (destination)
            8: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Passing floor',
                source=actors['TRANS'], target=actors['EVMAN:Cabin<S1>'], parameters={'floor': '3'}
            ),
            9: Interaction(
                direction=Direction.RESPONSE, action=ActionType.EXTERNAL_EVENT, name='Passing floor',
                source=actors['EVMAN:Cabin<S1>'], target=actors['UI'], parameters={'floor': '3'}
            ),

            # TRANS notifies Cabin that it has arrived
            10: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Arrived at floor',
                source=actors['TRANS'], target=actors['EVMAN:Cabin<S1>'], parameters=None
            ),

            # SIO notifies Door that it has opened
            11: Interaction(
                direction=Direction.STIMULUS, action=ActionType.SIGNAL_INSTANCE, name='Door opened',
                source=actors['SIO'], target=actors['EVMAN:Door<S1>'], parameters=None
            ),
        }


        _logger.info(f"Beginning scenario: {s.playground.name}")

        # Set monitored response
        from mx.actions.ext_signal import ExtSignal
        ExtSignal.announce = True

        # Send the initial stop request to ASLEV S1-3 and UI updated with request
        self.format_interaction(interactions[1])  # Stimulus from UI
        s.inject(stimulus=interactions[1])  # 1 Stop request -> ASLEV
        # MX

        self.format_announcements(announcement_tuples=s.announcements)  # 2 Set destination >|| UI
        s.go()
        # MX

        # Cabin S1 requests transport from TRANS
        self.format_announcements(announcement_tuples=s.announcements)  # 3 Go to floor >|| TRANS
        self.format_interaction(interactions[4])
        s.inject(stimulus=interactions[4])  # 4 Passing floor 1 TRANS -> Cabin
        # MX

        # Cabin reports passing floor 1
        self.format_announcements(announcement_tuples=s.announcements)  # 5 Passing floor 1 >|| UI
        self.format_interaction(interactions[6])
        s.inject(stimulus=interactions[6])  # 6 Passing floor 2 -> Cabin
        # MX

        # Cabin reports passing floor 2
        self.format_announcements(announcement_tuples=s.announcements)  # 5 Passing floor 2 >|| UI
        self.format_interaction(interactions[8])
        s.inject(stimulus=interactions[8])  # 8 Passing floor 3 -> Cabin
        # MX

        self.format_announcements(announcement_tuples=s.announcements)  # 5 Passing floor 3 >|| UI
        self.format_interaction(interactions[10])
        s.inject(stimulus=interactions[10])  # 10 TRANS Arrived at floor -> Cabin
        # MX

        self.format_announcements(announcement_tuples=s.announcements)  # 5 Passing floor 3 >|| UI
        self.format_interaction(interactions[11])  # 11 Door opening >|| SIO, UI (to trigger SIO to open the door)
        s.inject(stimulus=interactions[11])  # 11 SIO Door opened -> Door
        # Here we wait for the timer to go off
        # TODO: Implement Door state activies to get to Door OPEN state
        pass
        self.format_announcements(announcement_tuples=s.announcements)  # Door Opened >|| UI
        # Door has fully opened (note that timer will be pending)
        s.go()  # No more work to do / Scenario complete
        self.format_announcements(announcement_tuples=s.announcements)
        s.go()  # No more work to do / Scenario complete
        self.format_announcements(announcement_tuples=s.announcements)
        s.go()  # No more work to do / Scenario complete
        self.format_announcements(announcement_tuples=s.announcements)
        pass

    def format_interaction(self, i: Interaction):
        pass
        if i.action == ActionType.SIGNAL_INSTANCE:
            inst_str = '<' + '-'.join([str(v) for v in i.target.instance_id.values()]) + '>'
            formatted_i = f"{i.source.domain} >|| {i.target.domain} : {i.name} -> {i.target.class_name} {inst_str}"
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