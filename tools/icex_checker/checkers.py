"""Rubric checkers for ICEX Submission Checker (FR-7, Checker Types).

Each checker is a deterministic function of evidence gathered from the
GitHub Enterprise API. No LLM inference. Checkers return a Finding:

    assessment: 'pass' | 'partial' | 'fail' | 'needs-review'
    points_recommended: float or None
    evidence: list of short strings supporting the assessment
    notes: explanation of what was checked / what the TA must verify
    ta_confirm: True when a mechanical pass also requires the TA to
        confirm a judgment item (rendered as an explicit action item)

A finding with ta_confirm=True keeps its mechanical assessment (pass) but
adds the confirmation to the report's TA action items — the pass is not
downgraded to needs-review because it would lose the points signal.
"""

import datetime
import difflib
import re

from errors import (
    AuthFailureError,
    PRNotAccessibleError,
    RateLimitError,
)
from rubric import Criterion


class Finding:
    """Outcome of running one rubric criterion."""

    def __init__(self, criterion, assessment, points_recommended, evidence, notes, ta_confirm=False):
        self.criterion_name = criterion.name
        self.checker = criterion.checker
        self.points_max = criterion.points
        self.assessment = assessment
        self.points_recommended = points_recommended
        self.evidence = evidence
        self.notes = notes
        self.ta_confirm = ta_confirm


class CheckerContext:
    """Everything a checker needs beyond its params."""

    def __init__(self, client, semester_start, student_name, pr_url):
        self.client = client
        self.semester_start = semester_start
        self.student_name = student_name
        self.pr_url = pr_url  # "https://host/owner/repo/pull/N"
        self.username = None  # IU username from Canvas filename (V1-3)
        self.roster = None    # Roster object or None (V1-1)


def _parse_pr_url(url):
    """Return (owner, repo, number) or None for a github PR URL."""
    if not url:
        return None
    m = re.match(
        r"https?://[^/]+/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)", url
    )
    if not m:
        return None
    return m.group("owner"), m.group("repo"), int(m.group("number"))


def _half(points):
    return points / 2.0


def _repo_history(ctx, criterion):
    params = criterion.params
    owner, repo, number = _parse_pr_url(ctx.pr_url) or (None, None, None)
    if not owner:
        return Finding(
            criterion, "needs-review", None,
            ["PR URL missing or malformed"],
            "Cannot identify owner/repo from the submission URL.",
        )
    try:
        repo_info = ctx.client.get_repo(owner, repo)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None,
            ["repo endpoint not accessible"],
            "Repo could not be accessed — check the URL and TA access, then "
            "review the fork history manually.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["repo endpoint failed"],
            "API auth/rate-limit issue blocked the repo query.",
        )
    try:
        dates = ctx.client.get_commit_author_dates(owner, repo)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None,
            ["commits endpoint not accessible"],
            "Commit history could not be fetched — review fork history manually.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["commits endpoint failed"],
            "API auth/rate-limit issue blocked the commit query.",
        )

    cutoff = datetime.date.fromisoformat(ctx.semester_start)
    earliest = None
    for date_str in dates:
        try:
            d = datetime.datetime.fromisoformat(
                date_str.replace("Z", "+00:00")
            ).date()
        except ValueError:
            continue
        if earliest is None or d < earliest:
            earliest = d

    evidence = [
        "repo created: %s" % repo_info.created_at,
        "commits inspected (first page, per_page=100): %d" % len(dates),
    ]
    if earliest is not None:
        evidence.append("earliest commit author date: %s" % earliest.isoformat())

    if earliest is not None and earliest < cutoff:
        return Finding(
            criterion, "pass", criterion.points,
            evidence + ["earliest commit predates semester start %s" % cutoff.isoformat()],
            "Fork/mirror history confirmed: at least one commit was authored "
            "before the semester start date.",
        )
    if not dates:
        return Finding(
            criterion, "fail", 0, evidence,
            "Repo has no commits on the default branch.",
        )
    return Finding(
        criterion, "fail", 0, evidence,
        "All commit author dates are on/after semester start "
        "(%s) — the repo does not appear to be a fork/mirror of the class "
        "repo." % cutoff.isoformat(),
    )


