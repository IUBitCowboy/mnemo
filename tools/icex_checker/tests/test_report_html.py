"""Tests for the TA-facing HTML report emitter (report_html).

FA26 workflow change: TAs grade from Kurt's generated report.html; the
index must surface absences (exceptions + missing submissions), team
lanes must carry the Collaboration Coefficient arithmetic, and re-runs
overwrite with a fresh timestamp.
"""
import json
import pathlib

import pytest

import report_html
from checkers import Finding
from report import Assessment


class _StubRoster:
    """Mimics the real roster.Roster API surface (no .rows)."""

    ROWS = {
        "SE_TEAM01": {"ta": "TA Alpha", "members": [
            ("cs155", "Smith, Caleb"), ("bgtruong", "Truong, Bao")]},
        "SE_TEAM02": {"ta": "TA Alpha", "members": [
            ("hkataria", "Kataria, Hiten")]},
        "SE_TEAM03": {"ta": "TA Beta", "members": [
            ("jakecole", "Cole, Jackson")]},
    }

    @property
    def _teams(self):
        return {t: [m[0] for m in info["members"]]
                for t, info in self.ROWS.items()}

    def members(self, team_id):
        return [m[0] for m in self.ROWS.get(team_id, {"members": []})
                ["members"]]

    def ta_for_team(self, team_id):
        return self.ROWS.get(team_id, {}).get("ta", "")

    def canonical_username(self, raw):
        for members in self.ROWS.values():
            for m in members:
                if m[0] == raw:
                    return raw
        return raw


class _StubRubric:
    assignment = "A_TEST"
    course = "SE1"
    total_points = 20
    canvas_points = 20
    collaboration_coefficient = 1.0
    type = "individual"
    ownership_check = "self"


def _assessment(name="Smith, Caleb", netid="cs155", rec=None,
                late=False, findings=None, pr_details=None):
    if findings is None:
        findings = [
            Finding(_c("Presence"), "pass", 3,
                    ["evidence: ok"], "note", False),
            Finding(_c("Review row"), "needs-review", None,
                    ["evidence: pending"], "TA confirms the CI state",
                    True),
        ]
    return Assessment(
        assignment="A_TEST", course="SE1", semester="FA26",
        student_name=name, pr_url="https://github.iu.edu/o/r/pull/3",
        timestamp="2026-11-13T09:00:00", tool_version="v-test",
        pr_details=pr_details, findings=findings,
        is_late=late, canvas_points=20,
    )


def _c(name):
    import types
    return types.SimpleNamespace(name=name, points=3, checker="stub")


def _fake_client_file_kind():  # pragma: no cover - unused, appease linters
    return None


def _lane_dir(tmp_path, filenames):
    d = tmp_path / "lane-test"
    d.mkdir(exist_ok=True)
    for fn in filenames:
        (d / fn).write_text(
            "<html><title>Lane Title: X</title>"
            "<meta http-equiv='Refresh' content='0; "
            "url=https://github.iu.edu/o/r/pull/3'></html>")
    return d


_STUB = object()


def _run_emit(tmp_path, batch_results, batch_files, rubric=None,
              roster=_STUB, filtered=None):
    batch_dir = _lane_dir(tmp_path, batch_files)
    out_root = tmp_path / "out"
    out_root.mkdir(exist_ok=True)
    roster_obj = _StubRoster() if roster is _STUB else roster
    manifest, index = report_html.emit_lane(
        batch_dir, batch_results, out_root, "2026-11-13 09:00 EST",
        rubric or _StubRubric(), roster_obj,
        filtered_teams=filtered)
    return manifest, index, out_root


