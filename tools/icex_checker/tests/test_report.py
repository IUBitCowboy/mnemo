"""Tests for the report formatter (FR-8, FR-9, SC-5, SC-12)."""
import json

import pytest

from checkers import Finding
from report import (
    Assessment,
    build_json_report,
    build_text_report,
    summarize_findings,
)
from rubric import Criterion


def _criterion(name="Forked class Repo", points=1, checker="repo_history"):
    return Criterion(name=name, points=points, checker=checker, params={})


def _finding(assessment, points, name="Forked class Repo", checker="repo_history",
             evidence=None, notes="", ta_confirm=False):
    return Finding(
        criterion=_criterion(name=name, points=1, checker=checker),
        assessment=assessment,
        points_recommended=points,
        evidence=evidence or ["evidence line"],
        notes=notes,
        ta_confirm=ta_confirm,
    )


def _assessment():
    return Assessment(
        assignment="ICEX01",
        course="C291",
        semester="FA26",
        student_name="Jane Doe",
        pr_url="https://github.iu.edu/jdoe/fa26_c291/pull/42",
        timestamp="2026-08-30T12:00:00",
        tool_version="1.0.0",
        pr_details={
            "title": "Add hello.c",
            "description": "My pull request for ICEX01.",
            "head_ref": "jdoe-patch-1",
            "base_ref": "main",
            "commits": 3,
            "state": "open",
        },
        findings=[
            _finding("pass", 1, "Forked class Repo"),
            _finding("partial", 1, "Create Pull Request", "pr_exists_with_comment",
                     evidence=["body length: 4 chars"], notes="PR exists but comment is short."),
            _finding("needs-review", 0, "Manual Criterion", "no_such_checker",
                     notes="TA must check this by hand."),
            _finding("pass", 2, "PR URL submitted to Canvas", "pr_url_valid",
                     ta_confirm=True, notes="TA confirms ownership."),
        ],
        save_json_path=None,
    )


class TestSummarize:
    def test_counts_by_assessment(self):
        s = summarize_findings(_assessment().findings)

        assert s["pass"] == 2
        assert s["partial"] == 1
        assert s["fail"] == 0
        assert s["needs-review"] == 1

    def test_total_and_recommended_points(self):
        s = summarize_findings(_assessment().findings)

        assert s["total_points"] == 4
        assert s["recommended_points"] == 4


class TestTextReport:
    def test_contains_header_sections(self):
        text = build_text_report(_assessment())

        assert "ICEX01" in text
        assert "Jane Doe" in text
        assert "https://github.iu.edu/jdoe/fa26_c291/pull/42" in text
        assert "2026-08-30T12:00:00" in text

    def test_contains_summary_counts(self):
        text = build_text_report(_assessment())

        assert "passed: 2" in text
        assert "partial: 1" in text
        assert "needs-review: 1" in text

    def test_contains_per_criterion_detail(self):
        text = build_text_report(_assessment())

        assert "Forked class Repo" in text
        assert "Create Pull Request" in text
        assert "body length: 4 chars" in text

    def test_contains_pr_details(self):
        text = build_text_report(_assessment())

        assert "Add hello.c" in text
        assert "jdoe-patch-1" in text
        assert "Commits:" in text
        assert "3" in text
        assert "open" in text

    def test_contains_ta_action_items(self):
        """FR-8: needs-review and ta_confirm findings become explicit action items."""
        text = build_text_report(_assessment())

        assert "TA ACTION ITEMS" in text
        assert "Manual Criterion" in text
        assert "TA confirms ownership" in text

    def test_contains_pr_url_in_action_items(self):
        """SC-5: PR URL repeated for convenience in action items."""
        text = build_text_report(_assessment())

        assert text.count("https://github.iu.edu/jdoe/fa26_c291/pull/42") >= 2

    def test_never_contains_token(self):
        """SC-12: token value never appears in the report."""
        text = build_text_report(_assessment())

        assert "super-secret-token" not in text
        assert "ghp_" not in text


class TestJsonReport:
    def test_serializable_structure(self):
        data = build_json_report(_assessment())

        assert data["assignment"] == "ICEX01"
        assert data["student_name"] == "Jane Doe"
        assert data["pr_url"] == "https://github.iu.edu/jdoe/fa26_c291/pull/42"
        assert data["tool_version"] == "1.0.0"
        assert len(data["criteria"]) == 4
        assert data["criteria"][0]["assessment"] == "pass"
        assert data["criteria"][0]["points_recommended"] == 1

    def test_json_dump_roundtrip(self, tmp_path):
        data = build_json_report(_assessment())
        p = tmp_path / "out.json"
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

        loaded = json.loads(p.read_text(encoding="utf-8"))
        assert loaded["student_name"] == "Jane Doe"
        assert loaded["criteria"][1]["assessment"] == "partial"

    def test_never_contains_token(self):
        """SC-12: token value never appears in JSON output."""
        data = json.dumps(build_json_report(_assessment()))

        assert "super-secret-token" not in data
        assert "ghp_" not in data
