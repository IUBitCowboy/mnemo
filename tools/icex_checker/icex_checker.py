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
from roster import load_roster as load_roster_file
from rubric import (
    RubricNotFoundError,
    RubricParseError,
    find_rubric,
    infer_course_from_repo,
    load_rubric,
)

TOOL_VERSION = "1.1.1"
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

# MoJ (FA26 greenfield): team documents, EngLog entries, and grad memos
# are submitted as direct GitHub blob URLs, not PR URLs. The submission
# parser accepts both forms; checkers dispatch on the parsed kind.
_BLOB_URL_RE = re.compile(
    r"https?://(?P<host>[^/\"'\s<]+)/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/blob/(?P<tail>[^\"'\s<>]+)"
)

# A-line cycle closes (A_MJ02/A_MJ04) submit ONE GitHub Release URL —
# the release (tag + body) is the deliverable. /releases/tag/<tag>;
# backslash-escaped tags are not supported (tags here are plain).
_RELEASE_URL_RE = re.compile(
    r"https?://(?P<host>[^/\"'\s<]+)/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/releases/tag/(?P<tag>[^/?#\"'\s<>]+)"
)

# Canvas titles in the MoJ weeks: 'Week 12 | A_MJ05 - Ethics Opener'
# (pipe form, no colon after the assignment, space after Week). The
# assignment token may itself carry spaces ('Team PR') — the split is
# the first ' - '.
_MOJ_TITLE_RE = re.compile(
    r"Week\s*(?P<week>\d\d?)\s*\|\s*(?P<assignment>[A-Za-z][A-Za-z0-9_.()\- ]*?)\s*-\s*(?P<name>.+)"
)

_TITLE_RE = re.compile(
    r"Week(?P<week>\d\d?)\s*-\s*(?P<assignment>ICEX\d+)\s*:\s*(?P<name>.+)"
)

# Canvas downloads submissions as {username}[_LATE]_{canvas_id}_link.html
# (V1-3). Example: aldhaherirashed_LATE_6789124_link.html
_CANVAS_FILENAME_RE = re.compile(r"^(?P<user>.+?)(?:_(?P<late>LATE))?_(\d+)_link\.html$", re.IGNORECASE)


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
        self.username = None
        self.is_late = False


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
    _parse_filename(path, sub)

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
    """Parse the assignment identity from the <title> tag (FR-6).

    Two title shapes: the C291 'WeekNN - ICEXNN: Student Name' form and
    the MoJ 'Week NN | ASSIGNMENT - Name' form (FA26 greenfield).
    """
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return
    title = m.group(1).strip()
    t = _TITLE_RE.match(title)
    if not t:
        t = _MOJ_TITLE_RE.match(title)
        if not t:
            return
    sub.week = t.group("week")
    sub.assignment_id = t.group("assignment")
    sub.student_name = t.group("name").strip()
    sub.title_parsed = True


def _parse_filename(path, sub):
    """Parse IU username and LATE flag from the Canvas download filename (V1-3).

    Pattern: {username}[_LATE]_{canvas_id}_link.html. Unrecognized names
    degrade gracefully (EF-13): username stays None, is_late stays False.
    """
    name = pathlib.Path(path).name
    m = _CANVAS_FILENAME_RE.match(name)
    if not m:
        return
    sub.username = m.group("user")
    sub.is_late = m.group("late") is not None


def _is_submission_url(url):
    """True for a pull, blob, or release URL (MoJ accepts all forms)."""
    return (_PR_URL_RE.match(url) is not None
            or _BLOB_URL_RE.match(url) is not None
            or _RELEASE_URL_RE.match(url) is not None)


def _is_pr_url(url):
    return _is_submission_url(url)


