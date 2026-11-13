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

import csv
import datetime
import difflib
import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from errors import (
    AuthFailureError,
    PRNotAccessibleError,
    RateLimitError,
    SubmissionNotFoundError,
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
        self.roster_path: Optional[str] = None  # --roster path; sidecars near it
        self.ownership_check = None  # rubric-level default (V1-1)


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
    ownership_check = (criterion.params or {}).get(
        "ownership_check", getattr(ctx, "ownership_check", None) or "student"
    )

    if ownership_check == "none":
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "URL resolves to a real PR. Ownership check disabled by rubric.",
        )

    if ownership_check == "team":
        evidence.append("ownership_check: team")
        if ctx.username and ctx.roster is not None:
            team = ctx.roster.find_team(ctx.username)
            if team is None:
                return Finding(
                    criterion, "needs-review", None, evidence,
                    "Submitter '%s' is not in the roster — TA should verify "
                    "membership before confirming." % ctx.username,
                    ta_confirm=True,
                )
            evidence.append("submitter on team: %s" % team)
            return Finding(
                criterion, "pass", criterion.points, evidence,
                "URL resolves to a PR in the team repo; submitter is a "
                "confirmed roster member of %s." % team,
            )
        return Finding(
            criterion, "needs-review", None, evidence,
            "URL resolves to a PR in the team repo. No roster/username "
            "available, so membership could not be verified — TA should "
            "confirm the submitter is on the team (evidence-only mode, EF-12).",
        )

    # ownership_check == "student" (default): owner should match the submitter
    # Issue #6 fix: when the Canvas-filename IU username is available,
    # compare it deterministically against the repo owner. This replaces
    # the fragile display-name heuristic and kills the intermittency.
    if getattr(ctx, "username", None):
        if owner == ctx.username:
            evidence.append("owner matches IU username: %s" % owner)
            return Finding(
                criterion, "pass", criterion.points, evidence,
                "URL resolves to a real PR in the student's own repository "
                "(owner matches the Canvas-filename IU username).",
            )
        return Finding(
            criterion, "needs-review", None, evidence,
            "Repo owner '%s' does not match submitter's IU username '%s' — "
            "TA must verify the student actually owns this repository "
            "(github.iu.edu logins do not always match IU usernames)."
            % (owner, ctx.username),
            ta_confirm=True,
        )
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
        matched_regex = None
        try:
            matched_regex = re.fullmatch(expected_pattern, name, re.IGNORECASE)
        except re.error:
            matched_regex = None  # not a valid regex: treat as literal
        if name.lower() == expected_pattern.lower():
            pass  # exact match (case-insensitive)
        elif matched_regex is not None:
            # Regex patterns (e.g. 'fa26-team-\\d+-moj') full-match first;
            # literal templates are unaffected — fullmatch of a literal
            # on itself is the exact case already handled above.
            evidence.append("repo name fullmatches pattern: %s" % expected_pattern)
            return Finding(
                criterion, "pass", criterion.points, evidence,
                "Repo name '%s' matches the expected pattern '%s'." % (
                    name, expected_pattern),
            )
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
    if not _file_matches_target(target_file, files):
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
            files.append(_normalize_diff_path(line[6:]))
    return files


def _normalize_diff_path(path):
    """Normalize a diff file path for target-file matching (issues #3/#6).

    Handles GitHub's rename syntax ('exercises/{old => new}/hello.c'
    collapses to 'exercises/new/hello.c') so renamed files still match.
    """
    return re.sub(r"\{[^}]*=>\s*", "", path).replace("}", "", 1)


def _file_matches_target(target_file, files):
    """True when target_file matches a file in the diff.

    Matches when the diff path equals the target, ends with '/target',
    or (for bare targets like 'hello.c') the diff path's basename equals
    the target. Bare-basename matching only fires when the diff path is
    longer than the target, so explicit full paths still work.
    """
    norm_target = _normalize_diff_path(target_file)
    for f in files:
        if f == norm_target:
            return True
        if f.endswith("/" + norm_target):
            return True
        if "/" in f and f.rsplit("/", 1)[1] == norm_target:
            return True
    return False


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
            in_target = _file_matches_target(target_file, [_normalize_diff_path(line[6:])])
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


def _team_best_attribution(ctx, criterion):
    """Team Best: verify the student has ANY PR (open/closed/merged) in the
    team repo (V1-6).

    A closed PR is still evidence the student attempted the work. Evidence
    includes per-member PR counts for TA context (not gradeable, but helps
    spot contribution imbalance). With no roster/username, degrades to
    evidence-only needs-review.
    """
    owner, repo, number = _parse_pr_url(ctx.pr_url) or (None, None, None)
    if not owner:
        return Finding(
            criterion, "needs-review", None,
            ["cannot parse PR URL"],
            "Cannot identify the team repository from the submission URL.",
        )
    try:
        pulls = ctx.client.list_pulls(owner, repo)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None,
            ["pulls endpoint returned 404/403"],
            "Pull requests could not be listed — TA should review the repo directly.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None,
            ["pulls endpoint failed auth/rate-limit"],
            "API auth/rate-limit issue blocked the pull request query.",
        )

    by_author = {}
    for pr in pulls:
        by_author.setdefault(pr.get("author") or "?", []).append(pr)
    counts_line = "PRs per member: %s" % (
        ", ".join("%s: %d" % (a, len(v)) for a, v in sorted(by_author.items()))
        if by_author
        else "(none)"
    )
    evidence = [counts_line]

    if not ctx.username or ctx.roster is None:
        return Finding(
            criterion, "needs-review", None, evidence,
            "No roster/username available — TA should verify the submitter "
            "created a PR in the team repo.",
        )
    if ctx.roster.find_team(ctx.username) is None:
        return Finding(
            criterion, "needs-review", None, evidence,
            "Submitter '%s' is not in the roster — TA should verify." % ctx.username,
        )

    mine = by_author.get(ctx.username, [])
    if not mine:
        return Finding(
            criterion, "fail", 0, evidence,
            "Submitter '%s' has no pull requests in the team repo." % ctx.username,
        )
    merged = [pr for pr in mine if pr.get("state") == "merged"]
    open_prs = [pr for pr in mine if pr.get("state") == "open"]
    if merged or open_prs:
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "Submitter '%s' has %d PR(s) in the team repo (%d merged, %d open)."
            % (ctx.username, len(mine), len(merged), len(open_prs)),
        )
    return Finding(
        criterion, "pass", criterion.points, evidence,
        "Submitter '%s' has a closed (unmerged) PR — attempted the work but "
        "it was never merged. TA should confirm the situation." % ctx.username,
        ta_confirm=True,
    )


