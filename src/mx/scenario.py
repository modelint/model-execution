""" scenario.py -- Populate the schema """


# System
from pathlib import Path
from collections import namedtuple
import logging

# Model Integration
from sip_parser.parser import SIParser
from pyral.relation import Relation

# Model Execution
from mx.db_names import mmdb, udb
from mx.exceptions import *

AttrRef = namedtuple('AttrRef', 'from_attr to_attr to_class')

_logger = logging.getLogger(__name__)

class Scenario:

    def __init__(self, scenario_file: Path, domain: str):
        """
        We see that there is an R1 ref.  We need to find the target attributes and class
        The metamodel gives us Shaft.Bank -> Bank.Name

        We proceed for each instance of Shaft taking the R1 ref (L, P, or F)
        And go find the Bank population
        We find the L instance
        Now we grab the Name value and add it to our Shaft table by adding a key.
        And, at this point, we are building the relation.create command
        When we get all the values, we commit and move on to the next instance

        :param scenario_file:
        :param domain:
        """
        self.domain = domain

        # Parse the scenario's initial population file (*.sip file)
        parse_result = SIParser.parse_file(file_input=scenario_file, debug=False)
        self.name = parse_result.name  # Name of this scenario
        self.pop = parse_result.classes  # Dictionary of initial instance populations keyed by class name

        # Process each class (c) and its initial instance specification (i)
        for class_name, i_spec in self.pop.items():
            expanded_header = []  # A list of attributes with any references expanded to from_attributes
            instance_tuples = []  # The expanded instance tuples including values for the from_attributes
            ref_path = dict()  # Each
            for col in i_spec.header:
                # Each column in the parsed header for this class includes a sequence of attributes and
                # optional references. A reference points to some class via a relationship rnum
                if isinstance(col, str):  # Attributes are just string names
                    # The column is an attribute, just add it directly to the expanded header
                    # We need to delimit with underscores instead of spaces for database insertion
                    expanded_header.append(col.replace(' ', '_'))
                elif isinstance(col, list):  # It must be a list of dictionary describing a reference
                    for ref in col:
                        rnum = ref['rnum']
                        to_class = ref['to class']
                        R = f"Rnum:<{rnum}>, From_class:<{class_name}>, To_class:<{to_class}>, Domain:<{self.domain}>"
                        Relation.restrict(db=mmdb, relation='Attribute_Reference', restriction=R, svar_name='ra')
                        result = Relation.project(db=mmdb, attributes=('From_attribute','To_attribute'), svar_name='ra')
                        for attr_ref in result.body:
                            from_attr = attr_ref['From_attribute']
                            to_attr = attr_ref['To_attribute']
                            ref_path[to_class] = AttrRef(from_attr=from_attr, to_attr=to_attr, to_class=to_class)
                            if from_attr not in expanded_header:
                                expanded_header.append(from_attr)
                else:
                    msg = f"Unrecognized column format in initial instance parse: [{col}]"
                    _logger.exception(msg)
                    raise MXException(msg)

            for irow in i_spec.population:
                row_dict = dict()
                for index, attr in enumerate(expanded_header):
                    if attr not in ref_path:
                        row_dict[attr] = irow['row'][index]
                    else:
                        alias = irow['row'][index]['ref to']
                        # Get the population of the referenced class
                        target_pop = self.pop[ref_path[attr].to_class]
                        # Get index of referenced value
                        to_attr_index = target_pop.header.index(to_attr)

                        referenced_i = [i for i in target_pop.population if i['alias'] == alias][0]
                        # Find instance with matching alias
                        ref_value = referenced_i['row'][to_attr_index]
                        row_dict[from_attr] = ref_value
                        pass
                instance_tuples.append(row_dict)
            class_tuple_type_name = f"{class_name.replace(' ', '_')}_i"
            ClassTupleType = namedtuple(class_tuple_type_name+'_i', expanded_header)
            table = []
            for inst in instance_tuples:
                dvalues = [inst[name] for name in expanded_header]
                drow = ClassTupleType(*dvalues)
                table.append(drow)
            pass




