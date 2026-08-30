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


class TestVersion:
    def test_version_flag(self, capsys):
        code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert code == 0
        assert "icex_checker" in out
        assert "1.0.0" in out


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
        code = cli.main(["--batch", str(tmp_path), "--rubric", str(RUBRIC), "--output-dir", str(out_dir)])
        assert code == 0
        assert (out_dir / "a.json").is_file()
        assert (out_dir / "summary.json").is_file()
        summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
        assert len(summary["submissions"]) == 1
        assert summary["submissions"][0]["status"] == "processed"