def parse_github_url(url):
    """Parse a GitHub submission URL: PR or blob (MoJ).

    Returns a dict {kind, host, owner, repo, number, ref, path} where
    kind is 'pull' or 'blob', or None when the URL matches neither
    form. For blob URLs whose branch ref contains slashes, the split
    is ambiguous; callers that know the expected path should verify
    with _blob_ref_path_for() instead of relying on the naive split.
    """
    if not url:
        return None
    m = re.match(
        r"https?://(?P<host>[^/\s\"'<>]+)/(?P<owner>[A-Za-z0-9_.-]+)/"
        r"(?P<repo>[A-Za-z0-9_.-]+)/pull/(?P<number>\d+)",
        url,
    )
    if m:
        return {
            "kind": "pull",
            "host": m.group("host"),
            "owner": m.group("owner"),
            "repo": m.group("repo"),
            "number": int(m.group("number")),
            "ref": None,
            "path": None,
        }
    m = re.match(
        r"https?://(?P<host>[^/\s\"'<>]+)/(?P<owner>[A-Za-z0-9_.-]+)/"
        r"(?P<repo>[A-Za-z0-9_.-]+)/blob/(?P<tail>[^\s\"'<>]+)",
        url,
    )
    if m:
        tail = m.group("tail")
        if "/" in tail:
            ref, path = tail.split("/", 1)
        else:
            ref, path = tail, ""
        return {
            "kind": "blob",
            "host": m.group("host"),
            "owner": m.group("owner"),
            "repo": m.group("repo"),
            "number": None,
            "ref": ref,
            "path": path,
        }
    return None


def _blob_path_matches(parsed_path, expected_path):
    """True when the parsed blob path ends with the expected repo path.

    Handles slash-bearing branch refs, which make the ref/path split
    ambiguous in parse_github_url: the criterion knows the expected
    repo path, so the suffix decides.
    """
    if not expected_path:
        return True, parsed_path
    if parsed_path == expected_path:
        return True, parsed_path
    if parsed_path.endswith("/" + expected_path):
        return True, expected_path
    if "/" in parsed_path:
        # Re-split: maybe the first '/' ended a slash-bearing ref that
        # does not contain the expected path at all.
        return parsed_path.endswith(expected_path), parsed_path
    return False, parsed_path


def _parse_utc(value):
    """Parse an ISO 8601 timestamp; naive values are assumed UTC.

    Accepts the trailing-Z Git/Canvas spelling. Returns an aware
    datetime or None.
    """
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _resolve_sidecar_path(raw, ctx):
    """Resolve an instructor-share sidecar CSV (walls, timestamps).

    Tries the path as given (usually the run directory), then — for a
    relative path — the directory holding the roster file, since the
    roster and the sidecars live together on the OneDrive share.
    Returns the original string if nothing better exists (the caller's
    missing-file handling reports it normally).
    """
    if not raw:
        return raw
    p = pathlib.Path(raw)
    if p.is_absolute() or p.is_file():
        return raw
    if getattr(ctx, "roster_path", None):
        cand = pathlib.Path(ctx.roster_path).parent / raw
        if cand.is_file():
            return str(cand)
    return raw


def _team_aliases(raw):
    """Alias keys for a team id, for sidecar-CSV matching.

    Rosters in the wild carry varying prefixes ('SE_TEAM01', 'team01').
    Returns the full normalized form plus the trailing teamN token, so
    a wall/timestamps CSV written either way resolves.
    """
    text = str(raw).strip().lower()
    full = re.sub(r"^0+(\d)", r"\1", text)
    aliases = [full]
    m = re.search(r"team(\d+)$", full)
    if m:
        aliases.append("team" + m.group(1))
    return aliases


