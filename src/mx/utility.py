""" utility.py - Debug utilities """
# System
from contextlib import redirect_stdout
import logging

# Model Integration
from pyral.relation import Relation
from pyral.relvar import Relvar

def snake(name: str) -> str:
    return name.replace(' ', '_')

def print_classes(db: str, class_names=None, output_file=None, name=''):
    """
    Prints out model information either to a file or the console.

    Args:
        db: Name of the database to view
        class_names: A list of class names (relvars) to print
        output_file: Print to this file if specified, otherwise to the console
        name: Optional header name to be displayed
    """
    def _print_content():
        if not class_names:
            print(f"\nvvv {name} model from {db} database vvv")
            Relvar.printall(db=db)
            print(f"\n^^^ {name} model from {db} database ^^^\n")
        else:
            print(f"\nvvv {name} classes from {db} database vvv\n")
            for c in class_names:
                Relation.print(db=db, variable_name=c)
            print(f"\n^^^ {name} classes from {db} database ^^^\n")

    if output_file:
        with open(output_file, 'w') as f:
            with redirect_stdout(f):
                _print_content()
    else:
        _print_content()

def logtable(logger, db: str, variable_name: str, table_name: str | None = None):
    t = Relation.print(db=db, variable_name=variable_name, table_name=table_name, printout=True)
    msg = f"\n{t}\n"
    logger.debug(msg)