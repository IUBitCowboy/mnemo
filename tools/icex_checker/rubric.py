"""Rubric YAML loading and validation for ICEX Submission Checker."""

import datetime
import pathlib

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

    Attributes:
        assignment: ICEX identifier (e.g. "ICEX01").
        course: course code (e.g. "C291").
        semester: semester code (e.g. "FA26").
        total_points: sum of criterion points expected.
        semester_start: ISO date string when the semester began.
        criteria: list of Criterion objects.
    """

    def __init__(self, assignment, course, semester, total_points, semester_start, criteria):
        self.assignment = assignment
        self.course = course
        self.semester = semester
        self.total_points = total_points
        self.semester_start = semester_start
        self.criteria = criteria


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

    _validate_date(semester_start, "semester_start")

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


def find_rubric(assignment_id, search_dir):
    """Auto-detect a rubric file for an assignment (FR-5 fallback).

    Looks for '<assignment_id>.yaml' (case-insensitive) first in
    search_dir, then in search_dir/rubrics/. Returns the matching path or
    None.
    """
    base = pathlib.Path(search_dir)
    candidates = [
        base / ("%s.yaml" % assignment_id),
        base / ("%s.yml" % assignment_id),
        base / "rubrics" / ("%s.yaml" % assignment_id),
        base / "rubrics" / ("%s.yml" % assignment_id),
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    # Case-insensitive sweep (assignment ids are uppercase, files may vary)
    needle = assignment_id.lower()
    for d in (base, base / "rubrics"):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.yaml")):
            if f.stem.lower() == needle or f.stem.lower().startswith(needle + "_"):
                return f
    return None
