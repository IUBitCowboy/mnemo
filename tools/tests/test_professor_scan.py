"""Tests for tools/professor_scan.py — The Professor's deterministic
candidate-proposal scanner.

All fixtures are synthetic (tmp_path) so the suite does not depend on the
live repo state; the real-repo behavior is exercised separately (see
PROFESSOR_DESIGN_NOTES in the repo, or run:
  .venv/bin/python tools/professor_scan.py scan --muse-dir Clio
).
"""

import sys
from pathlib import Path

import pytest

# Make tools/ importable regardless of cwd
TOOLS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import professor_scan as ps  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    """A minimal synthetic mnemo repo: one muse + two skills."""
    muse = tmp_path / "Testmuse"
    muse.mkdir()
    (muse / "testmuse_base.md").write_text(
        "# ROLE\n\nYou are Testmuse.\n", encoding="utf-8")
    skills = tmp_path / "skills"
    (skills / "pedagogy").mkdir(parents=True)
    (skills / "techniques").mkdir(parents=True)
    return tmp_path


def write_muse_layer(repo, text):
    f = repo / "Testmuse" / "testmuse_slides.md"
    f.write_text(text, encoding="utf-8")
    return f


def write_technique(repo, name, text):
    f = repo / "skills" / "techniques" / f"{name}.md"
    f.write_text(text, encoding="utf-8")
    return f


def write_manifest(repo, lines):
    m = repo / "Testmuse" / "candidates.manifest"
    m.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return m


# ── scan ─────────────────────────────────────────────────────────────────────

def test_scan_finds_explicit_count_instance(repo):
    write_muse_layer(repo,
        "# Slides\n\nBefore generating the deck, propose **3 candidate "
        "Historical Hooks** for Slide 2. The instructor may select one.\n")
    inst, opp = ps.scan_scope(repo / "Testmuse", repo / "skills", repo)
    assert len(inst) == 1
    assert inst[0].count == 3
    assert inst[0].deferred is False
    assert inst[0].selection == "single"
    assert inst[0].slug == "historical-hook"


def test_scan_finds_deferred_count_instance(repo):
    write_technique(repo, "ref-format",
        "# References\n\nPropose **N candidate prompts** for the AI assistant. "
        "The count comes from the muse's candidates.manifest.\n")
    inst, _ = ps.scan_scope(repo / "Testmuse", repo / "skills", repo)
    assert len(inst) == 1
    assert inst[0].deferred is True
    assert inst[0].count is None


def test_scan_detects_multiple_selection(repo):
    write_technique(repo, "coach",
        "# Coaching\n\nPropose **4 candidate coaching questions**. "
        "The instructor may select one or more of the 4 candidates.\n")
    inst, _ = ps.scan_scope(repo / "Testmuse", repo / "skills", repo)
    assert inst[0].selection == "multiple"


def test_scan_multiline_noun_phrase(repo):
    # ta-followup-guide.md wraps the noun across a line break
    write_technique(repo, "ta-guide",
        "# TA Guide\n\nWhen generating, propose **4 candidate coaching\n"
        "questions** for the next team meeting. The instructor may:\n")
    inst, _ = ps.scan_scope(repo / "Testmuse", repo / "skills", repo)
    assert len(inst) == 1
    assert inst[0].noun == "coaching questions"
    assert inst[0].slug == "coaching-question"


def test_scan_multiline_noun_plain_phrase(repo):
    # Non-bolded noun wrapped across lines: plain regex on this line only —
    # acceptable to lose the wrap; must not crash or mis-slug.
    write_technique(repo, "ta-guide2",
        "# TA Guide\n\nWhen generating, propose 4 candidate coaching\n"
        "questions for the next team meeting.\n")
    inst, _ = ps.scan_scope(repo / "Testmuse", repo / "skills", repo)
    assert len(inst) == 1
    assert inst[0].noun == "coaching"
    assert inst[0].slug == "coaching"


def test_scan_excludes_opportunities_near_instances(repo):
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n"
        "Later, ask the instructor about the theme.\n")
    inst, opp = ps.scan_file(repo / "Testmuse" / "testmuse_slides.md",
                             "Testmuse/testmuse_slides.md")
    assert len(inst) == 1
    # the "instructor may" inside the instance is suppressed; the distant
    # "ask the instructor" line is still an opportunity
    assert len(opp) == 0
    # So: separate file check — a distant opportunity (4+ lines away) IS found
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n"
        "\n\n\n\n"
        "Later, ask the instructor about the theme.\n")
    inst, opp = ps.scan_file(repo / "Testmuse" / "testmuse_slides.md",
                             "Testmuse/testmuse_slides.md")
    assert len(inst) == 1
    assert len(opp) == 1
    assert "ask the instructor" in opp[0].excerpt


