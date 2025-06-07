""" mx_logger.py -- Model level logger """

# System
from pathlib import Path
from typing import Optional

# Model Integration
from pyral.relation import Relation

class MXLogger:

    def __init__(self, scenario_name: str, mode: str = 'w', include_timestamps: bool = False):
        self.scenario = scenario_name
        self.path = Path(f"{scenario_name.replace(' ', '_')}.log")
        self.file = self.path.open(mode=mode, encoding='utf-8')
        self.include_timestamps = include_timestamps
        self.header()

    def header(self):
        self.file.write(f"Executing scenario: {self.scenario}\n")
        self.file.write("---\n")

    def log(self, message: str, label: Optional[str] = None):
        if label:
            self.file.write(f"\n-- {label} --\n")
        self.file.write(message + "\n")

    def log_table(self, message: str, db: str, rv_name: str):
        self.file.write(f"{message}\n")
        t = Relation.print(db=db, variable_name=rv_name, printout=False)
        self.file.write(t)
        self.file.write("\n")

    def close(self):
        self.file.close()