def _load_team_submission_times(path):
    """Load the team->Canvas-submission-timestamps sidecar CSV (MoJ).

    FERPA posture matches roster.csv: the file lives on the instructor
    share, never in git. Expected columns: Team,SubmittedAt (UTC ISO
    8601, e.g. 2026-11-14T21:05:00Z). Returns {normalized_team:
    aware_datetime or raw-string}; failures return {} — the sidecar is
    a convenience, never a hard requirement.
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
    except OSError:
        return {}
    times = {}
    for row in rows:
        raw = (row.get("Team") or row.get("team") or "").strip()
        stamp = (row.get("SubmittedAt") or row.get("submittedat") or "").strip()
        if not raw or not stamp:
            continue
        for alias in _team_aliases(raw):
            times.setdefault(alias, stamp.strip())
    return times


def _blob_link_valid(ctx, criterion):
    """Verify a direct-GitHub blob URL resolves (MoJ).

    Params:
        expected_path: repo path the blob must point at (matched as a
            full or suffix path, so slash-bearing refs parse OK).
            Optional — no path check when omitted.
        expected_ref: branch/SHA the blob must name (e.g. "main").
            Optional.
        expected_repo_pattern: substring the repo name must contain
            (e.g. "fa26_se1_team"). Optional.

    Assessment:
        pass: URL is a blob, matches all given expectations, and the
            file exists at the ref (contents API).
        fail: URL is not a blob form, an expectation is violated, or
            the contents endpoint reports the path missing.
        needs-review: no URL in the submission, or API auth/rate-limit
            blocked the check.
    """
    params = criterion.params
    parsed = parse_github_url(ctx.pr_url)
    if parsed is None:
        return Finding(
            criterion, "needs-review", None,
            ["no recognizable GitHub URL in the submission"],
            "The submission carries no PR/blob URL — TA should review it directly.",
        )
    if parsed["kind"] != "blob":
        return Finding(
            criterion, "fail", 0,
            ["submission URL is a pull URL, not a blob URL"],
            "Rubric expects a direct GitHub blob link (e.g. the team "
            "document at its repo path); got %s." % ctx.pr_url,
        )
    evidence = ["url: %s" % ctx.pr_url]
    owner, repo = parsed["owner"], parsed["repo"]
    expected_path = params.get("expected_path")
    if expected_path and "{username}" in expected_path:
        username = getattr(ctx, "username", None)
        if not username:
            return Finding(
                criterion, "needs-review", None, evidence,
                "The rubric path template wants '{username}' but this "
                "submission has no resolved username (one-off import?) "
                "— TA verifies the path manually.",
            )
        expected_path = expected_path.replace("{username}", username)
        evidence.append("expected path (from username %s): %s"
                        % (username, expected_path))
    ok, effective_path = _blob_path_matches(parsed["path"], expected_path)
    if not ok:
        evidence.append("path mismatch: %s" % parsed["path"])
        return Finding(
            criterion, "fail", 0, evidence,
            "Blob points at '%s'; rubric expects '%s'."
            % (parsed["path"], expected_path or params.get("expected_path")),
        )
    expected_ref = params.get("expected_ref")
    if expected_ref and parsed["ref"] != expected_ref:
        evidence.append("ref mismatch: %s (expected %s)" % (parsed["ref"], expected_ref))
        return Finding(
            criterion, "fail", 0, evidence,
            "Blob ref '%s' does not match the expected ref '%s'."
            % (parsed["ref"], expected_ref),
        )
    pattern = params.get("expected_repo_pattern")
    if pattern and pattern not in repo:
        evidence.append("repo name does not match pattern: %s" % repo)
        return Finding(
            criterion, "fail", 0, evidence,
            "Repo '%s' does not match expected pattern '%s'." % (repo, pattern),
        )
    try:
        kind, content = ctx.client.get_file_contents(
            owner, repo, effective_path, ref=parsed["ref"]
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None, evidence,
            "API auth/rate-limit issue blocked the contents query.",
        )
    evidence.append("contents kind: %s" % kind)
    if kind == "file":
        size = len(content or "")
        evidence.append("size: %d bytes" % size)
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "Blob resolves: file '%s' present at ref '%s' (%s bytes)."
            % (effective_path, parsed["ref"], size),
        )
    if kind == "dir":
        return Finding(
            criterion, "fail", 0, evidence,
            "Blob path names a directory, not a file — TA should review.",
        )
    return Finding(
        criterion, "fail", 0, evidence,
        "File '%s' not found at ref '%s' (HTTP 404/403)." % (effective_path, parsed["ref"]),
    )


def _pr_from_given_branch(ctx, criterion):
    """Report the state of a PR from a given source branch (MoJ).

    For instructor-distributed GIVEN screens: the Team PR carries a
    0-pt evidence row naming the source branch the PR must come from
    (e.g. 'given/wk12-desk-edit'). Verifies it per team repo.

    Params:
        source_branch: regex the PR head ref must match (required).
        state: 'merged' (default), 'open', or 'any'.

    Assessment:
        pass: a PR with a matching head ref is in the required state.
        fail: matching PR(s) exist but not in the required state, or no
            matching PR exists.
        needs-review: API auth/rate-limit blocked the listing.
    """
    params = criterion.params
    source = params.get("source_branch") or ""
    wanted = params.get("state", "merged")
    parsed = parse_github_url(ctx.pr_url)
    if parsed is None:
        return Finding(
            criterion, "needs-review", None,
            ["no recognizable GitHub URL in the submission"],
            "Cannot identify the team repo — TA should review directly.",
        )
    owner, repo = parsed["owner"], parsed["repo"]
    evidence = ["repo: %s/%s" % (owner, repo)]
    try:
        pulls = ctx.client.list_pulls(owner, repo)
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None, evidence,
            "API auth/rate-limit issue blocked the pull listing.",
        )
    pat = re.compile(source)
    matching = [p for p in pulls if pat.fullmatch(p.get("head_ref") or "")]
    for p in matching:
        evidence.append(
            "PR #%s by %s: head '%s', state %s%s"
            % (
                p.get("number"),
                p.get("author") or "?",
                p.get("head_ref"),
                p.get("state"),
                (" (merged %s)" % p["merged_at"]) if p.get("merged_at") else "",
            )
        )
    if not matching:
        evidence.append("no PR with head ref matching '%s'" % source)
        return Finding(
            criterion, "fail", 0, evidence,
            "No pull request from source branch '%s' in %s/%s — the TA "
            "should check whether the team merged the GIVEN screen."
            % (source, owner, repo),
        )
    if wanted in ("any",):
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "PR from source branch '%s' exists (state %s)."
            % (source, matching[0].get("state")),
        )
    in_state = [p for p in matching if p.get("state") == wanted]
    if in_state:
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "%d PR(s) from branch '%s' in required state '%s'."
            % (len(in_state), source, wanted),
        )
    return Finding(
        criterion, "fail", 0, evidence,
        "PR(s) from branch '%s' exist but none is %s — TA should confirm."
        % (source, "merged" if wanted == "merged" else "open"),
    )


def _devlog_before_canvas(ctx, criterion):
    """Order-rule evidence: devlog commits vs the Canvas submission (MoJ).

    A_MJ05 Part (a): each member's position entry is committed to their
    own devlog repo BEFORE the team document is submitted to Canvas;
    the grader compares timestamps (assessed by order, no deadline).
    This checker gathers the GitHub-side evidence; the TA awards the
    5-pt criterion and applies the EngLog cap.

    Params:
        timestamps_file: sidecar CSV (Team,SubmittedAt — UTC ISO) with
            the team document's Canvas submission timestamps. Same
            FERPA posture as roster.csv: instructor share, never git.
            Optional; without it the checker reports needs-review.
        devlog_repo_pattern: repo-name template; {username} is
            substituted (default 'fa26-devlog-{username}').
        target_file: optional repo path — when set, only commits for
            that path are considered; when omitted, all default-branch
            commits are evidence (flagged as such).

    Assessment:
        pass: every roster member shows in-window commit evidence and
            no commit lands at/after the Canvas submission.
        fail: at least one member's latest relevant commit is at/after
            the Canvas submission timestamp.
        needs-review: missing roster/sidecar, inaccessible devlog
            repos, no commits for a member, or API errors — the TA
            decides on the affected members.
    """
    params = criterion.params
    parsed = parse_github_url(ctx.pr_url)
    if parsed is None:
        return Finding(
            criterion, "needs-review", None, [],
            "Cannot identify the team from the submission URL.",
        )
    if ctx.roster is None or not ctx.username:
        return Finding(
            criterion, "needs-review", None, [],
            "No roster available — member devlogs cannot be resolved; "
            "TA verifies the order manually.",
        )
    team = ctx.roster.find_team(ctx.username)
    members = ctx.roster.members(team) if team else None
    if not members:
        return Finding(
            criterion, "needs-review", None, [],
            "Submitter '%s' has no roster team — TA verifies order manually."
            % ctx.username,
        )
    stamp_path = _resolve_sidecar_path(params.get("timestamps_file"), ctx)
    submitted_raw = None
    if stamp_path:
        times = _load_team_submission_times(stamp_path)
        for alias in _team_aliases(team):
            if alias in times:
                submitted_raw = times[alias]
                break
    submitted = _parse_utc(submitted_raw)
    if submitted is None:
        return Finding(
            criterion, "needs-review", None, [],
            "No Canvas submission timestamp for team '%s' in '%s' — "
            "add a Team,SubmittedAt row (UTC ISO) and rerun."
            % (team, stamp_path or "(timestamps file unset)"),
        )
    evidence = [
        "team: %s; Canvas submission: %s" % (team, submitted_raw),
    ]
    if not params.get("target_file"):
        evidence.append("no path filter: all default-branch commits count")
    pattern = params.get("devlog_repo_pattern") or "fa26-devlog-{username}"
    any_after = False
    review_reasons = []
    in_window_members = 0
    for member in members:
        repo_name = pattern.format(username=member)
        try:
            commits = ctx.client.get_commits_for_path(
                member, repo_name, path=params.get("target_file")
            )
        except PRNotAccessibleError:
            review_reasons.append("%s: devlog repo not accessible" % member)
            continue
        except (AuthFailureError, RateLimitError):
            return Finding(
                criterion, "needs-review", None, evidence,
                "API auth/rate-limit issue blocked the devlog commits query.",
            )
        dates = [(c.get("sha") or "?", _parse_utc(c.get("date"))) for c in commits]
        dated = [(sha, dt) for sha, dt in dates if dt is not None]
        if not dated:
            review_reasons.append(
                "%s: no commits%s" % (
                    member,
                    (" for %s" % params["target_file"]) if params.get("target_file") else "",
                )
            )
            continue
        after_shas = [sha for sha, dt in dated if dt >= submitted]
        before = [(sha, dt) for sha, dt in dated if dt < submitted]
        if after_shas:
            any_after = True
            evidence.append(
                "%s: %d/%d commit(s) at/after submission (%s)"
                % (member, len(after_shas), len(dated), ", ".join(after_shas[:3]))
            )
            continue
        if before:
            latest_sha, latest_dt = max(before, key=lambda pair: pair[1])
            in_window_members += 1
            evidence.append(
                "%s: latest in-window commit %s at %s"
                % (member, latest_sha, latest_dt.isoformat())
            )
    if any_after:
        return Finding(
            criterion, "fail", 0, evidence,
            "At least one member's devlog commit is at/after the Canvas "
            "submission timestamp — that member's EngLog is capped 1 "
            "point; the TA applies the cap.",
        )
    if review_reasons:
        return Finding(
            criterion,
            "needs-review",
            None,
            evidence,
            "%d member(s) need manual confirmation: %s" % (
                len(review_reasons), "; ".join(review_reasons),
            ),
        )
    return Finding(
        criterion, "pass", criterion.points, evidence,
        "All %d in-window member(s) show devlog commits before the "
        "Canvas submission." % in_window_members,
    )





def _word_count(text):
    """Word count for reflection bars; markdown/punct don't inflate it."""
    return re.findall(r"[A-Za-z0-9'’\-]+", text)