def _pr_exists_with_comment(ctx, criterion):
    params = criterion.params
    min_len = int(params.get("min_comment_length", 10) or 10)
    owner, repo, number = _parse_pr_url(ctx.pr_url) or (None, None, None)
    if not owner:
        return Finding(
            criterion, "needs-review", None,
            ["PR URL missing or malformed"],
            "Cannot identify the pull request from the submission URL.",
        )
    try:
        pr = ctx.client.get_pr(owner, repo, number)
    except PRNotAccessibleError:
        return Finding(
            criterion, "fail", 0,
            ["PR endpoint returned 404/403"],
            "Pull request does not exist or is not accessible.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["PR endpoint failed auth/rate-limit"],
            "API auth/rate-limit issue blocked the PR query.",
        )

    body_len = len((pr.body or "").strip())
    evidence = [
        "PR #%d: %s" % (pr.number, pr.title),
        "state: %s" % pr.state,
        "body length: %d chars" % body_len,
        "body excerpt: %s" % _truncate(pr.body, 200),
    ]
    if body_len >= min_len:
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "PR exists with a substantive description (>= %d chars). "
            "TA must judge whether the comment is well-written." % min_len,
            ta_confirm=True,
        )
    return Finding(
        criterion, "partial", _half(criterion.points), evidence,
        "PR exists but its description is empty or shorter than the "
        "%d-char threshold — TA should assess partial credit." % min_len,
    )


def _pr_url_valid(ctx, criterion):
    owner, repo, number = _parse_pr_url(ctx.pr_url) or (None, None, None)
    if not owner:
        return Finding(
            criterion, "fail", 0,
            ["URL does not parse as github.com owner/repo/pull/N"],
            "PR URL is not a valid pull-request URL.",
        )
    try:
        pr = ctx.client.get_pr(owner, repo, number)
    except PRNotAccessibleError:
        # Maybe the repo exists but the PR number is wrong.
        try:
            ctx.client.get_repo(owner, repo)
        except PRNotAccessibleError:
            return Finding(
                criterion, "fail", 0,
                ["repo and PR endpoints both returned 404/403"],
                "The URL is completely inaccessible (repo not found or no "
                "access) — likely not a real submission.",
            )
        except (AuthFailureError, RateLimitError):
            return Finding(
                criterion, "needs-review", None,
                ["repo endpoint failed auth/rate-limit"],
                "API issue blocked repo verification.",
            )
        return Finding(
            criterion, "partial", _half(criterion.points),
            ["repo exists, PR endpoint returned 404/403"],
            "URL lands on the student's repo but the PR number does not "
            "resolve — TA should check which PR was actually opened.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["PR endpoint failed auth/rate-limit"],
            "API auth/rate-limit issue blocked PR verification.",
        )

    evidence = [
        "PR #%d resolves (HTTP 200)" % pr.number,
        "repo owner from URL: %s" % owner,
    ]
    if ctx.student_name:
        if not _owner_matches_student(owner, ctx.student_name):
            return Finding(
                criterion, "needs-review", None, evidence,
                "PR resolves but repo owner '%s' does not obviously match "
                "the submitting student '%s' — TA must verify ownership."
                % (owner, ctx.student_name),
                ta_confirm=True,
            )
        evidence.append("owner matches student name: %s" % owner)
    else:
        evidence.append("student name unavailable from title — ownership NOT verified")
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "PR resolves. Student name was not parsed from the submission "
            "title, so ownership was NOT mechanically verified — TA should "
            "confirm the repo belongs to the student.",
            ta_confirm=True,
        )
    return Finding(
        criterion, "pass", criterion.points, evidence,
        "URL resolves to a real PR in the student's own repository.",
    )


