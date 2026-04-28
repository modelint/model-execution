#!/usr/bin/env python3
"""Extract Transition blocks from a log file."""

import sys

def extract_transitions(filepath: str) -> None:
    with open(filepath) as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        if lines[i].strip() == "Transition:":
            print("".join(lines[i:i+3]), end="")
            i += 3
        else:
            i += 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <logfile>", file=sys.stderr)
        sys.exit(1)
    extract_transitions(sys.argv[1])