def _ollama_judge(endpoint, model, text, timeout=90):
    """Local-model judgment of a devlog reflection (FERPA: loopback only).

    Returns (verdict, reason) with verdict 'pass'|'fail', or (None, tail)
    when the reply doesn't parse. Raises OSError/URLError on transport
    failure — the caller degrades to needs-review.
    """
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": (
                "You are grading an engineering student's weekly devlog "
                "reflection. Decide whether the text contains (a) a "
                "specific lesson learned or observation about the week's "
                "work, and (b) a justification or cause for it (why it "
                "held, what caused it). Ignore grammar, formatting and "
                "word count. Answer with exactly two lines and nothing "
                "else:\n"
                "VERDICT: pass|fail\n"
                "REASON: <one sentence>")},
            {"role": "user", "content": text[:6000]},
        ],
    }
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = (data.get("message") or {}).get("content") or ""
    m = re.search(r"VERDICT:\s*(pass|fail)", content, re.IGNORECASE)
    if not m:
        return None, content.strip()[:200]
    r = re.search(r"REASON:\s*(.+)", content)
    return m.group(1).lower(), (r.group(1).strip() if r else "")


def _reflection_text_evidence(evidence, text, cap=1100):
    """Prefix the entry into the evidence so the TA verifies from the
    report without fetching anything; hard-capped for sane reports."""
    used = 0
    for line in text.splitlines():
        if used >= cap:
            evidence.append("entry: …(truncated at %d chars by the tool)" % cap)
            return
        cut = line[:140]
        evidence.append("entry: %s" % cut)
        used += len(cut) + 8


