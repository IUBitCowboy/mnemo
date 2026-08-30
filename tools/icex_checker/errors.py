"""Exception types for ICEX Submission Checker.

Defined in their own module so no other module has to import the
colliding name `icex_checker` (the CLI module file lives inside the
`icex_checker/` package directory per the spec's file layout; importing
`icex_checker` from a sibling module is filesystem-order-dependent and
would break on some platforms).
"""


class SubmissionNotFoundError(Exception):
    """Submission file does not exist or is not a regular file."""


class NotAnHTMLFileError(Exception):
    """Submission file exists but does not look like HTML."""


class NoPRUrlError(Exception):
    """Submission file contains no usable PR URL."""


class APIMissingTokenError(Exception):
    """No API token available through any authentication source."""


class AuthFailureError(Exception):
    """GitHub API rejected the token (HTTP 401)."""


class RateLimitError(Exception):
    """GitHub API rate limit reached (HTTP 403/429)."""


class PRNotAccessibleError(Exception):
    """PR or repository could not be accessed (HTTP 404/403)."""

    def __init__(self, message, status=None, body_message=None):
        super().__init__(message)
        self.status = status
        self.body_message = body_message


class NetworkError(Exception):
    """Network-level failure (DNS, connection refused, timeout)."""