def validate_pr_url(url, github_host):
    """Validate a PR or blob URL (FR-2; MoJ widens to blob form).

    Returns (ok, reason). ok is True for a valid HTTPS github host PR
    URL (or blob URL); otherwise False with a human-readable reason.
    """
    if not url:
        return False, "PR URL is empty"
    m = _PR_URL_RE.match(url)
    if not m:
        b = _BLOB_URL_RE.match(url)
        if b:
            if b.group("host") != github_host:
                return False, "PR URL points to %s, expected %s" % (
                    b.group("host"),
                    github_host,
                )
            if not url.startswith("https://"):
                return False, "PR URL must use HTTPS scheme"
            return True, None
        r = _RELEASE_URL_RE.match(url)
        if r:
            if r.group("host") != github_host:
                return False, "Release URL points to %s, expected %s" % (
                    r.group("host"),
                    github_host,
                )
            return True, None
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
    parser.add_argument(
        "--roster",
        help="Path to the team roster CSV (Team,TA,IU Username). Overrides the "
             "rubric-declared roster_file. The roster is a FERPA sidecar that "
             "lives on the instructor's OneDrive share, next to the submissions.",
    )
    parser.add_argument(
        "--teams",
        help="Comma-separated team numbers/ids to grade ('7' or '1,7,10' or "
             "'SE_TEAM07'). Requires --roster (or the rubric's roster_file) "
             "to resolve membership. Batch mode processes only those teams' "
             "submitters and the summary groups each team: the PR score plus "
             "per-student wall scores with the late adjustments.",
    )
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
        "--ag-score",
        type=int,
        metavar="N",
        help="AG score to include in the report (single-submission mode only)",
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
        "--html-out",
        help="Batch mode: write the TA HTML bundle (report.html index + "
        "per-submission pages) under this directory tree. Defaults to "
        "the batch directory's parent (the submissions root). Pass "
        "'--html-out off' to disable.",
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
        if args.ag_score is not None:
            print("warning: --ag-score is ignored in batch mode (EF-16)", file=sys.stderr)
        return _run_batch(args)

    if not args.submission:
        print("submission file required (or use --batch)", file=sys.stderr)
        return 1

    code, result = _process_one(args, args.submission)
    if code != 0:
        print(result, file=sys.stderr)
    elif result is None:
        return 0  # team-filter skip — already reported on stderr
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
    except OSError as e:
        return 1, (
            "submission file unreadable (%s): %s — retry in a moment; cloud "
            "hygiene may still be downloading it." % (type(e).__name__, e)
        )

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

    # EF-15: --ag-score out of range is fatal when the rubric defines AG.
    if args.ag_score is not None and rubric.ag_max_points is not None:
        if args.ag_score < 0 or args.ag_score > rubric.ag_max_points:
            return 1, "AG score %d is out of range (0-%d)" % (
                args.ag_score,
                rubric.ag_max_points,
            )

    roster_obj = None
    roster_path = args.roster or rubric.roster_file
    if roster_path:
        roster_obj = load_roster_file(roster_path)
        if roster_obj is None:
            print(
                "warning: roster file %s missing or unreadable — roster-"
                "dependent checks will run evidence-only (EF-12)" % roster_path,
                file=sys.stderr,
            )

    client = GitHubClient(token=token, host=args.github_host)
    # Attribution canonicalization: Canvas filenames carry the student's
    # display-name prefix (bowmancole); the roster carries IU netids
    # (ctbowman) which match github.iu.edu commit logins. Resolve the
    # filename token to the netid when a Canvas Name column exists.
    roster_username = sub.username
    if roster_obj is not None and sub.username:
        roster_username = roster_obj.canonical_username(sub.username)
        if roster_username != sub.username:
            print(
                "info: submission filename '%s' mapped to roster username "
                "'%s'" % (sub.username, roster_username),
                file=sys.stderr,
            )
        if getattr(args, "teams", None):
            requested, _unresolved = _resolve_requested_teams(args, roster_obj)
            submitter_team = roster_obj.find_team(roster_username)
            if requested and submitter_team not in requested:
                print(
                    "skipped: submitter %s is on team %s, not among the "
                    "requested teams (%s)"
                    % (roster_username, submitter_team or "(unknown)",
                       ", ".join(requested)),
                    file=sys.stderr,
                )
                return 0, None
    owner, repo, number = _split_pr_url(sub.pr_url)
    is_blob = number is None  # blob-URL submissions (EngLog, AGR memos):
    # no PR exists; the checkers fetch the blob file themselves.

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
    # Blob submissions carry no pull request; skip the fetch entirely
    # (the file itself is the artifact and the blob checkers read it).
    pr_details = {}
    if not is_blob:
        try:
            pr = client.get_pr(owner, repo, number)
            pr_details = {
                "title": pr.title,
                "description": pr.body,
                "head_ref": pr.head_ref,
                "base_ref": pr.base_ref,
                "commits": pr.commits,
                "state": pr.state,
                "merged": pr.merged,
            }
        except PRNotAccessibleError:
            pass
        except (AuthFailureError, RateLimitError, NetworkError) as exc:
            return 1, str(exc)

    if args.verbose:
        if is_blob:
            _m = re.search(r"/blob/[^/]+/(.+)$", sub.pr_url or "")
            print("API: blob %s/%s  path %s" % (
                owner, repo, _m.group(1) if _m else "?"), file=sys.stderr)
        else:
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
    ctx.username = roster_username
    ctx.roster = roster_obj
    if roster_obj is not None and roster_path:
        ctx.roster_path = roster_path  # sidecars (walls, times) live near it
    if rubric.ownership_check:
        # Default rubric-level ownership mode (V1-1) unless a criterion
        # overrides via its own params.
        ctx.ownership_check = rubric.ownership_check
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
        is_late=sub.is_late,
        ag_max_points=rubric.ag_max_points,
        handgrading_points=rubric.handgrading_points,
        ag_score=args.ag_score if not args.batch else None,
        canvas_points=rubric.canvas_points,
        collaboration_coefficient=rubric.collaboration_coefficient,
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
    """Explicit --rubric, else auto-detect by assignment id (FR-5).

    Issue #2: when the submission's repo name identifies the course
    (fa26_c291 -> C291), course-aware auto-detect disambiguates
    same-named assignments across classes.
    """
    if args.rubric:
        return args.rubric
    if sub.assignment_id:
        repo = None
        _owner, repo, _num = _split_pr_url(sub.pr_url)
        course = infer_course_from_repo(repo) if repo else None
        found = find_rubric(sub.assignment_id, str(TOOL_DIR), course=course)
        if found:
            return found
        found = find_rubric(sub.assignment_id, "./rubrics", course=course)
        if found:
            return found
    raise RubricNotFoundError("(auto-detect)")