def test_scan_no_skills_flag_scope(repo, capsys):
    write_technique(repo, "ref-format",
        "Propose **2 candidate prompts** here.\n")
    write_muse_layer(repo, "No pattern in the muse layer.\n")
    rc = ps.main(["scan", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo), "--no-skills"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Instances (0)" in out


def test_scan_json(repo, capsys):
    write_muse_layer(repo,
        "propose **3 candidate Hooks** for slide 2. The instructor may select one.\n")
    rc = ps.main(["scan", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo), "--json"])
    assert rc == 0
    import json
    data = json.loads(capsys.readouterr().out)
    assert data["muse"] == "Testmuse"
    assert len(data["instances"]) == 1
    assert data["instances"][0]["count"] == 3


def test_scan_skips_deprecated_persona_files(repo):
    f = repo / "Testmuse" / "testmuse_persona.md"
    f.write_text("propose **3 candidate Hooks**\n", encoding="utf-8")
    inst, _ = ps.scan_scope(repo / "Testmuse", repo / "skills", repo)
    assert inst == []


# ── slugify ──────────────────────────────────────────────────────────────────

def test_slugify_singularizes():
    assert ps.slugify("Historical Hooks") == "historical-hook"
    assert ps.slugify("coaching questions") == "coaching-question"
    assert ps.slugify("AI Assistant Prompts") == "ai-assistant-prompt"


def test_slugify_handles_punctuation():
    assert ps.slugify("Criteria & Weighting Schemes") == "criteria-weighting-scheme"
    assert ps.slugify("Evidence/Reflection Questions") == "evidence-reflection-question"


# ── draft ────────────────────────────────────────────────────────────────────

