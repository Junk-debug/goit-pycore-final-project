"""Allows running the package as `python -m personal_assistant`."""

import sys

from personal_assistant.cli import main

if __name__ == "__main__":
    sys.exit(main())
