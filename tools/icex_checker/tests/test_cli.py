"""Tests for the CLI entry point (Script Interface Contract, FR-10, EF-10/11)."""
import json
import pathlib

import pytest

import icex_checker as cli
from github_client import PR, Repo
from icex_checker import (
    APIMissingTokenError,
    AuthFailureError,
    NetworkError,
    PRNotAccessibleError,
    RateLimitError,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sample_submission.html"
RUBRIC = FIXTURES / "icex01_rubric.yaml"

PR_OK = {
    "number": 42,
    "title": "Add hello.c",
    "body": "My pull request for ICEX01.",
    "state": "open",
    "created_at": "2026-08-25T10:00:00Z",
    "updated_at": "2026-08-25T11:00:00Z",
    "head": {"ref": "jdoe-patch-1"},
    "base": {"ref": "main"},
    "commits": 3,
}
REPO_OK = {
    "full_name": "jdoe/fa26_c291",
    "name": "fa26_c291",
    "owner": {"login": "jdoe"},
    "created_at": "2026-08-20T09:00:00Z",
    "html_url": "https://github.iu.edu/jdoe/fa26_c291",
}
DIFF_OK = (
    "diff --git a/hello.c b/hello.c\n"
    "--- a/hello.c\n"
    "+++ b/hello.c\n"
    "@@ -1,2 +1,2 @@\n"
    "-    printf(\"Hello World!\\n\");\n"
    "+    printf(\"Hello Zoidberg!\\n\");\n"
)
COMMITS_OK = [{"sha": "a", "commit": {"author": {"date": "2026-05-01T12:00:00Z"}}}]


def _install_fake(monkeypatch, token="fake-token", token_error=None, pr_error=None,
                  repo_error=None, diff_error=None, commits_error=None):
    """Replace the CLI's GitHubClient with a canned fake; returns constructed list."""
    constructed = []

    class FakeGitHubClient:
        @classmethod
        def resolve_token(cls, t, host=None):
            if token_error:
                raise token_error
            return token

        def __init__(self, token, host):
            self.token = token
            self.host = host
            constructed.append(self)

        def get_pr(self, o, r, n):
            if pr_error:
                raise pr_error
            return PR(PR_OK)

        def get_repo(self, o, r):
            if repo_error:
                raise repo_error
            return Repo(REPO_OK)

        def get_commit_author_dates(self, o, r):
            if commits_error:
                raise commits_error
            return [c["commit"]["author"]["date"] for c in COMMITS_OK]

        def get_pr_commit_logins(self, o, r, n):
            if commits_error:
                raise commits_error
            return ["jdoe", "akumar"]

        def get_pr_diff(self, o, r, n):
            if diff_error:
                raise diff_error
            return DIFF_OK

    monkeypatch.setattr("icex_checker.GitHubClient", FakeGitHubClient)
    return constructed


def _html(tmp_path, name, url="https://github.iu.edu/jdoe/fa26_c291/pull/42",
          title="Week01 - ICEX01: Jane Doe"):
    p = tmp_path / name
    p.write_text(
        "<html><head><title>%s</title>"
        '<meta http-equiv="Refresh" content="0; url=%s">'
        "</head><body><a href=\"%s\">PR</a></body></html>" % (title, url, url),
        encoding="utf-8",
    )
    return p


def _rubric_with_ag(tmp_path_or_none, target="hello.c"):
    """A v1.1 AG rubric: ag_max_points 85, handgrading 15, canvas 10."""
    base = tmp_path_or_none if tmp_path_or_none is not None else pathlib.Path(".")
    p = base / "rubric_ag.yaml"
    p.write_text(
        "assignment: ICEX02\n"
        "course: C291\n"
        "semester: FA26\n"
        "total_points: 100\n"
        "semester_start: 2026-08-24\n"
        "ag_url: https://autograder.luddy.indiana.edu/web/project/2502\n"
        "ag_max_points: 85\n"
        "handgrading_points: 15\n"
        "canvas_points: 10\n"
        "criteria:\n"
        "  - name: AG Test Score\n"
        "    points: 85\n"
        "    checker: manual_review\n"
        "  - name: Handgrading\n"
        "    points: 15\n"
        "    checker: manual_review\n",
        encoding="utf-8",
    )
    return p


class TestVersion:
    def test_version_flag(self, capsys):
        code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert code == 0
        assert "icex_checker" in out
        assert "1.1.1" in out


class TestSingleSubmission:
    def test_success_prints_report(self, monkeypatch, capsys):
        _install_fake(monkeypatch)
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        out = capsys.readouterr().out
        assert code == 0
        assert "ICEX01" in out
        assert "Jane Doe" in out
        assert "TA ACTION ITEMS" in out

    def test_success_auto_detects_rubric(self, monkeypatch, capsys):
        """FR-5: omitting --rubric finds rubrics/icex01_fa26.yaml in the tool dir."""
        _install_fake(monkeypatch)
        code = cli.main([str(SAMPLE)])
        out = capsys.readouterr().out
        assert code == 0
        assert "ICEX01" in out

    def test_missing_submission_file(self, capsys):
        code = cli.main(["/nonexistent/nope.html", "--rubric", str(RUBRIC)])
        err = capsys.readouterr().err
        assert code == 1
        assert "submission file not found" in err

    def test_no_pr_url(self, capsys, tmp_path):
        p = _html(tmp_path, "nourl.html", url="")
        code = cli.main([str(p), "--rubric", str(RUBRIC)])
        assert code == 1
        assert "no PR URL found" in capsys.readouterr().err

    def test_wrong_host(self, capsys, tmp_path):
        p = _html(tmp_path, "wrong.html", url="https://github.com/jdoe/fa26_c291/pull/42")
        code = cli.main([str(p), "--rubric", str(RUBRIC)])
        assert code == 1
        assert "PR URL points to" in capsys.readouterr().err

    def test_missing_token(self, monkeypatch, capsys):
        _install_fake(monkeypatch, token_error=APIMissingTokenError("no API token found. Provide one via --token, GH_TOKEN, GITHUB_ENTERPRISE_TOKEN, or gh auth login."))
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        assert code == 1
        assert "token" in capsys.readouterr().err.lower()

    def test_auth_failure(self, monkeypatch, capsys):
        _install_fake(monkeypatch, pr_error=AuthFailureError("authentication failed (HTTP 401)"))
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        assert code == 1
        assert "authentication failed" in capsys.readouterr().err

    def test_rate_limit(self, monkeypatch, capsys):
        _install_fake(monkeypatch, pr_error=RateLimitError("rate limited by GitHub API (HTTP 403)"))
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        assert code == 1
        assert "rate limited" in capsys.readouterr().err

    def test_network_error(self, monkeypatch, capsys):
        _install_fake(monkeypatch, pr_error=NetworkError("network error: boom"))
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        assert code == 1
        assert "network error" in capsys.readouterr().err

    def test_pr_not_accessible_fatal_with_url(self, monkeypatch, capsys):
        """EF-6: repo also 404 -> fatal, with PR URL for manual review."""
        _install_fake(
            monkeypatch,
            pr_error=PRNotAccessibleError("PR not accessible (HTTP 404)", status=404),
            repo_error=PRNotAccessibleError("PR not accessible (HTTP 404)", status=404),
        )
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        err = capsys.readouterr().err
        assert code == 1
        assert "PR not accessible" in err
        assert "github.iu.edu/jdoe/fa26_c291/pull/42" in err

    def test_404_hint_mentions_token_scope(self, monkeypatch, capsys):
        """A 404 on a private repo usually means the token lacks access —
        the error must say so, not just report the status."""
        _install_fake(
            monkeypatch,
            pr_error=PRNotAccessibleError("PR not accessible (HTTP 404)", status=404),
            repo_error=PRNotAccessibleError("PR not accessible (HTTP 404)", status=404),
        )
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        err = capsys.readouterr().err
        assert code == 1
        assert "token" in err.lower()
        assert "private" in err.lower()

    def test_pr_404_with_valid_repo_continues(self, monkeypatch, capsys):
        """EF-6 vs pr_url_valid: PR 404 but repo exists -> checker partial, not fatal."""
        _install_fake(monkeypatch, pr_error=PRNotAccessibleError("PR not accessible (HTTP 404)", status=404))
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        out = capsys.readouterr().out
        assert code == 0
        assert "PR URL submitted to Canvas" in out
        assert "partial" in out

    def test_rubric_not_found(self, capsys):
        code = cli.main([str(SAMPLE), "--rubric", "/nonexistent/rubric.yaml"])
        assert code == 1
        assert "rubric file not found" in capsys.readouterr().err

    def test_save_json(self, monkeypatch, capsys, tmp_path):
        _install_fake(monkeypatch)
        out_json = tmp_path / "assessment.json"
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC), "--save-json", str(out_json)])
        assert code == 0
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["assignment"] == "ICEX01"
        assert len(data["criteria"]) == 5
        assert "Full JSON saved to" in capsys.readouterr().out

    def test_output_format_json(self, monkeypatch, capsys):
        _install_fake(monkeypatch)
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC), "--output-format", "json"])
        out = capsys.readouterr().out
        assert code == 0
        data = json.loads(out)
        assert data["student_name"] == "Jane Doe"

    def test_token_never_printed(self, monkeypatch, capsys):
        """SC-12: token value never appears in stdout or stderr."""
        _install_fake(monkeypatch, token="super-secret-token")
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        captured = capsys.readouterr()
        assert code == 0
        assert "super-secret-token" not in captured.out
        assert "super-secret-token" not in captured.err

    def test_github_host_override(self, monkeypatch, capsys, tmp_path):
        constructed = _install_fake(monkeypatch)
        p = _html(tmp_path, "custom.html", url="https://git.example.edu/jdoe/fa26_c291/pull/42")
        code = cli.main([str(p), "--rubric", str(RUBRIC), "--github-host", "git.example.edu"])
        assert code == 0
        assert constructed[0].host == "git.example.edu"

    def test_verbose_prints_api_details(self, monkeypatch, capsys):
        _install_fake(monkeypatch)
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC), "--verbose"])
        err = capsys.readouterr().err
        assert code == 0
        assert "Add hello.c" in err

    def test_no_submission_and_no_batch(self, capsys):
        code = cli.main([])
        assert code == 1
        assert "submission file required" in capsys.readouterr().err

    def test_output_dir_requires_batch(self, capsys):
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC), "--output-dir", "/tmp/x"])
        assert code == 1
        assert "--output-dir" in capsys.readouterr().err

    def test_ag_score_accepted_single_submission(self, monkeypatch, capsys):
        """V1-4/EF-15: --ag-score N accepted when rubric has ag_max_points."""
        _install_fake(monkeypatch)
        rubric_path = _rubric_with_ag(tmp_path_or_none=None)
        code = cli.main(
            [str(SAMPLE), "--rubric", str(rubric_path), "--ag-score", "80"]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "AG score: 80/85" in out

    def test_ag_score_out_of_range_fatal(self, monkeypatch, capsys):
        """EF-15: --ag-score above ag_max_points -> exit 1."""
        _install_fake(monkeypatch)
        rubric_path = _rubric_with_ag(tmp_path_or_none=None)
        code = cli.main(
            [str(SAMPLE), "--rubric", str(rubric_path), "--ag-score", "99"]
        )
        err = capsys.readouterr().err
        assert code == 1
        assert "out of range" in err

    def test_ag_score_ignored_in_batch(self, monkeypatch, capsys, tmp_path):
        """EF-16: --ag-score with --batch -> warning, ignored."""
        _install_fake(monkeypatch)
        _html(tmp_path, "a.html")
        rubric_path = _rubric_with_ag(tmp_path_or_none=tmp_path)
        code = cli.main(
            ["--batch", str(tmp_path), "--rubric", str(rubric_path), "--ag-score", "80"]
        )
        captured = capsys.readouterr()
        assert code == 0
        assert "ignored" in captured.err

    def test_merged_pr_state_in_report(self, monkeypatch, capsys):
        """EF-14: merged PR shows 'merged' in the report."""
        _install_fake(monkeypatch)
        code = cli.main([str(SAMPLE), "--rubric", str(RUBRIC)])
        out = capsys.readouterr().out
        assert code == 0
        assert "State:" in out
        # With default open PR_OK, state should be open; the merged branch
        # is covered at the report unit level.

    def test_late_filename_zeroes_handgrading_in_report(self, monkeypatch, capsys, tmp_path):
        """V1-3: LATE detection flows into Assessment -> report."""
        _install_fake(monkeypatch)
        p = _html(tmp_path, "jdoe_LATE_6789124_link.html")
        rubric_path = _rubric_with_ag(tmp_path_or_none=tmp_path)
        code = cli.main([str(p), "--rubric", str(rubric_path)])
        out = capsys.readouterr().out
        assert code == 0
        assert "LATE SUBMISSION" in out
        assert "Handgrading: 0/15" in out


class TestBatch:
    def test_empty_dir_exit_zero(self, capsys, tmp_path):
        """EF-10: empty batch dir -> message, exit 0."""
        code = cli.main(["--batch", str(tmp_path), "--rubric", str(RUBRIC)])
        out = capsys.readouterr().out
        assert code == 0
        assert "no .html submission files found" in out

    def test_batch_success(self, monkeypatch, capsys, tmp_path):
        _install_fake(monkeypatch)
        _html(tmp_path, "a.html")
        _html(tmp_path, "b.html")
        code = cli.main(["--batch", str(tmp_path), "--rubric", str(RUBRIC)])
        out = capsys.readouterr().out
        assert code == 0
        assert "a.html" in out
        assert "b.html" in out
        assert "SUMMARY" in out

    def test_batch_partial_failure_exit_2(self, monkeypatch, capsys, tmp_path):
        """EF-11: one good, one unprocessable -> exit 2, both in summary."""
        _install_fake(monkeypatch)
        _html(tmp_path, "good.html")
        _html(tmp_path, "bad.html", url="")
        code = cli.main(["--batch", str(tmp_path), "--rubric", str(RUBRIC)])
        out = capsys.readouterr().out
        assert code == 2
        assert "good.html" in out
        assert "bad.html" in out
        assert "no PR URL found" in out

    def test_batch_output_dir(self, monkeypatch, capsys, tmp_path):
        _install_fake(monkeypatch)
        _html(tmp_path, "a.html")
        out_dir = tmp_path / "out"
        code = cli.main(["--batch", str(tmp_path), "--rubric", str(RUBRIC), "--output-dir", str(out_dir), "--output-format", "json"])
        assert code == 0
        assert (out_dir / "a.json").is_file()
        assert (out_dir / "summary.json").is_file()
        summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
        assert len(summary["submissions"]) == 1
        assert summary["submissions"][0]["status"] == "processed"

    def test_batch_writes_error_json_for_failed_submission(self, monkeypatch, capsys, tmp_path):
        """Issue #4: failed submissions get an individual error JSON too,
        not just a summary.json row (README contract)."""
        _install_fake(monkeypatch)
        _html(tmp_path, "good.html")
        p = tmp_path / "bad.html"
        p.write_text("<html><head><title>Week01 - ICEX01: Nobody</title></head><body></body></html>", encoding="utf-8")  # no PR URL
        out_dir = tmp_path / "out"
        code = cli.main(["--batch", str(tmp_path), "--rubric", str(RUBRIC), "--output-dir", str(out_dir), "--output-format", "json"])
        assert code == 2
        assert (out_dir / "good.json").is_file()
        err_path = out_dir / "bad.json"
        assert err_path.is_file()
        data = json.loads(err_path.read_text(encoding="utf-8"))
        assert data["file"] == "bad.html"
        assert data["status"] == "failed"

    def test_batch_text_format_writes_txt_reports(self, monkeypatch, capsys, tmp_path):
        """Issue #7: --output-format text in batch mode writes .txt reports."""
        _install_fake(monkeypatch)
        _html(tmp_path, "a.html")
        out_dir = tmp_path / "out"
        code = cli.main(["--batch", str(tmp_path), "--rubric", str(RUBRIC),
                         "--output-dir", str(out_dir), "--output-format", "text"])
        assert code == 0
        assert (out_dir / "a.txt").is_file()
        text = (out_dir / "a.txt").read_text(encoding="utf-8")
        assert "ICEX CHECKER REPORT" in text or "TA ACTION ITEMS" in text


class TestRosterFlag:
    """--roster overrides the rubric-declared roster_file (FERPA sidecar)."""

    @staticmethod
    def _roster_csv(tmp_path):
        p = tmp_path / "FA26_P465_Team_Roster.csv"
        p.write_text(
            "Team,TA,IU Username\r\nSE_TEAM01,Someone,jdoe\r\n",
            encoding="utf-8",
        )
        return p

    @staticmethod
    def _attribution_rubric(tmp_path, roster_decl=None):
        yaml = (
            "assignment: ICEX_T\n"
            "course: C291\n"
            "semester: FA26\n"
            "semester_start: 2026-08-24\n"
            "type: individual\n"
            "total_points: 2\n"
            "criteria:\n"
            "  - name: authorship\n"
            "    points: 2\n"
            "    checker: commit_author_check\n"
        )
        if roster_decl:
            yaml += "roster_file: %s\n" % roster_decl
        p = tmp_path / "attr_rubric.yaml"
        p.write_text(yaml, encoding="utf-8")
        return p

    def test_flag_loads_roster_and_attributes(self, monkeypatch, capsys, tmp_path):
        _install_fake(monkeypatch)
        rubric_p = self._attribution_rubric(tmp_path)
        roster_p = self._roster_csv(tmp_path)
        html_p = _html(tmp_path, "jdoe_77_link.html")
        code = cli.main([
            str(html_p), "--rubric", str(rubric_p),
            "--roster", str(roster_p), "--verbose",
        ])
        out = capsys.readouterr()
        assert code == 0
        assert "submitter (from filename, in roster): jdoe" in out.out
        assert "warning" not in out.err
        assert "No roster available" not in out.out

    def test_flag_overrides_rubric_declaration(self, monkeypatch, capsys, tmp_path):
        """Rubric declares roster.csv (absent); --roster wins and no EF-12."""
        _install_fake(monkeypatch)
        monkeypatch.chdir(tmp_path)  # declared roster.csv resolves here
        rubric_p = self._attribution_rubric(tmp_path, roster_decl="roster.csv")
        roster_p = self._roster_csv(tmp_path)
        html_p = _html(tmp_path, "jdoe_77_link.html")
        code = cli.main([
            str(html_p), "--rubric", str(rubric_p),
            "--roster", str(roster_p), "--verbose",
        ])
        out = capsys.readouterr()
        assert code == 0
        assert "warning" not in out.err  # flag replaced the missing declared file
        assert "submitter (from filename, in roster): jdoe" in out.out

    def test_missing_flag_path_warns_and_degrades(self, monkeypatch, capsys, tmp_path):
        """--roster pointing nowhere: EF-12 warning, run continues."""
        _install_fake(monkeypatch)
        rubric_p = self._attribution_rubric(tmp_path)
        html_p = _html(tmp_path, "jdoe_77_link.html")
        code = cli.main([
            str(html_p), "--rubric", str(rubric_p),
            "--roster", str(tmp_path / "nobody.csv"),
        ])
        err = capsys.readouterr().err
        assert code == 0
        assert "warning: roster file" in err
        assert "nobody.csv" in err


TEAM_ROSTER_CSV = (
    "Team,TA,IU Username,Canvas Name\r\n"
    "SE_TEAM07,Shreyas Karanam,ybingley,bingleyyashoneel\r\n"
    "SE_TEAM07,Shreyas Karanam,cjlomax,lomaxcalvin\r\n"
    "SE_TEAM12,Yash Jain,sdondeti,dondetisusruth\r\n"
)


class TestTeamsFlag:
    """--teams: filter batch by roster team + a team-scores rollup."""

    @staticmethod
    def _setup(monkeypatch, tmp_path):
        _install_fake(monkeypatch)
        roster_p = tmp_path / "team_roster.csv"
        roster_p.write_text(TEAM_ROSTER_CSV, encoding="utf-8")
        rubric_p = tmp_path / "attr_rubric.yaml"
        rubric_p.write_text(
            "assignment: ICEX_T\n"
            "course: C291\n"
            "semester: FA26\n"
            "semester_start: 2026-08-24\n"
            "type: individual\n"
            "total_points: 2\n"
            "roster_file: %s\n"
            "criteria:\n"
            "  - name: authorship\n"
            "    points: 2\n"
            "    checker: commit_author_check\n" % roster_p,
            encoding="utf-8",
        )
        return rubric_p, roster_p

    def test_batch_filters_to_requested_teams_and_rolls_up(
            self, monkeypatch, capsys, tmp_path):
        rubric_p, roster_p = self._setup(monkeypatch, tmp_path)
        _html(tmp_path, "bingleyyashoneel_1_link.html")   # SE_TEAM07
        _html(tmp_path, "lomaxcalvin_2_link.html")        # SE_TEAM07
        _html(tmp_path, "dondetisusruth_3_link.html")     # SE_TEAM12
        out_dir = tmp_path / "rep"
        code = cli.main([
            "--batch", str(tmp_path), "--rubric", str(rubric_p),
            "--roster", str(roster_p),
            "--teams", "7", "--output-dir", str(out_dir),
        ])
        captured = capsys.readouterr()
        assert code == 0
        out = captured.out
        # Only the two team-7 files processed; team-12 skipped.
        assert "bingleyyashoneel_1_link.html" in out
        assert "lomaxcalvin_2_link.html" in out
        assert "skipped   (submitter sdondeti, team SE_TEAM12 not requested)" in out
        # Team rollup: one PR line + students.
        assert "TEAM RESULTS (SE_TEAM07)" in out
        assert "SE_TEAM07" in out
        # The shared fake yields commit logins ['jdoe','akumar'], which are
        # not team-07 netids — the PR projects 0/2 and both walls lose.
        assert "0/2 pts (projected" in out
        assert "bingleyyashoneel" in out or "ybingley" in out
        # summary.json carries the teams section.
        s = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
        assert len(s["submissions"]) == 2
        assert s["teams"][0]["team"] == "SE_TEAM07"
        assert s["teams"][0]["late_members"] == []
        assert "pr_url" in s["submissions"][0]

    def test_teams_without_roster_is_fatal(self, monkeypatch, capsys, tmp_path):
        _install_fake(monkeypatch)
        rubric_p = tmp_path / "attr_rubric.yaml"
        rubric_p.write_text(
            "assignment: ICEX_T\ncourse: C291\nsemester: FA26\n"
            "semester_start: 2026-08-24\ntype: individual\ntotal_points: 2\n"
            "criteria:\n  - name: authorship\n    points: 2\n"
            "    checker: commit_author_check\n", encoding="utf-8")
        _html(tmp_path, "bingleyyashoneel_1_link.html")
        code = cli.main([
            "--batch", str(tmp_path), "--rubric", str(rubric_p),
            "--teams", "7",
        ])
        err = capsys.readouterr().err
        assert code == 1
        assert "--teams needs team membership" in err

    def test_single_run_other_team_skips(self, monkeypatch, capsys, tmp_path):
        rubric_p, roster_p = self._setup(monkeypatch, tmp_path)
        html_p = _html(tmp_path, "dondetisusruth_3_link.html")  # SE_TEAM12
        code = cli.main([
            str(html_p), "--rubric", str(rubric_p),
            "--roster", str(roster_p), "--teams", "7",
        ])
        err = capsys.readouterr().err
        assert code == 0
        assert "skipped: submitter" in err
        assert "SE_TEAM12" in err
