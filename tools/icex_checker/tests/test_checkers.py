"""Tests for the rubric checkers (FR-7, EF-9, Checker Types)."""
import pathlib

import pytest

from checkers import (
    CHECKERS,
    CheckerContext,
    run_criterion,
)
from github_client import GitHubClient, Repo
from icex_checker import AuthFailureError, PRNotAccessibleError, RateLimitError
from rubric import Criterion

SEMESTER_START = "2026-08-24"

HELLO_DIFF_OK = (
    "diff --git a/hello.c b/hello.c\n"
    "index abc1234..def5678 100644\n"
    "--- a/hello.c\n"
    "+++ b/hello.c\n"
    "@@ -1,5 +1,5 @@\n"
    " #include <stdio.h>\n"
    " int main() {\n"
    "-    printf(\"Hello World!\\n\");\n"
    "+    printf(\"Hello Zoidberg!\\n\");\n"
    "     return 0;\n"
    " }\n"
)

HELLO_DIFF_WORLD_STILL_PRESENT = (
    "diff --git a/hello.c b/hello.c\n"
    "--- a/hello.c\n"
    "+++ b/hello.c\n"
    "@@ -1,2 +1,2 @@\n"
    "-    printf(\"Hello World!\\n\");\n"
    "+    printf(\"Hello World! - Zoidberg was here\\n\");\n"
)

HELLO_DIFF_NO_PRINTF = (
    "diff --git a/hello.c b/hello.c\n"
    "--- a/hello.c\n"
    "+++ b/hello.c\n"
    "@@ -1,2 +1,2 @@\n"
    "-    // a comment\n"
    "+    // a better comment\n"
)

OTHER_FILE_DIFF = (
    "diff --git a/readme.md b/readme.md\n"
    "--- a/readme.md\n"
    "+++ b/readme.md\n"
    "@@ -1,1 +1,1 @@\n"
    "-# ICEX01\n"
    "+# ICEX01 Submission\n"
)

# GitHub emits full repo paths: a student editing the file in place gets
# '+++ b/exercises/wk1/ICEX01/hello.c' (issue #3/#6).
NESTED_PATH_DIFF = (
    "diff --git a/exercises/wk1/ICEX01/hello.c b/exercises/wk1/ICEX01/hello.c\n"
    "index abc1234..def5678 100644\n"
    "--- a/exercises/wk1/ICEX01/hello.c\n"
    "+++ b/exercises/wk1/ICEX01/hello.c\n"
    "@@ -1,5 +1,5 @@\n"
    " #include <stdio.h>\n"
    " int main() {\n"
    "-    printf(\"Hello World!\\n\");\n"
    "+    printf(\"Hello Zoidberg!\\n\");\n"
    "     return 0;\n"
    " }\n"
)

# GitHub rename syntax: '+++ b/exercises/{old => new}/hello.c' (issue #3/#6).
RENAME_DIFF = (
    "diff --git a/hello.c b/exercises/{old => new}/hello.c\n"
    "similarity index 95%\n"
    "rename from hello.c\n"
    "rename to exercises/new/hello.c\n"
    "--- a/hello.c\n"
    "+++ b/exercises/{old => new}/hello.c\n"
    "@@ -1,5 +1,5 @@\n"
    "-    printf(\"Hello World!\\n\");\n"
    "+    printf(\"Hello Zoidberg!\\n\");\n"
)


def _ctx(client, student_name="Jane Doe", pr_url="https://github.iu.edu/jdoe/fa26_c291/pull/42"):
    return CheckerContext(
        client=client,
        semester_start=SEMESTER_START,
        student_name=student_name,
        pr_url=pr_url,
    )


def _ctx_v11(client, username="jdoe", roster=None, student_name="Jane Doe"):
    ctx = CheckerContext(
        client=client,
        semester_start=SEMESTER_START,
        student_name=student_name,
        pr_url="https://github.iu.edu/mnemo-course-dev/fa26_se1_team01/pull/3",
    )
    ctx.username = username
    ctx.roster = roster
    return ctx