def _reflection_entry(ctx, criterion):
    """Devlog reflection quality bar (EngLog; Kurt's 2026-11-12 ruling).

    A reflection earns its points when it carries (a) a specific lesson
    learned or observation AND (b) a justification or cause, in about
    100–200 words. The checker does the mechanical part (blob resolves
    in the student's own devlog repo, word count) and runs a LOCAL
    small model for the semantic part; the FULL entry text rides the
    evidence so the TA verifies from the report without running
    anything themselves.

    Params:
        min_words (default 100) — below it the projection fails.
        max_words (default 200) — soft: "at least" is the bar; a longer
            entry passes but the note carries the target.
        expected_path (optional) — require exactly this file (W8's
            wk08.md). Absent → any path in the devlog repo.
        expected_repo_pattern (default 'fa26-devlog-') — the blob must
            live in the student's own devlog repo (prefix or regex).
        llm_model (optional) — local judge (e.g. 'llama3.1:8b'); OMIT
            for a report-only run (TA judges from the entry text).
        llm_endpoint — default 'http://127.0.0.1:11434'; a non-loopback
            endpoint is REFUSED (student text must not leave the
            machine — FERPA standing rule).
    """
    params = criterion.params
    min_words = int(params.get("min_words", 100))
    max_words = int(params.get("max_words", 200))
    pattern = params.get("expected_repo_pattern") or "fa26-devlog-"
    expected_path = params.get("expected_path")
    llm_model = params.get("llm_model")
    endpoint = params.get("llm_endpoint") or "http://127.0.0.1:11434"

    if llm_model:
        host = urllib.parse.urlparse(endpoint).hostname or ""
        if host not in ("127.0.0.1", "localhost", "::1"):
            return Finding(
                criterion, "needs-review", None, [],
                "llm_endpoint %s refused — student text must not leave "
                "this machine (FERPA standing rule). Use a loopback "
                "endpoint or drop llm_model for a report-only run."
                % endpoint,
            )

    parsed = parse_github_url(ctx.pr_url)
    if parsed is None or parsed["kind"] != "blob":
        return Finding(
            criterion, "needs-review", None, [],
            "Submission is not a blob URL — the reflection rides a file "
            "in the devlog repo; run this rubric against that Canvas "
            "submission.",
        )
    owner, repo, path = parsed["owner"], parsed["repo"], parsed["path"]
    evidence = [
        "repo: %s/%s" % (owner, repo),
        "path: %s" % path,
    ]

    if pattern == "fa26-devlog-":
        repo_ok = bool(re.fullmatch(r"fa26-devlog-.+", repo, re.IGNORECASE))
    else:
        repo_ok = bool(re.search(pattern, repo, re.IGNORECASE))
    if not repo_ok:
        evidence.append("MISSING: blob must live in the student's own "
                        "devlog repo (%s)" % pattern)
        return Finding(
            criterion, "fail", 0, evidence,
            "The blob does not live in the student's own devlog repo — "
            "no evidence the entry is theirs. 0 pts (TA verifies).",
            ta_confirm=True,
        )
    if expected_path and path != expected_path:
        evidence.append("MISSING: expected entry file %s" % expected_path)
        return Finding(
            criterion, "fail", 0, evidence,
            "The submission points at %r, not the entry file the "
            "grading design requires (%r). 0 pts (TA confirms)."
            % (path, expected_path), ta_confirm=True,
        )

    try:
        kind, text = ctx.client.get_file_contents(owner, repo, path)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None, evidence,
            "Devlog block not accessible — TA reads the entry directly.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None, evidence,
            "Devlog fetch failed (auth/rate) — TA reviews.",
        )
    if kind == "missing":
        evidence.append("MISSING: no file at this blob path")
        return Finding(
            criterion, "fail", 0, evidence,
            "No file at the submitted blob path (404/moved) — 0 pts "
            "projected. TA verifies the URL and re-runs if the student "
            "renamed the entry.", ta_confirm=True,
        )
    if kind == "dir":
        return Finding(
            criterion, "fail", 0, evidence,
            "The blob URL points to a DIRECTORY, not a file — the "
            "submission should carry the FILE's blob URL. 0 pts "
            "(TA confirms).", ta_confirm=True,
        )
    if not text or not text.strip():
        evidence.append("entry file EMPTY")
        return Finding(
            criterion, "fail", 0, evidence,
            "The entry file is EMPTY — nothing to grade. 0 pts (TA "
            "confirms).", ta_confirm=True,
        )

    n_words = len(_word_count(text))
    evidence.append("word count: %d" % n_words)
    _reflection_text_evidence(evidence, text)

    short = n_words < min_words
    short_note = "Entry is %d words — below the %d-word bar." % (n_words, min_words)
    over_note = ""
    if n_words > max_words:
        over_note = " (%d words runs past the %d-word target — soft; " \
                    "'at least' is the bar)" % (n_words, max_words)

    if not llm_model:
        if short:
            return Finding(
                criterion, "needs-review", None, evidence,
                "%s Report-only run — TA judges: ONE-POINT deduction "
                "(%d of %d) if the entry text above carries the "
                "lesson+justification bar, 0 otherwise."
                % (short_note, max(criterion.points - 1, 0),
                   criterion.points), ta_confirm=True,
            )
        return Finding(
            criterion, "needs-review", None, evidence,
            "Report-only run (no llm_model) — TA judges the entry text "
            "above; full points when the lesson + justification bar is "
            "met.%s" % over_note, ta_confirm=True,
        )
    try:
        verdict, reason = _ollama_judge(endpoint, llm_model, text)
    except (OSError, urllib.error.URLError, ValueError) as e:
        return Finding(
            criterion, "needs-review", None, evidence,
            "Local model unreachable (%s: %.120s) — TA judges the "
            "entry text above (is ollama running? is llm_model pulled?)."
            % (type(e).__name__, str(e)), ta_confirm=True,
        )
    ferpa_note = "judged locally (%s on %s) — nothing left this machine%s" % (
        llm_model, endpoint, over_note)
    if verdict is None:
        return Finding(
            criterion, "needs-review", None, evidence,
            "Model reply unparseable (%.160s) — TA judges from the "
            "entry text above." % reason, ta_confirm=True,
        )
    if verdict == "fail":
        detail = ("no lesson/observation WITH its justification (%s)"
                  % reason)
        if short:
            detail = short_note + " " + detail
        return Finding(
            criterion, "fail", 0,
            evidence + ["model verdict: fail — %s" % reason],
            "%s — 0 pts projected; the TA verifies from the entry text "
            "above and overrules if the assertion erred. %s"
            % (detail, ferpa_note), ta_confirm=True,
        )
    if short:
        return Finding(
            criterion, "pass", max(criterion.points - 1, 0),
            evidence + ["model verdict: pass — %s" % reason],
            "%s ONE-POINT deduction applied (%d of %d): the assertion "
            "passed but the entry is short of the word minimum. TA "
            "verifies from the entry text above. %s"
            % (short_note, max(criterion.points - 1, 0),
               criterion.points, ferpa_note), ta_confirm=True,
        )
    return Finding(
        criterion, "pass", criterion.points,
        evidence + ["model verdict: pass — %s" % reason],
        "Lesson/observation with justification present — full points "
        "projected. TA verifies from the entry text above. %s"
        % ferpa_note, ta_confirm=True,
    )


