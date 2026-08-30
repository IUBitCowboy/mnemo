"""ICEX Submission Checker — main CLI entry point.

Reads a Canvas submission HTML file, extracts the pull request URL,
queries the GitHub Enterprise API (github.iu.edu) to verify rubric
criteria, and produces a structured report for the TA. The tool does NOT
grade — it surfaces evidence and flags discrepancies.

Script interface contract (spec v1.0.0):

    python3 icex_checker.py <submission.html> [--rubric FILE] [--token TOKEN]
        [--github-host HOST] [--save-json FILE] [--output-format text|json]
        [--batch DIR] [--output-dir DIR] [--verbose] [--version]

Exit codes: 0 success, 1 fatal error, 2 partial failure in batch mode.
"""

import argparse
import datetime
import json
import pathlib
import re
import sys

from checkers import CheckerContext, run_criterion
from errors import (
    APIMissingTokenError,
    AuthFailureError,
    NetworkError,
    NoPRUrlError,
    NotAnHTMLFileError,
    PRNotAccessibleError,
    RateLimitError,
    SubmissionNotFoundError,
)
from github_client import GitHubClient
from report import Assessment, build_json_report, build_text_report
from rubric import RubricNotFoundError, RubricParseError, find_rubric, load_rubric

TOOL_VERSION = "1.0.0"
TOOL_DIR = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Canvas submission parsing (FR-1, FR-2, FR-6)
# ---------------------------------------------------------------------------

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


def build_parser():
    parser = argparse.ArgumentParser(
        prog="icex_checker",
        description=(
            "Preliminary compliance assessment of C291 ICEX submissions. "
            "Reads a Canvas submission HTML file, verifies rubric criteria "
            "against the GitHub Enterprise API, and reports evidence for the "
            "TA. Does not grade."
        ),
    )
    parser.add_argument(
        "submission",
        nargs="?",
        help="Path to Canvas submission HTML file (required unless --batch)",
    )
    parser.add_argument("--rubric", help="Path to rubric YAML file (auto-detected if omitted)")
    parser.add_argument("--token", help="GitHub Enterprise API token")
    parser.add_argument(
        "--github-host",
        default="github.iu.edu",
        help="GitHub Enterprise host (default: github.iu.edu)",
    )
    parser.add_argument("--save-json", help="Save full assessment as JSON to this path")
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--batch",
        help="Batch mode: process all .html files in this directory",
    )
    parser.add_argument(
        "--output-dir",
        help="Batch mode: write JSON files here (requires --batch)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include API response details in output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="icex_checker %s" % TOOL_VERSION,
    )
    return parser


