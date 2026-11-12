"""GitHub Enterprise API client for ICEX Submission Checker."""

import os
import subprocess

import requests

from errors import (
    APIMissingTokenError,
    AuthFailureError,
    NetworkError,
    PRNotAccessibleError,
    RateLimitError,
)


class PR:
    """Pull request metadata (subset of the GitHub API response)."""

    def __init__(self, data):
        self.number = data.get("number")
        self.title = data.get("title") or ""
        self.body = data.get("body") or ""
        self.state = data.get("state") or ""
        self.merged = bool(data.get("merged"))
        self.created_at = data.get("created_at") or ""
        self.updated_at = data.get("updated_at") or ""
        head = data.get("head") or {}
        base = data.get("base") or {}
        self.head_ref = head.get("ref") or ""
        self.base_ref = base.get("ref") or ""
        self.commits = data.get("commits") or 0


class Repo:
    """Repository metadata (subset of the GitHub API response)."""

    def __init__(self, data):
        self.full_name = data.get("full_name") or ""
        self.name = data.get("name") or ""
        self.owner_login = (data.get("owner") or {}).get("login") or ""
        self.created_at = data.get("created_at") or ""
        self.html_url = data.get("html_url") or ""
        self.private = bool(data.get("private"))
        self.default_branch = data.get("default_branch") or ""


