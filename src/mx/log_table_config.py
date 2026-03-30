""" log_table_config.py -- Registers a table formatter """

import logging

TABLE = 25
logging.addLevelName(level=TABLE, levelName="TABLE")

class ConsoleWarningFilter(logging.Filter):
    def filter(self, record):
        return record.levelno >= logging.WARNING

class ConsoleTableFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == TABLE





# class ConsoleFilter(logging.Filter):
#     def filter(self, record):
#         return record.levelno == TABLE or record.levelno >= logging.WARNING

class TableAwareFormatter(logging.Formatter):
    def format(self, record):
        original = super().format(record)
        if record.levelno != TABLE:
            return original
        prefix = original[: original.index(record.getMessage())]
        msg = record.getMessage()
        lines = msg.splitlines()
        formatted_lines = []
        for i, line in enumerate(lines):
            formatted_lines.append(prefix + line if i == 0 else line)
        fout = f"{'\n'.join(formatted_lines)}\n"
        return fout

def log_table(logger: logging.Logger, table_str: str) -> None:
    logger.log(TABLE, table_str)