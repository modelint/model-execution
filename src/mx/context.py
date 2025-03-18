""" starting_context.py -- Populate the schema """

# System
from pathlib import Path
from collections import namedtuple
import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from mx.domain_model_db import DomainModelDB

# Model Integration
from sip_parser.parser import SIParser
from pyral.relation import Relation
from pyral.relvar import Relvar
from pyral.transaction import Transaction

# Model Execution
from mx.db_names import mmdb
from mx.exceptions import *

AttrRef = NamedTuple('AttrRef', from_attr=str, to_attr=str, to_class=str, alias=str)
MultipleAssignerInitialState = NamedTuple('MultipleAssignerInitialState', pclass=str, state=str)
# AttrRef = namedtuple('AttrRef', 'from_attr to_attr to_class alias')

_logger = logging.getLogger(__name__)

tcl_to_python = { 'string': str, 'boolean': bool, 'double': float, 'int': int }

pop_scenario = 'pop'  # Name of transaction that loads the schema

class Context:

    def __init__(self, domaindb: 'DomainModelDB'):
        """
        We see that there is an R1 ref.  We need to find the target attributes and class
        The metamodel gives us Shaft.Bank -> Bank.Name

        We proceed for each instance of Shaft taking the R1 ref (L, P, or F)
        And go find the Bank population
        We find the L instance
        Now we grab the Name value and add it to our Shaft table by adding a key.
        And, at this point, we are building the relation.create command
        When we get all the values, we commit and move on to the next instance

        :param sip_file:  The path to the *.sip file providing the intial instance population
        :param domain:  The subject matter domain being populated
        :param dbtypes: The actual TclRAL db_types used to represent user model db_types
        """
        self.domaindb = domaindb
        self.lifecycle_istates: dict[str, str] = {}
        self.ma_istates: dict[str, MultipleAssignerInitialState] = {}

        db_dir = self.domaindb.system.system_dir / self.domaindb.system.context_dir
        found_files = [file for file in db_dir.iterdir() if file.is_file() and
                       any(file.name.lower().startswith(prefix) for prefix in self.domaindb.prefixes)]
        if len(found_files) == 0:
            raise MXFileException(f"No .sip file found for domain [{self.domaindb.domain}] in: {db_dir.resolve()}")
        if len(found_files) > 1:
            raise MXFileException(f"Multiple db_types files for domain [{self.domaindb.domain}] in: {db_dir.resolve()}")

        sip_file = found_files[0]

        # Parse the starting_context's initial population file (*.sip file)
        _logger.info(f"Parsing sip: [{sip_file}]")
        parse_result = SIParser.parse_file(file_input=sip_file, debug=False)
        self.name = parse_result.name  # Name of this starting_context
        self.pop = parse_result.classes  # Dictionary of initial instance populations keyed by class name
        self.relations = dict()  # The set of relations keyed by relvar name ready for insertion into the user db

        _logger.info(f"Sip parsed, loading initial instance population into user db")
        # Process each class (c) and its initial instance specification (i)
        for class_name, i_spec in self.pop.items():
            expanded_header = []  # A list of attributes with any references expanded to from_attributes
            instance_tuples = []  # The expanded instance tuples including values for the from_attributes
            ref_path = dict()  # Each attribute reference and data required to resolve it
            for col_position, col in enumerate(i_spec.header):
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
                        # Look up the attribute reference(s) in the metamodel
                        R = (f"Rnum:<{rnum}>, From_class:<{class_name}>, To_class:<{to_class}>, "
                             f"Domain:<{self.domaindb.domain}>")
                        Relation.restrict(db=mmdb, relation='Attribute_Reference', restriction=R, svar_name='ra')
                        result = Relation.project(db=mmdb, attributes=('From_attribute', 'To_attribute'),
                                                  svar_name='ra')
                        if not result.body:
                            msg = f"Initial instance ref expansion: No attribute references defined for{R}"
                            _logger.exception(msg)
                            raise MXInitialInstanceReferenceException(msg)
                        # We already know the rnum, from class (class_name) and to class, so we just need a projection
                        # on the local attribute and where the attribute in the target class
                        for attr_ref in result.body:
                            # A reference can consist of multiple attributes, so we process each one
                            from_attr = attr_ref['From_attribute']
                            to_attr = attr_ref['To_attribute']
                            # Add a dictionary entry so that we can look up referenced values
                            ref_path[len(expanded_header)] = AttrRef(from_attr=from_attr, to_attr=to_attr,
                                                                     to_class=to_class, alias=col_position)
                            # We key the path to the position of the from_attr in the expanded header
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
                # save any initial states for classes and multiple assigners
                # TODO: Support single assigners (after SIP support added)
                for s in irow['initial_state']:
                    if len(s) == 1:
                        # save initial state for this class
                        self.lifecycle_istates[class_name] = s[0]
                    if len(s) == 2:
                        # index by rnum and save partitioning class and initial state
                        self.ma_istates[s[0]] = MultipleAssignerInitialState(pclass=class_name, state=s[1])

                # For each instance row under the class header parsed from the init file
                irow_col = 0  # Initial column position in the irow
                row_dict = dict()  # Each value for an instance keyed by attribute name in the expanded header
                in_ref = False  # We are not currently expanding a reference
                for index, attr in enumerate(expanded_header):
                    # We walk through the values matching the attribute order, so we remember the attr ordering
                    if attr in i_spec.header:
                        in_ref = False  # Not processing a reference
                        # If there is no matching key for the attribute in the ref_path, it means that
                        # this was not a reference that got expanded.  So we simply assign the value
                        # from the parsed population to the corresponding attribute in the expanded header
                        attr_value = irow['row'][irow_col]  # This will be a string
                        # Cast it to the appropriate TclRAL type for db insertion
                        cast_attr_value = self.cast_to_dbtype(attr_name=attr, attr_class=class_name, value=attr_value)
                        row_dict[attr.replace(' ', '_')] = cast_attr_value  # We can't have spaces in relvar names
                        irow_col = irow_col + 1  # Increment column position
                    else:
                        if not in_ref:
                            # We are beginning to process a reference, so we want to advance the position
                            # just once (not for every referential attribute)
                            irow_col = irow_col + 1
                        in_ref = True  # This keeps us from incrementing the counter until we're done
                        # The attribute was expanded from a reference and we need to obtain its value from
                        # an attribute in the target class for the instance matching the referenced alias
                        # So first we grab the alias associated with this instance's reference. It tells us which
                        # named instance in the target class to reference. For example this row from Shaft:
                        #    { [S4] [true] @P }
                        # has a third column value with the 'P' alias as designated by the @ character
                        # There is a matching row in the Bank population here:
                        #     P { [Penthouse] [4.0] [2.0] [25] [7.0] [9.0] }
                        #

                        # We want the reference path keyed to the current position in the expanded header
                        ref = ref_path[index]

                        alias = irow['row'][ref.alias]['ref to']  # The alias 'P' in the above example
                        # Get the population of the referenced class
                        target_pop = self.pop[ref.to_class]
                        # Get index of referenced value
                        to_attr_index = target_pop.header.index(ref.to_attr)
                        # Now search through the target population looking for the instance named by the alias
                        referenced_i = [i['row'] for i in target_pop.population if i['alias'] == alias][0]
                        # And then grab the value in that row corresponding to the to_attr_index
                        ref_value = referenced_i[to_attr_index]
                        # And now add the key value pair of referencing attr and target value to our row of values
                        cast_ref_value = self.cast_to_dbtype(attr_name=attr, attr_class=class_name, value=ref_value)
                        row_dict[ref.from_attr] = cast_ref_value
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
        self.insert()
        # Print out the populated user model
        print("\nPopulated user model\n-----")
        Relvar.printall(db=self.domaindb.alias)

    def cast_to_dbtype(self, attr_name: str, attr_class: str, value: str) -> int | str | float | bool:
        """
        Casts a string value to a python type (int, str, ...) that correponds to a TclRAL type that
        is used to represent the Scalar defined in the user model.

        Looks up the Scalar associated with the supplied attribute. This is the type specified in the user
        model such as 'Bank Name', 'Duration', etc.

        Consults the user model Scalar -> TclRAL type mapping to determine which type to use in the user db.
        These are low level system db_types that TclRAL supports like 'string', 'int', 'boolean', etc.

        :param attr_name: Name of the user model attribute
        :param attr_class: Name of the attribute's class
        :param value: The value to be cast
        :return: The TclRAL type used to represent the Scalar
        """
        # Look up the user type in the populated metamodel

        R = f"Class:<{attr_class}>, Name:<{attr_name}>, Domain:<{self.domaindb.domain}>"
        result = Relation.restrict(db=mmdb, relation='Attribute', restriction=R)
        if not result.body:
            msg = f"No Scalar found in populated metamodel for attribute [{self.domaindb.domain}:{attr_class}.{attr_name}]"
            _logger.exception(msg)
            raise MXScalarException(msg)
        scalar = result.body[0]['Scalar']
        dbtype = self.domaindb.user_types[scalar]
        # Now cast using corresponding python type
        # Boolean is a special case as it does not provide a string to bool casting function
        if dbtype == 'boolean':
            python_value = True if value.strip().lower() == 'true' else False
        else:
            python_value = tcl_to_python[dbtype](value)
        return python_value

    def insert(self):
        """
        Insert relations in the user database
        """
        Transaction.open(db=self.domaindb.alias, name=pop_scenario)
        for relation, population in self.relations.items():
            Relvar.insert(db=self.domaindb.alias, tr=pop_scenario, relvar=relation.replace(' ', '_'), tuples=population)
        Transaction.execute(db=self.domaindb.alias, name=pop_scenario)