class TestLaneEmission:
    def test_manifest_and_pages_written(self, tmp_path):
        results = [{"file": "cs155_1_link.html", "status": "processed",
                    "recommended_points": 3, "total_points": 6,
                    "team": "SE_TEAM01",
                    "pr_url": "https://github.iu.edu/o/r/pull/3",
                    "_assessment": _assessment()}]
        m, index, root = _run_emit(
            tmp_path, results,
            ["cs155_1_link.html", "bgtruong_2_link.html"])
        assert (root / "report.html").exists()
        assert (root / "TA-reports/lane-test/cs155.html").exists()
        page = (root / "TA-reports/lane-test/cs155.html").read_text()
        assert "RECOMMENDED, NOT FINAL" in page
        assert "email cs155" in page  # mailto link with netid
        assert m["entries"][0]["team"] == "SE_TEAM01"
        assert m["assignment_title"] == "Lane Title"

    def test_absent_member_surfaced(self, tmp_path):
        # Only cs155 submitted; bgtruong and SE_TEAM03 member missing.
        results = [{"file": "cs155_1_link.html", "status": "processed",
                    "recommended_points": 3, "total_points": 6,
                    "team": "SE_TEAM01", "pr_url": "", "_assessment":
                    _assessment()}]
        m, _, _ = _run_emit(tmp_path, results, ["cs155_1_link.html"])
        missing_names = [x["iu"] for x in m["missing"]]
        assert "bgtruong" in missing_names and "jakecole" in missing_names
        idx = None
        index = (tmp_path / "out" / "report.html").read_text()
        assert "MISSING — no Canvas submission file found" in index
        assert "bgtruong" in index

    def test_exception_surfaced(self, tmp_path):
        results = [
            {"file": "cs155_1_link.html", "status": "processed",
             "recommended_points": 3, "total_points": 6,
             "team": "SE_TEAM01", "pr_url": "", "_assessment": _assessment()},
            {"file": "bgtruong_2_link.html", "status": "failed",
             "error": "malformed URL or not a PR URL", "team": "SE_TEAM01"},
        ]
        m, _, _ = _run_emit(tmp_path, results,
                            ["cs155_1_link.html", "bgtruong_2_link.html"])
        assert m["exceptions"][0]["netid"] == "bgtruong"
        assert "malformed URL" in m["exceptions"][0]["error"]
        index = (tmp_path / "out" / "report.html").read_text()
        assert "Needs TA review — tool produced no report" in index
        # bgtruong had a file → exception, NOT missing
        assert "bgtruong" not in [x["iu"] for x in m["missing"]]

    def test_team_lane_member_gap(self, tmp_path):
        rubric = _StubRubric()
        rubric.type = "team"
        rubric.ownership_check = "team"
        results = [{"file": "cs155_1_link.html", "status": "processed",
                    "recommended_points": 25, "total_points": 30,
                    "team": "SE_TEAM01", "pr_url": "", "_assessment":
                    _assessment(rec=25)}]
        m, _, _ = _run_emit(tmp_path, results, ["cs155_1_link.html"],
                            rubric=rubric)
        # bgtruong belongs to the team with a deliverable → member gap
        assert any(g["iu"] == "bgtruong" for g in m["member_gaps"])
        assert m["type"] == "team"

    def test_team_lane_coefficient_math(self, tmp_path):
        rubric = _StubRubric()
        rubric.type = "team"
        rubric.collaboration_coefficient = 0.9
        results = [{"file": "cs155_1_link.html", "status": "processed",
                    "recommended_points": 25, "total_points": 30,
                    "team": "SE_TEAM01", "pr_url": "", "_assessment":
                    _assessment(rec=25)}]
        m, _, _ = _run_emit(tmp_path, results, ["cs155_1_link.html"],
                            rubric=rubric)
        index = (tmp_path / "out" / "report.html").read_text()
        assert "22" in index and "times;0.9" in index.replace("&times;"
                                                               "&#215;",
                                                               "times;")
        # page shows the TAP explanation
        page = (tmp_path / "out" / "TA-reports/lane-test/cs155.html"
                ).read_text()
        assert "TAP Collaboration" in page

    def test_filtered_teams_scoped_to_request(self, tmp_path):
        results = [{"file": "cs155_1_link.html", "status": "processed",
                    "recommended_points": 3, "total_points": 6,
                    "team": "SE_TEAM01", "pr_url": "", "_assessment":
                    _assessment()}]
        m, _, _ = _run_emit(tmp_path, results, ["cs155_1_link.html"],
                            filtered={"SE_TEAM01"})
        assert not any(x["iu"] == "jakecole" for x in m["missing"])

    def test_rerun_overwrites_with_new_timestamp(self, tmp_path):
        results = [{"file": "cs155_1_link.html", "status": "processed",
                    "recommended_points": 3, "total_points": 6,
                    "team": "SE_TEAM01", "pr_url": "", "_assessment":
                    _assessment()}]
        files = ["cs155_1_link.html"]
        m1, _, _ = _run_emit(tmp_path, results, files)
        page1 = (tmp_path / "out" / "TA-reports/lane-test/cs155.html"
                 ).read_text()
        m2, _, _ = _run_emit(tmp_path, results, files)
        page2 = (tmp_path / "out" / "TA-reports/lane-test/cs155.html"
                 ).read_text()
        # one page per student even after a re-run (overwrite, not append)
        pages = list((tmp_path / "out" / "TA-reports/lane-test")
                     .glob("*.html"))
        assert len(pages) == 1
        # the page always carries the run timestamp of its latest run
        assert "run " + m2["run_ts"] in page2 and "run " in page1

    def test_no_roster_still_emits(self, tmp_path):
        results = [{"file": "mysteryperson_1_link.html",
                    "status": "processed", "recommended_points": 3,
                    "total_points": 6, "team": None, "pr_url": "",
                    "_assessment": _assessment(name="Mystery")}]
        m, index, _ = _run_emit(
            tmp_path, results, ["mysteryperson_1_link.html"], roster=None)
        assert m["entries"][0]["team"] == ""
        assert (tmp_path / "out" / "report.html").exists()

    def test_csv_roster_carries_names_and_ids(self, tmp_path):
        csv_path = tmp_path / "roster.csv"
        csv_path.write_text(
            "Team,TA,IU Username,Canvas Name,Name,ID\r\n"
            "SE_TEAM01,TA Alpha,cs155,smithcaleb,\"Smith, Caleb\",12345\r\n"
            "SE_TEAM02,TABeta,hkataria,katariahiten,\"Kataria, Hiten\",6789\r\n")
        results = [{"file": "cs155_1_link.html", "status": "processed",
                    "recommended_points": 3, "total_points": 6,
                    "team": "SE_TEAM01", "pr_url": "", "_assessment":
                    _assessment()}]
        batch_dir = _lane_dir(tmp_path, ["cs155_1_link.html"])
        out_root = tmp_path / "out"
        out_root.mkdir()
        m, _ = report_html.emit_lane(
            batch_dir, results, out_root, "ts", _StubRubric(), None,
            roster_csv=str(csv_path))
        e = m["entries"][0]
        assert e["name"] == "Smith, Caleb" and e["canvas_id"] == "12345"
        assert e["ta"] == "TA Alpha"
        assert "hkataria" in [x["iu"] for x in m["missing"]]
        page = (out_root / "TA-reports/lane-test/cs155.html").read_text()
        assert "email cs155" in page and "12345" in page
        index = (out_root / "report.html").read_text()
        # missing-row cell carries the TA from the CSV; chips no longer
        # repeat TA names (dropped per Kurt, 2026-11-13)
        assert "TABeta" in index and "chip(this)" in index