def _split_pr_url(url):
    """Extract owner/repo/number from a pull URL; blob and release URLs
    give (owner, repo, None) — used only for course inference (MoJ)."""
    m = re.match(
        r"https?://[^/]+/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)", url
    )
    if not m:
        m = _BLOB_URL_RE.match(url or "")
        if not m:
            r = _RELEASE_URL_RE.match(url or "")
            if not r:
                return None, None, None
            return r.group("owner"), r.group("repo"), None
        return m.group("owner"), m.group("repo"), None
    return m.group("owner"), m.group("repo"), int(m.group("number"))


def _write_submission_report(out_dir, stem, assessment, args):
    """Write one submission's report file, honoring --output-format.

    Issue #7: batch mode previously ignored --output-format for the
    per-submission files and always wrote JSON. Now text is text.
    """
    if getattr(args, "output_format", "text") == "json":
        data = build_json_report(assessment)
        (out_dir / (stem + ".json")).write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
    else:
        (out_dir / (stem + ".txt")).write_text(
            build_text_report(assessment), encoding="utf-8"
        )


def _resolve_requested_teams(args, roster_obj):
    """--teams tokens -> roster team keys (None = no filter)."""
    if not getattr(args, "teams", None):
        return None, None
    tokens = [t.strip() for t in str(args.teams).split(",") if t.strip()]
    if roster_obj is None:
        return None, tokens
    requested = []
    unresolved = []
    for tok in tokens:
        raw = roster_obj.resolve_team(tok)
        if raw and raw not in requested:
            requested.append(raw)
        elif not raw:
            unresolved.append(tok)
    return requested, unresolved


