""" rvname.py -- Relation variable name assigner """

class RVN:
    """
    Relational Variable Name
    """

    _db_counter : dict[str, int] = {}

    @classmethod
    def init_for_db(cls, db: str):
        cls._db_counter[db] = 0

    @classmethod
    def name(cls, db: str, name: str = ""):
        suffix = "" if not name else f"_{name}"
        cls._db_counter[db] += 1
        unique_name = f"rvn_{cls._db_counter[db]}{suffix}"
        return unique_name