def _doc_contains(ctx, criterion):
    """Mechanical completeness for blob-URL documents (AGR_MJ series).

    Fetches the submitted blob file and verifies the document-shape
    requirements the grading design states mechanically: required
    section headers, required content tokens, and (as an evidence NOTE
    unless the row scores it) the word band. Presence projects the
    row's points; a missing requirement projects 0 for the TA to
    confirm — amass-then-subtract, so the TA still judges precision
    and substance, which stay manual by design ("graded on precision,
    not length").

    Params:
        expected_path / expected_repo_pattern — same meaning as
            blob_link_valid ('{username}' supported); re-checked here
            so the content row stands alone.
        require_headers — regex list; every pattern must match some
            heading line in the document ('^##?\\s' anchored).
        must_contain — regex list; every token must appear anywhere
            in the document text.
        min_words / max_words — soft band: emitted as a note when
            violated (the MJ01 page grades precision, not length;
            MJ02's format row scores the band, so that rubric sets
            band_enforced: true to project 0 on a band miss).
        band_enforced — see above (default False).
    """
    params = criterion.params
    expected_path = params.get("expected_path")
    expected_repo_pattern = params.get("expected_repo_pattern")
    require_headers = params.get("require_headers") or []
    must_contain = params.get("must_contain") or []
    min_words = params.get("min_words")
    max_words = params.get("max_words")
    band_enforced = bool(params.get("band_enforced"))

    parsed = parse_github_url(ctx.pr_url)
    if parsed is None or parsed["kind"] != "blob":
        return Finding(
            criterion, "needs-review", None, [],
            "Submission is not a blob URL — the document rides a file "
            "in the team or devlog repo.",
        )
    owner, repo, path = parsed["owner"], parsed["repo"], parsed["path"]
    evidence = ["repo: %s/%s" % (owner, repo), "path: %s" % path]

    if expected_repo_pattern:
        pat = (expected_repo_pattern == "fa26-devlog-"
               and r"fa26-devlog-.+" or expected_repo_pattern)
        if not re.search(pat, repo, re.IGNORECASE):
            evidence.append("MISSING: repo does not match %s" % expected_repo_pattern)
            return Finding(
                criterion, "fail", 0, evidence,
                "The document lives in '%s', not the repo shape the "
                "grading design requires (%s). 0 pts (TA verifies)."
                % (repo, expected_repo_pattern), ta_confirm=True,
            )
    if expected_path:
        want = expected_path
        if "{username}" in want:
            username = getattr(ctx, "username", None)
            if not username:
                return Finding(
                    criterion, "needs-review", None, evidence,
                    "Path template '{username}' unresolved (one-off "
                    "import?) — TA verifies the path manually.",
                )
            want = want.replace("{username}", username)
            evidence.append("expected path (from username %s): %s"
                            % (username, want))
        ok, _ = _blob_path_matches(path, want)
        if not ok:
            evidence.append("MISSING: path mismatch — got %s, want %s" % (path, want))
            return Finding(
                criterion, "fail", 0, evidence,
                "Document path is '%s'; the grading design requires "
                "'%s' — 0 pts (TA verifies the filename and the "
                "student's identity in it)." % (path, want),
                ta_confirm=True,
            )

    try:
        kind, text = ctx.client.get_file_contents(owner, repo, path)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None, evidence,
            "Document block not accessible — TA reads the file directly.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None, evidence,
            "Document fetch failed (auth/rate) — TA reviews.",
        )
    if kind == "missing":
        evidence.append("MISSING: no file at this blob path")
        return Finding(
            criterion, "fail", 0, evidence,
            "No file at the submitted blob path (404/moved) — 0 pts "
            "projected. TA verifies and re-runs if renamed.",
            ta_confirm=True,
        )
    if kind == "dir":
        return Finding(
            criterion, "fail", 0, evidence,
            "The submission points at a DIRECTORY, not the document "
            "file — 0 pts (TA confirms).", ta_confirm=True,
        )
    if not text or not text.strip():
        evidence.append("document file EMPTY")
        return Finding(
            criterion, "fail", 0, evidence,
            "The document file is EMPTY — nothing to grade. 0 pts "
            "(TA confirms).", ta_confirm=True,
        )

    missing = []
    headers = [ln for ln in text.splitlines()
               if re.match(r"^#{1,4}\s+\S", ln.strip())]
    for pat in require_headers:
        if not any(re.search(pat, h, re.IGNORECASE) for h in headers):
            missing.append("header '%s'" % pat)
    for pat in must_contain:
        if not re.search(pat, text, re.IGNORECASE):
            missing.append("content '%s'" % pat)
    if missing:
        evidence += ["MISSING: %s" % m for m in missing]
        return Finding(
            criterion, "fail", 0, evidence,
            "Required section/content missing from the document: %s — "
            "0 pts projected (TA verifies; the missing piece is what "
            "the page's grading design requires for this row)."
            % "; ".join(missing[:6]), ta_confirm=True,
        )

    n_words = len(_word_count(text))
    evidence.append("total word count: %d" % n_words)
    band_note = ""
    if min_words and n_words < min_words:
        band_note = " (%d words is UNDER the %d-word band" % (n_words, min_words)
    elif max_words and n_words > max_words:
        band_note = " (%d words runs OVER the %d-word band" % (n_words, max_words)
    if band_note:
        band_note += " — TA judges)"
        evidence.append(band_note)
        if band_enforced:
            return Finding(
                criterion, "fail", 0, evidence,
                "Word band missed: %s. 0 pts projected (TA verifies — "
                "near-misses are this row's judgment call)." % band_note,
                ta_confirm=True,
            )
    return Finding(
        criterion, "pass", criterion.points,
        evidence + ["required sections/content present"],
        "All mechanical requirements present — %d pts projected. TA "
        "subtracts for precision/substance issues%s. %s"
        % (criterion.points,
           band_note or (" (%d words)" % n_words if min_words or max_words else ""),
           "Sections must also appear in page order (TA check)."),
        ta_confirm=True,
    )