def _valid_student_repo(ctx, criterion):
    params = criterion.params
    expected_pattern = params.get("expected_repo_pattern", "")
    github_host = params.get("github_host", "github.iu.edu")
    owner, repo, number = _parse_pr_url(ctx.pr_url) or (None, None, None)
    if not owner:
        return Finding(
            criterion, "fail", 0,
            ["cannot parse owner/repo from URL"],
            "Cannot identify the repository from the submission URL.",
        )
    if "github.iu.edu" not in ctx.pr_url and github_host not in ctx.pr_url:
        return Finding(
            criterion, "fail", 0,
            ["URL host does not match %s" % github_host],
            "Repository is not hosted on %s." % github_host,
        )
    try:
        repo_info = ctx.client.get_repo(owner, repo)
    except PRNotAccessibleError:
        return Finding(
            criterion, "fail", 0,
            ["repo endpoint returned 404/403"],
            "Repository does not exist or is not accessible.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["repo endpoint failed auth/rate-limit"],
            "API auth/rate-limit issue blocked repo verification.",
        )

    evidence = [
        "repo full name: %s" % repo_info.full_name,
        "repo created: %s" % repo_info.created_at,
        "owner login: %s" % repo_info.owner_login,
        "repo URL: %s" % repo_info.html_url,
    ]
    name = repo_info.name or ""
    if expected_pattern:
        if name.lower() == expected_pattern.lower():
            pass  # exact match (case-insensitive)
        elif _strip_seps(name) == _strip_seps(expected_pattern) or (
            expected_pattern.lower() in name.lower()
        ):
            return Finding(
                criterion, "partial", _half(criterion.points), evidence,
                "Repo name '%s' is a close match to the expected pattern "
                "'%s' (separator/order variant) — TA should confirm it is "
                "the course repo." % (name, expected_pattern),
            )
        else:
            return Finding(
                criterion, "fail", 0, evidence,
                "Repo name '%s' does not match the expected course pattern "
                "'%s'." % (name, expected_pattern),
            )

    if repo_info.owner_login and _looks_like_service_account(repo_info.owner_login):
        return Finding(
            criterion, "needs-review", None, evidence,
            "Repo owner '%s' looks like a shared/service account rather "
            "than a student — TA should verify." % repo_info.owner_login,
            ta_confirm=True,
        )
    return Finding(
        criterion, "pass", criterion.points, evidence,
        "Repo exists on %s, name matches the course pattern, and the owner "
        "is present in the URL path." % github_host,
    )


def _strip_seps(s):
    """Lowercase and strip separators for close-match comparison."""
    return s.lower().replace("_", "").replace("-", "").replace(".", "")


def _owner_matches_student(owner, student_name):
    """Deterministic owner-vs-name heuristic (FR-7 pr_url_valid).

    Returns True when the repo owner plausibly corresponds to the student
    name: owner is a substring of the compacted name, any name token
    (>=3 chars) appears in the owner, or owner is initials+lastname
    (e.g. 'jdoe' for 'Jane Doe'). Returns False otherwise. Ownership
    confirmation remains TA judgment; this only gates the needs-review flag.
    """
    if not owner or not student_name:
        return False
    owner_l = owner.lower()
    name_l = student_name.lower()
    tokens = [t for t in re.split(r"[\s._-]+", name_l) if t]
    if not tokens:
        return False
    if owner_l in name_l.replace(" ", ""):
        return True
    for t in tokens:
        if len(t) >= 3 and t in owner_l:
            return True
    initials = "".join(t[0] for t in tokens)
    if owner_l == initials + tokens[-1]:
        return True
    if owner_l == initials:
        return True
    return False


def _looks_like_service_account(login):
    """Deterministic keyword check for shared/service account logins.

    Only flags obvious non-student accounts; ownership confirmation is
    always TA judgment. github.iu.edu usernames are typically IU NetIDs.
    """
    service_words = (
        "admin", "service", "team", "root", "system", "ithelp",
        "helpdesk", "infrastructure", "github-actions", "bot",
        "instructor", "teaching", "course-",
    )
    login_lower = login.lower()
    return any(w in login_lower for w in service_words)


