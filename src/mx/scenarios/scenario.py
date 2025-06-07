""" scenario_ping.py -- Calls the ping method """

# This file will be generated from a scenario script, but its handcoded for now

# System
import logging
from typing import TYPE_CHECKING
import time

if TYPE_CHECKING:
    from mx.xe import XE

# MX
from mx.dispatched_event import DispatchedEvent
from mx.method import Method

_logger = logging.getLogger(__name__)

class Scenario:

    def __init__(self, xe: "XE"):
        self.xe = xe
        pass

    def run(self):
        """

        :return:
        """
        for i in self.xe.scenario['interactions']:
            # Is the interaction a stimulus or an inspection?  The only two we have right now
            if i.get('stimulate', None):
                self.inject_stimulus(i['stimulate'])
            elif i.get('look', None):
                self.look(i['look'])
            elif i.get('delay', None):
                self.process_delay(i['delay'])
            else:
                print("Unknown interaction type")
        pass

    def inject_stimulus(self, stimulus):
        if stimulus["type"] == "model operation":
            self.package_model_op(stimulus)
            pass
        elif isinstance(stimulus.action, MXSignalEvent):
            print("signal event")
            DispatchedEvent(signal=stimulus.action)
            pass
        elif isinstance(stimulus.action, MXLifecycleStateEntered):
            print("state entered")
        else:
            print("Unknown stimulus type")

    def package_model_op(self, operation):
        if operation["name"] == "call method":
            self.process_method_call(operation)

    def process_method_call(self, m):
        name = m["method name"]
        class_name = m["class name"]
        domain_alias = m["dest"]
        instance_id = m["instance"]
        params = m["parameters"]

        self.xe.mxlog.log(f"Calling {domain_alias}:{class_name}.{name}({params}) on instance {instance_id}")
        m = Method(xe=self.xe, name=name, class_name=class_name,
                   domain_name=self.xe.system.domains[domain_alias].name, domain_alias=domain_alias,
                   instance_id=instance_id, parameters=params)

    def process_signal(self):
        pass

    def look(self, model_element):
        pass

    def process_delay(self, delay):
        _logger.info(f"Processing: {delay} sec...")
        time.sleep(delay)
        pass