def main(argv=None):
    """CLI entry point. Returns the process exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if exc.code is not None else 0

    if args.output_dir and not args.batch:
        print("--output-dir requires --batch", file=sys.stderr)
        return 1

    if args.batch:
        return _run_batch(args)

    if not args.submission:
        print("submission file required (or use --batch)", file=sys.stderr)
        return 1

    code, result = _process_one(args, args.submission)
    if code != 0:
        print(result, file=sys.stderr)
    return code


def _process_one(args, submission_path):
    """Process a single submission.

    Returns (exit_code, result) where result is an Assessment on success
    or an error message string on failure. Errors are returned, not
    printed, so single mode can send them to stderr and batch mode to
    stdout.
    """
    try:
        sub = parse_submission(submission_path)
    except SubmissionNotFoundError:
        return 1, "submission file not found: %s" % submission_path
    except NotAnHTMLFileError:
        return 1, "submission file does not appear to be HTML: %s" % submission_path
    except NoPRUrlError:
        return 1, "no PR URL found in submission file: %s" % submission_path

    ok, reason = validate_pr_url(sub.pr_url, args.github_host)
    if not ok:
        return 1, reason

    try:
        rubric_path = _resolve_rubric(args, sub)
        rubric = load_rubric(rubric_path)
    except RubricNotFoundError:
        return 1, "rubric file not found: %s" % (args.rubric or "(auto-detect)")
    except RubricParseError as exc:
        return 1, str(exc)

    try:
        token = GitHubClient.resolve_token(args.token, host=args.github_host)
    except APIMissingTokenError as exc:
        return 1, str(exc)

    client = GitHubClient(token=token, host=args.github_host)
    owner, repo, number = _split_pr_url(sub.pr_url)

    # Pre-flight: the repo must be reachable (EF-6 fatal path). A missing
    # PR number with a valid repo is NOT fatal — pr_url_valid handles it
    # as partial credit.
    try:
        client.get_repo(owner, repo)
    except PRNotAccessibleError as exc:
        return 1, (
            "PR not accessible (%s). PR URL for manual review: %s\n"
            "If the repo is private, this usually means the token lacks "
            "access: check that GH_TOKEN is a github.iu.edu token (not "
            "github.com) with the 'repo' scope, or unset GH_TOKEN and let "
            "the tool use `gh auth token --hostname github.iu.edu`."
            % (exc, sub.pr_url)
        )
    except (AuthFailureError, RateLimitError, NetworkError) as exc:
        return 1, str(exc)

    # Best-effort PR metadata for the report (FR-4). A 404 here just means
    # the PR number is wrong — the checkers surface that as partial.
    pr_details = {}
    try:
        pr = client.get_pr(owner, repo, number)
        pr_details = {
            "title": pr.title,
            "description": pr.body,
            "head_ref": pr.head_ref,
            "base_ref": pr.base_ref,
            "commits": pr.commits,
            "state": pr.state,
        }
    except PRNotAccessibleError:
        pass
    except (AuthFailureError, RateLimitError, NetworkError) as exc:
        return 1, str(exc)

    if args.verbose:
        print(
            "API: PR #%d %s (%s)"
            % (number, pr_details.get("title", "?"), pr_details.get("state", "?")),
            file=sys.stderr,
        )

    ctx = CheckerContext(
        client=client,
        semester_start=rubric.semester_start,
        student_name=sub.student_name,
        pr_url=sub.pr_url,
    )
    findings = [run_criterion(ctx, c) for c in rubric.criteria]

    assessment = Assessment(
        assignment=rubric.assignment,
        course=rubric.course,
        semester=rubric.semester,
        student_name=sub.student_name,
        pr_url=sub.pr_url,
        timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
        tool_version=TOOL_VERSION,
        pr_details=pr_details,
        findings=findings,
        save_json_path=args.save_json if not args.batch else None,
    )

    if args.output_format == "json" and not args.batch:
        print(json.dumps(build_json_report(assessment), indent=2))
    else:
        print(build_text_report(assessment))

    if args.save_json and not args.batch:
        pathlib.Path(args.save_json).write_text(
            json.dumps(build_json_report(assessment), indent=2), encoding="utf-8"
        )

    return 0, assessment


def _resolve_rubric(args, sub):
    """Explicit --rubric, else auto-detect by assignment id (FR-5)."""
    if args.rubric:
        return args.rubric
    if sub.assignment_id:
        found = find_rubric(sub.assignment_id, str(TOOL_DIR))
        if found:
            return found
        found = find_rubric(sub.assignment_id, "./rubrics")
        if found:
            return found
    raise RubricNotFoundError("(auto-detect)")


def _split_pr_url(url):
    m = re.match(
        r"https?://[^/]+/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)", url
    )
    if not m:
        return None, None, None
    return m.group("owner"), m.group("repo"), int(m.group("number"))


def _run_batch(args):
    """Batch mode (FR-10, EF-10, EF-11)."""
    batch_dir = pathlib.Path(args.batch)
    files = sorted(batch_dir.glob("*.html"))
    if not files:
        print("no .html submission files found in %s" % args.batch)
        return 0

    out_dir = pathlib.Path(args.output_dir) if args.output_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    failures = 0
    for f in files:
        print("=" * 72)
        print("SUBMISSION: %s" % f.name)
        print("=" * 72)
        code, result = _process_one(args, str(f))
        if code == 0:
            summary = _summary_of(result)
            results.append(
                {
                    "file": f.name,
                    "status": "processed",
                    "recommended_points": summary["recommended_points"],
                    "total_points": summary["total_points"],
                }
            )
            if out_dir:
                data = build_json_report(result)
                (out_dir / (f.stem + ".json")).write_text(
                    json.dumps(data, indent=2), encoding="utf-8"
                )
        else:
            failures += 1
            print("ERROR: %s" % result)
            results.append({"file": f.name, "status": "failed", "error": result})

    print()
    print("SUMMARY")
    print("-" * 72)
    for r in results:
        if r["status"] == "processed":
            print(
                "%-30s processed  %s/%s pts"
                % (r["file"], r["recommended_points"], r["total_points"])
            )
        else:
            print("%-30s FAILED    %s" % (r["file"], r.get("error", "")))

    if out_dir:
        (out_dir / "summary.json").write_text(
            json.dumps({"submissions": results}, indent=2), encoding="utf-8"
        )

    return 2 if failures else 0


def _summary_of(assessment):
    from report import summarize_findings

    return summarize_findings(assessment.findings)


if __name__ == "__main__":
    sys.exit(main())
