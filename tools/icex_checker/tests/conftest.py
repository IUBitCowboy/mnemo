"""Make the icex_checker package importable from tests regardless of cwd."""
import pathlib
import sys

PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))
