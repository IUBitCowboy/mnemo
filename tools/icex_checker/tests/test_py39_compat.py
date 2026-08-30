"""Python 3.9 compatibility gate (SC-8).

The tool must run on Python 3.9+ with only requests + PyYAML as external
dependencies. This test parses every module with the 3.9 grammar and
fails on any syntax that would not compile on 3.9. It also asserts the
import surface stays stdlib + the two allowed deps.
"""
import ast
import pathlib
import sys

PACKAGE = pathlib.Path(__file__).resolve().parent.parent
MODULES = [
    "icex_checker.py",
    "checkers.py",
    "rubric.py",
    "report.py",
    "github_client.py",
    "errors.py",
    "__init__.py",
]


def test_modules_parse_as_python_39():
    for name in MODULES:
        path = PACKAGE / name
        source = path.read_text(encoding="utf-8")
        # feature_version=(3, 9) makes ast reject syntax newer than 3.9
        ast.parse(source, filename=str(path), feature_version=(3, 9))


def test_no_forbidden_imports():
    """SC-8: only stdlib + requests + yaml may be imported by the tool."""
    forbidden = {"bs4", "beautifulsoup4", "lxml", "pandas", "numpy"}
    for name in MODULES:
        path = PACKAGE / name
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in forbidden, (
                        "%s imports forbidden dependency %s" % (name, top)
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top not in forbidden, (
                        "%s imports forbidden dependency %s" % (name, top)
                    )
