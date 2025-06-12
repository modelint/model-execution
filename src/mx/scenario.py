""" scenario_ping.py -- Calls the ping method """

# This file will be generated from a scenario script, but its handcoded for now

# System
import logging
from typing import TYPE_CHECKING
import time

if TYPE_CHECKING:
    from mx.xe import XE

# MX
from mx.interaction_event import InteractionEvent
from mx.method import Method
from mx.mxtypes import StateMachineType

_logger = logging.getLogger(__name__)


class Scenario:

    def __init__(self, xe: "XE"):
        self.xe = xe

    def run(self):
        """

        :return:
        """
        # Process each interaction in the scenario
        for i in self.xe.scenario['interactions']:
            match i["type"]:
                case "signal":
                    self.process_signal(i)
                    pass
                case "method call":
                    self.process_method_call(i)
                    pass
                case "delay":
                    pass
                case _:
                    print("Unknown interaction type")
                    pass
        #     pass
        #     # Is the interaction a stimulus or an inspection?  The only two we have right now
        #     if i.get('stimulate', None):
        #         self.inject_stimulus(i['stimulate'])
        #     elif i.get('look', None):
        #         self.look(i['look'])
        #     elif i.get('delay', None):
        #         self.process_delay(i['delay'])
        #     else:
        #         print("Unknown interaction type")
        # pass

    def inject_stimulus(self, stimulus):
        if stimulus["type"] == "model operation":
            self.package_model_op(stimulus)
        else:
            print("Unknown stimulus type")

    def package_model_op(self, operation):
        op_name = operation.get("name", None)
        if not op_name:
            pass
        match op_name:
            case "signal event":
                self.process_signal(operation)
            case "call method":
                self.process_method_call(operation)
            case _:
                pass

    def process_method_call(self, m):
        name = m["method name"]
        class_name = m["class name"]
        domain_alias = m["dest"]
        instance_id = m["instance"]
        params = m["parameters"]

        formatted_params = ", ".join(f"{k}: {v}" for k, v in params.items())
        formatted_id = ", ".join(f"{k}: {v}" for k, v in instance_id.items())

        self.xe.mxlog.log(f"Calling {domain_alias}:{class_name}.{name}({formatted_params}) on instance"
                          f" [{{{formatted_id}}}]")
        m = Method(xe=self.xe, name=name, class_name=class_name,
                   domain_name=self.xe.system.domains[domain_alias].name, domain_alias=domain_alias,
                   instance_id=instance_id, parameters=params)

    def process_signal(self, s):
        target_domain = self.xe.system.domains[s["domain"]]
        sm_type = s.get("state machine", None)
        if not sm_type:
            # TODO: raise exception
            pass
        match sm_type:
            case "lifecycle":
                ie = InteractionEvent.to_lifecycle(source=s.get("source", None), event_spec=s["name"],
                                                   to_instance=s["instance"], to_class=s["class"],
                                                   params=s.get("params", {}), domain=target_domain)
            case "single assigner":
                ie = InteractionEvent.to_single_assigner(source=s.get("source", None), event_spec=s["name"],
                                                         to_rnum=s["rnum"], params=s.get("params", {}),
                                                         domain=target_domain)
            case "multiple assigner":
                ie = InteractionEvent.to_multiple_assigner(source=s.get("source", None), event_spec=s["name"],
                                                           partitioning_instance=s["instance"],
                                                           partitioning_class=s["class"], to_rnum=s["rnum"],
                                                           params=s.get("params", {}), domain=target_domain)
            case _:
                # TODO: raise exception
                pass

        pass

    def look(self, model_element):
        pass

    def process_delay(self, delay):
        _logger.info(f"Processing: {delay} sec...")
        time.sleep(delay)
        pass