class GitHubClient:
    """Authenticated client for the GitHub Enterprise REST API.

    Base URL: https://{host}/api/v3
    Authentication: Authorization: token {token} (never logged).
    """

    def __init__(self, token, host):
        self.token = token
        self.host = host
        self.api_root = "https://%s/api/v3" % host
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": "token %s" % token,
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "icex-checker/1.0",
            }
        )

    # -- auth resolution ---------------------------------------------------

    @staticmethod
    def resolve_token(token, host=None):
        """Resolve an API token (FR-3, SC-9).

        Order: --token arg, GH_TOKEN, GITHUB_ENTERPRISE_TOKEN, then
        `gh auth token --hostname <host>`. Returns the token string or
        raises APIMissingTokenError with setup help.

        When falling back to `gh auth token`, the host is passed via
        --hostname so that the correct token is returned for multi-host
        setups (e.g. a user authenticated to both github.com and
        github.iu.edu). Without --hostname, `gh auth token` may return
        the token for a different host than the one the tool is querying.
        """
        if token:
            return token
        env_gh = os.environ.get("GH_TOKEN")
        if env_gh:
            return env_gh.strip()
        env_ent = os.environ.get("GITHUB_ENTERPRISE_TOKEN")
        if env_ent:
            return env_ent.strip()
        cmd = ["gh", "auth", "token"]
        if host:
            cmd.extend(["--hostname", host])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            proc = None
        if proc is not None and proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        raise APIMissingTokenError(
            "no API token found. Provide one via --token, GH_TOKEN, "
            "GITHUB_ENTERPRISE_TOKEN, or run `gh auth login` so the tool "
            "can use `gh auth token`."
        )

    # -- low-level request -------------------------------------------------

    def _raw_request(self, method, path, **kwargs):
        """Perform an HTTP request; returns a requests.Response.

        Raises NetworkError on connection-level failures.
        """
        try:
            return self.session.request(method, self.api_root + path, timeout=30, **kwargs)
        except requests.exceptions.Timeout as exc:
            raise NetworkError("network error: request timed out (%s)" % exc) from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError("network error: %s" % exc) from exc

    def _request(self, method, path, **kwargs):
        """JSON request with error mapping (EF-4..EF-7).

        Returns the parsed JSON body for 2xx. Raises AuthFailureError,
        RateLimitError, PRNotAccessibleError, or NetworkError.
        """
        resp = self._raw_request(method, path, **kwargs)
        status = resp.status_code
        if 200 <= status < 300:
            if not resp.content:
                return None
            return resp.json()
        body_message = None
        try:
            body_message = resp.json().get("message")
        except ValueError:
            pass
        if status == 401:
            raise AuthFailureError(
                "authentication failed (HTTP 401). Create a token with "
                "'repo' scope at https://%s/settings/tokens" % self.host
            )
        if status == 403 or status == 429:
            reset = resp.headers.get("X-RateLimit-Reset")
            extra = ""
            if reset:
                import datetime

                reset_dt = datetime.datetime.fromtimestamp(
                    int(reset), tz=datetime.timezone.utc
                )
                extra = " (resets at %s UTC)" % reset_dt.isoformat()
            raise RateLimitError(
                "rate limited by GitHub API (HTTP %d)%s. If this is not a "
                "rate limit, your token may lack permission for this repo."
                % (status, extra)
            )
        raise PRNotAccessibleError(
            "PR not accessible (HTTP %d)" % status,
            status=status,
            body_message=body_message,
        )

    # -- endpoints ---------------------------------------------------------

    def get_pr(self, owner, repo, number):
        """GET /repos/{owner}/{repo}/pulls/{number} (FR-4)."""
        data = self._request("GET", "/repos/%s/%s/pulls/%d" % (owner, repo, number))
        return PR(data)

    def get_repo(self, owner, repo):
        """GET /repos/{owner}/{repo} (FR-4)."""
        data = self._request("GET", "/repos/%s/%s" % (owner, repo))
        return Repo(data)

    def get_commit_author_dates(self, owner, repo):
        """GET /repos/{owner}/{repo}/commits?per_page=100 (first page only).

        Returns a list of commit author date strings.
        """
        data = self._request(
            "GET",
            "/repos/%s/%s/commits" % (owner, repo),
            params={"per_page": 100},
        )
        if not isinstance(data, list):
            return []
        dates = []
        for commit in data:
            author = (commit.get("commit") or {}).get("author") or {}
            if author.get("date"):
                dates.append(author["date"])
        return dates

    def get_pr_commit_logins(self, owner, repo, number):
        """GET /repos/{owner}/{repo}/pulls/{number}/commits (V1-2).

        Returns a list of commit author logins (GitHub usernames).
        """
        data = self._request(
            "GET",
            "/repos/%s/%s/pulls/%d/commits" % (owner, repo, number),
            params={"per_page": 100},
        )
        if not isinstance(data, list):
            return []
        logins = []
        for commit in data:
            author = commit.get("author") or {}
            if author.get("login"):
                logins.append(author["login"])
        return logins

    def get_pr_commits(self, owner, repo, number):
        """GET /repos/{owner}/{repo}/pulls/{number}/commits (W8 wall evidence).

        First page (per_page=100). Returns a list of {sha, login, date,
        message} dicts: sha truncated to 8 chars, login the top-level
        author login ("?" when the API provides none), date the commit
        author date string, message the subject line (first line,
        truncated at 80 chars).
        """
        data = self._request(
            "GET",
            "/repos/%s/%s/pulls/%d/commits" % (owner, repo, number),
            params={"per_page": 100},
        )
        if not isinstance(data, list):
            return []
        commits = []
        for commit in data:
            author = (commit.get("commit") or {}).get("author") or {}
            gh_author = commit.get("author") or {}
            message = (commit.get("commit") or {}).get("message") or ""
            commits.append(
                {
                    "sha": (commit.get("sha") or "")[:8],
                    "login": gh_author.get("login") or "?",
                    "date": author.get("date"),
                    "message": message.split("\n", 1)[0][:80],
                }
            )
        return commits

    def list_pulls(self, owner, repo):
        """GET /repos/{owner}/{repo}/pulls?state=all (V1-6).

        First page (per_page=100), all states. Returns a list of dicts:
        {number, author, title, state ('open'/'closed'/'merged'), merged_at}.
        """
        data = self._request(
            "GET",
            "/repos/%s/%s/pulls" % (owner, repo),
            params={"state": "all", "per_page": 100},
        )
        if not isinstance(data, list):
            return []
        pulls = []
        for pr in data:
            user = pr.get("user") or {}
            merged_at = pr.get("merged_at")
            pulls.append(
                {
                    "number": pr.get("number"),
                    "author": user.get("login") or "",
                    "title": pr.get("title") or "",
                    "state": "merged" if merged_at else (pr.get("state") or ""),
                    "merged_at": merged_at,
                    "head_ref": (pr.get("head") or {}).get("ref") or "",
                }
            )
        return pulls

    def get_file_contents(self, owner, repo, path, ref=None):
        """GET /repos/{owner}/{repo}/contents/{path}[?ref=] (MoJ).

        For blob-URL submissions (AGR memos, EngLog entries, team
        documents like docs/a_mj05_ethics_opener.md).

        Returns ('file', decoded_text) when the path is a file,
        ('dir', None) when it is a directory listing, ('missing', None)
        on 404/403. Auth and rate-limit failures raise.
        """
        params = {}
        if ref:
            params["ref"] = ref
        try:
            data = self._request(
                "GET",
                "/repos/%s/%s/contents/%s" % (owner, repo, path),
                params=params,
            )
        except PRNotAccessibleError:
            return "missing", None
        if isinstance(data, list):
            return "dir", None
        if isinstance(data, dict) and data.get("type") == "file":
            import base64

            raw = data.get("content") or ""
            try:
                return "file", base64.b64decode(raw).decode("utf-8", errors="replace")
            except Exception:
                return "file", None
        return "missing", None

    def get_commits_for_path(self, owner, repo, path=None):
        """GET /repos/{owner}/{repo}/commits[?path=]&per_page=100 (MoJ).

        First page only. Returns a list of {sha, date, author} dicts,
        where date is the commit author date string and author is the
        top-level login when the API provides one (else "?").
        """
        params = {"per_page": 100}
        if path:
            params["path"] = path
        data = self._request(
            "GET",
            "/repos/%s/%s/commits" % (owner, repo),
            params=params,
        )
        if not isinstance(data, list):
            return []
        commits = []
        for commit in data:
            author = (commit.get("commit") or {}).get("author") or {}
            commits.append(
                {
                    "sha": (commit.get("sha") or "")[:8],
                    "date": author.get("date"),
                    "author": (commit.get("author") or {}).get("login") or "?",
                }
            )
        return commits

    def get_pr_diff(self, owner, repo, number):
        """GET the PR diff with the diff media type (FR-4).

        The response is plain unified-diff text, not JSON.
        """
        resp = self._raw_request(
            "GET",
            "/repos/%s/%s/pulls/%d" % (owner, repo, number),
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        status = resp.status_code
        if 200 <= status < 300:
            return resp.text
        if status == 401:
            raise AuthFailureError("authentication failed (HTTP 401)")
        if status in (403, 429):
            raise RateLimitError("rate limited by GitHub API (HTTP %d)" % status)
        raise PRNotAccessibleError(
            "PR not accessible (HTTP %d)" % status,
            status=status,
            body_message=resp.text[:300],
        )
