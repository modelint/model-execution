""" mx_logger.py -- Model level logger """

# System
from pathlib import Path
from typing import Optional

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

    def close(self):
        self.file.close()