class _FakeClient:
    """Minimal stand-in for GitHubClient with overridable endpoint results."""

    def __init__(self):
        self.pr_data = {"number": 42, "title": "t", "body": "x" * 40, "state": "open"}
        self.pr_error = None
        self.repo_data = {
            "full_name": "jdoe/fa26_c291",
            "name": "fa26_c291",
            "owner": {"login": "jdoe"},
            "created_at": "2026-08-20T09:00:00Z",
            "html_url": "https://github.iu.edu/jdoe/fa26_c291",
        }
        self.commit_dates = ["2026-08-25T10:00:00Z"]
        self.repo_error = None
        self.commit_error = None
        self.diff_text = HELLO_DIFF_OK
        self.diff_error = None
        self.pr_commit_logins = ["jdoe"]
        self.file_kind = "missing"
        self.file_text = None
        self.file_error = None
        self.path_commits = {}
        self.path_commit_error = None
        self.pr_commit_rows = []
        self.pr_commit_error = None
        self.pulls = []
        self.calls = []

    def get_pr(self, owner, repo, number):
        self.calls.append(("pr", owner, repo, number))
        if self.pr_error:
            raise self.pr_error
        return type("PR", (), self.pr_data)()

    def get_repo(self, owner, repo):
        self.calls.append(("repo", owner, repo))
        if self.repo_error:
            raise self.repo_error
        return Repo(self.repo_data)

    def get_commit_author_dates(self, owner, repo):
        self.calls.append(("commits", owner, repo))
        if self.commit_error:
            raise self.commit_error
        return list(self.commit_dates)

    def get_pr_commit_logins(self, owner, repo, number):
        self.calls.append(("pr_commits", owner, repo, number))
        if self.commit_error:
            raise self.commit_error
        return list(self.pr_commit_logins)

    def list_pulls(self, owner, repo):
        self.calls.append(("pulls", owner, repo))
        return list(self.pulls)

    def get_file_contents(self, owner, repo, path, ref=None):
        self.calls.append(("contents", owner, repo, path, ref))
        if self.file_error:
            raise self.file_error
        return (self.file_kind, self.file_text)

    def get_commits_for_path(self, owner, repo, path=None):
        self.calls.append(("path_commits", owner, repo, path))
        if self.path_commit_error:
            raise self.path_commit_error
        return list(self.path_commits.get(owner, []))

    def get_pr_commits(self, owner, repo, number):
        self.calls.append(("pr_commits_full", owner, repo, number))
        if self.pr_commit_error:
            raise self.pr_commit_error
        return list(self.pr_commit_rows)

    def get_pr_diff(self, owner, repo, number):
        self.calls.append(("diff", owner, repo, number))
        if self.diff_error:
            raise self.diff_error
        return self.diff_text


def _criterion(checker, params=None, name="Criterion", points=1):
    return Criterion(name=name, points=points, checker=checker, params=params or {})


def _finding(criterion, ctx):
    return run_criterion(ctx, criterion)


# ---------------------------------------------------------------------------
# repo_history
# ---------------------------------------------------------------------------


class TestRepoHistory:
    def test_pass_when_commit_predates_semester(self):
        c = _FakeClient()
        c.commit_dates = ["2026-05-01T12:00:00Z", "2026-08-25T10:00:00Z"]
        f = _finding(_criterion("repo_history", points=1), _ctx(c))

        assert f.assessment == "pass"
        assert f.points_recommended == 1

    def test_fail_when_all_commits_after_semester_start(self):
        c = _FakeClient()
        c.commit_dates = ["2026-08-25T10:00:00Z", "2026-08-26T10:00:00Z"]
        f = _finding(_criterion("repo_history", points=1), _ctx(c))

        assert f.assessment == "fail"
        assert f.points_recommended == 0

    def test_fail_when_zero_commits(self):
        c = _FakeClient()
        c.commit_dates = []
        f = _finding(_criterion("repo_history", points=1), _ctx(c))

        assert f.assessment == "fail"

    def test_needs_review_when_repo_unreachable(self):
        c = _FakeClient()
        c.repo_error = PRNotAccessibleError("PR not accessible (HTTP 404)", status=404)
        f = _finding(_criterion("repo_history", points=1), _ctx(c))

        assert f.assessment == "needs-review"

    def test_needs_review_when_commits_api_fails(self):
        c = _FakeClient()
        c.commit_error = AuthFailureError("auth")
        f = _finding(_criterion("repo_history", points=1), _ctx(c))

        assert f.assessment == "needs-review"


# ---------------------------------------------------------------------------
# pr_exists_with_comment
# ---------------------------------------------------------------------------