def _diff_content_check(ctx, criterion):
    params = criterion.params
    target_file = params.get("target_file", "")
    must_contain = params.get("must_contain_modified", "")
    must_not_contain = params.get("must_not_contain", "")
    owner, repo, number = _parse_pr_url(ctx.pr_url) or (None, None, None)
    if not owner:
        return Finding(
            criterion, "needs-review", None,
            ["cannot parse PR URL"],
            "Cannot identify the pull request from the submission URL.",
        )
    try:
        diff = ctx.client.get_pr_diff(owner, repo, number)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None,
            ["diff endpoint returned 404/403"],
            "Diff could not be fetched — TA should review the PR directly.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["diff endpoint failed auth/rate-limit"],
            "API auth/rate-limit issue blocked the diff query.",
        )

    files = _files_in_diff(diff)
    evidence = ["files in diff: %s" % (", ".join(files) if files else "(empty diff)")]
    if not files:
        return Finding(
            criterion, "fail", 0, evidence,
            "Diff is empty or unparseable.",
        )
    if target_file not in files:
        return Finding(
            criterion, "fail", 0, evidence,
            "Target file '%s' is not in the diff." % target_file,
        )

    added_lines = _added_lines_for(diff, target_file)
    evidence.append(
        "added lines in %s:\n%s" % (target_file, _truncate("\n".join(added_lines), 500))
    )

    contains_ok = not must_contain or any(must_contain in line for line in added_lines)
    not_contains_ok = not must_not_contain or not any(
        must_not_contain in line for line in added_lines
    )

    if contains_ok and not_contains_ok:
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "Target file modified; '%s' present in added lines; '%s' "
            "absent from added lines. TA must confirm the replacement is "
            "the student's actual name." % (must_contain, must_not_contain),
            ta_confirm=True,
        )
    return Finding(
        criterion, "partial", _half(criterion.points), evidence,
        "Target file is in the diff but content checks partially fail "
        "(printf modified: %s; '%s' still present in added lines: %s). "
        "TA should judge partial credit." % (contains_ok, must_not_contain, not not_contains_ok),
    )


def _files_in_diff(diff):
    files = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:])
    return files


def _added_lines_for(diff, target_file):
    """Return lines added to target_file in the diff (hunks after the
    '+++ b/<file>' header). Only '+' lines (excluding '+++') are added
    lines; '-' lines are the old content and must NOT be checked.
    """
    lines = diff.splitlines()
    in_target = False
    added = []
    for line in lines:
        if line.startswith("+++ b/"):
            in_target = line[6:] == target_file
            continue
        if line.startswith("diff --git "):
            in_target = False
            continue
        if not in_target:
            continue
        if line.startswith("+++"):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return added


def _truncate(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _manual_review(ctx, criterion):
    """Placeholder checker for criteria that require human judgment (EF-9).

    Returns needs-review with the criterion's label (from params) as the
    note. Used for AG scores, handgrading, and any criterion the tool
    cannot check mechanically. The TA enters the value manually.
    """
    label = criterion.params.get("label", "TA review required")
    return Finding(
        criterion, "needs-review", None,
        ["manual review — tool cannot check this criterion"],
        "%s" % label,
    )


def _pattern_count(ctx, criterion):
    """Count regex pattern occurrences in added lines of a target file.

    Params:
        target_file: full repo path (e.g. "exercises/wk1/PASN01/arttree.c")
        pattern: regex pattern to count in added lines
        expected_count: the count to compare against
        comparison: "exact" (default), "at_least", or "at_most"

    Assessment:
        pass: count meets the comparison condition
        fail: count does not match, or target file not in diff
        needs-review: API error prevents fetching the diff
    """
    params = criterion.params
    target_file = params.get("target_file", "")
    pattern = params.get("pattern", "")
    expected = int(params.get("expected_count", 0))
    comparison = params.get("comparison", "exact")

    owner, repo, number = _parse_pr_url(ctx.pr_url) or (None, None, None)
    if not owner:
        return Finding(
            criterion, "needs-review", None,
            ["cannot parse PR URL"],
            "Cannot identify the pull request from the submission URL.",
        )
    try:
        diff = ctx.client.get_pr_diff(owner, repo, number)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None,
            ["diff endpoint returned 404/403"],
            "Diff could not be fetched — TA should review the PR directly.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["diff endpoint failed auth/rate-limit"],
            "API auth/rate-limit issue blocked the diff query.",
        )

    files = _files_in_diff(diff)
    evidence = ["files in diff: %s" % (", ".join(files) if files else "(empty diff)")]
    if not files:
        return Finding(criterion, "fail", 0, evidence, "Diff is empty or unparseable.")
    if target_file not in files:
        return Finding(
            criterion, "fail", 0, evidence,
            "Target file '%s' is not in the diff." % target_file,
        )

    added_lines = _added_lines_for(diff, target_file)
    count = sum(len(re.findall(pattern, line)) for line in added_lines)
    evidence.append("pattern %r found %d time(s) in added lines" % (pattern, count))

    if comparison == "at_least":
        ok = count >= expected
        comp_desc = "at least %d" % expected
    elif comparison == "at_most":
        ok = count <= expected
        comp_desc = "at most %d" % expected
    else:
        ok = count == expected
        comp_desc = "exactly %d" % expected

    if ok:
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "Pattern count meets requirement (%s, found %d)." % (comp_desc, count),
        )
    return Finding(
        criterion, "fail", 0, evidence,
        "Pattern count does not meet requirement (expected %s, found %d)." % (comp_desc, count),
    )


