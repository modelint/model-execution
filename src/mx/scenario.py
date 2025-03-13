""" scenario.py -- Runs a scenario """

# System
import logging
from typing import NamedTuple, Dict, Any
import time

_logger = logging.getLogger(__name__)

# Bridge operations
MXEventToInstance = NamedTuple('MXEventToInstance', op=str | None, source=Dict[str, Any] | None, event_spec=str,
                               state_model=str, domain=str,
                               params=Dict[str, Any], instance=Dict[str, Any])

# Bridgeable conditions
MXLifecycleStateEntered = NamedTuple('MXStateEntered', instance=Dict[str, Any], state=str, state_model=str, domain=str)

# Interaction
MXInteraction = NamedTuple('MXInteraction', source=str, dest=str, delay=float,
                           action=MXEventToInstance | MXLifecycleStateEntered)

s = [
    # UI requests floor going up
    MXInteraction(source='UI', dest='EVMAN', delay=0,
                  action=MXEventToInstance(op='BLEV', source=None, event_spec='Floor request',
                                           state_model='Bank Level', domain='EVMAN',
                                           params={'dir': '.up'},
                                           instance={'Bank': 'Lower Floors', 'Floor': 'L'})
                  ),
    # Cabin starts opening door
    MXInteraction(source='EVMAN', dest='TRANS', delay=0,
                  action=MXLifecycleStateEntered(instance={'Shaft': 'S1'}, state='OPENING',
                                                 state_model='Door', domain='EVMAN')
                  ),
    # Trans reports door opened
    MXInteraction(source='TRANS', dest='EVMAN', delay=2.0,
                  action=MXEventToInstance(op='DOOR', source=None, event_spec='Door opened',
                                           state_model='Door', domain='EVMAN',
                                           params={},
                                           instance={'Shaft': 'S1'})
                  ),
    # UI updates door status
    MXInteraction(source='EVMAN', dest='UI', delay=0,
                  action=MXLifecycleStateEntered(instance={'Shaft': 'S1'}, state='OPEN',
                                                 state_model='Door', domain='EVMAN')
                  ),
    # UI button press floor 3
    MXInteraction(source='UI', dest='EVMAN', delay=1.5,
                  action=MXEventToInstance(op='SLEV', source=None, event_spec='Stop request',
                                           state_model='Accessible Shaft Level', domain='EVMAN',
                                           params={},
                                           instance={'Floor': '3', 'Shaft': 'S1'})
                  ),
    # Cabin starts closing door
    MXInteraction(source='EVMAN', dest='TRANS', delay=0,
                  action=MXLifecycleStateEntered(instance={'Shaft': 'S1'}, state='CLOSING',
                                                 state_model='Door', domain='EVMAN')
                  ),
    # Trans reports door closed
    MXInteraction(source='TRANS', dest='EVMAN', delay=2.0,
                  action=MXEventToInstance(op='DOOR', source=None, event_spec='Door closed',
                                           state_model='Door', domain='EVMAN',
                                           params={},
                                           instance={'Shaft': 'S1'})
                  ),
    # UI updates door status
    MXInteraction(source='EVMAN', dest='UI', delay=0,
                  action=MXLifecycleStateEntered(instance={'Shaft': 'S1'}, state='CLOSED',
                                                 state_model='Door', domain='EVMAN')
                  ),
    # Cabin requests transit
    MXInteraction(source='EVMAN', dest='TRANS', delay=0,
                  action=MXLifecycleStateEntered(instance={'Shaft': 'S1'}, state='Requesting transport',
                                                 state_model='Cabin', domain='EVMAN')
                  ),
    # Tranport accepts request
    MXInteraction(source='TRANS', dest='EVMAN', delay=0.0,
                  action=MXEventToInstance(op='CABIN', source=None, event_spec='Transport in progress',
                                           state_model='Cabin', domain='EVMAN',
                                           params={},
                                           instance={'Shaft': 'S1'})
                  ),
    # Transport complete
    MXInteraction(source='TRANS', dest='EVMAN', delay=4.0,
                  action=MXEventToInstance(op='CABIN', source=None, event_spec='Arrived at floor',
                                           state_model='Cabin', domain='EVMAN',
                                           params={},
                                           instance={'Shaft': 'S1'})
                  ),
]


class Scenario:

    @classmethod
    def run(cls):
        for i in s:
            if i.delay:
                _logger.info(f"Processing: {i.delay} sec...")
                time.sleep(i.delay)
            if isinstance(i.action, MXEventToInstance):
                print("signal event")
            elif isinstance(i.action, MXLifecycleStateEntered):
                print("state entered")
            else:
                print("Unknown interaction type")
        pass
