"""Tests for the MoJ checkers (blob_link_valid, pr_from_given_branch,
devlog_before_canvas) and the URL/title parser extensions (FA26
greenfield: direct-GitHub blob submissions, MoJ Canvas titles).
"""
import pathlib

import pytest

from checkers import (
    CHECKERS,
    parse_github_url,
)
from icex_checker import (
    AuthFailureError,
    PRNotAccessibleError,
    RateLimitError,
    _split_pr_url,
    parse_submission,
)
import rubric
import checkers
from roster import Roster
from errors import (AuthFailureError, PRNotAccessibleError, RateLimitError,
                    SubmissionNotFoundError)

from test_checkers import _FakeClient, _ctx, _ctx_v11, _criterion, _finding

SEMESTER_START = "2026-08-24"

BLOB_URL_MAIN = (
    "https://github.iu.edu/mnemo-course-dev/fa26_se1_team01/"
    "blob/main/docs/a_mj05_ethics_opener.md"
)
BLOB_URL_SLASHREF = (
    "https://github.iu.edu/mnemo-course-dev/fa26_se1_team01/"
    "blob/feature/x/docs/a_mj05_ethics_opener.md"
)


# ---------------------------------------------------------------------------
# parse_github_url
# ---------------------------------------------------------------------------


class TestParseGithubUrl:
    def test_pull_form(self):
        p = parse_github_url("https://github.iu.edu/org/repo/pull/17")
        assert p["kind"] == "pull"
        assert (p["owner"], p["repo"], p["number"]) == ("org", "repo", 17)
        assert p["ref"] is None and p["path"] is None

    def test_blob_form_main_ref(self):
        p = parse_github_url(BLOB_URL_MAIN)
        assert p["kind"] == "blob"
        assert p["owner"] == "mnemo-course-dev"
        assert p["repo"] == "fa26_se1_team01"
        assert p["ref"] == "main"
        assert p["path"] == "docs/a_mj05_ethics_opener.md"

    def test_blob_naive_split_is_ambiguous_for_slash_refs(self):
        p = parse_github_url(BLOB_URL_SLASHREF)
        assert p["kind"] == "blob"
        assert (p["ref"], p["path"]) == ("feature", "x/docs/a_mj05_ethics_opener.md")

    def test_none_for_non_github_url(self):
        assert parse_github_url("https://example.edu/repo/pull/1") is None
        assert parse_github_url("") is None
        assert parse_github_url(None) is None


def test_blob_path_suffix_resolution():
    """The criterion's expected path decides the ambiguous ref split."""
    from checkers import _blob_path_matches

    ok, eff = _blob_path_matches("x/docs/a_mj05_ethics_opener.md",
                                 "docs/a_mj05_ethics_opener.md")
    assert ok and eff == "docs/a_mj05_ethics_opener.md"
    ok, _ = _blob_path_matches("x/docs/other.md", "docs/a_mj05_ethics_opener.md")
    assert not ok
    ok, eff = _blob_path_matches("anything.md", "")
    assert ok and eff == "anything.md"


# ---------------------------------------------------------------------------
# blob_link_valid
# ---------------------------------------------------------------------------


class TestBlobLinkValid:
    def test_pass_when_file_exists_at_expected_path(self):
        c = _FakeClient()
        c.file_kind, c.file_text = "file", "# Ethics Opener\n"
        f = _finding(
            _criterion(
                "blob_link_valid",
                {
                    "expected_path": "docs/a_mj05_ethics_opener.md",
                    "expected_ref": "main",
                    "expected_repo_pattern": "fa26_se1_team",
                },
                points=0,
            ),
            _ctx(c, pr_url=BLOB_URL_MAIN),
        )
        assert f.assessment == "pass"
        assert ("contents", "mnemo-course-dev", "fa26_se1_team01",
                "docs/a_mj05_ethics_opener.md", "main") in c.calls

    def test_fail_when_file_missing(self):
        c = _FakeClient()
        c.file_kind = "missing"
        f = _finding(
            _criterion("blob_link_valid",
                       {"expected_path": "docs/a_mj05_ethics_opener.md"}, points=0),
            _ctx(c, pr_url=BLOB_URL_MAIN),
        )
        assert f.assessment == "fail"

    def test_fail_when_ref_mismatches(self):
        c = _FakeClient()
        alt = BLOB_URL_MAIN.replace("/blob/main/", "/blob/develop/")
        f = _finding(
            _criterion("blob_link_valid",
                       {"expected_ref": "main", "expected_path": "docs/a_mj05_ethics_opener.md"},
                       points=0),
            _ctx(c, pr_url=alt),
        )
        assert f.assessment == "fail"

    def test_fail_when_not_a_blob_url(self):
        c = _FakeClient()
        f = _finding(
            _criterion("blob_link_valid", {"expected_path": "docs/x.md"}, points=0),
            _ctx(c, pr_url="https://github.iu.edu/org/repo/pull/5"),
        )
        assert f.assessment == "fail"

    def test_fail_when_repo_pattern_mismatches(self):
        c = _FakeClient()
        c.file_kind = "file"
        f = _finding(
            _criterion("blob_link_valid",
                       {"expected_path": "docs/a_mj05_ethics_opener.md",
                        "expected_repo_pattern": "fa26_se1_team"},
                       points=0),
            _ctx(c, pr_url="https://github.iu.edu/jdoe/fa26-devlog-jdoe/blob/main/docs/a_mj05_ethics_opener.md"),
        )
        assert f.assessment == "fail"

    def test_fail_when_path_is_a_directory(self):
        c = _FakeClient()
        c.file_kind = "dir"
        f = _finding(
            _criterion("blob_link_valid", {"expected_path": "docs"}, points=0),
            _ctx(c, pr_url=BLOB_URL_MAIN.replace(
                "blob/main/docs/a_mj05_ethics_opener.md", "blob/main/docs")),
        )
        assert f.assessment == "fail"

    def test_needs_review_without_url(self):
        c = _FakeClient()
        f = _finding(
            _criterion("blob_link_valid", {}, points=0), _ctx(c, pr_url=None)
        )
        assert f.assessment == "needs-review"

    def test_needs_review_on_auth_failure(self):
        c = _FakeClient()
        c.file_error = AuthFailureError("auth")
        f = _finding(
            _criterion("blob_link_valid", {"expected_path": "docs/a_mj05_ethics_opener.md"},
                       points=0),
            _ctx(c, pr_url=BLOB_URL_MAIN),
        )
        assert f.assessment == "needs-review"


# ---------------------------------------------------------------------------
# pr_from_given_branch
# ---------------------------------------------------------------------------


