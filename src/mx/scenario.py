""" scenario_ping.py -- Calls the ping method """

# This file will be generated from a scenario script, but its handcoded for now

# System
import logging
from typing import TYPE_CHECKING
import time
from operator import itemgetter

if TYPE_CHECKING:
    from mx.xe import XE

# MX
from mx.interaction_event import InteractionEvent
from mx.method import Method
from mx.mxtypes import StateMachineType
from mx.exceptions import *

_logger = logging.getLogger(__name__)


class Scenario:

    def __init__(self, xe: "XE"):
        self.xe = xe
        try:
            self.name, self.description, self.participating_domains = itemgetter(
                "name", "description", "domains"
            )(xe.scenario_parse["Scenario"])
        except KeyError as e:
            msg = f"Missing field: {e} in scenario file"
            _logger.error(msg)
            raise

        self.interactions = xe.scenario_parse.get("Interactions", [])
        self.pending_response = None  # The response we are currently waiting on


    def inject(self, stimulus):
        """
        Inject stimulus into the executing system

        Args:
            stimulus: Scenario specified stimulus to inject
        """
        stype = stimulus.get("type")
        if not stype:
            msg = f"No type specified for stimulus: [{stimulus}]"
            _logger.error(msg)
            raise MXScenarioDirectorInput(msg)

        match stype:
            case "event":
                self.process_signal(stimulus)
                pass

    def process_response(self, r):
        """
        Process the response by notifying the user somehow (log, display, etc)

        Args:
            response: Scenario specified stimulus to inject
        """
        # Set to pending response and return control to MX
        self.pending_response = r
        # run the MX loop
        match r["type"]:
            case 'external event':
                from_inst_str = '-'.join(f"{v}" for v in r["instance"].values())
                msg = f"{r["type"]} | {r['name']}() from {r['from']}::{r['class']}[{from_inst_str}] to {r['to']}"
                print(msg)
                pass
            case _:
                pass

    def run(self):
        """
        Process each interaction, if any, in the scenario
        """
        for i in self.interactions:
            # Each interaction is a single dictonary item with a key specifying the interaction type
            itype, idesc = list(i.items())[0]  # Split out k,v of single dictionary item
            match itype:
                case "stimulus":
                    self.inject(stimulus=idesc)
                case "response":
                    self.process_response(r=idesc)
                case _:
                    msg = f"Unknown interaction type: [{itype}]"
                    _logger.error(msg)
                    raise MXScenarioDirectorInput(msg)

            # match i["type"]:
            #     case "signal":
            #         self.process_signal(i)
            #         pass
            #     case "call method":
            #         self.process_method_call(i)
            #         pass
            #     case "delay":
            #         pass
            #     case _:
            #         print("Unknown interaction type")
            #         pass
        #     # Is the interaction a stimulus or an inspection?  The only two we have right now
        #     if i.get('stimulate', None):
        #         self.inject_stimulus(i['stimulate'])
        #     elif i.get('look', None):
        #         self.look(i['look'])
        #     elif i.get('delay', None):
        #         self.process_delay(i['delay'])
        #     else:
        #         print("Unknown interaction type")

        # Run the system
        self.xe.system.go()
        pass  # All work completed
        # No more interactions




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
        name = m["name"]
        class_name = m["class"]
        domain_alias = m["domain"]
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
        target_domain_alias = s['to']
        # TODO: Always provide a source, EE, inst, rel, rel-pinst
        # TODO: We'll need to define a source Data Class
        target_domain = self.xe.system.domains[target_domain_alias]
        ie = InteractionEvent.to_lifecycle(event_spec=s["name"],
                                           to_instance=s["instance"], to_class=s["class"],
                                           params=s.get("params", {}), domain=target_domain)

    def look(self, model_element):
        pass

    def process_delay(self, delay):
        _logger.info(f"Processing: {delay} sec...")
        time.sleep(delay)
        pass
