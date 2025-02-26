""" scenario.py -- Populate the schema """


# System
from pathlib import Path

# Model Integration
from sip_parser.parser import SIParser

class Scenario:

    def __init__(self, scenario_file: Path):
        result = SIParser.parse_file(file_input=scenario_file, debug=True)
        pass