def _pr_body_contains(ctx, criterion):
    """Mechanical completeness of the Team PR body (MoJ amass-then-subtract).

    Params:
        items: list of dicts describing required body fragments:
            {"label": str,
             "section": r"ICEX_MJ01"}         — a `### <section>` heading must
                                                 exist and contain a ticked box
                                                 (`- [x]`); the section slice runs
                                                 to the next `###` heading.
            {"label", "require": regex}       — regex must match the body.
            {"label", "section", "require"}   — regex must match inside the slice.
            {"label", "forbid": regex}        — regex must NOT appear anywhere
                                                 (template-placeholder check).
            Regexes match IGNORECASE. `label` drives evidence and the missing
            report.

    Assessment (Kurt's 2026-11-11 projection ruling):
        pass + ta_confirm: every item present → the full criterion points are
            recommended as the projection; the TA verifies and SUBTRACTS for
            detail issues rather than adding.
        fail (0) + items missing: anything missing is reported as LOST POINTS
            with the missing list; components that are present are assumed
            correct.
        needs-review: PR URL unusable or API errors.
    """
    items = criterion.params.get("items") or []
    parsed = parse_github_url(ctx.pr_url)
    if parsed is None or parsed["kind"] != "pull":
        return Finding(
            criterion, "needs-review", None, [],
            "Run this rubric against the Team PR's Canvas submission (a pull "
            "URL) — the body completeness rides the PR.",
        )
    owner, repo, number = parsed["owner"], parsed["repo"], parsed["number"]
    evidence = ["PR: #%s" % number]
    try:
        pr = ctx.client.get_pr(owner, repo, number)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None, evidence,
            "PR endpoint not accessible — TA reviews the body directly.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None, evidence,
            "API auth/rate-limit issue blocked the PR fetch.",
        )
    body = pr.body or ""
    if not body.strip():
        return Finding(
            criterion, "fail", 0, evidence + ["PR body is EMPTY"],
            "The PR body carries nothing — every component is a lost point. "
            "TA reviews the PR directly.",
            ta_confirm=True,
        )

    def _section_slice(name):
        m = re.search(
            r"(?ms)^#{2,3}\s*%s\b.*?(?=^#{1,6}\s|\Z)" % re.escape(name), body
        )
        return m.group(0) if m else None

    missing = []
    for item in items:
        label = item.get("label") or "(unlabeled item)"
        section = item.get("section")
        conds = []  # (ok, where) — all must hold; forbid negates its match
        slice_ = _section_slice(section) if section else None
        if section:
            if slice_ is None:
                conds.append((False, "section %s (heading absent)" % section))
            elif item.get("require"):
                ok = bool(re.search(item["require"], slice_, re.IGNORECASE))
                conds.append((ok, "section %s" % section))
            else:
                ticks = re.findall(r"-\s*\[x\]", slice_, re.IGNORECASE)
                conds.append((bool(ticks), "section %s (ticked: %d)" % (
                    section, len(ticks)) if ticks else
                    "section %s (no ticked boxes)" % section))
        if item.get("require") and not section:
            ok = bool(re.search(item["require"], body, re.IGNORECASE))
            conds.append((ok, "body"))
        if item.get("forbid"):
            hit = bool(re.search(item["forbid"], body, re.IGNORECASE))
            conds.append((not hit, "template placeholder %s" % (
                "STILL PRESENT" if hit else "replaced")))
        present = bool(conds) and all(ok for ok, _w in conds)
        if present:
            evidence.append(
                "present: %s — %s" % (label, "; ".join(w for _o, w in conds)))
        else:
            missing.append(label)
            evidence.append("MISSING: %s (%s)" % (
                label, "; ".join(w for _o, w in conds)))

    if missing:
        return Finding(
            criterion, "fail", 0, evidence,
            "Missing components reported as lost points: %s. Components "
            "present are assumed correct — the TA verifies and subtracts."
            % "; ".join(missing),
            ta_confirm=True,
        )
    return Finding(
        criterion, "pass", criterion.points, evidence,
        "All required PR-body components present — full points projected. "
        "TA verifies the details and subtracts for issues.",
        ta_confirm=True,
    )