def test_draft_defaults_deferred_to_four(repo, capsys):
    write_technique(repo, "ref-format",
        "Propose **N candidate prompts** for the AI assistant.\n")
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n")
    rc = ps.main(["draft", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PROPOSED by The Professor" in out
    lines = [l for l in out.split("\n") if l and not l.startswith("#")]
    deferred = [l for l in lines if l.startswith("prompt |")]
    assert deferred and deferred[0].split("|")[1].strip() == "4"
    explicit = [l for l in lines if l.startswith("hook |")]
    assert explicit and explicit[0].split("|")[1].strip() == "3"


def test_draft_writes_file(repo):
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n")
    out_path = repo / "draft.manifest"
    rc = ps.main(["draft", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo), "--out", str(out_path)])
    assert rc == 0
    assert out_path.is_file()
    assert "hook | 3" in out_path.read_text()


# ── validate ─────────────────────────────────────────────────────────────────

def test_validate_good_manifest(repo, capsys):
    write_manifest(repo, [
        "# comment",
        "hook | 3 | single | Testmuse/testmuse_slides.md | choose the hook",
    ])
    rc = ps.main(["validate", str(repo / "Testmuse" / "candidates.manifest")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "VALID" in out
    assert "hook" in out


def test_validate_rejects_bad_count(repo, capsys):
    write_manifest(repo, ["hook | three | single | f.md | choose"])
    rc = ps.main(["validate", str(repo / "Testmuse" / "candidates.manifest")])
    assert rc == 1


def test_validate_rejects_negative_count(repo):
    write_manifest(repo, ["hook | -1 | single | f.md | choose"])
    rc = ps.main(["validate", str(repo / "Testmuse" / "candidates.manifest")])
    assert rc == 1


def test_validate_allows_zero_disable(repo, capsys):
    write_manifest(repo, ["hook | 0 | single | f.md | disabled"])
    rc = ps.main(["validate", str(repo / "Testmuse" / "candidates.manifest")])
    assert rc == 0
    assert "hook | 0" in capsys.readouterr().out


def test_validate_rejects_bad_selection(repo):
    write_manifest(repo, ["hook | 3 | both | f.md | choose"])
    rc = ps.main(["validate", str(repo / "Testmuse" / "candidates.manifest")])
    assert rc == 1


def test_validate_rejects_wrong_arity(repo):
    write_manifest(repo, ["hook | 3 | single | f.md"])
    rc = ps.main(["validate", str(repo / "Testmuse" / "candidates.manifest")])
    assert rc == 1


def test_validate_missing_file(repo, capsys):
    rc = ps.main(["validate", str(repo / "nope.manifest")])
    assert rc == 1
    assert "not found" in capsys.readouterr().out


# ── audit ────────────────────────────────────────────────────────────────────

def test_audit_clean_when_manifest_matches(repo, capsys):
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n")
    write_manifest(repo, [
        "historical-hook | 3 | single | Testmuse/testmuse_slides.md | choose the hook",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CLEAN" in out


def test_audit_clean_steady_state_deferred(repo, capsys):
    # The intended steady state: shared skill defers (N), manifest supplies.
    write_technique(repo, "ref-format",
        "Propose **N candidate prompts**. The count comes from the muse's "
        "candidates.manifest. The instructor may select one.\n")
    write_manifest(repo, [
        "prompt | 3 | single | skills/techniques/ref-format.md | choose the prompt",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 0
    assert "CLEAN" in capsys.readouterr().out


def test_audit_detects_count_drift(repo, capsys):
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n")
    write_manifest(repo, [
        "historical-hook | 5 | single | Testmuse/testmuse_slides.md | choose the hook",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "DRIFT" in out
    assert "count=3" in out and "5" in out


def test_audit_flags_unmanaged_instance(repo, capsys):
    # Two instances in different files; manifest covers only one.
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n")
    write_technique(repo, "ref-format",
        "Propose **3 candidate prompts**. The instructor may select one.\n")
    write_manifest(repo, [
        "historical-hook | 3 | single | Testmuse/testmuse_slides.md | choose the hook",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "MISSING unmanaged instance" in out
    assert "prompt" in out


def test_audit_per_instance_coverage_in_same_file(repo, capsys):
    # Two instances in ONE file; manifest entry for only one must not hide
    # the other (regression: per-file coverage bug).
    write_technique(repo, "combined",
        "# Combined\n\npropose **3 candidate Hooks** here. The instructor may "
        "select one.\n\npropose **4 candidate Prompts** there. The instructor "
        "may select one.\n")
    write_manifest(repo, [
        "historical-hook | 3 | single | skills/techniques/combined.md | choose the hook",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "MISSING unmanaged instance" in out
    assert "prompt" in out


def test_audit_deferred_without_entry_is_error(repo, capsys):
    # A shared skill defers to the manifest, but no entry exists: the muse
    # literally cannot know how many to propose.
    write_technique(repo, "ref-format",
        "Propose **N candidate prompts**. The count comes from the muse's "
        "candidates.manifest.\n")
    # Empty (but present) manifest — parse succeeds, coverage check fires.
    write_manifest(repo, ["# (nothing ratified yet)"])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "ERROR unmanaged instance" in out


def test_audit_disabled_element_is_info_not_problem(repo, capsys):
    # Instructor disposed "off": count=0 is a valid disposition.
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n")
    write_manifest(repo, [
        "historical-hook | 0 | single | Testmuse/testmuse_slides.md | disabled for this muse",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "INFO" in out and "disabled" in out
    assert "CLEAN" in out


def test_audit_duplicate_slug_is_error(repo, capsys):
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n")
    write_manifest(repo, [
        "historical-hook | 3 | single | Testmuse/testmuse_slides.md | a",
        "historical-hook | 5 | single | Testmuse/testmuse_slides.md | b",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 1
    assert "duplicate slug" in capsys.readouterr().out


def test_audit_missing_source_file_is_error(repo, capsys):
    write_manifest(repo, [
        "hook | 3 | single | Testmuse/does-not-exist.md | choose the hook",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 1
    assert "source file not found" in capsys.readouterr().out


def test_audit_no_manifest_reports_and_fails(repo, capsys):
    write_muse_layer(repo,
        "propose **3 candidate Hooks**. The instructor may select one.\n")
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 1
    assert "manifest not found" in capsys.readouterr().out


def test_audit_selection_drift(repo, capsys):
    write_technique(repo, "coach",
        "Propose **4 candidate coaching questions**. The instructor may "
        "select one or more.\n")
    write_manifest(repo, [
        "coaching-question | 4 | single | skills/techniques/coach.md | choose",
    ])
    rc = ps.main(["audit", "--muse-dir", str(repo / "Testmuse"),
                  "--repo-root", str(repo)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "DRIFT" in out and "'multiple'" in out and "'single'" in out


# ── CLI robustness ────────────────────────────────────────────────────────────

def test_scan_missing_muse_dir(repo, capsys):
    rc = ps.main(["scan", "--muse-dir", str(repo / "Nope")])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_audit_missing_muse_dir(repo):
    rc = ps.main(["audit", "--muse-dir", str(repo / "Nope")])
    assert rc == 2