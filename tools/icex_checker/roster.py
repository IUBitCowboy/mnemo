"""Team roster loader for ICEX Submission Checker (V1-1/V1-2, EF-12).

The roster maps team identifiers to IU usernames (which equal GitHub
logins on github.iu.edu). Loaded from an optional instructor-provided
CSV on the OneDrive share. All failures return None — the roster is a
convenience, never a hard requirement.
"""

import csv
import pathlib
import re

_TEAM_ID_RE = re.compile(r"team(\d+)$", re.IGNORECASE)
_LEADING_ZEROS_RE = re.compile(r"0+(\d)")


def _norm(team_id):
    """Normalize a team identifier so team1 == Team01 == team01."""
    s = team_id.strip().lower()
    return _LEADING_ZEROS_RE.sub(r"\1", s)


class Roster:
    """Team -> usernames mapping plus conveniences.

    Team identifiers are stored under their original CSV form (e.g.
    "team01", "Team01") and matched case- and leading-zero-insensitively
    via a normalized alias map. Lookup methods return the original form.
    The optional TA column is exposed for TA-to-team mapping.
    """

    def __init__(self, teams, ta_by_team=None):
        self._teams = teams  # raw team key -> [usernames]
        self._ta_by_team = ta_by_team or {}  # raw team key -> TA login
        self._norm_to_raw = {}
        self._user_to_raw = {}
        for raw, users in teams.items():
            self._norm_to_raw.setdefault(_norm(raw), raw)
            for user in users:
                self._user_to_raw[user] = raw

    def _resolve(self, team_id):
        """Return the raw team key for a (maybe unnormalized) team id."""
        if not team_id:
            return None
        return self._norm_to_raw.get(_norm(team_id))

    def members(self, team_id):
        """Usernames for a team, or None if the team is unknown."""
        raw = self._resolve(team_id)
        return self._teams.get(raw) if raw else None

    def find_team(self, username):
        """The team a username belongs to (original form), or None."""
        return self._user_to_raw.get(username)

    def ta_for_team(self, team_id):
        """The TA assigned to a team (from the TA column), or None."""
        raw = self._resolve(team_id)
        return self._ta_by_team.get(raw) if raw else None

    def team_from_repo(self, repo_name):
        """Team key parsed from a repo name (fa26_se1_team01 -> team01).

        Returns the original roster form only if the team exists in the
        roster; otherwise None.
        """
        m = _TEAM_ID_RE.search(repo_name)
        if not m:
            return None
        return self._resolve("team" + m.group(1))


def load_roster(path):
    """Load a roster from CSV.

    Accepts two formats (headers matched case-insensitively):
      - v1.0: `team,iu_username`
      - v1.1: `Team,TA,IU Username` (TA column informational, exposed via
        Roster.ta_for_team)

    Returns a Roster, or None on any failure (missing file, malformed
    CSV, unrecognized columns) — callers warn and continue (EF-12).
    """
    p = pathlib.Path(path)
    if not p.is_file():
        return None
    try:
        with open(p, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return None
            fields = [c.strip().lower() for c in reader.fieldnames]
            team_col = None
            user_col = None
            ta_col = None
            for i, name in enumerate(fields):
                if name in ("team", "team name"):
                    team_col = i
                elif name in ("iu_username", "iu username", "username", "user"):
                    user_col = i
                elif name in ("ta", "ta username"):
                    ta_col = i
            if team_col is None or user_col is None:
                return None
            teams = {}
            ta_by_team = {}
            for row in reader:
                values = [row.get(h) for h in reader.fieldnames]
                t = values[team_col]
                u = values[user_col]
                if not t or not u or not u.strip():
                    return None
                teams.setdefault(t.strip(), []).append(u.strip())
                if ta_col is not None and values[ta_col]:
                    ta_by_team.setdefault(t.strip(), values[ta_col].strip())
    except (csv.Error, OSError, UnicodeDecodeError):
        return None
    if not teams:
        return None
    return Roster(teams, ta_by_team)