class TestPrExistsWithComment:
    def test_pass_with_confirmation_when_body_long_enough(self):
        c = _FakeClient()
        c.pr_data["body"] = "My pull request for ICEX01."
        f = _finding(
            _criterion("pr_exists_with_comment", {"min_comment_length": 10}, points=2),
            _ctx(c),
        )

        assert f.assessment == "pass"
        assert f.points_recommended == 2
        assert f.ta_confirm is True  # TA judges "well-written"

    def test_partial_when_body_too_short(self):
        c = _FakeClient()
        c.pr_data["body"] = "ok"
        f = _finding(
            _criterion("pr_exists_with_comment", {"min_comment_length": 10}, points=2),
            _ctx(c),
        )

        assert f.assessment == "partial"
        assert f.points_recommended == 1  # half of 2

    def test_partial_when_body_empty(self):
        c = _FakeClient()
        c.pr_data["body"] = ""
        f = _finding(
            _criterion("pr_exists_with_comment", {"min_comment_length": 10}, points=2),
            _ctx(c),
        )

        assert f.assessment == "partial"

    def test_fail_when_pr_missing(self):
        c = _FakeClient()
        c.pr_error = PRNotAccessibleError("PR not accessible (HTTP 404)", status=404)
        f = _finding(
            _criterion("pr_exists_with_comment", {"min_comment_length": 10}, points=2),
            _ctx(c),
        )

        assert f.assessment == "fail"
        assert f.points_recommended == 0

    def test_needs_review_when_access_denied(self):
        c = _FakeClient()
        c.pr_error = AuthFailureError("auth")
        f = _finding(
            _criterion("pr_exists_with_comment", {"min_comment_length": 10}, points=2),
            _ctx(c),
        )

        assert f.assessment == "needs-review"

    def test_default_min_comment_length_is_10(self):
        c = _FakeClient()
        c.pr_data["body"] = "12345"  # shorter than 10
        f = _finding(_criterion("pr_exists_with_comment", points=2), _ctx(c))

        assert f.assessment == "partial"


# ---------------------------------------------------------------------------
# pr_url_valid
# ---------------------------------------------------------------------------


class TestPrUrlValid:
    def test_pass_when_pr_accessible(self):
        c = _FakeClient()
        f = _finding(_criterion("pr_url_valid", points=2), _ctx(c))

        assert f.assessment == "pass"
        assert f.points_recommended == 2

    def test_partial_when_pr_missing_but_repo_exists(self):
        c = _FakeClient()
        c.pr_error = PRNotAccessibleError("PR not accessible (HTTP 404)", status=404)
        f = _finding(_criterion("pr_url_valid", points=2), _ctx(c))

        assert f.assessment == "partial"

    def test_fail_when_everything_missing(self):
        c = _FakeClient()
        c.pr_error = PRNotAccessibleError("PR not accessible (HTTP 404)", status=404)
        c.repo_error = PRNotAccessibleError("PR not accessible (HTTP 404)", status=404)
        f = _finding(_criterion("pr_url_valid", points=2), _ctx(c))

        assert f.assessment == "fail"
        assert f.points_recommended == 0

    def test_needs_review_when_owner_does_not_match_student_name(self):
        c = _FakeClient()
        c.repo_data["owner"] = {"login": "x42_ghost"}
        c.repo_data["full_name"] = "x42_ghost/fa26_c291"
        f = _finding(
            _criterion("pr_url_valid", points=2),
            _ctx(c, pr_url="https://github.iu.edu/x42_ghost/fa26_c291/pull/42"),
        )

        assert f.assessment == "needs-review"
        assert f.ta_confirm is True

    def test_pass_notes_ownership_when_title_unparsed(self):
        """Without a student name we cannot verify ownership; mechanically the
        PR is 200, so assessment passes with a verification note."""
        c = _FakeClient()
        f = _finding(_criterion("pr_url_valid", points=2), _ctx(c, student_name=None))

        assert f.assessment == "pass"
        assert "ownership" in f.notes.lower()


# ---------------------------------------------------------------------------
# valid_student_repo
# ---------------------------------------------------------------------------