class TestPrFromGivenBranch:
    def test_pass_when_given_pr_merged(self):
        c = _FakeClient()
        c.pulls = [
            {"number": 14, "author": "seiffert", "title": "desk screen",
             "state": "merged", "merged_at": "2026-11-11T09:00:00Z",
             "head_ref": "given/wk12-desk-edit"},
            {"number": 15, "author": "jdoe", "title": "team work",
             "state": "open", "merged_at": None, "head_ref": "icex/wk12-red-ink"},
        ]
        f = _finding(
            _criterion("pr_from_given_branch",
                       {"source_branch": "given/wk12-desk-edit", "state": "merged"},
                       points=0),
            _ctx_v11(c, username="jdoe"),
        )
        assert f.assessment == "pass"

    def test_fail_when_pr_open_but_merge_required(self):
        c = _FakeClient()
        c.pulls = [
            {"number": 14, "author": "seiffert", "title": "desk screen",
             "state": "open", "merged_at": None, "head_ref": "given/wk12-desk-edit"},
        ]
        f = _finding(
            _criterion("pr_from_given_branch",
                       {"source_branch": "given/wk12-desk-edit", "state": "merged"},
                       points=0),
            _ctx_v11(c, username="jdoe"),
        )
        assert f.assessment == "fail"

    def test_fail_when_no_matching_branch(self):
        c = _FakeClient()
        c.pulls = [
            {"number": 15, "author": "jdoe", "title": "team work",
             "state": "open", "merged_at": None, "head_ref": "icex/wk12-red-ink"},
        ]
        f = _finding(
            _criterion("pr_from_given_branch",
                       {"source_branch": "given/wk12-desk-edit"}, points=0),
            _ctx_v11(c, username="jdoe"),
        )
        assert f.assessment == "fail"

    def test_state_any_passes_on_open(self):
        c = _FakeClient()
        c.pulls = [
            {"number": 14, "author": "seiffert", "title": "desk screen",
             "state": "open", "merged_at": None, "head_ref": "given/wk12-desk-edit"},
        ]
        f = _finding(
            _criterion("pr_from_given_branch",
                       {"source_branch": "given/wk12-desk-edit", "state": "any"},
                       points=0),
            _ctx_v11(c, username="jdoe"),
        )
        assert f.assessment == "pass"

    def test_needs_review_on_rate_limit(self):
        c = _FakeClient()

        def boom(owner, repo):
            raise RateLimitError("rate limited")

        c.list_pulls = boom
        f = _finding(
            _criterion("pr_from_given_branch",
                       {"source_branch": "given/wk12-desk-edit"}, points=0),
            _ctx_v11(c, username="jdoe"),
        )
        assert f.assessment == "needs-review"


# ---------------------------------------------------------------------------
# devlog_before_canvas
# ---------------------------------------------------------------------------


TEAM = {"Team01": ["jdoe", "rhaldhah", "akumar"]}


def _stamp_csv(tmp_path, rows=(("Team01", "2026-11-10T21:05:00Z"),)):
    p = tmp_path / "times_a_mj05.csv"
    lines = ["Team,SubmittedAt"]
    lines += ["%s,%s" % row for row in rows]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


class TestDevlogBeforeCanvas:
    def _roster(self):
        return Roster(TEAM)

    def test_pass_when_all_entries_precede_submission(self, tmp_path):
        c = _FakeClient()
        c.path_commits = {
            "jdoe": [{"sha": "aaa11111", "date": "2026-11-09T15:00:00Z",
                      "author": "jdoe"}],
            "rhaldhah": [{"sha": "bbb22222", "date": "2026-11-10T20:00:00Z",
                          "author": "rhaldhah"}],
            "akumar": [{"sha": "ccc33333", "date": "2026-11-08T09:00:00Z",
                        "author": "akumar"}],
        }
        f = _finding(
            _criterion("devlog_before_canvas",
                       {"timestamps_file": _stamp_csv(tmp_path),
                        "devlog_repo_pattern": "fa26-devlog-{username}"},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=self._roster()),
        )
        assert f.assessment == "pass"
        assert any("aaa11111" in e for e in f.evidence)

    def test_fail_when_entry_lands_after_submission(self, tmp_path):
        c = _FakeClient()
        c.path_commits = {
            "jdoe": [{"sha": "aaa11111", "date": "2026-11-09T15:00:00Z",
                      "author": "jdoe"}],
            "rhaldhah": [{"sha": "bbb22222", "date": "2026-11-10T20:00:00Z",
                          "author": "rhaldhah"}],
            "akumar": [{"sha": "ddd44444", "date": "2026-11-11T08:00:00Z",
                        "author": "akumar"}],
        }
        f = _finding(
            _criterion("devlog_before_canvas",
                       {"timestamps_file": _stamp_csv(tmp_path),
                        "devlog_repo_pattern": "fa26-devlog-{username}"},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=self._roster()),
        )
        assert f.assessment == "fail"
        assert "EngLog" in f.notes

    def test_needs_review_without_timestamps_file(self):
        c = _FakeClient()
        c.path_commits = {"jdoe": [{"sha": "aaa11111",
                                    "date": "2026-11-09T15:00:00Z",
                                    "author": "jdoe"}]}
        f = _finding(
            _criterion("devlog_before_canvas",
                       {"devlog_repo_pattern": "fa26-devlog-{username}"},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=self._roster()),
        )
        assert f.assessment == "needs-review"

    def test_needs_review_when_roster_missing(self):
        c = _FakeClient()
        f = _finding(
            _criterion("devlog_before_canvas", {}, points=0),
            _ctx_v11(c, username="jdoe", roster=None),
        )
        assert f.assessment == "needs-review"

    def test_needs_review_when_devlog_repo_missing(self, tmp_path):
        c = _FakeClient()
        c.path_commit_error = PRNotAccessibleError(
            "PR not accessible (HTTP 404)", status=404
        )
        f = _finding(
            _criterion("devlog_before_canvas",
                       {"timestamps_file": _stamp_csv(tmp_path),
                        "devlog_repo_pattern": "fa26-devlog-{username}"},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=self._roster()),
        )
        assert f.assessment == "needs-review"

    def test_naive_timestamp_is_read_as_utc(self, tmp_path):
        p = tmp_path / "times.csv"
        p.write_text("Team,SubmittedAt\nTeam01,2026-11-10 21:05:00\n",
                     encoding="utf-8")
        c = _FakeClient()
        c.path_commits = {
            m: [{"sha": "aaa11111", "date": "2026-11-09T15:00:00Z",
                 "author": m}]
            for m in ("jdoe", "rhaldhah", "akumar")
        }
        f = _finding(
            _criterion("devlog_before_canvas",
                       {"timestamps_file": str(p),
                        "devlog_repo_pattern": "fa26-devlog-{username}"},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=self._roster()),
        )
        assert f.assessment == "pass"

    def test_no_commits_for_member_needs_review(self, tmp_path):
        c = _FakeClient()
        c.path_commits = {
            "jdoe": [{"sha": "aaa11111", "date": "2026-11-09T15:00:00Z",
                      "author": "jdoe"}],
        }
        f = _finding(
            _criterion("devlog_before_canvas",
                       {"timestamps_file": _stamp_csv(tmp_path),
                        "devlog_repo_pattern": "fa26-devlog-{username}"},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=self._roster()),
        )
        assert f.assessment == "needs-review"
        assert any("rhaldhah" in e for e in f.evidence) or \
            "rhaldhah" in f.notes


# ---------------------------------------------------------------------------
# pr_commits_by_wall (W8 wall evidence)
# ---------------------------------------------------------------------------


WALLS_CSV = "Team,WallMJ01,WallMJ02\nTeam01,2026-10-05T16:00:00Z,2026-10-07T16:00:00Z\n"


def _wall_csv(tmp_path):
    p = tmp_path / "walls_wk08.csv"
    p.write_text(WALLS_CSV, encoding="utf-8")
    return str(p)


