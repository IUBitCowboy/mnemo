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


def _ctx(client, student_name="Jane Doe", pr_url="https://github.iu.edu/jdoe/fa26_c291/pull/42"):
    return CheckerContext(
        client=client,
        semester_start=SEMESTER_START,
        student_name=student_name,
        pr_url=pr_url,
    )


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


# ---------------------------------------------------------------------------
# registry / unknown checker
# ---------------------------------------------------------------------------


def test_registry_has_all_five_checkers():
    assert set(CHECKERS) == {
        "repo_history",
        "pr_exists_with_comment",
        "pr_url_valid",
        "valid_student_repo",
        "diff_content_check",
    }


def test_unknown_checker_is_needs_review_not_fatal():
    """EF-9: unknown checker -> needs-review with explicit note; tool continues."""
    c = _FakeClient()
    f = _finding(_criterion("time_travel_checker", points=2), _ctx(c))

    assert f.assessment == "needs-review"
    assert "unknown checker type" in f.notes
    assert f.points_recommended == 0