class TestValidStudentRepo:
    @staticmethod
    def _criterion():
        return _criterion(
            "valid_student_repo",
            {"expected_repo_pattern": "fa26_c291", "github_host": "github.iu.edu"},
            points=2,
        )

    def test_pass_when_name_matches_pattern(self):
        c = _FakeClient()
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "pass"
        assert f.points_recommended == 2

    def test_partial_when_name_is_close_match(self):
        c = _FakeClient()
        c.repo_data["name"] = "fa26-c291"  # close to fa26_c291
        c.repo_data["full_name"] = "jdoe/fa26-c291"
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "partial"
        assert f.points_recommended == 1

    def test_fail_when_name_unrelated(self):
        c = _FakeClient()
        c.repo_data["name"] = "my-random-project"
        c.repo_data["full_name"] = "jdoe/my-random-project"
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "fail"

    def test_fail_when_repo_does_not_exist(self):
        c = _FakeClient()
        c.repo_error = PRNotAccessibleError("PR not accessible (HTTP 404)", status=404)
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "fail"

    def test_needs_review_when_owner_does_not_look_like_student(self):
        c = _FakeClient()
        c.repo_data["owner"] = {"login": "sysadmin"}
        c.repo_data["full_name"] = "sysadmin/fa26_c291"
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "needs-review"

    def test_pattern_match_is_case_insensitive(self):
        c = _FakeClient()
        c.repo_data["name"] = "FA26_C291"
        c.repo_data["full_name"] = "jdoe/FA26_C291"
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "pass"


# ---------------------------------------------------------------------------
# diff_content_check
# ---------------------------------------------------------------------------


class TestDiffContentCheck:
    @staticmethod
    def _criterion():
        return _criterion(
            "diff_content_check",
            {"target_file": "hello.c", "must_contain_modified": "printf", "must_not_contain": "World"},
            points=3,
        )

    def test_pass_with_confirmation_when_all_checks_mechanical(self):
        c = _FakeClient()
        c.diff_text = HELLO_DIFF_OK
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "pass"
        assert f.points_recommended == 3
        assert f.ta_confirm is True  # TA verifies the name

    def test_world_in_removed_line_does_not_fail(self):
        """The -line 'Hello World' is the OLD code; only added lines matter."""
        c = _FakeClient()
        c.diff_text = HELLO_DIFF_OK
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "pass"

    def test_partial_when_world_still_in_added_lines(self):
        c = _FakeClient()
        c.diff_text = HELLO_DIFF_WORLD_STILL_PRESENT
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "partial"
        assert f.points_recommended == 1.5  # half of 3

    def test_partial_when_printf_not_in_added_lines(self):
        c = _FakeClient()
        c.diff_text = HELLO_DIFF_NO_PRINTF
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "partial"

    def test_fail_when_target_file_not_in_diff(self):
        c = _FakeClient()
        c.diff_text = OTHER_FILE_DIFF
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "fail"
        assert f.points_recommended == 0

    def test_fail_when_diff_empty(self):
        c = _FakeClient()
        c.diff_text = ""
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "fail"

    def test_nested_path_matches_bare_target_file(self):
        """Issues #3/#6: 'hello.c' must match 'exercises/wk1/ICEX01/hello.c'."""
        c = _FakeClient()
        c.diff_text = NESTED_PATH_DIFF
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "pass"
        assert f.ta_confirm is True

    def test_nested_path_failure_reports_true_reason(self):
        """Issue #3: when the content check fails on a nested path, the note
        must name the CONTENT failure, not claim the file is absent."""
        c = _FakeClient()
        c.diff_text = NESTED_PATH_DIFF
        crit = _criterion(
            "diff_content_check",
            {"target_file": "hello.c", "must_not_contain": "Zoidberg"},
            points=3,
        )
        f = _finding(crit, _ctx(c))

        assert f.assessment == "partial"
        assert "not in the diff" not in f.notes
        assert "Zoidberg" in f.notes

    def test_rename_syntax_matches_target_file(self):
        """Issues #3/#6: GitHub rename paths 'a/{old => new}/hello.c' must
        match a bare 'hello.c' target."""
        c = _FakeClient()
        c.diff_text = RENAME_DIFF
        f = _finding(self._criterion(), _ctx(c))

        assert f.assessment == "pass"
        assert f.ta_confirm is True


# ---------------------------------------------------------------------------
# registry / unknown checker
# ---------------------------------------------------------------------------