class TestPrCommitsByWall:
    def _c(self, rows):
        c = _FakeClient()
        c.pr_commit_rows = rows
        c.diff_text = (
            "diff --git a/CONTRIBUTIONS.md b/CONTRIBUTIONS.md\n"
            "--- a/CONTRIBUTIONS.md\n"
            "+++ b/CONTRIBUTIONS.md\n"
            "@@ -1,1 +1,2 @@\n"
            "+found: roles assigned\n"
        )
        return c

    def test_pass_when_all_commits_land_by_their_walls(self, tmp_path):
        c = self._c([
            {"sha": "aaa11111", "login": "jdoe",
             "date": "2026-10-05T15:00:00Z", "message": "skeleton"},
            {"sha": "bbb22222", "login": "rhaldhah",
             "date": "2026-10-07T15:00:00Z", "message": "diagnosis"},
            {"sha": "ccc33333", "login": "akumar",
             "date": "2026-10-07T15:30:00Z", "message": "tests"},
        ])
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": _wall_csv(tmp_path),
                        "wall_columns": ["WallMJ01", "WallMJ02"]},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=Roster(TEAM)),
        )
        assert f.assessment == "pass"
        assert f.ta_confirm is False
        assert any("CONTRIBUTIONS" in e for e in f.evidence)

    def test_late_commit_surfaces_as_ta_confirm(self, tmp_path):
        c = self._c([
            {"sha": "aaa11111", "login": "jdoe",
             "date": "2026-10-05T15:00:00Z", "message": "skeleton"},
            {"sha": "bbb22222", "login": "rhaldhah",
             "date": "2026-10-07T15:00:00Z", "message": "diagnosis"},
            {"sha": "ddd44444", "login": "akumar",
             "date": "2026-10-08T09:00:00Z", "message": "late fix"},
        ])
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": _wall_csv(tmp_path),
                        "wall_columns": ["WallMJ01", "WallMJ02"]},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=Roster(TEAM)),
        )
        assert f.assessment == "pass"
        assert f.ta_confirm is True
        assert any("AFTER the last wall" in e for e in f.evidence)

    def test_bands_split_the_two_walls(self, tmp_path):
        c = self._c([
            {"sha": "aaa11111", "login": "jdoe",
             "date": "2026-10-05T15:00:00Z", "message": "D1 work"},
            {"sha": "ccc33333", "login": "jdoe",
             "date": "2026-10-07T15:59:00Z", "message": "D2 work"},
            {"sha": "eee55555", "login": "jdoe",
             "date": "2026-10-07T17:30:00Z", "message": "after 4PM"},
            {"sha": "bbb22222", "login": "rhaldhah",
             "date": "2026-10-07T15:00:00Z", "message": "D2 work"},
            {"sha": "ccc34444", "login": "akumar",
             "date": "2026-10-07T15:30:00Z", "message": "D2 work"},
        ])
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": _wall_csv(tmp_path),
                        "wall_columns": ["WallMJ01", "WallMJ02"]},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=Roster(TEAM)),
        )
        # The 17:30 commit is after both walls (late for both);
        # 15:59 landed by WallMJ02 — D2 banding must not call it late.
        assert f.ta_confirm is True
        joined = " | ".join(f.evidence)
        assert "1 by WallMJ01" in joined
        assert "WallMJ02" in joined

    def test_member_with_no_commits_needs_review(self, tmp_path):
        c = self._c([
            {"sha": "aaa11111", "login": "jdoe",
             "date": "2026-10-05T15:00:00Z", "message": "skeleton"},
        ])
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": _wall_csv(tmp_path),
                        "wall_columns": ["WallMJ01", "WallMJ02"]},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=Roster(TEAM)),
        )
        assert f.assessment == "needs-review"

    def test_needs_review_without_wall_file(self):
        c = self._c([
            {"sha": "aaa11111", "login": "jdoe",
             "date": "2026-10-05T15:00:00Z", "message": "skeleton"},
        ])
        f = _finding(
            _criterion("pr_commits_by_wall", {}, points=0),
            _ctx_v11(c, username="jdoe", roster=Roster(TEAM)),
        )
        assert f.assessment == "needs-review"

    def test_team_id_alias_se_team01_matches_team01_wall(self, tmp_path):
        """Roster 'SE_TEAM01' resolves a wall CSV row written 'team01'."""
        p = tmp_path / "walls2.csv"
        p.write_text(
            "Team,WallMJ01,WallMJ02\nteam01,2026-10-05T20:00:00Z,2026-10-07T20:00:00Z\n",
            encoding="utf-8",
        )
        c = self._c([
            {"sha": "aaa11111", "login": "jdoe",
             "date": "2026-10-05T19:00:00Z", "message": "skeleton"},
            {"sha": "bbb22222", "login": "rhaldhah",
             "date": "2026-10-07T19:00:00Z", "message": "diagnosis"},
            {"sha": "ccc33333", "login": "akumar",
             "date": "2026-10-07T19:30:00Z", "message": "tests"},
        ])
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": str(p),
                        "wall_columns": ["WallMJ01", "WallMJ02"]},
                       points=0),
            _ctx_v11(c, username="jdoe",
                     roster=Roster({"SE_TEAM01": ["jdoe", "rhaldhah", "akumar"]})),
        )
        assert f.assessment == "pass"


    def test_sidecar_resolves_next_to_roster(self, tmp_path):
        """Wall file lives beside the roster on the share, not in CWD."""
        share = tmp_path / "share"
        share.mkdir()
        (share / "roster.csv").write_text(
            "Team,TA,IU Username\r\nSE_TEAM01,TA,jdoe\r\n", encoding="utf-8")
        (share / "walls.csv").write_text(
            "Team,WallAt\r\nSE_TEAM01,2026-10-05T18:00:00Z\r\n", encoding="utf-8")
        c = self._c([
            {"sha": "aaa11111", "login": "jdoe",
             "date": "2026-10-05T15:00:00Z", "message": "skeleton"},
        ])
        ctx = _ctx_v11(c, username="jdoe", roster=Roster({"SE_TEAM01": ["jdoe"]}))
        ctx.roster_path = str(share / "roster.csv")
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": "walls.csv", "wall_columns": ["WallAt"]},
                       points=0),
            ctx,
        )
        assert f.assessment in ("pass", "needs-review") or f.ta_confirm
        assert any("WallAt: 2026-10-05T18:00:00Z" in e for e in f.evidence)

    def test_needs_review_when_submission_is_not_a_pull(self, tmp_path):
        c = self._c([])
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": _wall_csv(tmp_path)}, points=0),
            _ctx(c, pr_url=BLOB_URL_MAIN),  # a blob, not a PR
        )
        assert f.assessment == "needs-review"

    def test_contributions_missing_reported_not_failed(self, tmp_path):
        c = self._c([
            {"sha": "aaa11111", "login": "jdoe",
             "date": "2026-10-05T15:00:00Z", "message": "skeleton"},
            {"sha": "bbb22222", "login": "rhaldhah",
             "date": "2026-10-07T15:00:00Z", "message": "x"},
            {"sha": "ccc33333", "login": "akumar",
             "date": "2026-10-07T15:30:00Z", "message": "y"},
        ])
        c.diff_text = (
            "diff --git a/app.py b/app.py\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1,1 +1,2 @@\n"
            "+print(1)\n"
        )
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": _wall_csv(tmp_path),
                        "wall_columns": ["WallMJ01", "WallMJ02"]},
                       points=0),
            _ctx_v11(c, username="jdoe", roster=Roster(TEAM)),
        )
        assert f.assessment == "pass" and f.ta_confirm is False
        assert any("NOT in the PR diff" in e for e in f.evidence)


# ---------------------------------------------------------------------------
# valid_student_repo regex patterns (FA26 MoJ team repos)
# ---------------------------------------------------------------------------


