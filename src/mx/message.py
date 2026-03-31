""" message.py -- Format tabular messages for logging """

# System
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation

# MX
from mx.actions.flow import label, FlowDir

def table_msg(db: str, variable_name: str, table_name: str | None = None) -> str:
    """
    Formats a table to display the value of some relational variable

    Args:
        db:  Use this database session
        variable_name:  Name of the relational variable
        table_name:  Descriptive table name

    Returns:
        A formatted string that can be logged or printed to the console
    """
    t = Relation.print(db=db, variable_name=variable_name, table_name=table_name, printout=False)
    return f"\n\n{t}\n"

def nsflow_msg(db: str, flow_name: str, flow_dir: FlowDir, flow_type: str, activity: "ActivityExecution",
               rv_name: str) -> str:
    """
    Formats a table representing a data flow in the desired direction (input or output)

    Args:
        db: The database to use
        flow_name: Name of the data flow (F1, F2, etc)
        flow_dir: Input or output
        flow_type: Data type of the flow (class name, table name, scalar, etc)
        activity: Activity Execution object
        rv_name:  Name of the relational variable

    Returns:
        A formatted string that can be logged or printed to the console
    """
    flow_label = label(name=flow_name, activity=activity)
    show_label = f"<{flow_label}>" if flow_label else ""
    indir, outdir = ("->", "") if flow_dir == FlowDir.IN else ("", "->")
    tname = f"{indir} {flow_name} {show_label} {outdir} :: {flow_type}"
    return table_msg(db=db, variable_name=rv_name, table_name=tname)

def sflow_msg(db: str, flow_name: str, flow_dir: FlowDir, flow_type: str, activity: "ActivityExecution",
              rv_name: str) -> str:
    """

    Args:
        db: The database to use
        flow_name: Name of the data flow (F1, F2, etc)
        flow_dir: Input or output
        flow_type: Data type of the flow (class name, table name, scalar, etc)
        activity: Activity Execution object
        rv_name:  Name of the relational variable

    Returns:
        A formatted string that can be logged or printed to the console
    """
    flow_label = label(name=flow_name, activity=activity)
    show_label = f"<{flow_label}>" if flow_label else ""
    indir, outdir = ("->", "") if flow_dir == FlowDir.IN else ("", "->")
    tname = f"{indir} {flow_name} {show_label} {outdir} :: {flow_type}"
    return table_msg(db=db, variable_name=rv_name, table_name=tname)
