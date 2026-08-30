"""Re-export the CLI module's public API.

The spec's file layout puts `icex_checker.py` (the CLI module) inside
the `icex_checker/` package directory. `import icex_checker` may resolve
to the package or the module file depending on filesystem scan order, so
this package re-exports the module's public names to make both
resolutions equivalent.
"""

from .icex_checker import *  # noqa: F401,F403
