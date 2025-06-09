""" mx_logger.py -- Model level logger """

# System
from pathlib import Path
from typing import Optional, TYPE_CHECKING

# Model Integration
from pyral.relation import Relation

# MX
from mx.actions.flow import label, FlowDir
if TYPE_CHECKING:
    from mx.activity import Activity

class MXLogger:

    def __init__(self, scenario_name: str, mode: str = 'w', include_timestamps: bool = False):
        self.scenario = scenario_name
        self.path = Path(f"{scenario_name.replace(' ', '_')}.log")
        self.file = self.path.open(mode=mode, encoding='utf-8', buffering=1)
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

    def log_nsflow(self, flow_name: str, flow_dir: FlowDir, flow_type: str, activity: "Activity", db: str, rv_name: str):
        flow_label = label(name=flow_name, activity=activity)
        show_label = f"<{flow_label}>" if flow_label else ""
        indir, outdir = ("->", "") if flow_dir == FlowDir.IN else ("", "->")
        self.log_table(message=f"{indir} {flow_name} {show_label} {outdir} :: {flow_type}", db=db, rv_name=rv_name)

    def log_sflow(self, flow_name: str, flow_dir: FlowDir, flow_type: str, activity: "Activity"):
        flow_label = label(name=flow_name, activity=activity)
        show_label = f"<{flow_label}>" if flow_label else ""
        indir, outdir = ("->", "") if flow_dir == FlowDir.IN else ("", "->")
        self.log(message=f"{indir} {flow_name} {show_label} {outdir} :: {flow_type}")

    def close(self):
        self.file.close()