def _commit_author_check(ctx, criterion):
    """Verify the submitting student contributed commits to the PR (V1-2).

    Attribution chain: Canvas filename -> IU username -> roster lookup
    (SE1: IU username IS the github.iu.edu login) -> compare against
    commit author logins from the PR commits API.

    Degradation (EF-12/EF-13): without a usable roster or username, list
    the commit authors as evidence and return needs-review. Never guesses.
    """
    owner, repo, number = _parse_pr_url(ctx.pr_url) or (None, None, None)
    if not owner:
        return Finding(
            criterion, "needs-review", None,
            ["cannot parse PR URL"],
            "Cannot identify the pull request from the submission URL.",
        )
    try:
        logins = ctx.client.get_pr_commit_logins(owner, repo, number)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None,
            ["PR commits endpoint returned 404/403"],
            "PR commits could not be fetched — TA should verify attribution manually.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["PR commits endpoint failed auth/rate-limit"],
            "API auth/rate-limit issue blocked the commit query.",
        )

    unique_logins = sorted(set(logins))
    evidence = ["commit authors: %s" % (", ".join(unique_logins) if unique_logins else "(none)")]

    if not ctx.username:
        return Finding(
            criterion, "needs-review", None, evidence,
            "No IU username available (unrecognized submission filename). "
            "TA should verify the submitter's identity against the commit "
            "authors listed above.",
        )
    if ctx.roster is None:
        return Finding(
            criterion, "needs-review", None, evidence,
            "No roster available. TA should verify manually that the "
            "submitter appears among the commit authors above.",
        )
    if ctx.roster.find_team(ctx.username) is None:
        return Finding(
            criterion, "needs-review", None, evidence,
            "Submitter '%s' is not in the roster. TA should verify the "
            "username and the commit authors above." % ctx.username,
        )

    evidence.append("submitter (from filename, in roster): %s" % ctx.username)
    if ctx.username in logins:
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "Submitting student appears among the PR commit authors.",
        )
    return Finding(
        criterion, "fail", 0, evidence,
        "Submitting student '%s' is NOT among the PR commit authors — "
        "likely a wrong submission (e.g. the PR they approved rather than "
        "created). TA should confirm." % ctx.username,
        ta_confirm=True,
    )


CHECKERS = {
    "repo_history": _repo_history,
    "pr_exists_with_comment": _pr_exists_with_comment,
    "pr_url_valid": _pr_url_valid,
    "valid_student_repo": _valid_student_repo,
    "diff_content_check": _diff_content_check,
    "manual_review": _manual_review,
    "pattern_count": _pattern_count,
    "commit_author_check": _commit_author_check,
}


def run_criterion(ctx, criterion):
    """Run the checker for a criterion (FR-7). Unknown checker types are
    reported as needs-review without aborting (EF-9)."""
    checker = CHECKERS.get(criterion.checker)
    if checker is None:
        return Finding(
            criterion, "needs-review", 0, [],
            "unknown checker type '%s' for criterion '%s' — no automated "
            "check available; TA review required." % (criterion.checker, criterion.name),
        )
    return checker(ctx, criterion)
