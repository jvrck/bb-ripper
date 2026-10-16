"""Compatibility launcher for running bb-ripper directly from a checkout."""

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from bb_ripper.__main__ import main as package_main  # pylint: disable=wrong-import-position


def main():
    """Delegate to the installed package entry point."""
    return package_main()


if __name__ == "__main__":
    sys.exit(main())