def test_registry_has_expected_checkers():
    assert set(CHECKERS) == {
        "repo_history",
        "pr_exists_with_comment",
        "pr_url_valid",
        "valid_student_repo",
        "diff_content_check",
        "manual_review",
        "pattern_count",
        "commit_author_check",
        "team_best_attribution",
        "blob_link_valid",
        "pr_from_given_branch",
        "devlog_before_canvas",
        "pr_commits_by_wall",
        "pr_body_contains",
        "doc_contains",
        "reflection_entry",
    }


def test_unknown_checker_is_needs_review_not_fatal():
    """EF-9: unknown checker -> needs-review with explicit note; tool continues."""
    c = _FakeClient()
    f = _finding(_criterion("time_travel_checker", points=2), _ctx(c))

    assert f.assessment == "needs-review"
    assert "unknown checker type" in f.notes


def test_manual_review_shows_label_and_needs_review():
    """manual_review checker returns needs-review with the label from params."""
    c = _FakeClient()
    crit = Criterion(
        name="AG Score", points=85, checker="manual_review",
        params={"label": "Enter AG score (0-85) from https://ag.example.com"},
    )
    f = _finding(crit, _ctx(c))

    assert f.assessment == "needs-review"
    assert f.points_recommended is None
    assert "Enter AG score" in f.notes
    assert "https://ag.example.com" in f.notes


# ---------------------------------------------------------------------------
# pattern_count
# ---------------------------------------------------------------------------

ARTTREE_DIFF = (
    "diff --git a/exercises/wk1/PASN01/arttree.c b/exercises/wk1/PASN01/arttree.c\n"
    "--- a/exercises/wk1/PASN01/arttree.c\n"
    "+++ b/exercises/wk1/PASN01/arttree.c\n"
    "@@ -0,0 +1,12 @@\n"
    "+/* arttree.c\n"
    "+ * programmer: Jane Doe\n"
    "+ */\n"
    "+#include <stdio.h>\n"
    "+int main() {\n"
    '+    printf("      &\\n");\n'
    '+    printf("     #o#\\n");\n'
    '+    printf("    ##*##\\n");\n'
    '+    printf("  ###*#*###  ||");\n'
    "+    return 0;\n"
    "+}\n"
)


