""" utility.py - Debug utilities """
from contextlib import redirect_stdout

# Model Integration
from pyral.relation import Relation
from pyral.relvar import Relvar

def print_models(db: str, class_names=None, output_file=None):
    """
    Prints out model information either to a file or the console.

    Args:
        db: Name of the database to view
        class_names: A list of class names (relvars) to print
        output_file: Print to this file if specified, otherwise to the console
    """
    def _print_content():
        if not class_names:
            Relvar.printall(db=db)
        else:
            for c in class_names:
                Relation.print(db=db, variable_name=c)

    if output_file:
        with open(output_file, 'w') as f:
            with redirect_stdout(f):
                _print_content()
    else:
        _print_content()