def _wall_projections_from(assessment):
    """Per-member wall scores from a run's pr_commits_by_wall finding.

    Returns ({member: {"MJ01": "10", ...}}, {member: late}) or (None, {}).
    """
    proj = {}
    late = set()
    for f in getattr(assessment, "findings", []) or []:
        if getattr(f, "checker", None) != "pr_commits_by_wall":
            continue
        for e in getattr(f, "evidence", []) or []:
            m = re.match(r"^project ([^:]+): (.+)$", e)
            if m:
                member = m.group(1).strip()
                vals = {}
                for pair in m.group(2).split(","):
                    k, _sep, v = pair.strip().partition("=")
                    if _sep:
                        vals[k.strip()] = v.strip()
                if vals:
                    proj[member] = vals
                continue
            m = re.match(r"^([^:]+): \d+ commit\(s\) AFTER", e)
            if m:
                late.add(m.group(1).strip())
    return (proj or None), late


def _team_rollup(results):
    """Group processed batch results by team for the team results print.

    Each entry: {"team": ..., "prs": [{"url", "recommended", "total"}...],
    "students": {member: {"MJ01": ..., "MJ02": ...}}, "late": set}
    """
    groups = {}
    for r in results:
        if r.get("status") != "processed" or not r.get("team"):
            continue
        g = groups.setdefault(r["team"], {"prs": {}, "students": {}, "late": set()})
        url = r.get("pr_url") or "(no PR URL)"
        entry = g["prs"].setdefault(url, {"recommended": r["recommended_points"],
                                          "total": r["total_points"]})
        proj, late = _wall_projections_from(r.get("_assessment"))
        if proj:
            g["students"].update(proj)
        g["late"] |= late
    return groups


def _print_team_results(requested, groups):
    """The TA-facing team block: PR score + per-student wall scores."""
    if not groups:
        return
    hdr = ", ".join(requested) if requested else "all roster teams"
    print()
    print("TEAM RESULTS (%s)" % hdr)
    print("-" * 72)
    for team in sorted(groups):
        g = groups[team]
        print("%s" % team)
        for url, entry in sorted(g["prs"].items()):
            print("  url %-53s -> %s/%s pts (projected, TA subtracts)" % (
                url, entry["recommended"], entry["total"]))
        if g["students"]:
            cols = sorted({k for v in g["students"].values() for k in v})
            for member in sorted(g["students"]):
                marks = " " if member not in g["late"] else "*"
                cells = " ".join(
                    "%s=%s%s" % (col, g["students"][member].get(col, "?"), marks)
                    for col in cols)
                print("    %-16s %s" % (member, cells))
            print("    (* = commits after the wall — 8.5 late adjustment;"
                  " sha list in the per-file report)")
        print()


