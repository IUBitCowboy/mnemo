"""Canvas submission parser for ICEX Submission Checker."""

import pathlib
import re

_META_REFRESH_RE = re.compile(
    r'<meta[^>]*http-equiv\s*=\s*["\']?[Rr]efresh["\']?[^>]*content\s*=\s*["\']0;\s*url\s*=\s*([^"\']+)["\']',
    re.IGNORECASE,
)

_LINK_HREF_RE = re.compile(r'<a[^>]+href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

_PR_URL_RE = re.compile(
    r"https?://(?P<host>[^/\"'\s<]+)/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/pull/(?P<number>\d+)"
)

_TITLE_RE = re.compile(
    r"Week(?P<week>\d\d?)\s*-\s*(?P<assignment>ICEX\d+)\s*:\s*(?P<name>.+)"
)


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


class Submission:
    """Parsed submission data.

    Attributes:
        pr_url: PR URL extracted from the file (meta refresh preferred).
        url_discrepancy: True when meta and body-link URLs disagree.
        week: week number string from the <title> (e.g. "01"), or None.
        assignment_id: ICEX identifier from the <title> (e.g. "ICEX01"),
            or None.
        student_name: student name from the <title>, or None.
        title_parsed: True when the <title> matched the expected pattern.
    """

    def __init__(self, pr_url=None, url_discrepancy=False):
        self.pr_url = pr_url
        self.url_discrepancy = url_discrepancy
        self.week = None
        self.assignment_id = None
        self.student_name = None
        self.title_parsed = False


def parse_submission(path):
    """Parse a Canvas submission HTML file (FR-1, FR-6).

    Extracts the PR URL from the meta refresh tag and/or a body link,
    preferring the meta refresh URL when they disagree, and parses the
    assignment identifier from the <title> tag.

    Returns a Submission object. Raises SubmissionNotFoundError,
    NotAnHTMLFileError, or NoPRUrlError.
    """
    p = pathlib.Path(path)
    if not p.is_file():
        raise SubmissionNotFoundError(str(p))

    text = p.read_text(encoding="utf-8", errors="replace")
    if "<html" not in text.lower() and "<head" not in text.lower():
        raise NotAnHTMLFileError(str(p))

    sub = Submission()
    _parse_title(text, sub)

    meta_match = _META_REFRESH_RE.search(text)
    meta_url = meta_match.group(1).strip() if meta_match else None

    body_url = None
    for m in _LINK_HREF_RE.finditer(text):
        href = m.group(1).strip()
        if _is_pr_url(href):
            body_url = href
            break

    if meta_url:
        sub.pr_url = meta_url
        if body_url and body_url != meta_url:
            sub.url_discrepancy = True
    elif body_url:
        sub.pr_url = body_url
    else:
        raise NoPRUrlError(str(p))

    return sub


def _parse_title(text, sub):
    """Parse 'WeekNN - ICEXNN: Student Name' from the <title> tag (FR-6)."""
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return
    title = m.group(1).strip()
    t = _TITLE_RE.match(title)
    if not t:
        return
    sub.week = t.group("week")
    sub.assignment_id = t.group("assignment")
    sub.student_name = t.group("name").strip()
    sub.title_parsed = True


def _is_pr_url(url):
    return _PR_URL_RE.match(url) is not None


def validate_pr_url(url, github_host):
    """Validate a PR URL (FR-2).

    Returns (ok, reason). ok is True for a valid HTTPS github host PR URL;
    otherwise False with a human-readable reason.
    """
    if not url:
        return False, "PR URL is empty"
    m = _PR_URL_RE.match(url)
    if not m:
        return False, "malformed URL or not a PR URL"
    if m.group("host") != github_host:
        return False, "PR URL points to %s, expected %s" % (
            m.group("host"),
            github_host,
        )
    if not url.startswith("https://"):
        return False, "PR URL must use HTTPS scheme"
    return True, None