class TestRepoPatternRegex:
    def _finding(self, pattern, repo_name, points=0):
        c = _FakeClient()
        c.repo_data = {
            "full_name": "csci-p465-p565/%s" % repo_name,
            "name": repo_name,
            "owner": {"login": "csci-p465-p565"},
            "created_at": "2026-10-06T14:11:26Z",
            "html_url": "https://github.iu.edu/csci-p465-p565/%s" % repo_name,
        }
        return _finding(
            _criterion("valid_student_repo",
                       {"expected_repo_pattern": pattern,
                        "github_host": "github.iu.edu"},
                       points=points),
            _ctx(c, pr_url="https://github.iu.edu/csci-p465-p565/%s/pull/2" % repo_name),
        )

    def test_regex_pattern_fullmatch_passes(self):
        f = self._finding("fa26-team-\\d+-moj", "fa26-team-01-moj")
        assert f.assessment == "pass"

    def test_regex_pattern_fullmatch_case_insensitive(self):
        f = self._finding("FA26-TEAM-\\d+-MOJ", "fa26-team-42-moj")
        assert f.assessment == "pass"

    def test_regex_pattern_nonmatching_repo_fails(self):
        f = self._finding("fa26-team-\\d+-moj", "fa26-team-01")
        assert f.assessment == "fail"

    def test_invalid_regex_falls_through_to_literal_ladder(self):
        # 'fa26(\\d+' is not a valid regex — must not crash; the literal
        # ladder decides (substring miss → fail).
        f = self._finding("fa26(\\d+", "fa26-team-01-moj")
        assert f.assessment == "fail"

    def test_literal_template_semantics_unchanged(self):
        # Shipped literal behavior: exact-name literal vs unrelated name → fail.
        f = self._finding("fa26_se1_team", "fa26-team-01-moj")
        assert f.assessment == "fail"


# ---------------------------------------------------------------------------
# pr_body_contains (MoJ amass-then-subtract projections)
# ---------------------------------------------------------------------------

MJ_BODY_OK = (
    "## Reviewer Focus\r\nCheck our CI diagnosis closely.\r\n"
    "## This Week's ICEXs\r\n"
    "### ICEX_MJ01 - Founding the Ministry\r\n"
    "- [x] File structure matches the tree\r\n"
    "- [ ] Stretch goal\r\n"
    "**Summary:** Flask factory.\r\n"
    "### ICEX_MJ02 - The Silliness Detector\r\n"
    "- [x] ci.yml runs the suite on push\r\n"
    "**Reach task:** count endpoint.\r\n"
    "## Standup Record\r\n"
    "| # | Date | Attendees |\r\n|---|------|-----------|\r\n"
    "| 1 | Oct 12 | all |\r\n| 2 |  |  |\r\n"
    "**Team:** Team 7\r\n**Branch:** `icex/wk8-cicd`\r\n**Week:** 8\r\n"
)


class TestPrBodyContains:
    def _finding(self, body, items):
        c = _FakeClient()
        c.pr_data["body"] = body
        return _finding(
            _criterion("pr_body_contains", {"items": items}, points=10),
            _ctx(c),
        )

    def items(self, *labels):
        return [{"label": _l, "section": "ICEX_MJ01"} for _l in labels]

    def test_complete_body_projects_full_points(self):
        f = self._finding(MJ_BODY_OK, self.items("MJ01 DoD"))
        assert f.assessment == "pass"
        assert f.points_recommended == 10
        assert f.ta_confirm is True

    def test_unticked_section_counts_missing(self):
        body = MJ_BODY_OK.replace("- [x]", "- [ ]")
        f = self._finding(body, self.items("MJ01 DoD"))
        assert f.assessment == "fail"
        assert f.points_recommended == 0
        assert any("MISSING" in e for e in f.evidence)

    def test_absent_section_counts_missing(self):
        f = self._finding("## Reviewer Focus\r\nbody", self.items("MJ01 DoD"))
        assert f.assessment == "fail"
        assert f.points_recommended == 0

    def test_empty_body_is_all_lost_points(self):
        f = self._finding("", self.items("MJ01 DoD"))
        assert f.assessment == "fail" and f.points_recommended == 0
        assert "EMPTY" in " ".join(f.evidence)

    def test_require_pattern_global(self):
        f = self._finding(MJ_BODY_OK, [
            {"label": "footer", "require": r"\*\*Team:.*\bTeam\s*0?\d"},
        ])
        assert f.assessment == "pass"

    def test_forbid_catches_template_placeholder(self):
        body = MJ_BODY_OK.replace(
            "## Reviewer Focus\r\nCheck our CI diagnosis closely.",
            "## Reviewer Focus\r\n[2-3 sentences: the decision ...]")
        f = self._finding(body, [
            {"label": "Reviewer Focus written",
             "require": r"##\s*Reviewer Focus",
             "forbid": r"\[2-3 sentences:"},
        ])
        assert f.assessment == "fail" and f.points_recommended == 0

    def test_require_inside_section(self):
        f = self._finding(MJ_BODY_OK, [
            {"label": "standup row filled",
             "section": "Standup Record",
             "require": r"\|\s*\d+\s*\|[^|]*[^\s|]"},
        ])
        assert f.assessment == "pass"
        body = MJ_BODY_OK.replace("| 1 | Oct 12 | all |", "| 1 |  |  |")
        f2 = self._finding(body, [
            {"label": "standup row filled",
             "section": "Standup Record",
             "require": r"\|\s*\d+\s*\|[^|]*[^\s|]"},
        ])
        assert f2.assessment == "fail"