class TestChips:
    """Team filter chips: All preselected, one chip per team, no TA chips,
    and the .hide rule that actually hides filtered rows."""

    def _index(self, tmp_path):
        results = [
            {"file": "cs155_1_link.html", "status": "processed",
             "recommended_points": 3, "total_points": 6,
             "team": "SE_TEAM01", "pr_url": "", "_assessment": _assessment()},
            {"file": "jakecole_2_link.html", "status": "processed",
             "recommended_points": 4, "total_points": 6,
             "team": "SE_TEAM03", "pr_url": "", "_assessment":
             _assessment(name="Cole, Jackson", rec=4)},
        ]
        m, index, out = _run_emit(
            tmp_path, results,
            ["cs155_1_link.html", "jakecole_2_link.html"])
        return m, (tmp_path / "out" / "report.html").read_text()

    def test_all_chip_preselected_and_no_ta_chips(self, tmp_path):
        import re
        m, index = self._index(tmp_path)
        chips_html = re.search(r'<div class="chips">(.*?)</div>', index,
                               re.S).group(1)
        assert 'chip on" data-team="*"' in chips_html
        assert "TA: " not in chips_html

    def test_filterable_rows_exposed(self, tmp_path):
        m, index = self._index(tmp_path)
        assert index.count('data-team="SE_TEAM01"') >= 1
        assert index.count('data-team="SE_TEAM03"') >= 1
        # the hide rule must ship with the page or filtering is a no-op
        assert ".hide { display:none" in index


