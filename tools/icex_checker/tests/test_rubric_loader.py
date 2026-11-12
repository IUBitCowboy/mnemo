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


class TestCourseInference:
    """Issue #2: repo name -> course code for disambiguating same-named
    assignments across classes (ICEX06 exists in C291 and P465)."""

    def test_c291_repo_pattern(self):
        assert rubric.infer_course_from_repo("fa26_c291") == "C291"

    def test_se1_team_repo_pattern(self):
        assert rubric.infer_course_from_repo("fa26_se1_team01") == "SE1"

    def test_p465_section_maps_to_collective_se1(self):
        """Issue #2 comment: P465 undergrad + P565 grad sections meet
        concurrently and are collectively 'SE1' — repo pattern infers SE1."""
        assert rubric.infer_course_from_repo("fa26_p465") == "SE1"

    def test_p565_grad_section_maps_to_se1(self):
        assert rubric.infer_course_from_repo("fa26_p565") == "SE1"

    def test_unknown_pattern_returns_none(self):
        assert rubric.infer_course_from_repo("some_random_repo") is None

    def test_find_rubric_searches_course_subdirectory(self, tmp_path):
        """rubrics/c291/icex06.yaml and rubrics/se1/p465_icex06.yaml both
        exist — course inference must pick the right one."""
        c291_dir = tmp_path / "rubrics" / "c291"
        se1_dir = tmp_path / "rubrics" / "se1"
        c291_dir.mkdir(parents=True)
        se1_dir.mkdir(parents=True)
        (c291_dir / "icex06_fa26.yaml").write_text("# c291\n", encoding="utf-8")
        (se1_dir / "p465_icex06_fa26.yaml").write_text("# se1\n", encoding="utf-8")

        assert rubric.find_rubric("ICEX06", str(tmp_path), course="C291") == c291_dir / "icex06_fa26.yaml"
        assert rubric.find_rubric("ICEX06", str(tmp_path), course="SE1") == se1_dir / "p465_icex06_fa26.yaml"

    def test_find_rubric_no_course_sweeps_subdirs_on_unique_match(self, tmp_path):
        """Transcript-only submissions have no repo, so no course — a needle
        matching exactly ONE file across course subdirs still auto-detects
        (issue #2: p465_icex06 lives in rubrics/se1/)."""
        se1_dir = tmp_path / "rubrics" / "se1"
        se1_dir.mkdir(parents=True)
        (se1_dir / "p465_icex06_fa26.yaml").write_text("# se1\n", encoding="utf-8")

        assert rubric.find_rubric("ICEX06", str(tmp_path), course=None) == se1_dir / "p465_icex06_fa26.yaml"

    def test_find_rubric_no_course_ambiguous_across_courses_returns_none(self, tmp_path):
        """ICEX06 in both c291/ and se1/ with no course inferred -> ambiguous,
        tool must not guess; TA passes --rubric."""
        c291_dir = tmp_path / "rubrics" / "c291"
        se1_dir = tmp_path / "rubrics" / "se1"
        c291_dir.mkdir(parents=True)
        se1_dir.mkdir(parents=True)
        (c291_dir / "icex06_fa26.yaml").write_text("# c291\n", encoding="utf-8")
        (se1_dir / "p465_icex06_fa26.yaml").write_text("# se1\n", encoding="utf-8")

        assert rubric.find_rubric("ICEX06", str(tmp_path), course=None) is None

    def test_find_rubric_without_course_falls_back_to_flat(self, tmp_path):
        """No course inferred -> old behavior: flat rubrics/ dir wins."""
        flat = tmp_path / "rubrics"
        flat.mkdir()
        (flat / "icex06_fa26.yaml").write_text("# flat\n", encoding="utf-8")

        assert rubric.find_rubric("ICEX06", str(tmp_path), course=None) == flat / "icex06_fa26.yaml"

    def test_course_prefixed_file_matches_in_course_subdir(self, tmp_path):
        """Issue #2: 'p465_icex06_fa26.yaml' in rubrics/se1/ must match
        needle ICEX06 — the section prefix does not break the sweep."""
        se1_dir = tmp_path / "rubrics" / "se1"
        se1_dir.mkdir(parents=True)
        (se1_dir / "p465_icex06_fa26.yaml").write_text("# p465\n", encoding="utf-8")

        found = rubric.find_rubric("ICEX06", str(tmp_path), course="SE1")

        assert found == se1_dir / "p465_icex06_fa26.yaml"


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


class TestRubricFleetSweep:
    """Gate: every shipped rubric in rubrics/*/*.yaml parses under the
    real loader, its criterion points sum to its declared total, and no
    criterion names an unknown checker type. Runs across both course
    fleets (SE1 + C291) so a malformed or mis-typed rubric cannot ship
    to ta-tools unnoticed."""

    def test_fleet_parses_and_sums(self):
        from checkers import CHECKERS

        rubrics_dir = pathlib.Path(__file__).resolve().parent.parent / "rubrics"
        files = sorted(rubrics_dir.glob("*/*.yaml"))
        assert files, "rubric fleet not found"

        problems = []
        for path in files:
            r = rubric.load_rubric(str(path))
            s = sum(c.points for c in r.criteria)
            if s != r.total_points:
                problems.append(
                    "%s: criteria sum %s != total_points %s"
                    % (path.name, s, r.total_points)
                )
            for c in r.criteria:
                if c.checker not in CHECKERS:
                    problems.append(
                        "%s: criterion '%s' names unknown checker '%s'"
                        % (path.name, c.name, c.checker)
                    )
        assert not problems, "\n".join(problems)