class TestReleaseChecks:
    """A_MJ02/04 release rows + client ops (tag, body, CI, timing)."""

    RELEASE_BODY = (
        "## What We Did\nMerged [PR #1](https://github.iu.edu/o/r/pull/1) "
        "and [PR #2](https://github.iu.edu/o/r/pull/2) for the flask front "
        "door.\n\n## What We Learned\nSQLAlchemy ORM mapping clicked.\n\n"
        "## What We Do Different\nNext cycle: PRs smaller; CI first.\n\n"
        "## Team & Process Retrospective\nCompared MoJ with MFE.\n\n"
        "## Architecture\n![architecture](docs/arch.png)\n\n"
        "## requirements.txt Map\nflask routes, sqlalchemy models."
    )

    def _ctx_release(self, release, state="success", kind="release"):
        import test_checkers as tck
        c = tck._FakeClient()
        c.release = release
        c.status_state = state
        cr = _criterion("release_contains", {}, points=8)
        ctx = _ctx(c, pr_url="https://github.iu.edu/o/fa26-team-01-moj"
                              "/releases/tag/moj-c1-v1.0")
        return cr, ctx, c

    def test_release_url_parses_to_release_kind(self):
        parsed = checkers.parse_github_url(
            "https://github.iu.edu/o/r/releases/tag/moj-c1-v1.0")
        assert parsed["kind"] == "release" and parsed["ref"] == "moj-c1-v1.0"

    def test_full_body_projects(self):
        cr, ctx, c = self._ctx_release(
            {"body": self.RELEASE_BODY,
             "published_at": "2026-10-24T20:00:00Z"})
        f = _finding(cr, ctx)
        assert f.assessment == "pass" and f.points_recommended == 8
        assert any("PR links found: 2" in e for e in f.evidence)
        assert not any("late:" in e for e in f.evidence)

    def test_late_release_carries_cap_signal(self):
        import test_checkers as tck
        c = tck._FakeClient()
        c.release = {"body": self.RELEASE_BODY,
                     "published_at": "2026-10-29T02:00:00Z"}
        cr = _criterion("release_contains",
                        {"due": "2026-10-26T23:59:00-04:00"}, points=8)
        ctx = _ctx(c, pr_url="https://github.iu.edu/o/fa26-team-01-moj"
                             "/releases/tag/moj-c1-v1.0")
        f = _finding(cr, ctx)
        assert f.assessment == "pass"
        assert any("LATE" in e and "5%/day" in e for e in f.evidence)
        assert "1.9 days" in f.notes and "−10 pts" in f.notes

    def test_body_without_pr_links_fails(self):
        body = "## What We Did\nstuff.\n\n## What We Learned\nx\n\n## What We Do Different\ny"
        f = self._rerun(body, min_pr_links=2)
        assert f.assessment == "fail"
        assert "PR links" in f.notes

    def _rerun(self, body, **extra):
        import test_checkers as tck
        c = tck._FakeClient()
        c.release = {"body": body, "published_at": "2026-10-24T20:00:00Z"}
        cr = _criterion("release_contains", extra, points=8)
        return _finding(cr, _ctx(
            c, pr_url="https://github.iu.edu/o/fa26-team-01-moj"
                      "/releases/tag/moj-c1-v1.0"))

    def test_missing_header_fails(self):
        f = self._rerun(self.RELEASE_BODY, require_headers=["budget"])
        assert f.assessment == "fail"
        assert "header 'budget'" in f.notes

    def test_draft_release_fails(self):
        f = self._rerun("", expected_repo_pattern="fa26-team-")
        assert f.assessment == "fail"
        # empty body -> MISSING body content? "" -> get_release fine but
        # body empty -> fail with EMPTY
        assert "no description" in f.notes

    def test_missing_release_404(self):
        import test_checkers as tck
        c = tck._FakeClient()
        c.release_error = SubmissionNotFoundError("no release")
        cr = _criterion("release_contains", {}, points=8)
        f = _finding(cr, _ctx(
            c, pr_url="https://github.iu.edu/o/fa26-team-01-moj"
                      "/releases/tag/moj-c1-v1.0"))
        assert f.assessment == "fail"
        assert "No release with tag" in f.notes

    def test_ci_green_full_points(self):
        import test_checkers as tck
        c = tck._FakeClient()
        c.status_state = "success"
        cr = _criterion("release_ci_green", {}, points=5)
        f = _finding(cr, _ctx(
            c, pr_url="https://github.iu.edu/o/fa26-team-01-moj"
                      "/releases/tag/moj-c1-v1.0"))
        assert f.assessment == "pass" and f.points_recommended == 5

    def test_ci_red_zero_no_appeal(self):
        import test_checkers as tck
        c = tck._FakeClient()
        c.status_state = "failure"
        cr = _criterion("release_ci_green", {}, points=5)
        f = _finding(cr, _ctx(
            c, pr_url="https://github.iu.edu/o/fa26-team-01-moj"
                      "/releases/tag/moj-c1-v1.0"))
        assert f.assessment == "fail" and f.points_recommended == 0
        assert "no appeal" in f.notes

    def test_ci_pending_needs_review(self):
        import test_checkers as tck
        c = tck._FakeClient()
        c.status_state = "pending"
        cr = _criterion("release_ci_green", {}, points=5)
        f = _finding(cr, _ctx(
            c, pr_url="https://github.iu.edu/o/fa26-team-01-moj"
                      "/releases/tag/moj-c1-v1.0"))
        assert f.assessment == "needs-review"


class TestDocInPr:
    """A_MJ01-B: doc on the PR head branch + member positions."""

    DECISION_DOC = (
        "## Section 1 — Decision Summary\nSQLite embedded, two reasons.\n\n"
        "## Section 2 — Strongest Counterargument\nNoSQL flexibility named.\n\n"
        "## Section 3 — Ethical Challenge\nTables and week named.\n\n"
        "## Section 4 — Synthesis Reflection\nSurfaced by discussion.\n\n"
        "## Section 5 — Individual Positions\n- @ybingley affirms (vision req)\n"
        "- @cfampo affirms (vision req)"
    )

    def _ctx_pr(self, doc=DECISION_DOC, **param_extra):
        import test_checkers as tck
        c = tck._FakeClient()
        c.file_kind, c.file_text = "file", doc
        c.pr_data = {"title": "Decision: SQL vs NoSQL Database Engine",
                     "head_ref": "decision/sql-nosql", "body": "pr body"}
        roster = tck._roster_with_team("SE_TEAM01", ["ctbowman", "mfbah"])
        params = {
            "expected_branch": "decision/sql-nosql",
            "expected_title": "decision: ?sql vs nosql",
            "expected_path": "decisions/sql_nosql.md",
        }
        params.update(param_extra)
        cr = _criterion("doc_in_pr", params, points=4)
        ctx = _ctx(c, pr_url="https://github.iu.edu/o/fa26-team-01-moj/pull/3")
        ctx.roster = roster
        ctx.username = "ctbowman"
        return cr, ctx, c

    def test_everything_present_projects_full(self):
        cr, ctx, c = self._ctx_pr(
            self.DECISION_DOC.replace("@cfampo", "@ctbowman")
            + "\n- @hasiddiq affirms")
        f = _finding(cr, ctx)
        assert f.assessment == "pass", f.notes
        assert f.points_recommended == 4
        assert any("head ref" in e for e in f.evidence)

    def test_wrong_branch_fails(self):
        cr, ctx, c = self._ctx_pr()
        c.file_text = self.DECISION_DOC
        ctx_roster = ctx
        c.pr_data["head_ref"] = "main"
        f = _finding(cr, ctx_roster)
        assert f.assessment == "fail" and "decision/sql-nosql" in f.notes

    def test_wrong_title_fails(self):
        cr, ctx, c = self._ctx_pr()
        c.pr_data["title"] = "Update readme"
        f = _finding(cr, ctx)
        assert f.assessment == "fail" and "title" in f.notes.lower()

    def test_doc_on_head_not_main(self):
        # the fetch must use the head ref, not main - _FakeClient records ref
        cr, ctx, c = self._ctx_pr()
        _finding(cr, ctx)
        assert getattr(c, "last_file_ref", None) == "decision/sql-nosql"

    def test_missing_member_entries_fail_with_names(self):
        cr, ctx, c = self._ctx_pr(
            self.DECISION_DOC.replace("@cfampo", "@ctbowman")
            + "\n- @hasiddiq affirms",
            require_all_usernames=True)
        f = _finding(cr, ctx)
        assert f.assessment == "fail"
        assert "mfbah" in f.notes

    def test_missing_header_fails(self):
        cr, ctx, c = self._ctx_pr("# only a title\n\nbody text",
                                  require_headers=["decision summary"])
        f = _finding(cr, ctx)
        assert f.assessment == "fail" and "header" in f.notes