class TestPatternCount:
    def test_pass_when_count_matches_expected(self):
        """4 printf statements in added lines, expect exactly 4."""
        c = _FakeClient()
        c.diff_text = ARTTREE_DIFF
        f = _finding(
            _criterion("pattern_count", params={
                "target_file": "exercises/wk1/PASN01/arttree.c",
                "pattern": r"printf\s*\(",
                "expected_count": 4,
            }, points=20),
            _ctx(c),
        )
        assert f.assessment == "pass"
        assert f.points_recommended == 20

    def test_fail_when_count_does_not_match(self):
        """3 printf statements but expect 4."""
        diff_3_printf = ARTTREE_DIFF.replace(
            '+    printf("  ###*#*###  ||");\n', ''
        )
        c = _FakeClient()
        c.diff_text = diff_3_printf
        f = _finding(
            _criterion("pattern_count", params={
                "target_file": "exercises/wk1/PASN01/arttree.c",
                "pattern": r"printf\s*\(",
                "expected_count": 4,
            }, points=20),
            _ctx(c),
        )
        assert f.assessment == "fail"
        assert f.points_recommended == 0

    def test_fail_when_target_file_not_in_diff(self):
        c = _FakeClient()
        c.diff_text = OTHER_FILE_DIFF
        f = _finding(
            _criterion("pattern_count", params={
                "target_file": "exercises/wk1/PASN01/arttree.c",
                "pattern": r"printf\s*\(",
                "expected_count": 4,
            }, points=20),
            _ctx(c),
        )
        assert f.assessment == "fail"
        assert f.points_recommended == 0

    def test_pass_with_at_least_count(self):
        """Count newlines in printf format strings, at least 1 expected."""
        c = _FakeClient()
        c.diff_text = ARTTREE_DIFF
        f = _finding(
            _criterion("pattern_count", params={
                "target_file": "exercises/wk1/PASN01/arttree.c",
                "pattern": r'\\n',
                "expected_count": 1,
                "comparison": "at_least",
            }, points=20),
            _ctx(c),
        )
        assert f.assessment == "pass"

    def test_fail_with_at_most_count(self):
        """At most 1 printf with \\n, but 3 have it."""
        c = _FakeClient()
        c.diff_text = ARTTREE_DIFF
        f = _finding(
            _criterion("pattern_count", params={
                "target_file": "exercises/wk1/PASN01/arttree.c",
                "pattern": r'\\n',
                "expected_count": 1,
                "comparison": "at_most",
            }, points=20),
            _ctx(c),
        )
        assert f.assessment == "fail"

    def test_evidence_includes_count_found(self):
        c = _FakeClient()
        c.diff_text = ARTTREE_DIFF
        f = _finding(
            _criterion("pattern_count", params={
                "target_file": "exercises/wk1/PASN01/arttree.c",
                "pattern": r"printf\s*\(",
                "expected_count": 4,
            }, points=20),
            _ctx(c),
        )
        assert any("4" in e for e in f.evidence)

    def test_counts_occurrences_not_lines(self):
        """Two printf on ONE line must count as 2, not 1."""
        c = _FakeClient()
        c.diff_text = (
            "diff --git a/arttree.c b/arttree.c\n"
            "--- a/arttree.c\n"
            "+++ b/arttree.c\n"
            "@@ -1,1 +1,1 @@\n"
            '+    printf("a"); printf("b");\n'
        )
        f = _finding(
            _criterion("pattern_count", params={
                "target_file": "arttree.c",
                "pattern": r"printf\s*\(",
                "expected_count": 2,
            }, points=20),
            _ctx(c),
        )
        assert f.assessment == "pass"
        assert "found 2 time(s)" in f.evidence[-1]

    def test_counts_multiple_newline_escapes_in_one_string(self):
        """Two \\n escapes in ONE format string must count as 2, not 1."""
        c = _FakeClient()
        c.diff_text = (
            "diff --git a/arttree.c b/arttree.c\n"
            "--- a/arttree.c\n"
            "+++ b/arttree.c\n"
            "@@ -1,1 +1,1 @@\n"
            '+    printf("a\\nb\\n");\n'
        )
        f = _finding(
            _criterion("pattern_count", params={
                "target_file": "arttree.c",
                "pattern": r"\\n",
                "expected_count": 1,
                "comparison": "at_most",
            }, points=20),
            _ctx(c),
        )
        assert f.assessment == "fail"  # 2 occurrences > at_most 1
        assert "found 2 time(s)" in f.evidence[-1]


# ---------------------------------------------------------------------------
# commit_author_check (V1-2)
# ---------------------------------------------------------------------------


class _RosterStub:
    """Minimal roster stand-in mirroring the real Roster API (find_team)."""

    def __init__(self, user_to_team):
        self._map = user_to_team

    def find_team(self, username):
        return self._map.get(username)


class TestCommitAuthorCheck:
    @staticmethod
    def _criterion():
        return _criterion("commit_author_check", points=0)

    def test_pass_when_student_login_is_commit_author(self):
        c = _FakeClient()
        c.pr_commit_logins = ["rhaldhah", "jdoe"]
        ctx = _ctx_v11(c, username="jdoe", roster=_RosterStub({"jdoe": "team01"}))
        f = _finding(self._criterion(), ctx)

        assert f.assessment == "pass"
        assert "jdoe" in f.evidence[-1]

    def test_fail_with_ta_confirm_when_login_not_in_commits(self):
        """Wrong submission: roster available, student's login absent."""
        c = _FakeClient()
        c.pr_commit_logins = ["rhaldhah"]
        ctx = _ctx_v11(c, username="jdoe", roster=_RosterStub({"jdoe": "team01"}))
        f = _finding(self._criterion(), ctx)

        assert f.assessment == "fail"
        assert f.ta_confirm is True
        assert f.points_recommended == 0

    def test_needs_review_when_no_roster(self):
        """EF-12: no roster -> evidence-only, commit authors listed."""
        c = _FakeClient()
        c.pr_commit_logins = ["rhaldhah", "jdoe"]
        f = _finding(self._criterion(), _ctx_v11(c, username="jdoe", roster=None))

        assert f.assessment == "needs-review"
        assert "rhaldhah" in f.evidence[-1]

    def test_needs_review_when_username_missing(self):
        """EF-13: unrecognized filename -> evidence-only."""
        c = _FakeClient()
        c.pr_commit_logins = ["rhaldhah"]
        ctx = _ctx_v11(c, username=None, roster=_RosterStub({"jdoe": "team01"}))
        f = _finding(self._criterion(), ctx)

        assert f.assessment == "needs-review"

    def test_needs_review_when_login_not_in_roster(self):
        c = _FakeClient()
        c.pr_commit_logins = ["rhaldhah"]
        ctx = _ctx_v11(c, username="ghost", roster=_RosterStub({}))
        f = _finding(self._criterion(), ctx)

        assert f.assessment == "needs-review"