def _rubric_roster_path(args, sample_file):
    """The rubric-declared roster path for --teams when --roster is absent."""
    try:
        sub = parse_submission(sample_file)
        rubric_path = _resolve_rubric(args, sub)
        rubric = load_rubric(rubric_path)
        return (rubric.roster_file or None) if rubric else None
    except Exception:
        return None


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

    # --teams: resolve the requested roster teams, then filter each
    # submission by its submitter's team before processing.
    # The roster also loads for the HTML bundle (membership mapping)
    # whenever a roster path is available.
    roster_obj = None
    _need_roster = (getattr(args, "teams", None)
                    or (getattr(args, "html_out", None)
                        and args.html_out != "off"))
    roster_path = None
    if _need_roster:
        roster_path = args.roster or _rubric_roster_path(args, str(files[0]))
        if not roster_path:
            if getattr(args, "teams", None):
                print(
                    "--teams needs team membership: pass --roster (or make the "
                    "rubric's roster_file resolvable for this run).",
                    file=sys.stderr,
                )
                return 1
            print(
                "note: no roster available — HTML bundle will not map "
                "submitters to teams/TA (pass --roster).",
                file=sys.stderr,
            )
        else:
            roster_obj = load_roster_file(roster_path)
            if roster_obj is None:
                print(
                    "roster file %s unreadable — team mapping unavailable."
                    % roster_path,
                    file=sys.stderr,
                )
                return 1
    requested, unresolved = _resolve_requested_teams(args, roster_obj)
    if unresolved:
        print(
            "warning: --teams token(s) not found in the roster: %s"
            % ", ".join(unresolved),
            file=sys.stderr,
        )

    results = []
    skipped = []
    failures = 0
    for f in files:
        team_key = None
        submitter = None
        pr_url = None
        if roster_obj is not None:
            # Team membership rides the filename's canvas-name prefix —
            # no file read (which would force OneDrive hydration of all
            # 48 submissions just to find the requested teams' files).
            submitter = f.stem.split("_")[0]
            canon = (
                roster_obj.canonical_username(submitter) if submitter else None
            )
            team_key = roster_obj.find_team(canon) if canon else None
            if requested is not None and team_key not in (requested or []):
                skipped.append({
                    "file": f.name,
                    "team": team_key or "(unknown team)",
                    "submitter": canon if submitter else "(unparsed)",
                })
                continue
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
                    "team": team_key,
                    "pr_url": getattr(result, "pr_url", None) or pr_url,
                    "_assessment": result,
                }
            )
            if out_dir:
                _write_submission_report(out_dir, f.stem, result, args)
        else:
            failures += 1
            print("ERROR: %s" % result)
            results.append({"file": f.name, "status": "failed", "error": result})
            # Issue #4: every submission gets an individual output file,
            # including failures (README contract).
            if out_dir:
                (out_dir / (f.stem + ".json")).write_text(
                    json.dumps(
                        {
                            "tool": "icex_checker",
                            "tool_version": TOOL_VERSION,
                            "file": f.name,
                            "status": "failed",
                            "error": str(result),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

    print()
    print("SUMMARY")
    print("-" * 72)
    for s in skipped:
        print(
            "%-30s skipped   (submitter %s, team %s not requested)"
            % (s["file"], s["submitter"], s["team"])
        )
    for r in results:
        if r["status"] == "processed":
            print(
                "%-30s processed  %s/%s pts"
                % (r["file"], r["recommended_points"], r["total_points"])
            )
        else:
            print("%-30s FAILED    %s" % (r["file"], r.get("error", "")))

    groups = _team_rollup(results)
    _print_team_results(requested, groups)

    if out_dir:
        summary_payload = {
            "submissions": [
                dict(
                    {k: v for k, v in r.items()
                     if not k.startswith("_") and k != "pr_url"},
                    pr_url=r.get("pr_url"),
                )
                for r in results
            ]
        }
        if groups:
            summary_payload["teams"] = [
                {
                    "team": team,
                    "prs": [
                        {"url": url, "recommended_points": entry["recommended"],
                         "total_points": entry["total"]}
                        for url, entry in sorted(g["prs"].items())
                    ],
                    "students": g["students"],
                    "late_members": sorted(g["late"]),
                }
                for team, g in sorted(groups.items())
            ]
        (out_dir / "summary.json").write_text(
            json.dumps(summary_payload, indent=2), encoding="utf-8"
        )

    html_out = getattr(args, "html_out", None)
    if html_out is not None and html_out != "off":
        from report_html import emit_lane

        def _html_root_default(batch):
            # Kurt's submissions tree nests the Canvas download lanes
            # under submissions/canvas/ — walk up to the share root
            # (the directory literally named "submissions") so the
            # report bundle always lands where the TAs' share starts.
            here = pathlib.Path(batch).resolve()
            for anc in [here] + list(here.parents):
                if anc.name == "submissions":
                    return anc
            return here.parent

        rubric_path = args.rubric or _resolve_rubric(args, files[0])
        rubric = load_rubric(rubric_path)
        html_root = pathlib.Path(
            html_out) if html_out else _html_root_default(batch_dir)
        run_ts = datetime.datetime.now().astimezone().strftime(
            "%Y-%m-%d %H:%M %Z")
        try:
            manifest, index_path = emit_lane(
                batch_dir, results, html_root, run_ts, rubric, roster_obj,
                filtered_teams=requested, roster_csv=roster_path,
            )
            print()
            print("HTML: index  %s" % index_path)
            print(
                "HTML: lane    %s (%d pages, %d exception(s))"
                % (manifest["lane_dir"],
                   len(manifest["entries"]),
                   len(manifest["exceptions"])),
            )
        except OSError as e:
            print("HTML: emission failed (%s)" % e, file=sys.stderr)

    return 2 if failures else 0


def _summary_of(assessment):
    from report import summarize_findings

    return summarize_findings(assessment.findings)


if __name__ == "__main__":
    sys.exit(main())