class TestDocContains:
    """AGR_MJ document-shape checks: headers, tokens, word band."""

    DOC = (
        "# AGR_MJ01 decision record\n\n## 1. Context\nThe Vision has "
        "600,000 joke-tellers and 2,000,000 jokes; browsing stays under "
        "200 milliseconds. Team A_MJ01 chose embedded SQLite after "
        "weighing the research.\n\n## 2. The Decision as Made\nWe kept "
        "the team engine and the ORM as built.\n\n## 3. Options "
        "Considered\nSQL over NoSQL; embedded over server.\n\n## 4. "
        "Analysis at Vision Scale\nThe file is the bottleneck at "
        "scale.\n\n## 5. The FOSS Judgment\nThe FOSS principle stands "
        "until proven not to work; Cycle 3 re-decides.\n\n## 6. "
        "Consequences\nMigration path and observable signals defined."
    )
    THREAT_MEMO = (
        "MEMORANDUM\nTo:   Instructor\nFrom: Student, CSCI-P565\n"
        "Date: 2026-11-10\nRe:   Threat-Model Assessment\n\n"
        "## 1. Context\nCycle 2 state summary.\n\n## 2. Assets\nThree "
        "assets with value and motivation.\n\n## 3. Threats\nFive "
        "threats listed; one addresses model poisoning in the AI "
        "pipeline.\n\n## 4. Countermeasures\nCountermeasures mapped, "
        "including one against prompt injection.\n\n## 5. AI Injection\n"
        "Expanded scope covered.\n\n## 6. AI Use Disclosure\nI used "
        "Claude to summarize STRIDE; the analysis is my own."
    )

    def _finding(self, doc=DOC, kind="file", **params):
        import test_checkers as tck
        c = tck._FakeClient()
        c.file_kind = kind
        c.file_text = doc
        cr = _criterion("doc_contains", params, points=5)
        ctx = _ctx(c, pr_url="https://github.iu.edu/org/fa26-team-03-moj"
                              "/blob/main/docs/ddr/ddr1-mfbah.md")
        ctx.username = "mfbah"
        return _finding(cr, ctx)

    def test_everything_present_projects_full(self):
        f = self._finding(
            expected_path="docs/ddr/ddr1-{username}.md",
            require_headers=["context", "options considered", "consequences"],
            must_contain=["600[,.]?000", "foss"])
        assert f.assessment == "pass" and f.points_recommended == 5
        assert "total word count" in " ".join(f.evidence)

    def test_missing_header_fails_with_name(self):
        f = self._finding(require_headers=["budget plan"])
        assert f.assessment == "fail" and f.points_recommended == 0
        assert "header 'budget plan'" in f.notes

    def test_missing_token_fails_with_name(self):
        f = self._finding(must_contain=["bitcoin"])
        assert f.assessment == "fail"
        assert "content 'bitcoin'" in f.notes

    def test_username_template_resolves(self):
        f = self._finding(expected_path="docs/ddr/ddr1-{username}.md")
        assert f.assessment == "pass"
        assert any("from username mfbah" in e for e in f.evidence)

    def test_username_template_mismatch_fails(self):
        f = self._finding(expected_path="docs/ddr/ddr9-{username}.md")
        assert f.assessment == "fail"
        assert "ddr9-mfbah" in f.notes

    def test_wrong_repo_fails(self):
        f = self._finding(expected_repo_pattern="fa26-devlog-")
        assert f.assessment == "fail"

    def test_band_violation_note_only_default(self):
        f = self._finding(min_words=2000, max_words=1)
        assert f.assessment == "pass"
        assert "UNDER the 2000-word band" in f.notes

    def test_band_violation_enforced_fails(self):
        f = self._finding(min_words=2000, band_enforced=True)
        assert f.assessment == "fail"
        assert "near-misses" in f.notes

    def test_band_within_passes_quietly(self):
        f = self._finding(min_words=1, max_words=900)
        assert f.assessment == "pass"
        assert "UNDER" not in f.notes and "OVER" not in f.notes

    def test_missing_file_fails(self):
        f = self._finding(kind="missing")
        assert f.assessment == "fail"
        assert "No file at the submitted blob path" in f.notes

    def test_threat_memo_ai_tokens_found(self):
        memo = self._finding(
            doc=self.THREAT_MEMO,
            expected_repo_pattern="fa26-team-",
            require_headers=["threats", "countermeasures"],
            must_contain=[
                r"prompt injection|model poisoning|data exfiltration|ai-related|\bai\b",
                "memorandum"])
        assert memo.assessment == "pass"


class TestReflectionEntry:
    """Devlog reflection bar: word count + local-assertion judge."""

    GOOD_ENTRY = (
        "# Week 9\n\nType 2 — Observation with cause.\n\n"
        "Our CI failure on Tuesday taught me that a test suite can pass "
        "locally and still be wrong about the contract. The suite "
        "asserted only HTTP status codes, not the JSON body, so any "
        "handler change that kept the status but dropped the payload "
        "slipped through green. That happened because our fixtures built "
        "the expected envelope by hand instead of reading it from the "
        "router. Once we pinned the envelope in one place and let every "
        "test import it, the false green disappeared and the next "
        "handler refactor was caught immediately. The lesson is that "
        "'green' only means the assertions you wrote, and weak "
        "assertions quietly define a weaker contract than the one the "
        "spec describes."
    )
    TOO_SHORT = "I learned a lot this week. CI was useful and the team worked well together."

    def _finding(self, repo="fa26-devlog-jdoe", path="icex_mj03.md",
                 kind="file", text=GOOD_ENTRY, judge=("pass", "ok"),
                 judge_raises=None, **params):
        import test_checkers as tck
        c = tck._FakeClient()
        c.file_kind = kind
        c.file_text = text
        params.setdefault("expected_repo_pattern", "fa26-devlog-")
        monkey = pytest.MonkeyPatch()

        def _noop(*a, **k):
            return judge

        if judge_raises is not None:
            def _raise(*a, **k):
                raise judge_raises
            monkey.setattr(checkers, "_ollama_judge", _raise)
        elif "llm_model" in params or True:
            monkey.setattr(checkers, "_ollama_judge", _noop)
        params.setdefault("llm_model", "test-judge")
        cr = _criterion("reflection_entry", params, points=10)
        url = "https://github.iu.edu/jdoe/%s/blob/main/%s" % (repo, path)
        ctx = _ctx(c, pr_url=url)
        try:
            return _finding(cr, ctx)
        finally:
            monkey.undo()

    def test_healthy_entry_projects_full_points(self):
        f = self._finding()
        assert f.assessment == "pass"
        assert f.points_recommended == 10
        assert f.ta_confirm is True
        assert any("model verdict: pass" in e for e in f.evidence)
        assert any("word count:" in e for e in f.evidence)
        assert any(e.startswith("entry: ") for e in f.evidence)

    def test_too_short_judge_pass_gets_one_point_deduction(self):
        f = self._finding(text=self.TOO_SHORT)
        # TOO_SHORT is 14 words: too short, but the assertion (stubbed
        # pass) carries it — Kurt's 2026-11-12 rule: -1, not zero.
        assert f.assessment == "pass"
        assert f.points_recommended == 9
        assert "ONE-POINT deduction" in f.notes
        assert "below the 100-word bar" in f.notes

    def test_too_short_judge_fail_is_zero(self):
        f = self._finding(text=self.TOO_SHORT,
                          judge=("fail", "an announcement, no lesson"))
        assert f.assessment == "fail" and f.points_recommended == 0
        assert "below the 100-word bar" in f.notes
        assert "announcement, no lesson" in f.notes

    def test_too_short_report_only_carries_pending_deduction(self):
        f = self._finding(text=self.TOO_SHORT, **{"llm_model": None})
        assert f.assessment == "needs-review"
        assert "ONE-POINT deduction" in f.notes
        assert f.points_recommended is None

    def test_judge_fail_is_lost_points_with_reason(self):
        f = self._finding(
            judge=("fail", "a summary without a personal claim"))
        assert f.assessment == "fail" and f.points_recommended == 0
        assert any("model verdict: fail" in e for e in f.evidence)
        assert "summary without a personal claim" in f.notes

    def test_missing_file_fails_with_url_note(self):
        f = self._finding(kind="missing")
        assert f.assessment == "fail"
        assert any("no file at this blob path" in e for e in f.evidence)

    def test_directory_blob_fails(self):
        f = self._finding(kind="dir")
        assert f.assessment == "fail"
        assert "DIRECTORY" in f.notes

    def test_wrong_repo_fails_before_fetch(self):
        f = self._finding(repo="fa26-team-07-moj")
        assert f.assessment == "fail"
        assert any("own devlog repo" in e for e in f.evidence)

    def test_expected_path_mismatch_fails(self):
        f = self._finding(path="junk.md", **{"expected_path": "icex_mj03.md"})
        assert f.assessment == "fail"
        assert any("expected entry file" in e for e in f.evidence)

    def test_report_only_run_needs_review_with_text(self):
        f = self._finding(**{"llm_model": None})
        assert f.assessment == "needs-review"
        assert any(e.startswith("entry: ") for e in f.evidence)
        assert "report-only" in f.notes.lower()

    def test_unreachable_local_model_needs_review(self):
        f = self._finding(judge_raises=OSError("connection refused"))
        assert f.assessment == "needs-review"
        assert "ollama" in f.notes.lower()

    def test_non_loopback_endpoint_refused(self):
        f = self._finding(**{"llm_endpoint": "http://api.example.com:11434"})
        assert f.assessment == "needs-review"
        assert "FERPA" in f.notes

    def test_over_target_note_but_passes(self):
        long_text = self.GOOD_ENTRY + " " + " ".join(
            "w%d" % i for i in range(120))
        f = self._finding(text=long_text)
        assert f.assessment == "pass"
        assert "200-word target" in f.notes


