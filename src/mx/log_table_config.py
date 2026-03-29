""" log_table_config.py -- Registers a table formatter """

import logging

TABLE = 25
logging.addLevelName(TABLE, "TABLE")

class TableAwareFormatter(logging.Formatter):
    def format(self, record):
        original = super().format(record)
        if record.levelno != TABLE:
            return original
        prefix = original[: original.index(record.getMessage())]
        lines = record.getMessage().splitlines()
        return '\n'.join(
            [prefix + lines[0]] + ['    ' + l for l in lines[1:]]
        )

def log_table(logger: logging.Logger, table_str: str) -> None:
    logger.log(TABLE, table_str)