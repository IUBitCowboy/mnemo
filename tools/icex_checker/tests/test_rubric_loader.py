"""Tests for the rubric YAML loader (FR-5, EF-8, auto-detection)."""
import pathlib

import pytest

import rubric


def _rubric_path():
    return pathlib.Path(__file__).parent / "fixtures" / "icex01_rubric.yaml"


class TestLoadRubric:
    def test_loads_valid_rubric(self):
        """FR-5: a valid rubric YAML loads with criteria."""
        r = rubric.load_rubric(_rubric_path())

        assert r.assignment == "ICEX01"
        assert r.course == "C291"
        assert r.semester == "FA26"
        assert r.total_points == 10
        assert len(r.criteria) == 5
        assert r.criteria[0].name == "Forked class Repo"
        assert r.criteria[0].points == 1
        assert r.criteria[0].checker == "repo_history"
        assert r.criteria[2].checker == "pr_url_valid"

    def test_missing_file_raises(self, tmp_path):
        """EF-8: missing rubric file raises RubricNotFoundError."""
        with pytest.raises(rubric.RubricNotFoundError):
            rubric.load_rubric(tmp_path / "nope.yaml")

    def test_invalid_yaml_raises(self, tmp_path):
        """EF-8: invalid YAML raises RubricParseError with the parse error."""
        p = tmp_path / "bad.yaml"
        p.write_text("criteria: [unclosed\n", encoding="utf-8")
        with pytest.raises(rubric.RubricParseError) as exc:
            rubric.load_rubric(p)
        assert "invalid YAML" in str(exc.value)

    def test_missing_criteria_field_raises(self, tmp_path):
        """A rubric without a criteria list is rejected."""
        p = tmp_path / "nocr.yaml"
        p.write_text("assignment: ICEX01\ncourse: C291\n", encoding="utf-8")
        with pytest.raises(rubric.RubricParseError):
            rubric.load_rubric(p)

    def test_criterion_requires_checker_and_points(self, tmp_path):
        """Criterion without checker or points is rejected with a clear error."""
        p = tmp_path / "badc.yaml"
        p.write_text(
            "assignment: ICEX01\n"
            "course: C291\n"
            "semester: FA26\n"
            "total_points: 10\n"
            "semester_start: 2026-08-24\n"
            "criteria:\n"
            "  - name: Broken\n"
            "    points: 2\n",
            encoding="utf-8",
        )
        with pytest.raises(rubric.RubricParseError) as exc:
            rubric.load_rubric(p)
        assert "checker" in str(exc.value)

    def test_semester_start_required_when_repo_history_used(self, tmp_path):
        """repo_history needs semester_start; its absence must be a clear
        error, not a silent convention. (Determinism: no invented defaults.)"""
        p = tmp_path / "nosem.yaml"
        p.write_text(
            "assignment: ICEX01\n"
            "course: C291\n"
            "semester: FA26\n"
            "total_points: 10\n"
            "criteria:\n"
            "  - name: Forked\n"
            "    points: 1\n"
            "    checker: repo_history\n",
            encoding="utf-8",
        )
        with pytest.raises(rubric.RubricParseError) as exc:
            rubric.load_rubric(p)
        assert "semester_start" in str(exc.value)


class TestAutoDetect:
    def _icex(self, name="ICEX01"):
        d = pathlib.Path(__file__).parent / "fixtures"
        return d, name

    def test_detects_rubric_in_tool_dir(self):
        """FR-5: finds <assignment>.yaml next to the tool code."""
        d, _ = self._icex()
        found = rubric.find_rubric("ICEX01", str(d))
        assert found is not None

    def test_detects_rubric_in_rubrics_dir(self, tmp_path):
        """FR-5: finds rubrics/<assignment>.yaml relative to a search dir."""
        (tmp_path / "rubrics").mkdir()
        (tmp_path / "rubrics" / "icex01.yaml").write_text("assignment: ICEX01\n", encoding="utf-8")
        found = rubric.find_rubric("ICEX01", str(tmp_path))
        assert found is not None
        assert "rubrics" in str(found)

    def test_no_match_returns_none(self, tmp_path):
        assert rubric.find_rubric("ICEX99", str(tmp_path)) is None


class TestV11FieldsTolerated:
    """v1.1 rubric fields must load on the current loader without changes."""

    def test_team_rubric_with_v11_fields_loads(self, tmp_path):
        p = tmp_path / "team.yaml"
        p.write_text(
            "assignment: ICEX01\n"
            "course: C291\n"
            "semester: FA26\n"
            "total_points: 10\n"
            "semester_start: 2026-08-24\n"
            "type: team\n"
            "canvas_points: 10\n"
            "roster_file: roster.csv\n"
            "ownership_check: team\n"
            "team_mode: team_best\n"
            "criteria:\n"
            "  - name: Attribution\n"
            "    points: 0\n"
            "    checker: team_best_attribution\n",
            encoding="utf-8",
        )
        r = rubric.load_rubric(p)
        assert r.assignment == "ICEX01"
        assert len(r.criteria) == 1

    def test_ag_rubric_with_v11_fields_loads(self, tmp_path):
        p = tmp_path / "ag.yaml"
        p.write_text(
            "assignment: PASN01\n"
            "course: C291\n"
            "semester: FA26\n"
            "total_points: 100\n"
            "semester_start: 2026-08-24\n"
            "ag_url: https://autograder.luddy.indiana.edu/web/project/2206\n"
            "ag_max_points: 100\n"
            "handgrading_points: 0\n"
            "criteria:\n"
            "  - name: AG\n"
            "    points: 100\n"
            "    checker: manual_review\n",
            encoding="utf-8",
        )
        r = rubric.load_rubric(p)
        assert r.assignment == "PASN01"
