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
        self.relations = dict()  # This is the set of relations keyed by relvar name ready for insertion into the user db

        # Process each class (c) and its initial instance specification (i)
        for class_name, i_spec in self.pop.items():
            alias_index = dict()
            expanded_header = []  # A list of attributes with any references expanded to from_attributes
            instance_tuples = []  # The expanded instance tuples including values for the from_attributes
            ref_path = dict()  # Each
            for col in i_spec.header:
                # Each column in the parsed header for this class includes a sequence of attributes and
                # optional references. A reference points to some class via a relationship rnum
                if isinstance(col, str):  # Attributes are just string names
                    # The column is an attribute, just add it directly to the expanded header
                    expanded_header.append(col)
                elif isinstance(col, list):  # It must be a list of dictionaries describing a reference
                    for ref in col:
                        # Since an attribute may participate in more than one relationship
                        # there may be multiple references in the same column, for example:
                        #    R38>Bank Level, R5>Bank
                        # is parsed into two components
                        rnum = ref['rnum']  # The rnum on this reference
                        to_class = ref['to class']  # Refering to some target attribute in this class
                        # Lookup the attribute reference in the metamodel
                        R = f"Rnum:<{rnum}>, From_class:<{class_name}>, To_class:<{to_class}>, Domain:<{self.domain}>"
                        Relation.restrict(db=mmdb, relation='Attribute_Reference', restriction=R, svar_name='ra')
                        result = Relation.project(db=mmdb, attributes=('From_attribute','To_attribute'), svar_name='ra')
                        if not result.body:
                            msg = f"Initial instance ref expansion: No attribute references defined for{R}"
                            _logger.exception(msg)
                            raise MXInitialInstanceReferenceException(msg)
                        # We already know the rnum, from class (class_name) and to class, so we just need a projection
                        # on the local attribute and where the attribute in the target class
                        ref_path[to_class] = []
                        alias_position = len(expanded_header)
                        for attr_ref in result.body:
                            # A reference can consist of multiple attributes, so we process each one
                            from_attr = attr_ref['From_attribute']
                            to_attr = attr_ref['To_attribute']
                            alias_index[from_attr] = alias_position
                            # Add a dictionary entry so that we can lookup up referenced values
                            ref_path[to_class].append(AttrRef(from_attr=from_attr, to_attr=to_attr, to_class=to_class))
                            # Add the from attribute to our expanded header
                            if from_attr not in expanded_header:
                                # It might already be there if the same attribute participates in more than one
                                # relationship. If so, we only need one value anyway, so add the from attr only
                                # if it isn't already in the header.
                                expanded_header.append(from_attr)
                else:
                    msg = f"Unrecognized column format in initial instance parse: [{col}]"
                    _logger.exception(msg)
                    raise MXException(msg)

            # Now that the relation header for our instance population is created, we need to fill in the relation
            # body (the actual instance values corresponding to each attribute in the expanded header)
            for irow in i_spec.population:
                row_dict = dict()  # Each value for an instance keyed by attribute name in the expanded header
                for index, attr in enumerate(expanded_header):
                    # We walk through the values matching the attribute order, so we remember the attr ordering
                    if attr in i_spec.header:
                        # If there is no matching key for the attribute in the ref_path, it means that
                        # this was not a reference that got expanded.  So we simply assign the value
                        # from the parsed population to the corressponding attribute in the expanded header
                        row_dict[attr.replace(' ','_')] = irow['row'][index]
                    else:
                        # The attribute was expanded from a reference and we need to obtain its value from
                        # an attribute in the target class for the instance matching the referenced alias
                        # So first we grab the alias associated with this instance's reference. It tells us which
                        # named instance in the target class to reference. For example this row from Shaft:
                        #    { [S4] [true] @P }
                        # has a third column value with the 'P' alias as designated by the @ character
                        # There is a matching row in the Bank population here:
                        #     P { [Penthouse] [4.0] [2.0] [25] [7.0] [9.0] }
                        #
                        alias_position = alias_index[attr]
                        alias = irow['row'][alias_position]['ref to']  # The alias 'P' in the above example
                        # Get the population of the referenced class
                        target_pop = self.pop[to_class]
                        # target_pop = self.pop[ref_path[attr].to_class]
                        # Get index of referenced value
                        to_attr_index = target_pop.header.index(to_attr)
                        # Now search through the target population looking for the instance named by the alias
                        referenced_i = [i for i in target_pop.population if i['alias'] == alias][0]
                        # And then grab the value in that row corresponding to the to_attr_index
                        ref_value = referenced_i['row'][to_attr_index]
                        # And now add the key value pair of referencing attr and target value to our row of values
                        row_dict[from_attr] = ref_value
                instance_tuples.append(row_dict)  # Add the completed row of attr values to our relation

            # Now we are ready to create the structure we need to insert into the class relvar in the user db
            expanded_header = [a.replace(' ', '_') for a in expanded_header]  # Replace spaces from any attribute name
            class_tuple_type_name = f"{class_name.replace(' ', '_')}_i"
            ClassTupleType = namedtuple(class_tuple_type_name, expanded_header)
            table = []
            for inst in instance_tuples:
                dvalues = [inst[name] for name in expanded_header]
                drow = ClassTupleType(*dvalues)
                table.append(drow)
            self.relations[class_name] = table
            pass
        pass




