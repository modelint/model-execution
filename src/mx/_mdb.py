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
import time

# Model Integration
from pyral.database import Database

# MX
from mx.system import System
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
        self.s = None

    def initialize(self, sys_path: Path, verbose: bool):
        self.sys_path = sys_path
        self.verbose = verbose
        # Now we can try loading the system
        self.s = System()  # Create the singleton instance
        self.s.initialize(system_path=sys_path, verbose=verbose)

        # Try printing it out
        print_classes(db=mmdb, class_names=['Class', 'Attribute'], output_file='class.txt')

        self.s.load_domains(playground='one_bank_one_shaft')

        print_classes(db='EVMAN', class_names=['Cabin', 'Door'], output_file='evman_cabin_door.txt')


        # Begin hard coded scenario
        actors = {
            'EVMAN:ASLEV<S1-3>': InternalAddress(
                domain_name='Elevator Management',
                domain_alias='EVMAN',
                sm_name='Accessible Shaft Level', sm_alias='ASLEV',
                sm_type='lifecycle',
                instance_id={'Shaft': 'S1', 'Floor': '3'}
            ),
            'UI': ExternalAddress(domain='UI'),
            'EVMAN:R53 / Shaft': InternalAddress(
                domain_name='Elevator Management',
                domain_alias='EVMAN',
                sm_name='R53', sm_alias=None,
                sm_type='ma',
                instance_id={'ID': 'S1'}
            ),
            'EVMAN:XFER<S1>': InternalAddress(domain_name='Elevator Management',
                                              domain_alias='EVMAN',
                                              sm_name='Transfer', sm_alias='XFER',
                                              sm_type='lifecycle',
                                              instance_id={'Shaft': 'S1'}),
            'EVMAN:Cabin<S1>': InternalAddress(domain_name='Elevator Management',
                                               domain_alias='EVMAN',
                                               sm_name='Cabin', sm_alias=None,
                                               sm_type='lifecycle',
                                               instance_id={'Shaft': 'S1'}),
            'TRANS': ExternalAddress(domain='TRANS'),
            'SIO': ExternalAddress(domain='SIO'),
            'EVMAN:Door<S1>': InternalAddress(domain_name='Elevator Management',
                                              domain_alias='EVMAN',
                                              sm_name='Door',
                                              sm_alias=None,
                                              sm_type='lifecycle',
                                              instance_id={'Shaft': 'S1'}),
        }

        stimuli = [
            # Send the initial stop request to ASLEV S1-3
            Interaction(
                description="",
                delay=0,
                direction=Direction.STIMULUS,
                action=ActionType.SIGNAL_INSTANCE,
                name='Stop request',
                source=actors['UI'], source_actor='UI',
                target=actors['EVMAN:ASLEV<S1-3>'], target_actor='EVMAN:ASLEV<S1-3>',
                parameters=None
            ),

            # Passing floors TRANS reports passing floor, UI notified
            # Floor 1
            Interaction(
                description="",
                delay=3,
                direction=Direction.STIMULUS,
                action=ActionType.SIGNAL_INSTANCE,
                name='Passing floor',
                source=actors['TRANS'], source_actor='TRANS',
                target=actors['EVMAN:Cabin<S1>'], target_actor='EVMAN:Cabin<S1>',
                parameters={'floor': '1'}
            ),
            # Floor 2
            Interaction(
                description="",
                delay=2,
                direction=Direction.STIMULUS,
                action=ActionType.SIGNAL_INSTANCE,
                name='Passing floor',
                source=actors['TRANS'], source_actor='TRANS',
                target=actors['EVMAN:Cabin<S1>'], target_actor='EVMAN:Cabin<S1>',
                parameters={'floor': '2'}
            ),
            # Floor 3 (destination)
            Interaction(
                description="",
                delay=2,
                direction=Direction.STIMULUS,
                action=ActionType.SIGNAL_INSTANCE,
                name='Passing floor',
                source=actors['TRANS'], source_actor='TRANS',
                target=actors['EVMAN:Cabin<S1>'], target_actor='EVMAN:Cabin<S1>',
                parameters={'floor': '3'}
            ),

            # TRANS notifies Cabin that it has arrived
            Interaction(
                description="",
                delay=3,
                direction=Direction.STIMULUS,
                action=ActionType.SIGNAL_INSTANCE,
                name='Arrived at floor',
                source=actors['TRANS'], source_actor='TRANS',
                target=actors['EVMAN:Cabin<S1>'], target_actor='EVMAN:Cabin<S1>',
                parameters=None
            ),

            # SIO notifies Door that it has opened
            Interaction(
                description="",
                delay=1,
                direction=Direction.STIMULUS,
                action=ActionType.SIGNAL_INSTANCE,
                name='Door opened',
                source=actors['SIO'], source_actor='SIO',
                target=actors['EVMAN:Door<S1>'], target_actor='EVMAN:Door<S1>',
                parameters=None
            ),
        ]


        _logger.info(f"Beginning scenario: {self.s.playground.name}")
        pass

        for stim in stimuli:
            if stim.delay:
                time.sleep(stim.delay)
            self.s.inject(stimulus=stim)  # 1 Stop request -> ASLEV
            self.run_thru_announcements()

        # Set monitored response (all choices default to true for now)

        # pe = self.s.domains['EVMAN'].get_pending_events()

    def run_thru_announcements(self):
        while self.s.announcements:
            self.format_announcements(announcement_tuples=self.s.announcements)
            self.s.go()

    def format_interaction(self, i: Interaction):
        print()
        if i.action == ActionType.SIGNAL_INSTANCE:
            inst_str = '<' + '-'.join([str(v) for v in i.target.instance_id.values()]) + '>'
            formatted_i = f"{i.source.domain} >|| {i.target.domain} : {i.name} -> {i.target.sm_alias} {inst_str}"
        else:
            formatted_i = "Unimplemented Action Type"
        print(f"{formatted_i}")

    def format_sm_addr(self, sm_addr: InternalAddress ) -> str:
        inst_str = '<' + '-'.join([str(v) for v in sm_addr.instance_id.values()]) + '>'
        return f"{sm_addr.sm_alias} {inst_str}"

    def format_inst_id(self, i: dict[str, Any]) -> str:
        return '<' + '-'.join([str(v) for v in i.values()]) + '>'

    def format_announcements(self, announcement_tuples: list[Announcement]):
        for a in announcement_tuples:
            match type(a).__name__:
                case 'mx_ExternalEvent_Announcement':
                    if a.source.instance_id:
                        inst_str = '<' + '-'.join([str(v) for v in a.source.instance_id.values()]) + '>'
                    else:
                        inst_str = ""
                    pstrings = [f"{n}={v[0]}" for n,v in a.params.items()]
                    param_str = ', '.join(pstrings)
                    p_paren = '()' if not param_str else f"( {param_str} )"
                    implicit = '*' if a.implicit else ''
                    formatted_a = f"{a.domain} >|| {a.ee} : {a.source.sm_alias}{inst_str} {a.event}{p_paren}{implicit}"
                    print(f"    {formatted_a}")
                    self.announcements.append(formatted_a)
                case 'mx_InteractionSignal_Announcement':
                    if isinstance(a.source, ExternalAddress):
                        formatted_a = f"{a.source.domain} >|| {a.dest.domain_alias} : {a.event} -> "
                        formatted_a = formatted_a + self.format_sm_addr(a.dest)
                        print(f"    {formatted_a}")
                    else:
                        formatted_a = f"{a.source.domain_alias} >|| {a.event} -> "
                        formatted_a = formatted_a + self.format_sm_addr(a.dest)
                        print(f"    {formatted_a}")
                case 'mx_StateEntry_Announcement':
                    formatted_a = f"{a.sm} {self.format_inst_id(a.inst)} >[{a.state}]"
                    print(f"        {formatted_a}")
                case _:
                    pass
