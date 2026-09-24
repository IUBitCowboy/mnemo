"""Rubric YAML loading and validation for ICEX Submission Checker."""

import datetime
import pathlib
import re

import yaml


class RubricNotFoundError(Exception):
    """Rubric file does not exist."""


class RubricParseError(Exception):
    """Rubric file is missing required fields, malformed, or invalid YAML."""


class Criterion:
    """One rubric criterion.

    Attributes:
        name: human-readable criterion name.
        points: maximum points.
        checker: checker type name (e.g. "repo_history").
        params: checker-specific parameters dict (may be None/empty).
    """

    def __init__(self, name, points, checker, params=None):
        self.name = name
        self.points = points
        self.checker = checker
        self.params = params or {}


class Rubric:
    """A loaded rubric definition.

    v1.1 optional fields (V1-1/V1-4): type, canvas_points, ag_max_points,
    handgrading_points, ag_url, roster_file, ownership_check, team_mode —
    all default None/0 and tolerated by the loader for backward compat.
    """

    def __init__(
        self,
        assignment,
        course,
        semester,
        total_points,
        semester_start,
        criteria,
        rtype=None,
        canvas_points=None,
        ag_max_points=None,
        handgrading_points=0,
        ag_url=None,
        roster_file=None,
        ownership_check=None,
        team_mode=None,
        collaboration_coefficient=None,
    ):
        self.assignment = assignment
        self.course = course
        self.semester = semester
        self.total_points = total_points
        self.semester_start = semester_start
        self.criteria = criteria
        self.type = rtype or "icex"
        self.canvas_points = canvas_points
        self.ag_max_points = ag_max_points
        self.handgrading_points = handgrading_points
        self.ag_url = ag_url
        self.roster_file = roster_file
        self.ownership_check = ownership_check
        self.team_mode = team_mode
        self.collaboration_coefficient = collaboration_coefficient


def load_rubric(path):
    """Load and validate a rubric definition from a YAML file (FR-5).

    Raises RubricNotFoundError if the file is missing and RubricParseError
    if the YAML is invalid or fails validation.
    """
    p = pathlib.Path(path)
    if not p.is_file():
        raise RubricNotFoundError(str(p))

    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RubricParseError("rubric file is invalid YAML: %s" % exc) from exc

    if not isinstance(data, dict):
        raise RubricParseError("rubric file is invalid YAML: top level is not a mapping")

    assignment = data.get("assignment")
    course = data.get("course")
    semester = data.get("semester")
    total_points = data.get("total_points")
    semester_start = data.get("semester_start")
    criteria_data = data.get("criteria")

    if not assignment:
        raise RubricParseError("rubric missing required field 'assignment'")
    if not course:
        raise RubricParseError("rubric missing required field 'course'")
    if not semester:
        raise RubricParseError("rubric missing required field 'semester'")
    if total_points is None:
        raise RubricParseError("rubric missing required field 'total_points'")
    if semester_start is None:
        raise RubricParseError(
            "rubric missing required field 'semester_start' "
            "(needed by repo_history; format YYYY-MM-DD)"
        )

    semester_start = _validate_date(semester_start, "semester_start")

    if not isinstance(criteria_data, list) or not criteria_data:
        raise RubricParseError("rubric missing required field 'criteria' (non-empty list)")

    criteria = []
    for i, item in enumerate(criteria_data):
        if not isinstance(item, dict):
            raise RubricParseError("criteria[%d] is not a mapping" % i)
        name = item.get("name")
        points = item.get("points")
        checker = item.get("checker")
        if not name:
            raise RubricParseError("criteria[%d] missing required field 'name'" % i)
        if points is None:
            raise RubricParseError("criteria[%d] ('%s') missing required field 'points'" % (i, name))
        if not checker:
            raise RubricParseError("criteria[%d] ('%s') missing required field 'checker'" % (i, name))
        params = item.get("params") or {}
        if not isinstance(params, dict):
            raise RubricParseError("criteria[%d] ('%s') 'params' must be a mapping" % (i, name))
        criteria.append(Criterion(name=name, points=points, checker=checker, params=params))

    return Rubric(
        assignment=assignment,
        course=course,
        semester=semester,
        total_points=total_points,
        semester_start=semester_start,
        criteria=criteria,
        rtype=data.get("type"),
        canvas_points=data.get("canvas_points"),
        ag_max_points=data.get("ag_max_points"),
        handgrading_points=data.get("handgrading_points") or 0,
        ag_url=data.get("ag_url"),
        roster_file=data.get("roster_file"),
        ownership_check=data.get("ownership_check"),
        team_mode=data.get("team_mode"),
        collaboration_coefficient=data.get("collaboration_coefficient"),
    )