class TestWallProjections:
    """Per-member wall projections (10 / 8.5 late / 0 missing completion)."""

    def _c(self, rows, body=MJ_BODY_OK):
        c = _FakeClient()
        c.pr_commit_rows = rows
        c.pr_data["body"] = body
        c.diff_text = (
            "diff --git a/CONTRIBUTIONS.md b/CONTRIBUTIONS.md\n"
            "+++ b/CONTRIBUTIONS.md\n"
        )
        return c

    def test_projections_on_time_and_late(self, tmp_path):
        walls = tmp_path / "walls.csv"
        walls.write_text(
            "Team,WallMJ01,WallMJ02\n"
            "SE_TEAM07,2026-10-12T18:00:00Z,2026-10-14T18:00:00Z\n",
            encoding="utf-8")
        c = self._c([
            {"sha": "aaa11111", "login": "ybingley",
             "date": "2026-10-12T16:01:07Z", "message": "tests"},
            {"sha": "bbb22222", "login": "ybingley",
             "date": "2026-10-14T16:59:30Z", "message": "contrib"},
            {"sha": "ccc33333", "login": "svasandi",
             "date": "2026-10-15T21:24:26Z", "message": "late contrib"},
            {"sha": "ddd44444", "login": "svasandi",
             "date": "2026-10-14T17:43:14Z", "message": "on-time d2"},
        ])
        ctx = _ctx_v11(c, username="ybingley",
                       roster=Roster({"SE_TEAM07": ["ybingley", "svasandi"]}))
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": str(walls),
                        "wall_columns": ["WallMJ01", "WallMJ02"],
                        "section_patterns": {"WallMJ01": "ICEX_MJ01",
                                             "WallMJ02": "ICEX_MJ02"}},
                       points=0),
            ctx,
        )
        joined = " | ".join(f.evidence)
        # ybingley: everything by the walls → 10 both; svasandi: the
        # late tail after the last wall projects 8.5 on both lines (TA
        # maps the artifact).
        assert "project ybingley: MJ01=10, MJ02=10" in joined
        assert "project svasandi: MJ01=8.5, MJ02=8.5" in joined
        assert f.ta_confirm is True

    def test_missing_completion_loses_the_wall_line(self, tmp_path):
        walls = tmp_path / "walls.csv"
        walls.write_text(
            "Team,WallMJ01,WallMJ02\n"
            "SE_TEAM07,2026-10-12T18:00:00Z,2026-10-14T18:00:00Z\n",
            encoding="utf-8")
        body = MJ_BODY_OK.replace(
            "### ICEX_MJ02 - The Silliness Detector\r\n- [x] ci.yml runs the suite on push\r\n",
            "")
        c = self._c([
            {"sha": "aaa11111", "login": "ybingley",
             "date": "2026-10-12T16:01:07Z", "message": "tests"},
        ], body=body)
        ctx = _ctx_v11(c, username="ybingley",
                       roster=Roster({"SE_TEAM07": ["ybingley"]}))
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": str(walls),
                        "wall_columns": ["WallMJ01", "WallMJ02"],
                        "section_patterns": {"WallMJ01": "ICEX_MJ01",
                                             "WallMJ02": "ICEX_MJ02"}},
                       points=0),
            ctx,
        )
        joined = " | ".join(f.evidence)
        assert "completion WallMJ02: MISSING" in joined
        assert "project ybingley: MJ01=10, MJ02=0" in joined

    def test_submitter_projection_line(self, tmp_path):
        walls = tmp_path / "walls.csv"
        walls.write_text(
            "Team,WallMJ01,WallMJ02\n"
            "SE_TEAM07,2026-10-12T18:00:00Z,2026-10-14T18:00:00Z\n",
            encoding="utf-8")
        c = self._c([
            {"sha": "aaa11111", "login": "ybingley",
             "date": "2026-10-12T16:01:07Z", "message": "tests"},
        ])
        ctx = _ctx_v11(c, username="ybingley",
                       roster=Roster({"SE_TEAM07": ["ybingley"]}))
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": str(walls),
                        "wall_columns": ["WallMJ01", "WallMJ02"]},
                       points=0),
            ctx,
        )
        assert any("submitter's projected wall score" in e for e in f.evidence)

    def test_zero_commit_member_projects_zero(self, tmp_path):
        """A roster member with no PR commits projects 0 and flags."""
        walls = tmp_path / "walls.csv"
        walls.write_text(
            "Team,WallMJ01,WallMJ02\n"
            "SE_TEAM07,2026-10-12T18:00:00Z,2026-10-14T18:00:00Z\n",
            encoding="utf-8")
        c = self._c([
            {"sha": "aaa11111", "login": "ybingley",
             "date": "2026-10-12T16:01:07Z", "message": "tests"},
        ])
        ctx = _ctx_v11(c, username="absent_member",
                       roster=Roster({"SE_TEAM07": ["ybingley", "absent_member"]}))
        f = _finding(
            _criterion("pr_commits_by_wall",
                       {"wall_file": str(walls),
                        "wall_columns": ["WallMJ01", "WallMJ02"],
                        "section_patterns": {"WallMJ01": "ICEX_MJ01",
                                             "WallMJ02": "ICEX_MJ02"}},
                       points=0),
            ctx,
        )
        joined = " | ".join(f.evidence)
        assert f.assessment == "needs-review"
        assert "project absent_member: MJ01=0, MJ02=0" in joined
        assert "no commits authored in the PR" in f.notes


# ---------------------------------------------------------------------------
# W8 titles / auto-detect
# ---------------------------------------------------------------------------


class TestW8TitleParse:
    def test_team_pr_title_parses_with_space(self, tmp_path):
        html = (
            "<html><head><title>Week 8 | Team PR - Founding the Ministry &amp; CI</title>"
            "<meta http-equiv=\"refresh\" content=\"0; url=%s\">"
            "</head><body></body></html>" % (
                "https://github.iu.edu/mnemo-course-dev/fa26_se1_team01/pull/3")
        )
        p = tmp_path / "jdoe_999_link.html"
        p.write_text(html, encoding="utf-8")
        sub = parse_submission(str(p))
        assert sub.assignment_id == "Team PR"
        assert sub.week == "8"

    def test_find_rubric_normalizes_spaces(self, tmp_path):
        """Canvas-title 'Team PR' finds team_pr_*.yaml via underscore needle."""
        (tmp_path / "rubrics" / "se1").mkdir(parents=True)
        (tmp_path / "rubrics" / "se1" / "team_pr_wk08_fa26.yaml").write_text(
            "assignment: Team PR\ncourse: SE1\ntotal_points: 30\n",
            encoding="utf-8",
        )
        found = rubric.find_rubric("Team PR", str(tmp_path), course="se1")
        assert found is not None
        assert found.name == "team_pr_wk08_fa26.yaml"


class TestRegistry:
    def test_moj_checkers_registered(self):
        for name in ("blob_link_valid", "pr_from_given_branch",
                     "devlog_before_canvas"):
            assert name in CHECKERS