class TestHalvesAndStudentView:
    """Two-TA model: A/B halves (alphabetical default, halves.csv
    override) + the per-student review surface (students.html
    gradebook + TA-reports/students/<netid>.html pages)."""

    def _index(self, tmp_path):
        results = [
            {"file": "cs155_1_link.html", "status": "processed",
             "recommended_points": 3, "total_points": 6,
             "team": "", "pr_url": "", "_assessment":
             _assessment(rec=3)},
            {"file": "jakecole_2_link.html", "status": "processed",
             "recommended_points": 4, "total_points": 6,
             "team": "", "pr_url": "", "_assessment":
             _assessment(name="Cole, Jackson", rec=4)},
        ]
        m, index, out = _run_emit(
            tmp_path, results,
            ["cs155_1_link.html", "jakecole_2_link.html"])
        return m, out

    def test_half_chips_present(self, tmp_path):
        m, out = self._index(tmp_path)
        index = (out / "report.html").read_text()
        assert 'data-half="A"' in index and 'data-half="B"' in index

    def test_rows_carry_half(self, tmp_path):
        m, out = self._index(tmp_path)
        index = (out / "report.html").read_text()
        # both students carry a data-half attribute on their rows
        assert index.count('data-half="') >= 2

    def test_halves_csv_override_wins(self, tmp_path):
        m, out = self._index(tmp_path)
        (out / "halves.csv").write_text("# manual\njakecole,b\n")
        report_html.emit_index(out, "2026-11-15 12:00 EST")
        index = (out / "report.html").read_text()
        # alphabetical default: cs155 < jakecole, so cs155 -> A; the
        # csv listed only jakecole and must not disturb that
        srow = [l for l in index.splitlines()
                if 'data-half=' in l and "cs155" in l]
        assert srow and 'data-half="A"' in srow[0]

    def test_students_gradebook_and_pages(self, tmp_path):
        m, out = self._index(tmp_path)
        sgb = out / "students.html"
        assert sgb.exists()
        g = sgb.read_text()
        assert "Half A" in g and "Half B" in g
        assert "/6" in g            # score cells
        spages = sorted((out / "TA-reports" / "students").glob("*.html"))
        assert spages
        page = spages[0].read_text()
        assert "Graded sum:" in page
        assert "A_TEST" in page
        assert "&larr; all students" in page

    def test_students_rows_carry_half(self, tmp_path):
        m, out = self._index(tmp_path)
        g = (out / "students.html").read_text()
        assert 'data-half="' in g