def _validate_date(value, field):
    """Return the ISO date string or raise RubricParseError."""
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            datetime.date.fromisoformat(value)
            return value
        except ValueError as exc:
            raise RubricParseError("rubric field '%s' is not a valid date: %r" % (field, value)) from exc
    raise RubricParseError("rubric field '%s' must be a YYYY-MM-DD string" % field)


def infer_course_from_repo(repo_name):
    """Infer the course code from a submission repo name (issue #2).

    'fa26_c291' -> C291. 'fa26_p465'/'fa26_p565' and 'fa26_se1_team*'
    all map to the collective SE1 (P465 undergrad + P565 grad sections
    meet concurrently; the instructor refers to both as SE1).
    Returns None for unknown patterns.
    """
    m = re.search(r"_c(\d+)(?:_|$)", repo_name or "")
    if m:
        return "C%s" % m.group(1)
    m = re.search(r"_se(\d)(?:_team\d*)?(?:_|$)", repo_name or "")
    if m:
        return "SE%s" % m.group(1)
    m = re.search(r"_p(\d+)(?:_|$)", repo_name or "")
    if m:
        # P465/P565 are sections of the collective SE1
        return "SE1"
    return None


def find_rubric(assignment_id, search_dir, course=None):
    """Auto-detect a rubric file for an assignment (FR-5 fallback).

    Looks for '<assignment_id>.yaml' (case-insensitive) first in
    search_dir, then in search_dir/rubrics/. With a known course
    (issue #2), search_dir/rubrics/<course-lower>/ is searched FIRST so
    same-named assignments in different classes disambiguate correctly.
    Returns the matching path or None.
    """
    base = pathlib.Path(search_dir)
    search_roots = []
    if course:
        search_roots.append(base / "rubrics" / course.lower())
    search_roots.extend([base, base / "rubrics"])
    for root in search_roots:
        candidates = [
            root / ("%s.yaml" % assignment_id),
            root / ("%s.yml" % assignment_id),
        ]
        for cand in candidates:
            if cand.is_file():
                return cand
    # Case-insensitive sweep (assignment ids are uppercase, files may vary).
    # Issue #2: files in course subdirs may carry a course prefix
    # ('p465_icex06_fa26.yaml') — match when the needle appears as the
    # assignment token in the stem. With no course known, sweep the
    # course subdirectories too; a unique match auto-detects, and an
    # ambiguous match (same needle in two courses) returns None — the
    # tool never guesses, the TA passes --rubric.
    needle = assignment_id.lower()
    search_dirs = list(search_roots)
    if not course:
        for sub in sorted((base / "rubrics").glob("*/")) if (base / "rubrics").is_dir() else []:
            if sub not in search_dirs:
                search_dirs.append(sub)
    matches = []
    for d in search_dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.yaml")):
            stem = f.stem.lower()
            if (
                stem == needle
                or stem.startswith(needle + "_")
                or stem.endswith("_" + needle)
                or (needle + "_") in stem
            ):
                matches.append(f)
    if course:
        return matches[0] if matches else None
    if len(matches) == 1:
        return matches[0]
    return None