class TestMoJParserIntegration:
    def test_moj_title_parses_assignment_id(self, tmp_path):
        html = (
            "<html><head><title>Week 12 | A_MJ05 - Ethics Opener</title>"
            "<meta http-equiv=\"refresh\" content=\"0; url=%s\">"
            "</head><body></body></html>" % BLOB_URL_MAIN
        )
        p = tmp_path / "jdoe_123456_link.html"
        p.write_text(html, encoding="utf-8")
        sub = parse_submission(str(p))
        assert sub.assignment_id == "A_MJ05"
        assert sub.week == "12"
        assert sub.student_name == "Ethics Opener"
        assert sub.pr_url == BLOB_URL_MAIN

    def test_blob_url_survives_body_link_extraction(self, tmp_path):
        html = (
            "<html><body><a href=\"%s\">the team document</a></body></html>"
            % BLOB_URL_MAIN
        )
        p = tmp_path / "jdoe_123456_link.html"
        p.write_text(html, encoding="utf-8")
        sub = parse_submission(str(p))
        assert sub.pr_url == BLOB_URL_MAIN

    def test_split_pr_url_accepts_blob(self):
        owner, repo, number = _split_pr_url(BLOB_URL_MAIN)
        assert (owner, repo, number) == ("mnemo-course-dev", "fa26_se1_team01", None)

    def test_split_pr_url_still_parses_pull(self):
        owner, repo, number = _split_pr_url(
            "https://github.iu.edu/org/repo/pull/7"
        )
        assert (owner, repo, number) == ("org", "repo", 7)


class _PathRefClient:
    """Fake client whose file results vary by (path, ref) — for the
    path-tolerance behaviors."""

    def __init__(self, files, pulls=(), diff_text=""):
        self._files = files          # {(path, ref): (kind, text)}
        self.pr_data = {"title": "t", "head_ref": "feat/br", "body": "b"}
        self.pulls = list(pulls)
        self.diff_text = diff_text
        self.calls = []

    def get_file_contents(self, owner, repo, path, ref=None):
        self.calls.append(("contents", owner, repo, path, ref))
        return self._files.get((path, ref), ("missing", None))

    def get_repo(self, owner, repo):
        self.calls.append(("repo", owner, repo))
        return type("R", (), {"full_name": "%s/%s" % (owner, repo),
                              "created_at": "2026-08-20T09:00:00Z"})()

    def get_pr(self, owner, repo, number):
        self.calls.append(("pr", owner, repo, number))
        return type("PR", (), self.pr_data)()

    def get_pr_diff(self, owner, repo, number):
        return self.diff_text


def _doc_ctx(client, url, params, roster_members=("ctbowman", "mfbah"),
             username="ctbowman"):
    import test_checkers as tck
    roster = tck._roster_with_team("SE_TEAM01", list(roster_members))
    cr = _criterion("doc_contains", params, points=5)
    ctx = _ctx(client, pr_url=url)
    ctx.roster = roster
    ctx.username = username
    return cr, ctx


DOC_BODY = (
    "# Logging requirements\n\n## Individual summaries\nMembers. Names "
    "600,000.\n\n## Unified specification\nTen events, each with log "
    "level.\n\n## Conflicts and resolutions\nWe argued; SQLite won.\n\n"
    "## Synthesis reflection\nSTRIDE: one threat named.\n\n## Process\n"
    "@ctbowman @mfbah listed."
)
PULL_URL = "https://github.iu.edu/o/fa26-team-01-moj/pull/3"


class TestDocPathTolerance:
    """A_MJ03 FA26 conventions: drifted doc names and slice-branch refs
    resolve by tolerance params, with path-deviation evidence."""

    URL_MAIN = ("https://github.iu.edu/o/fa26-team-01-moj/"
                "blob/main/docs/requirements/logging_requirements.md")
    URL_RENAMED = ("https://github.iu.edu/o/fa26-team-01-moj/"
                   "blob/main/docs/logging-spec.md")
    URL_SLASHREF = ("https://github.iu.edu/o/fa26-team-01-moj/"
                    "blob/assignment/amj03-log/docs/logging/a_mj03_team01.md")

    def test_basename_tolerance_passes(self):
        c = _PathRefClient({("docs/requirements/logging_requirements.md",
                             "main"): ("file", DOC_BODY)})
        cr, ctx = _doc_ctx(c, self.URL_MAIN, {
            "expected_path": "docs/logging_requirements.md",
            "allow_name_regex": "logging"})
        f = _finding(cr, ctx)
        assert f.assessment == "pass", f.notes
        assert any("path deviation" in e for e in f.evidence)

    def test_name_regex_tolerance_passes(self):
        c = _PathRefClient({("docs/logging-spec.md", "main"):
                            ("file", DOC_BODY)})
        cr, ctx = _doc_ctx(c, self.URL_RENAMED, {
            "expected_path": "docs/logging_requirements.md",
            "allow_name_regex": "logging|mj.?03"})
        f = _finding(cr, ctx)
        assert f.assessment == "pass", f.notes
        assert any("path deviation" in e for e in f.evidence)

    def test_no_tolerance_fails_on_rename(self):
        c = _PathRefClient({("docs/logging-spec.md", "main"):
                            ("file", DOC_BODY)})
        cr, ctx = _doc_ctx(c, self.URL_RENAMED, {
            "expected_path": "docs/logging_requirements.md"})
        f = _finding(cr, ctx)
        assert f.assessment == "fail" \
            and any("path mismatch" in e for e in f.evidence)

    def test_multi_segment_ref_sweep(self):
        c = _PathRefClient({("docs/logging/a_mj03_team01.md",
                             "assignment/amj03-log"): ("file", DOC_BODY)})
        cr, ctx = _doc_ctx(c, self.URL_SLASHREF, {
            "expected_path": "docs/logging_requirements.md",
            "allow_name_regex": "logging|mj.?03"})
        f = _finding(cr, ctx)
        assert f.assessment == "pass", f.notes
        assert any("multi-segment ref" in e for e in f.evidence)

    def test_pr_doc_head_deleted_reads_main(self):
        files = {("docs/logging_requirements.md", "decision/log"):
                 ("missing", None),
                 ("docs/logging_requirements.md", None): ("file", DOC_BODY)}
        c = _PathRefClient(files)
        c.pr_data["head_ref"] = "decision/log"
        c.roster = None
        cr, ctx = _doc_ctx(c, PULL_URL, {
            "expected_path": "docs/logging_requirements.md",
            "require_all_usernames": True})
        ctx.roster = __import__("test_checkers")._roster_with_team(
            "SE_TEAM01", ["ctbowman", "mfbah"])
        f = _finding(cr, ctx)
        assert f.assessment == "pass", f.notes
        assert any("MERGED file on main" in e for e in f.evidence)

    def test_pr_doc_found_via_diff_scan(self):
        # head deleted, main lacks the doc, PR diff carries it at a
        # drifted path → resolve from the PR's changed files.
        files = {("docs/logging_requirements.md", None): ("missing", None),
                 ("decisions/logging-requirements.md", None):
                     ("file", DOC_BODY)}
        c = _PathRefClient(
            files,
            diff_text="diff --git a/decisions/logging-requirements.md")
        c.pr_data["head_ref"] = "decision/log"
        cr, ctx = _doc_ctx(c, PULL_URL, {
            "expected_path": "docs/logging_requirements.md",
            "allow_name_regex": "logging|mj.?03",
            "require_all_usernames": True})
        f = _finding(cr, ctx)
        assert f.assessment == "pass", f.notes
        assert any("PR's changed files" in e for e in f.evidence)
