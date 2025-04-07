""" scenario_ping.py -- Calls the ping method """

# This file will be generate form a scenario script in the future
# but I'm handcoding this for now

# System
import logging
from typing import NamedTuple
import time

# MX
from mx.dispatched_event import DispatchedEvent
from mx.method import Method
from mx.bridge import *

_logger = logging.getLogger(__name__)


# Interaction
class MXInteraction(NamedTuple):
    source: str | None  # Source domain
    dest: str  # Destination domain
    delay: float  # Wait this long until triggering the interaction
    action: ModeledOperation | BridgeableCondition


s = [
    # We simply call the cabin ping method
    MXInteraction(source=None, dest='EVMAN', delay=0,
                  action=MXCallMethod(ee=None, source=None, method='Ping',
                                      class_name='Cabin', params={'dir': '.up'},
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
            if isinstance(i.action, MXCallMethod):
                pass
            if isinstance(i.action, MXSignalEvent):
                print("signal event")
                DispatchedEvent(signal=i.action)
                pass

            elif isinstance(i.action, MXLifecycleStateEntered):
                print("state entered")
            else:
                print("Unknown interaction type")
        pass