# ---------------------------------------------------------------------------
# team_best_attribution (V1-6)
# ---------------------------------------------------------------------------


class TestTeamBestAttribution:
    @staticmethod
    def _criterion():
        return _criterion("team_best_attribution", points=0)

    def _ctx(self, c, username="jdoe", roster=None):
        return _ctx_v11(c, username=username, roster=roster)

    def test_pass_when_student_has_merged_pr(self):
        c = _FakeClient()
        c.pulls = [
            {"number": 8, "author": "jdoe", "state": "merged", "title": "add name"},
            {"number": 9, "author": "rhaldhah", "state": "merged", "title": "add email"},
        ]
        ctx = self._ctx(c, username="jdoe", roster=_RosterStub({"jdoe": "team01"}))
        f = _finding(self._criterion(), ctx)

        assert f.assessment == "pass"

    def test_pass_when_student_has_open_pr(self):
        c = _FakeClient()
        c.pulls = [
            {"number": 10, "author": "jdoe", "state": "open", "title": "add name"},
        ]
        ctx = self._ctx(c, username="jdoe", roster=_RosterStub({"jdoe": "team01"}))
        f = _finding(self._criterion(), ctx)

        assert f.assessment == "pass"

    def test_ta_confirm_when_only_closed_unmerged(self):
        """Attempted but never merged — TA should confirm (V1-6 semantics)."""
        c = _FakeClient()
        c.pulls = [
            {"number": 9, "author": "jdoe", "state": "closed", "title": "add name"},
        ]
        ctx = self._ctx(c, username="jdoe", roster=_RosterStub({"jdoe": "team01"}))
        f = _finding(self._criterion(), ctx)

        assert f.assessment == "pass"  # still evidence of attempt
        assert f.ta_confirm is True

    def test_fail_when_no_prs_and_roster_available(self):
        c = _FakeClient()
        c.pulls = [{"number": 9, "author": "rhaldhah", "state": "merged", "title": "x"}]
        ctx = self._ctx(c, username="jdoe", roster=_RosterStub({"jdoe": "team01"}))
        f = _finding(self._criterion(), ctx)

        assert f.assessment == "fail"
        assert f.points_recommended == 0

    def test_needs_review_when_no_roster(self):
        c = _FakeClient()
        c.pulls = [{"number": 9, "author": "jdoe", "state": "merged", "title": "x"}]
        f = _finding(self._criterion(), self._ctx(c, username="jdoe", roster=None))

        assert f.assessment == "needs-review"

    def test_evidence_lists_team_pr_counts(self):
        """V1-6 evidence: per-member PR counts for TA context."""
        c = _FakeClient()
        c.pulls = [
            {"number": 8, "author": "jdoe", "state": "merged", "title": "a"},
            {"number": 9, "author": "rhaldhah", "state": "merged", "title": "b"},
        ]
        ctx = self._ctx(c, username="jdoe", roster=_RosterStub({"jdoe": "team01"}))
        f = _finding(self._criterion(), ctx)

        team_evidence = [e for e in f.evidence if "PRs" in e]
        assert any("jdoe: 1" in e for e in team_evidence)
        assert any("rhaldhah: 1" in e for e in team_evidence)


