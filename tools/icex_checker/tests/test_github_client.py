"""Tests for the GitHub Enterprise API client (FR-3, FR-4, EF-4..EF-7)."""
import types

import pytest
import requests

from icex_checker import (
    APIMissingTokenError,
    AuthFailureError,
    NetworkError,
    PRNotAccessibleError,
    RateLimitError,
)
from github_client import GitHubClient

PR_PAYLOAD = {
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

REPO_PAYLOAD = {
    "full_name": "jdoe/fa26_c291",
    "name": "fa26_c291",
    "owner": {"login": "jdoe"},
    "created_at": "2026-08-20T09:00:00Z",
    "pushed_at": "2026-08-25T12:00:00Z",
    "html_url": "https://github.iu.edu/jdoe/fa26_c291",
    "private": False,
    "default_branch": "main",
}

COMMITS_PAYLOAD = [
    {"sha": "abc123", "commit": {"author": {"date": "2026-05-01T12:00:00Z"}}},
    {"sha": "def456", "commit": {"author": {"date": "2026-08-26T10:00:00Z"}}},
]


def _client():
    return GitHubClient(token="test-token", host="github.iu.edu")


class TestTokenResolution:
    """Authentication resolution order (FR-3, SC-9)."""

    def test_gh_token_env_var(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "env-gh")
        assert GitHubClient.resolve_token(token=None) == "env-gh"

    def test_github_enterprise_token_env_var(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_ENTERPRISE_TOKEN", "env-enterprise")
        assert GitHubClient.resolve_token(token=None) == "env-enterprise"

    def test_cli_token_precedes_env(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "env-gh")
        assert GitHubClient.resolve_token(token="cli-token") == "cli-token"

    def test_gh_auth_token_fallback(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_ENTERPRISE_TOKEN", raising=False)

        class FakeProc:
            returncode = 0
            stdout = "gh-token-from-cli\n"

        monkeypatch.setattr("subprocess.run", lambda *a, **k: FakeProc())
        assert GitHubClient.resolve_token(token=None) == "gh-token-from-cli"

    def test_gh_auth_missing_raises_helpful_message(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_ENTERPRISE_TOKEN", raising=False)

        def boom(*a, **k):
            raise FileNotFoundError("gh not found")

        monkeypatch.setattr("subprocess.run", boom)
        with pytest.raises(APIMissingTokenError) as exc:
            GitHubClient.resolve_token(token=None)
        assert "token" in str(exc.value).lower()


class TestGetPR:
    def test_fetches_pr_metadata(self):
        c = _client()
        c._request = lambda method, path, **kw: PR_PAYLOAD
        pr = c.get_pr("jdoe", "fa26_c291", 42)

        assert pr.number == 42
        assert pr.title == "Add hello.c"
        assert pr.body == "My pull request for ICEX01."
        assert pr.state == "open"
        assert pr.head_ref == "jdoe-patch-1"
        assert pr.base_ref == "main"
        assert pr.commits == 3

    def test_pr_404_raises_not_accessible(self):
        c = _client()

        def not_found(method, path, **kw):
            raise PRNotAccessibleError(
                "PR not accessible (HTTP 404)", status=404, body_message="Not Found"
            )

        c._request = not_found
        with pytest.raises(PRNotAccessibleError) as exc:
            c.get_pr("jdoe", "fa26_c291", 42)
        assert exc.value.status == 404


class TestGetRepo:
    def test_fetches_repo_info(self):
        c = _client()
        c._request = lambda method, path, **kw: REPO_PAYLOAD
        repo = c.get_repo("jdoe", "fa26_c291")

        assert repo.full_name == "jdoe/fa26_c291"
        assert repo.owner_login == "jdoe"
        assert repo.created_at == "2026-08-20T09:00:00Z"
        assert repo.name == "fa26_c291"
        assert repo.default_branch == "main"


class TestGetCommits:
    def test_returns_author_dates(self):
        c = _client()
        c._request = lambda method, path, **kw: COMMITS_PAYLOAD
        dates = c.get_commit_author_dates("jdoe", "fa26_c291")

        assert dates == ["2026-05-01T12:00:00Z", "2026-08-26T10:00:00Z"]

    def test_first_page_only(self):
        """FR-4: first page only; per_page is capped at 100."""
        seen = {}

        def capture(method, path, **kw):
            seen.update(kw)
            return []

        c = _client()
        c._request = capture
        c.get_commit_author_dates("jdoe", "fa26_c291")

        assert seen["params"] == {"per_page": 100}


class TestGetDiff:
    def test_accepts_diff_media_type(self):
        c = _client()
        seen = {}
        c.get_pr = lambda *a, **k: PR_PAYLOAD

        def fake_raw(method, path, **kw):
            seen.update(kw)
            return types.SimpleNamespace(status_code=200, text="raw diff")

        c._raw_request = fake_raw

        text = c.get_pr_diff("jdoe", "fa26_c291", 42)

        assert text == "raw diff"
        assert seen["headers"]["Accept"] == "application/vnd.github.v3.diff"


class TestErrorMapping:
    """EF-4..EF-7: HTTP errors map to typed exceptions.

    Exercises the REAL _request/_raw_request mapping code by patching the
    session.request seam — never by replacing the mapping itself.
    """

    @staticmethod
    def _response(status_code, body=None, headers=None):
        body = body or {}

        def _json():
            return body

        return types.SimpleNamespace(
            status_code=status_code,
            headers=headers or {},
            json=_json,
            message=body.get("message"),
            text="",
        )

    def _patch_session(self, c, fake):
        c.session.request = fake

    def test_401_is_auth_failure(self):
        c = _client()
        self._patch_session(c, lambda *a, **k: self._response(401))
        with pytest.raises(AuthFailureError):
            c.get_repo("jdoe", "fa26_c291")

    def test_403_is_rate_limit(self):
        c = _client()
        self._patch_session(c, lambda *a, **k: self._response(403, {"message": "API rate limit exceeded"}))
        with pytest.raises(RateLimitError):
            c.get_repo("jdoe", "fa26_c291")

    def test_404_is_pr_not_accessible(self):
        c = _client()
        self._patch_session(c, lambda *a, **k: self._response(404))
        with pytest.raises(PRNotAccessibleError) as exc:
            c.get_repo("jdoe", "fa26_c291")
        assert exc.value.status == 404

    def test_connection_error_is_network_error(self):
        c = _client()

        def boom(*a, **k):
            raise requests.exceptions.ConnectionError("boom")

        self._patch_session(c, boom)
        with pytest.raises(NetworkError):
            c.get_repo("jdoe", "fa26_c291")

    def test_timeout_is_network_error(self):
        c = _client()

        def boom(*a, **k):
            raise requests.exceptions.Timeout("slow")

        self._patch_session(c, boom)
        with pytest.raises(NetworkError):
            c.get_repo("jdoe", "fa26_c291")


def test_api_base_uses_host():
    c = GitHubClient(token="t", host="github.iu.edu")
    assert c.api_root == "https://github.iu.edu/api/v3"
