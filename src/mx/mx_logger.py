""" mx_logger.py -- Model level logger """

# System
from pathlib import Path
from typing import Optional

class MXLogger:

    def __init__(self, path: str | Path, mode: str = 'w', include_timestamps: bool = False):
        self.path = Path(path)
        self.file = self.path.open(mode, encoding='utf-8')
        self.include_timestamps = include_timestamps

    def header(self):

    def log(self, message: str, label: Optional[str] = None):
        if label:
            self.file.write(f"\n-- {label} --\n")
        self.file.write(message + "\n")

    def close(self):
        self.file.close()