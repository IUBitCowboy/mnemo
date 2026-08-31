"""Tests for the team roster loader (V1-1/V1-2, EF-12)."""
import pytest

import roster

CSV_GOOD = (
    "team,iu_username\n"
    "team01,jsmith\n"
    "team01,jdoe\n"
    "team01,rhaldhah\n"
    "team02,akumar\n"
    "team02,bliu\n"
)

# Real-world format (v1.1): Team,TA,IU Username — TA column informational.
CSV_TA = (
    "Team,TA,IU Username\n"
    "team01,ta_smith,jsmith\n"
    "team01,ta_smith,jdoe\n"
    "team01,ta_smith,rhaldhah\n"
    "team02,ta_jones,akumar\n"
    "team02,ta_jones,bliu\n"
)


class TestLoadRoster:
    def test_loads_valid_csv(self, tmp_path):
        p = tmp_path / "roster.csv"
        p.write_text(CSV_GOOD, encoding="utf-8")

        r = roster.load_roster(str(p))

        assert r is not None
        assert r.members("team01") == ["jsmith", "jdoe", "rhaldhah"]
        assert r.members("team02") == ["akumar", "bliu"]
        assert r.members("team99") is None

    def test_missing_file_returns_none(self, tmp_path):
        """EF-12: missing roster -> None (caller warns and continues)."""
        assert roster.load_roster(str(tmp_path / "nope.csv")) is None

    def test_malformed_csv_returns_none(self, tmp_path):
        """EF-12: malformed roster -> None, no crash."""
        p = tmp_path / "bad.csv"
        p.write_text('team,iu_username\n"unclosed,line\n', encoding="utf-8")
        assert roster.load_roster(str(p)) is None

    def test_wrong_columns_returns_none(self, tmp_path):
        p = tmp_path / "wrong.csv"
        p.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        assert roster.load_roster(str(p)) is None

    def test_three_column_ta_format_loads(self, tmp_path):
        """v1.1: Team,TA,IU Username — Team + IU Username parsed, TA ignored."""
        p = tmp_path / "roster_ta.csv"
        p.write_text(CSV_TA, encoding="utf-8")

        r = roster.load_roster(str(p))

        assert r is not None
        assert r.members("team01") == ["jsmith", "jdoe", "rhaldhah"]
        assert r.members("team02") == ["akumar", "bliu"]
        assert r.find_team("jdoe") == "team01"

    def test_ta_column_available_for_mapping(self, tmp_path):
        """The TA column is exposed so TAs can see their team assignments."""
        p = tmp_path / "roster_ta.csv"
        p.write_text(CSV_TA, encoding="utf-8")

        r = roster.load_roster(str(p))

        assert r.ta_for_team("team01") == "ta_smith"
        assert r.ta_for_team("team02") == "ta_jones"
        assert r.ta_for_team("team99") is None


class TestLookups:
    def test_find_team_for_user(self, tmp_path):
        p = tmp_path / "roster.csv"
        p.write_text(CSV_GOOD, encoding="utf-8")
        r = roster.load_roster(str(p))

        assert r.find_team("jdoe") == "team01"
        assert r.find_team("akumar") == "team02"
        assert r.find_team("nobody") is None

    def test_team_from_repo_name(self, tmp_path):
        """V1-1: trailing team identifier parsed from repo name."""
        p = tmp_path / "roster.csv"
        p.write_text(CSV_GOOD, encoding="utf-8")
        r = roster.load_roster(str(p))

        assert r.team_from_repo("fa26_se1_team01") == "team01"
        assert r.team_from_repo("fa26_se1_team02") == "team02"
        assert r.team_from_repo("fa26_c291") is None

    def test_team_id_case_insensitive(self, tmp_path):
        """Repo team01 matches roster Team01."""
        p = tmp_path / "roster.csv"
        p.write_text("team,iu_username\nTeam01,jsmith\nTeam01,jdoe\n", encoding="utf-8")
        r = roster.load_roster(str(p))

        assert r.team_from_repo("fa26_se1_team01") is not None
        assert r.members("team01") == ["jsmith", "jdoe"]

    def test_repo_team_numbers_matching_roster(self, tmp_path):
        """V1-6: repo 'team1' vs roster 'team01' must resolve."""
        p = tmp_path / "roster.csv"
        p.write_text("team,iu_username\nteam1,jsmith\n", encoding="utf-8")
        r = roster.load_roster(str(p))

        assert r.team_from_repo("fa26_se1_team1") == "team1"