class TestPrUrlValidUsernameOwnership:
    """Issue #6: deterministic username-vs-owner comparison replaces
    name-matching when the Canvas filename username is available."""

    def test_username_owner_match_passes(self):
        c = _FakeClient()
        ctx = CheckerContext(
            client=c, semester_start=SEMESTER_START, student_name="Jane Doe",
            pr_url="https://github.iu.edu/jdoe/fa26_c291/pull/42",
        )
        ctx.username = "jdoe"  # from Canvas filename (V1-3)
        f = _finding(
            _criterion("pr_url_valid", {"ownership_check": "student"}), ctx
        )

        assert f.assessment == "pass"
        assert any("owner matches IU username" in e for e in f.evidence)

    def test_username_owner_mismatch_needs_review_with_confirm(self):
        """Issue #6 live case: albarwanialmukhtar submitted a PR owned by
        alalbarw — a genuine mismatch the tool must surface, not silence."""
        c = _FakeClient()
        ctx = CheckerContext(
            client=c, semester_start=SEMESTER_START, student_name="Jane Doe",
            pr_url="https://github.iu.edu/alalbarw/fa26_c291/pull/5",
        )
        ctx.username = "albarwanialmukhtar"
        f = _finding(
            _criterion("pr_url_valid", {"ownership_check": "student"}), ctx
        )

        assert f.assessment == "needs-review"
        assert f.ta_confirm is True
        assert "alalbarw" in f.notes
        assert "albarwanialmukhtar" in f.notes

    def test_username_match_takes_priority_over_name_heuristic(self):
        """Username comparison is deterministic — it wins over name-matching
        even when the name heuristic would say otherwise."""
        c = _FakeClient()
        ctx = CheckerContext(
            client=c, semester_start=SEMESTER_START, student_name="Zaphod Beeblebrox",
            pr_url="https://github.iu.edu/jdoe/fa26_c291/pull/42",
        )
        ctx.username = "jdoe"
        f = _finding(
            _criterion("pr_url_valid", {"ownership_check": "student"}), ctx
        )

        assert f.assessment == "pass"

    def test_no_username_falls_back_to_name_matching(self):
        """v1.0 behavior preserved when the filename yields no username."""
        c = _FakeClient()
        ctx = CheckerContext(
            client=c, semester_start=SEMESTER_START, student_name="Jane Doe",
            pr_url="https://github.iu.edu/jdoe/fa26_c291/pull/42",
        )
        ctx.username = None
        f = _finding(
            _criterion("pr_url_valid", {"ownership_check": "student"}), ctx
        )

        assert f.assessment == "pass"  # name heuristic still matches jdoe


# ---------------------------------------------------------------------------
# ownership_check toggle (V1-1) — pr_url_valid behavior
# ---------------------------------------------------------------------------


class TestPrUrlValidOwnership:
    @staticmethod
    def _criterion(ownership_check="student"):
        return _criterion(
            "pr_url_valid",
            {"ownership_check": ownership_check},
            points=2,
        )

    def _ctx(self, c, username="jdoe", roster=None):
        return _ctx_v11(c, username=username, roster=roster)

    def _personal_ctx(self, c, username="jdoe", roster=None):
        """Student-mode context: PR in the student's OWN repo (C291 style)."""
        ctx = CheckerContext(
            client=c,
            semester_start=SEMESTER_START,
            student_name="Jane Doe",
            pr_url="https://github.iu.edu/jdoe/fa26_c291/pull/42",
        )
        ctx.username = username
        ctx.roster = roster
        return ctx

    def test_team_mode_without_roster_needs_review(self):
        """ownership_check: team, no roster -> cannot verify membership ->
        needs-review (evidence-only, EF-12). needs-review IS the action
        item — no separate ta_confirm (D-1 semantics)."""
        c = _FakeClient()
        f = _finding(self._criterion("team"), self._ctx(c))

        assert f.assessment == "needs-review"
        assert f.ta_confirm is False
        # No student-name matching runs in team mode
        assert not any("owner matches student name" in e for e in f.evidence)

    def test_team_mode_with_roster_verifies_membership(self):
        """ownership_check: team + roster -> membership verified via roster team."""
        c = _FakeClient()
        roster = _RosterStub({"jdoe": "team01"})
        f = _finding(self._criterion("team"), self._ctx(c, username="jdoe", roster=roster))

        assert f.assessment == "pass"
        assert any("team01" in e for e in f.evidence)

    def test_student_mode_default_matches_submitter(self):
        """ownership_check: student (default) -> owner must match submitter."""
        c = _FakeClient()
        f = _finding(self._criterion("student"), self._personal_ctx(c, username="jdoe"))

        assert f.assessment == "pass"
        assert any(
            "owner matches IU username" in e or "owner matches student name" in e
            for e in f.evidence
        )

    def test_none_mode_skips_all_ownership(self):
        c = _FakeClient()
        f = _finding(self._criterion("none"), self._ctx(c, username="jdoe"))

        assert f.assessment == "pass"