class TestUpdateHistory:
    """Delta tracking: first run ships no badge; a changed later run
    badges the page and the index row; an unchanged run stays badge-free
    while still recording the snapshot; history is capped."""

    def _results(self, rec, commits=None, pr_details=None):
        if commits is not None:
            pr_details = {"commits": [{"sha": str(i)}
                                      for i in range(commits)]}
        # the score rides the FINDINGS: the page recomputes rec from
        # them, so the entry-level recommended_points must mirror the
        # same sum or page and index badges diverge
        return [{"file": "cs155_1_link.html", "status": "processed",
                 "recommended_points": rec, "total_points": 6,
                 "team": "SE_TEAM01",
                 "pr_url": "https://github.iu.edu/o/r/pull/3",
                 "_assessment": _assessment(
                     findings=[Finding(_c("Presence"), "pass", rec,
                                       ["evidence: ok"], "note", False)],
                     pr_details=pr_details)}]

    def test_first_run_records_no_history_no_badge(self, tmp_path):
        m, index, root = _run_emit(tmp_path, self._results(3),
                                   ["cs155_1_link.html"])
        e = m["entries"][0]
        assert e["history"] == [] and e["commits"] is None
        page = (root / "TA-reports/lane-test/cs155.html").read_text()
        assert "Score update since" not in page
        assert "b delta" not in index.read_text()

    def test_delta_badge_on_score_change(self, tmp_path):
        _run_emit(tmp_path, self._results(3), ["cs155_1_link.html"])
        m, index, root = _run_emit(tmp_path, self._results(5),
                                   ["cs155_1_link.html"])
        e = m["entries"][0]
        assert len(e["history"]) == 1
        assert e["history"][0]["recommended"] == 3
        assert e["history"][0]["ts"] == "2026-11-13 09:00 EST"
        page = (root / "TA-reports/lane-test/cs155.html").read_text()
        assert "Score update since" in page
        assert "&#9650; 3 &rarr; 5" in page
        assert "since 2026-11-13 09:00 EST" in page
        assert "&#9650; 3 &rarr; 5" in index.read_text()

    def test_score_down_arrow(self, tmp_path):
        _run_emit(tmp_path, self._results(5), ["cs155_1_link.html"])
        _, _, root = _run_emit(tmp_path, self._results(3),
                               ["cs155_1_link.html"])
        page = (root / "TA-reports/lane-test/cs155.html").read_text()
        assert "&#9660; 5 &rarr; 3" in page

    def test_no_badge_when_unchanged(self, tmp_path):
        _run_emit(tmp_path, self._results(3), ["cs155_1_link.html"])
        m, index, root = _run_emit(tmp_path, self._results(3),
                                   ["cs155_1_link.html"])
        e = m["entries"][0]
        assert e["history"] and e["history"][0]["recommended"] == 3
        page = (root / "TA-reports/lane-test/cs155.html").read_text()
        assert "Score update since" not in page
        assert "b delta" not in index.read_text()

    def test_commit_delta_without_score_change(self, tmp_path):
        _run_emit(tmp_path, self._results(5, commits=2),
                  ["cs155_1_link.html"])
        m, index, root = _run_emit(tmp_path, self._results(5, commits=4),
                                   ["cs155_1_link.html"])
        e = m["entries"][0]
        assert e["history"][0]["commits"] == 2 and e["commits"] == 4
        page = (root / "TA-reports/lane-test/cs155.html").read_text()
        assert "commits 2 &rarr; 4" in page
        assert "&#9650;" not in page and "&#9660;" not in page
        assert "commits 2 &rarr; 4" in index.read_text()

    def test_history_capped_at_five(self, tmp_path):
        m = index = root = None
        for rec in [3, 4, 5, 6, 7, 8, 9]:
            m, _, _ = _run_emit(tmp_path, self._results(rec),
                                ["cs155_1_link.html"])
        e = m["entries"][0]
        assert len(e["history"]) == 5
        assert [s["recommended"] for s in e["history"]] == [4, 5, 6, 7, 8]

    def test_commits_of_shapes(self):
        # the real PR model carries the API commit COUNT int
        # (github_client.py); lists are accepted defensively
        assert report_html._commits_of(
            _assessment(pr_details={"commits": 3})) == 3
        assert report_html._commits_of(
            _assessment(pr_details={"commits": [1, 2]})) == 2
        assert report_html._commits_of(_assessment(pr_details={})) is None
        assert report_html._commits_of(_assessment(pr_details=None)) is None
        assert report_html._commits_of(
            _assessment(pr_details={"commits": True})) is None
