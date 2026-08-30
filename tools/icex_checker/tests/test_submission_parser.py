"""Tests for the Canvas submission parser (FR-1, FR-6, EF-1, EF-2)."""
import pathlib
import re

import pytest

from icex_checker import (
    NoPRUrlError,
    NotAnHTMLFileError,
    SubmissionNotFoundError,
    parse_submission,
    validate_pr_url,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _write_html(base_dir, body, title="Week01 - ICEX01: Jane Doe", extra_head=""):
    p = pathlib.Path(base_dir) / "sub.html"
    p.write_text(
        "<html><head><title>%s</title>%s</head><body>%s</body></html>"
        % (title, extra_head, body),
        encoding="utf-8",
    )
    return p


def test_extracts_pr_url_from_meta_refresh():
    """FR-1/SC-1: PR URL is extracted from the meta refresh tag."""
    sub = parse_submission(FIXTURES / "sample_submission.html")

    assert sub.pr_url == "https://github.iu.edu/jdoe/fa26_c291/pull/42"
    assert sub.url_discrepancy is False


def test_falls_back_to_body_link_when_meta_absent(tmp_path):
    """FR-1: PR URL is extracted from the body <a href> when no meta tag."""
    p = _write_html(
        tmp_path, body='<a href="https://github.iu.edu/alice/fa26_c291/pull/7">my PR</a>'
    )
    sub = parse_submission(p)

    assert sub.pr_url == "https://github.iu.edu/alice/fa26_c291/pull/7"
    assert sub.url_discrepancy is False


def test_meta_refresh_wins_and_flags_disagreement(tmp_path):
    """FR-1: meta URL wins over a disagreeing body link and flags it."""
    body = '<a href="https://github.iu.edu/alice/fa26_c291/pull/7">my PR</a>'
    head_extra = (
        '<meta http-equiv="Refresh" content="0; '
        'url=https://github.iu.edu/alice/fa26_c291/pull/99">'
    )
    p = _write_html(tmp_path, body=body, extra_head=head_extra)

    sub = parse_submission(p)

    assert sub.pr_url == "https://github.iu.edu/alice/fa26_c291/pull/99"
    assert sub.url_discrepancy is True


def test_no_pr_url_raises(tmp_path):
    """EF-2: no URL anywhere -> NoPRUrlError."""
    p = _write_html(tmp_path, body="<p>here is my submission</p>")
    with pytest.raises(NoPRUrlError):
        parse_submission(p)


def test_missing_file_raises():
    """EF-1: nonexistent file -> SubmissionNotFoundError."""
    with pytest.raises(SubmissionNotFoundError):
        parse_submission(FIXTURES / "does_not_exist.html")


def test_not_html_raises(tmp_path):
    """EF-1: non-HTML file -> NotAnHTMLFileError."""
    p = tmp_path / "plain.txt"
    p.write_text("just some text, no html at all", encoding="utf-8")
    with pytest.raises(NotAnHTMLFileError):
        parse_submission(p)


def test_parses_title_components():
    """FR-6: title 'Week01 - ICEX01: Jane Doe' parses week/assignment/name."""
    sub = parse_submission(FIXTURES / "sample_submission.html")

    assert sub.week == "01"
    assert sub.assignment_id == "ICEX01"
    assert sub.student_name == "Jane Doe"
    assert sub.title_parsed is True


def test_unparseable_title_is_nonfatal(tmp_path):
    """FR-6: odd title warns (title_parsed False) but still yields a URL."""
    p = _write_html(
        tmp_path,
        body='<a href="https://github.iu.edu/alice/fa26_c291/pull/7">x</a>',
        title="My Homework",
    )
    sub = parse_submission(p)

    assert sub.pr_url == "https://github.iu.edu/alice/fa26_c291/pull/7"
    assert sub.title_parsed is False
    assert sub.assignment_id is None


class TestFilenameParsing:
    """V1-3: IU username extraction + LATE detection from Canvas filename."""

    def _write(self, tmp_path, name):
        p = tmp_path / name
        p.write_text(
            "<html><head><title>Week01 - ICEX01: Jane Doe</title>"
            '<a href="https://github.iu.edu/jdoe/fa26_c291/pull/42">x</a>'
            "</head><body></body></html>",
            encoding="utf-8",
        )
        return p

    def test_late_filename_parses_username_and_flag(self, tmp_path):
        """aldhaherirashed_LATE_6789124_link.html -> username + is_late."""
        sub = parse_submission(
            self._write(tmp_path, "aldhaherirashed_LATE_6789124_link.html")
        )

        assert sub.username == "aldhaherirashed"
        assert sub.is_late is True

    def test_regular_filename_parses_username_no_flag(self, tmp_path):
        sub = parse_submission(self._write(tmp_path, "jdoe_6789124_link.html"))

        assert sub.username == "jdoe"
        assert sub.is_late is False

    def test_unrecognized_filename_degrades_gracefully(self, tmp_path):
        """EF-13: no crash, username None, processing continues."""
        sub = parse_submission(self._write(tmp_path, "random_file.html"))

        assert sub.username is None
        assert sub.is_late is False
        assert sub.pr_url == "https://github.iu.edu/jdoe/fa26_c291/pull/42"

    def test_late_flag_is_case_insensitive(self, tmp_path):
        sub = parse_submission(self._write(tmp_path, "jdoe_late_6789124_link.html"))

        assert sub.is_late is True


class TestValidatePRUrl:
    def test_valid_url(self):
        """FR-2: valid github.iu.edu PR URL passes."""
        ok, reason = validate_pr_url(
            "https://github.iu.edu/jdoe/fa26_c291/pull/42",
            "github.iu.edu",
        )
        assert ok is True
        assert reason is None

    def test_wrong_host(self):
        """EF-3: public GitHub URL fails with the host expected message."""
        ok, reason = validate_pr_url(
            "https://github.com/jdoe/fa26_c291/pull/42",
            "github.iu.edu",
        )
        assert ok is False
        assert "PR URL points to" in reason
        assert "github.iu.edu" in reason

    def test_not_a_pr_url(self):
        """FR-2: repo URL without /pull/N is invalid."""
        ok, reason = validate_pr_url(
            "https://github.iu.edu/jdoe/fa26_c291", "github.iu.edu"
        )
        assert ok is False
        assert "not a PR URL" in reason

    def test_http_scheme_rejected(self):
        """FR-2: http:// is rejected (must be HTTPS)."""
        ok, reason = validate_pr_url(
            "http://github.iu.edu/jdoe/fa26_c291/pull/42", "github.iu.edu"
        )
        assert ok is False
        assert "HTTPS" in reason

    def test_malformed_url(self):
        ok, reason = validate_pr_url("not a url", "github.iu.edu")
        assert ok is False