def _pr_commits_by_wall(ctx, criterion):
    """Wall-timing evidence: per-member PR commits vs the wall (W8 MoJ).

    W8-15 ICEX walls (MJ01+): the in-class deliverable is on-time when
    each member's commits land on the branch by the session's wall
    (2 PM US/Eastern on the class day, from the shared
    moj_walls_fa26.csv); the wall scores are entered per member on
    the no-submission ICEX Canvas lines (late → 8.5). The week's Team
    PR carries every branch commit, so THIS
    checker reads the PR's commit list and reconciles it against the
    roster and the CONTRIBUTIONS.md process record. The TA awards all
    points; this row only gathers evidence and flags.

    Params:
        wall_file: sidecar CSV (Team,<WallColumn>… — UTC ISO 8601) with
            each team's wall timestamps; one CSV column per wall that
            week (W8 carries WallMJ01 and WallMJ02). Same FERPA posture
            as roster.csv: instructor share, never in git. Optional;
            without it the timing evidence reports needs-review.
        wall_columns: the CSV timestamp columns, in order (default
            ['WallAt']). Banding: commits are grouped by which walls
            they precede; only commits after the LAST wall are
            unambiguously late for any ICEX.
        contributions_file: repo path (suffix-matched in the PR diff)
            of the checkpoint writeup process record. Default
            'CONTRIBUTIONS.md'; pass an empty value to skip.

    Assessment:
        pass: every roster member has PR commits and no commit lands
            after the last wall, with the contributions file in the
            diff.
        pass + ta_confirm: evidence gathered, but at least one commit
            is after the last wall (late for both ICEXs' walls — the
            8.5 rule applies where the TA maps the artifact).
        needs-review: PR URL unusable, roster/wall sidecar missing, a
            member has no commits (absent vs not-pushing — the TA
            knows who attended), or API errors.
    """
    params = criterion.params
    parsed = parse_github_url(ctx.pr_url)
    if parsed is None or parsed["kind"] != "pull":
        return Finding(
            criterion, "needs-review", None, [],
            "Run this rubric against the Team PR's Canvas submission "
            "(a pull URL) — the wall evidence rides the PR commits.",
        )
    owner, repo, number = parsed["owner"], parsed["repo"], parsed["number"]
    evidence = ["PR: %s/%s#%s" % (owner, repo, number)]
    try:
        commits = ctx.client.get_pr_commits(owner, repo, number)
    except PRNotAccessibleError:
        return Finding(
            criterion, "needs-review", None, evidence,
            "PR commits endpoint not accessible — TA reviews the PR directly.",
        )
    except (AuthFailureError, RateLimitError):
        return Finding(
            criterion, "needs-review", None, evidence,
            "API auth/rate-limit issue blocked the PR commits query.",
        )
    if not commits:
        return Finding(
            criterion, "needs-review", None, evidence,
            "PR has no commits on the first page — TA reviews the PR directly.",
        )

    members = None
    team = None
    if ctx.roster is not None and ctx.username:
        team = ctx.roster.find_team(ctx.username)
        members = ctx.roster.members(team) if team else None
    if not members:
        evidence.append("no roster: commits listed per login (author mapping is the TA's)")
        members = sorted(set(c.get("login") or "?" for c in commits))

    wall_path = _resolve_sidecar_path(params.get("wall_file"), ctx)
    wall_columns = params.get("wall_columns") or ["WallAt"]
    walls = []  # [(column, aware_datetime, raw)]
    if wall_path:
        try:
            with open(wall_path, newline="", encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
        except OSError:
            rows = []
        aliases = _team_aliases(team or "")
        row = None
        for r in rows:
            cell = (r.get("Team") or r.get("team") or "").strip()
            if cell and set(_team_aliases(cell)) & set(aliases):
                row = r
                break
        for col in wall_columns:
            raw = (row or {}).get(col) or (row or {}).get(col.lower()) or ""
            dt = _parse_utc(raw)
            walls.append((col, dt, raw or None))
    else:
        walls = [(col, None, None) for col in wall_columns]
    usable = [(col, dt, raw) for col, dt, raw in walls if dt is not None]
    if not usable:
        return Finding(
            criterion, "needs-review", None, evidence,
            "No wall timestamps for team '%s' in '%s' (columns %s) — "
            "add Team,<WallColumn> rows (ISO-8601 with the US/Eastern "
            "offset, e.g. 2 PM = T14:00:00-04:00) and rerun."
            % (team or "(?)", wall_path or "(wall file unset)",
               ", ".join(wall_columns)),
        )
    for col, _dt, raw in usable:
        evidence.append("%s: %s" % (col, raw))

    # Completion per wall column: the PR body must carry the ICEX's
    # `### <section>` heading with at least one ticked DoD box (Kurt's
    # projection model: a missing section is a LOST wall line).
    completion = {}  # col -> True / False / None (no pattern or fetch failed)
    section_patterns = params.get("section_patterns") or {}
    if section_patterns:
        try:
            _pr = ctx.client.get_pr(owner, repo, number)
            _body = _pr.body or ""
        except (PRNotAccessibleError, AuthFailureError, RateLimitError):
            _body = None
            evidence.append("PR body unavailable for completion check")
        for col, _dt, _raw in usable:
            name = section_patterns.get(col)
            if not name or _body is None:
                completion[col] = None
                continue
            m = re.search(
                r"(?ms)^#{2,3}\s*%s\b.*?(?=^#{1,6}\s|\Z)" % re.escape(name),
                _body,
            )
            complete = bool(m) and bool(re.search(
                r"-\s*\[x\]", m.group(0), re.IGNORECASE))
            completion[col] = complete
            evidence.append(
                "completion %s: %s (section %s%s)" % (
                    col, "complete" if complete else "MISSING — projected 0",
                    name, ", ticked" if complete else "")
            )

    any_late = False
    review_reasons = []
    last_wall_dt = max(wdt for _c, wdt, _r in usable)
    for member in members:
        mine = [c for c in commits if (c.get("login") or "?") == member]
        if not mine:
            review_reasons.append(
                "%s: no commits authored in the PR (absent, or pushed "
                "under another login — TA decides)" % member
            )
            # No wall commits = no evidence: the amass model projects 0
            # on every wall line until the TA grades attendance manually.
            evidence.append(
                "project %s: %s" % (
                    member,
                    ", ".join(
                        "%s=0" % col.replace("Wall", "")
                        for col, _wdt, _rw in usable
                    ),
                )
            )
            continue
        dated = [(c.get("sha") or "?", _parse_utc(c.get("date")), c) for c in mine]
        dated = [(sha, dt, c) for sha, dt, c in dated if dt is not None]
        if not dated:
            review_reasons.append("%s: commits without usable dates" % member)
            continue
        bands = []
        after_last = []
        for sha, dt, c in dated:
            wall_for_band = None
            for col, wdt, _raw in usable:
                if dt <= wdt:
                    wall_for_band = col
                    break
            if wall_for_band:
                bands.append((wall_for_band, sha))
            else:
                after_last.append((sha, dt))
        band_summary = []
        for col, _dt, _raw in usable:
            n = sum(1 for b, _sha in bands if b == col)
            if n:
                band_summary.append("%d by %s" % (n, col))
        if after_last:
            any_late = True
            evidence.append(
                "%s: %d commit(s) AFTER the last wall %s (%s) — 8.5 "
                "applies where the TA maps the artifact"
                % (member, len(after_last),
                   max(_col for _col, _dt, _raw in usable),
                   ", ".join(sha for sha, _dt in after_last[:3]))
            )
        if band_summary:
            evidence.append("%s: %s" % (member, "; ".join(band_summary) +
                (" (+%d after last wall)" % len(after_last) if after_last else "")))
        else:
            evidence.append("%s: all %d commit(s) after the last wall" % (member, len(dated)))
            any_late = True
        # Projection per Kurt's amass-then-subtract model (2026-11-11):
        # completion present and all commits by the wall → 10; any commit
        # of the member landing after that column's wall → 8.5 (the late
        # flag the TA applies); completion missing → 0 lost, for everyone.
        mem_dts = [dt for _sha, dt, _c in dated]
        proj = []
        for col, wdt, _raw in usable:
            if completion.get(col) is False:
                val = 0
            elif any(d > last_wall_dt for d in mem_dts):
                # Unattributable post-wall commits are the late tail —
                # 8.5 on each wall line until the TA maps the artifact
                # (the late shas are listed above).
                val = "8.5"
                any_late = True
            else:
                val = "10"
            proj.append("%s=%s" % (col.replace("Wall", ""), val))
        evidence.append("project %s: %s" % (member, ", ".join(proj)))

    own = [e for e in evidence if e.startswith(
        "project %s:" % (ctx.username or "\0none\0"))]
    if own:
        evidence.append("submitter's projected wall score — %s" % own[0])

    if params.get("contributions_file", "CONTRIBUTIONS.md"):
        target = params.get("contributions_file") or "CONTRIBUTIONS.md"
        try:
            diff = ctx.client.get_pr_diff(owner, repo, number)
        except PRNotAccessibleError:
            diff = None
        except (AuthFailureError, RateLimitError):
            diff = None
        if diff is None:
            evidence.append(
                "CONTRIBUTIONS check skipped: diff not fetched — "
                "TA verifies the writeup manually."
            )
        else:
            files = _files_in_diff(diff)
            hit = [f for f in files if f.endswith(target) or f == target]
            if hit:
                evidence.append("CONTRIBUTIONS file present in PR diff: %s" % hit[0])
            else:
                evidence.append(
                    "CONTRIBUTIONS file '%s' NOT in the PR diff — "
                    "completeness gate may fail; TA decides." % target
                )

    if review_reasons:
        return Finding(
            criterion, "needs-review", None, evidence,
            "%d member(s) need manual confirmation: %s" % (
                len(review_reasons), "; ".join(review_reasons)),
        )
    if any_late:
        return Finding(
            criterion, "pass", criterion.points, evidence,
            "Evidence gathered — at least one member committed after "
            "the wall; enter 8.5 for those members on the wall line. "
            "The TA awards all points.",
            ta_confirm=True,
        )
    return Finding(
        criterion, "pass", criterion.points, evidence,
        "Evidence gathered: every member's commits land by the wall; "
        "the TA awards points.",
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
    "team_best_attribution": _team_best_attribution,
    "blob_link_valid": _blob_link_valid,
    "pr_from_given_branch": _pr_from_given_branch,
    "devlog_before_canvas": _devlog_before_canvas,
    "pr_commits_by_wall": _pr_commits_by_wall,
    "pr_body_contains": _pr_body_contains,
    "doc_contains": _doc_contains,
    "reflection_entry": _reflection_entry,
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
