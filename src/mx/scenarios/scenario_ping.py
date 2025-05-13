""" scenario_ping.py -- Calls the ping method """

# This file will be generated from a scenario script, but its handcoded for now

# System
import logging
from typing import NamedTuple, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from mx.xe import XE

# MX
from mx.dispatched_event import DispatchedEvent
from mx.method import Method
from mx.domain import Domain
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
                                      class_name='Cabin', params={'dir': 'up'},
                                      instance={'Shaft': 'S1'})
                  ),
]
class Scenario:

    def __init__(self, xe: "XE"):
        self.xe = xe
        pass

    def run(self):
        """

        :return:
        """
        for i in s:
            if i.delay:
                _logger.info(f"Processing: {i.delay} sec...")
                time.sleep(i.delay)
            if isinstance(i.action, MXCallMethod):
                m = Method(xe=self.xe, name=i.action.method, class_name=i.action.class_name,
                           domain_name=self.xe.system.domains[i.dest].name, domain_alias=i.dest,
                           instance_id=i.action.instance, parameters=i.action.params)
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
