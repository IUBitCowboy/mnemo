#!/usr/bin/env python3
"""professor_scan.py — deterministic candidate-proposal pattern scanner for Mnemo.

The Professor (the meta-agent that designs muses) uses this tool to auto-detect
candidate-proposal pattern instances in muse files and Mnemo skills, and to
manage each muse's ratified configuration in `candidates.manifest`.

Design stance: this tool is deliberately deterministic. It reports what the
files say and applies transparent heuristics for instructor-choice-point
language. It never makes the pedagogical judgment itself. The Professor
proposes; the instructor disposes.

Commands
--------
  scan      Find candidate-proposal instances (hardcoded counts, manifest-
            deferred prose) and heuristic choice-point opportunities in a
            muse's files plus the shared Mnemo skills.
  draft     Propose a candidates.manifest from scan output (for the
            instructor to edit and ratify).
  audit     Verify a muse's existing candidates.manifest against its files:
            integrity, pattern anchors, count drift, unmanaged instances.
  validate  Schema-check a candidates.manifest file alone.

Manifest format (pipe-delimited, '#' starts a comment):

  element-slug | candidate-count | single|multiple | source-file | what-the-instructor-chooses

Source paths are repo-root-relative. `candidate-count` is the number of
alternatives the muse proposes for that element. The manifest is the muse's
ratified, instructor-owned configuration; shared Layer-1 skills defer to it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

# ── Pattern recognition ──────────────────────────────────────────────────────

# "propose **3 candidate Historical Hooks**", "propose 4 candidate questions"
RE_EXPLICIT_COUNT = re.compile(
    r"propose\s+\*{0,2}(\d+)\*{0,2}\s+candidate\b",
    re.IGNORECASE,
)
# "propose N candidates ..." — count-free, deferred to the muse's manifest
RE_DEFERRED_COUNT = re.compile(
    r"propose\s+\*{0,2}N\*{0,2}\s+candidates?\b",
    re.IGNORECASE,
)
# The noun phrase being proposed: "candidate **Noun**" (bolded noun)
RE_NOUN_BOLD = re.compile(r"candidate\s+\*\*([^*]+)\*\*")
# "**N candidate Noun**" — the bold block wraps count + noun together
RE_NOUN_BOLDWRAP = re.compile(r"candidate\s+([^*]+?)\*\*")
RE_NOUN_PLAIN = re.compile(r"candidate\s+([A-Za-z][A-Za-z0-9&'/ -]*)")
# A whole file that references the manifest is manifest-aware
RE_MANIFEST_REF = re.compile(r"candidates\.manifest", re.IGNORECASE)
# Selection semantics near an instance
RE_MULTI_SELECT = re.compile(r"select\s+one\s+or\s+more", re.IGNORECASE)
# Instructor choice-point language (heuristic opportunities — NOT instances)
RE_OPPORTUNITY = re.compile(
    r"\b(ask\s+(?:me|the\s+instructor)|the\s+instructor(?:'s)?\s+"
    r"(?:may|should|selects|owns|disposes)|instructor\s+review)\b",
    re.IGNORECASE,
)

DEFAULT_COUNT = 4  # ratified default for deferred (count-free) instances


@dataclass
class Instance:
    """A candidate-proposal pattern instance found in a file."""

    slug: str            # deterministic kebab slug of the proposed noun
    noun: str            # the noun phrase as written
    file: str            # path as given (repo-root-relative when scanning a muse)
    line: int            # 1-based line number of "propose ..."
    count: Optional[int] # explicit count, or None when manifest-deferred
    deferred: bool       # True = count comes from the muse's manifest
    selection: str       # "single" | "multiple"
    excerpt: str         # the matched sentence fragment, whitespace-collapsed

    def key(self) -> str:
        return f"{self.file}::{self.slug}"


@dataclass
class Opportunity:
    """Heuristic instructor-choice-point language — a candidate for the
    pattern, not yet an instance. The Professor reviews these against the
    three ownership questions; the instructor decides."""

    file: str
    line: int
    excerpt: str


@dataclass
class ManifestEntry:
    slug: str
    count: int
    selection: str
    source: str
    chooses: str
    raw_line: int = 0

    @classmethod
    def parse(cls, line: str, line_no: int) -> "tuple[Optional[ManifestEntry], Optional[str]]":
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 5:
            return None, "expected 5 pipe-delimited fields"
        slug, count_s, selection, source, chooses = parts
        if not slug:
            return None, "empty element slug"
        try:
            count = int(count_s)
        except ValueError:
            return None, f"candidate-count '{count_s}' is not an integer"
        if count < 0:
            return None, f"candidate-count {count} must be >= 0 (0 = pattern disabled for this muse)"
        if selection not in ("single", "multiple"):
            return None, f"selection '{selection}' must be single|multiple"
        if not source:
            return None, "empty source file"
        return cls(slug, count, selection, source, chooses, line_no), None


# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(noun: str) -> str:
    """Deterministic slug for a proposed noun phrase.

    'Historical Hooks' -> 'historical-hook'; 'coaching questions' ->
    'coaching-question'. Naive singularization keeps draft/audit derivation
    stable; the ratified manifest slug is descriptive metadata the Professor
    may refine during the design dialogue.
    """
    s = noun.strip().lower()
    s = re.sub(r"[&/]+", " ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > 3 and s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]
    return s or "element"


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def scan_file(path: Path, rel: str):
    """Scan one file for instances and opportunities.

    Returns (instances, opportunities). Lines within ±3 of an explicit
    instance are excluded from opportunity hits (they are already managed).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"professor_scan: cannot read {path}: {e}", file=sys.stderr)
        return [], []

    lines = text.split("\n")
    instances, opportunities = [], []
    instance_lines = set()

    for i, line in enumerate(lines):
        m = RE_EXPLICIT_COUNT.search(line)
        deferred = False
        if not m:
            m = RE_DEFERRED_COUNT.search(line)
            if m:
                deferred = True
            else:
                continue
        count = None if deferred else int(m.group(1))

        # Noun phrase: "candidate **Noun**", "**N candidate Noun**" (whole
        # phrase bolded, possibly line-wrapped), or plain text.
        tail = line[m.start():]
        nm = RE_NOUN_BOLD.search(tail)
        if nm is None:
            nm = RE_NOUN_BOLDWRAP.search(tail)
        if nm is None and i + 1 < len(lines):
            # line wrap inside the bold block: "candidate coaching\nquestions**"
            nm = RE_NOUN_BOLDWRAP.search(collapse(tail + "\n" + lines[i + 1]))
        if nm is None:
            nm = RE_NOUN_PLAIN.search(tail)
        noun = collapse(nm.group(1)) if nm else "element"

        # Selection semantics from this line forward (within 500 chars)
        window = collapse("\n".join(lines[i:i + 12]))[:500]
        selection = "multiple" if RE_MULTI_SELECT.search(window) else "single"

        excerpt = collapse(line)[:160]
        instances.append(Instance(slugify(noun), noun, rel, i + 1, count,
                                  deferred, selection, excerpt))
        for j in range(max(0, i - 3), min(len(lines), i + 4)):
            instance_lines.add(j)

    for i, line in enumerate(lines):
        if i in instance_lines:
            continue
        m = RE_OPPORTUNITY.search(line)
        if m:
            opportunities.append(Opportunity(rel, i + 1, collapse(line)[:160]))

    return instances, opportunities


def discover_muse_files(muse_dir: Path):
    """Muse-owned markdown files: <muse>_<type>.md convention plus base.

    Excludes deprecated monoliths (*_persona*), mirrors mnemo_activate.sh's
    _mnemo_discover_layers plus the base file itself.
    """
    muse_name = muse_dir.name.lower()
    files = []
    for f in sorted(muse_dir.glob("*.md")):
        if f.name.startswith(".") or "_persona" in f.name:
            continue
        files.append(f)
    return files


def scan_scope(muse_dir: Path, skills_dir: Optional[Path], repo_root: Path):
    """Scan a muse's files plus the shared skills. Returns (instances,
    opportunities) with repo-root-relative paths."""
    instances, opportunities = [], []
    for f in discover_muse_files(muse_dir):
        inst, opp = scan_file(f, str(f.relative_to(repo_root)))
        instances += inst
        opportunities += opp
    if skills_dir and skills_dir.is_dir():
        for sub in ("pedagogy", "techniques"):
            d = skills_dir / sub
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                inst, opp = scan_file(f, str(f.relative_to(repo_root)))
                instances += inst
                opportunities += opp
    return instances, opportunities


def parse_manifest(path: Path):
    """Parse a candidates.manifest. Returns (entries, errors).

    On a missing/unreadable file returns ([], [<error>]) — never None.
    """
    entries, errors = [], []
    if not path.is_file():
        return [], [f"manifest not found: {path}"]
    lines = path.read_text(encoding="utf-8").split("\n")
    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entry, err = ManifestEntry.parse(line, i)
        if entry is None:
            errors.append(f"line {i}: {err}")
        else:
            entries.append(entry)
    return entries, errors


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_scan(args) -> int:
    muse_dir = Path(args.muse_dir).resolve()
    if not muse_dir.is_dir():
        print(f"professor_scan: muse directory not found: {muse_dir}", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root).resolve() if args.repo_root else muse_dir.parent
    skills_dir = Path(args.skills_dir).resolve() if args.skills_dir else repo_root / "skills"
    no_skills = args.no_skills

    instances, opportunities = ([], [])
    if not no_skills:
        instances, opportunities = scan_scope(muse_dir, skills_dir, repo_root)

    if args.json:
        print(json.dumps({
            "muse": muse_dir.name,
            "instances": [asdict(i) for i in instances],
            "opportunities": [asdict(o) for o in opportunities],
        }, indent=2))
        return 0

    print(f"# Candidate-proposal scan — {muse_dir.name}")
    print(f"# scope: muse files + shared skills ({skills_dir})")
    print()
    if instances:
        print(f"## Instances ({len(instances)})")
        for inst in instances:
            count = str(inst.count) if inst.count else "deferred→manifest"
            print(f"  {inst.file}:{inst.line}  [{inst.slug}]  count={count}  "
                  f"selection={inst.selection}")
            print(f"      {inst.excerpt}")
    else:
        print("## Instances (0)")
    print()
    if opportunities:
        print(f"## Choice-point opportunities ({len(opportunities)}) — heuristics,")
        print("## The Professor reviews these against the three ownership questions;")
        print("## the instructor decides which become instances.")
        for opp in opportunities:
            print(f"  {opp.file}:{opp.line}  {opp.excerpt}")
    else:
        print("## Choice-point opportunities (0)")
    return 0


def cmd_draft(args) -> int:
    muse_dir = Path(args.muse_dir).resolve()
    if not muse_dir.is_dir():
        print(f"professor_scan: muse directory not found: {muse_dir}", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root).resolve() if args.repo_root else muse_dir.parent
    skills_dir = Path(args.skills_dir).resolve() if args.skills_dir else repo_root / "skills"

    instances, opportunities = scan_scope(muse_dir, skills_dir, repo_root)

    out = []
    out.append(f"# candidates.manifest — PROPOSED by The Professor for {muse_dir.name}")
    out.append("# The instructor edits, then ratifies. This file is the muse's")
    out.append("# instructor-owned candidate-proposal configuration.")
    out.append("# element-slug | candidate-count | single|multiple | source-file | what-the-instructor-chooses")
    seen = set()
    for inst in instances:
        if inst.key() in seen:
            continue
        seen.add(inst.key())
        count = inst.count if inst.count is not None else DEFAULT_COUNT
        out.append(f"{inst.slug} | {count} | {inst.selection} | {inst.file} | [describe what the instructor chooses]")
    if not instances:
        out.append("# (no instances found — The Professor should review choice-point")
        out.append("#  opportunities and propose elements during the design dialogue)")
    draft = "\n".join(out) + "\n"

    if args.out:
        Path(args.out).write_text(draft, encoding="utf-8")
        print(f"Draft written to {args.out} — review with the instructor before ratifying.")
    else:
        print(draft, end="")
    return 0


def cmd_audit(args) -> int:
    muse_dir = Path(args.muse_dir).resolve()
    if not muse_dir.is_dir():
        print(f"professor_scan: muse directory not found: {muse_dir}", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root).resolve() if args.repo_root else muse_dir.parent
    skills_dir = Path(args.skills_dir).resolve() if args.skills_dir else repo_root / "skills"
    manifest_path = muse_dir / "candidates.manifest"

    entries, errors = parse_manifest(manifest_path)
    if not entries and errors:
        for e in errors:
            print(f"ERROR {e}")
        return 1

    problems = []
    infos = []
    problems += [f"ERROR {e}" for e in errors]

    # Scan the muse + shared skills so we can cross-check anchors and drift.
    instances, _ = scan_scope(muse_dir, skills_dir, repo_root)
    inst_by_file = {}
    for inst in instances:
        inst_by_file.setdefault(inst.file, []).append(inst)
    matched_keys = set()

    for entry in entries:
        src_path = repo_root / entry.source
        if not src_path.is_file():
            problems.append(
                f"ERROR {manifest_path.name}:{entry.raw_line}: source file not found: {entry.source}")
            continue
        file_insts = inst_by_file.get(entry.source, [])
        if not file_insts:
            problems.append(
                f"WARN {manifest_path.name}:{entry.raw_line}: no pattern anchor in "
                f"{entry.source} — element '{entry.slug}' has no candidate-proposal "
                f"language in its source file")
            continue
        # Match instance by slug: exact, then containment, then unique-instance
        # fallback. Record the match so per-instance coverage is precise.
        matched = None
        for inst in file_insts:
            if inst.slug == entry.slug:
                matched = inst
                break
        if matched is None:
            for inst in file_insts:
                if inst.slug in entry.slug or entry.slug in inst.slug:
                    matched = inst
                    break
        if matched is None and len(file_insts) == 1:
            matched = file_insts[0]
        if matched is None:
            problems.append(
                f"WARN {manifest_path.name}:{entry.raw_line}: cannot match "
                f"'{entry.slug}' to any instance in {entry.source} — refine the slug "
                f"or the source prose")
            continue
        matched_keys.add(matched.key())
        if entry.count == 0:
            # Instructor disposed "off": element disabled for this muse.
            infos.append(
                f"INFO {manifest_path.name}:{entry.raw_line}: element '{entry.slug}' "
                f"is disabled (count=0) for this muse — the muse will not propose "
                f"candidates for it")
        elif matched.deferred:
            # Count supplied by the manifest — this is the intended steady state.
            pass
        elif matched.count is not None and matched.count != entry.count:
            problems.append(
                f"DRIFT {manifest_path.name}:{entry.raw_line}: file hardcodes "
                f"count={matched.count} but manifest ratifies {entry.count} "
                f"for '{entry.slug}' — generalize the shared skill prose "
                f"(propose N candidates) or re-align the manifest")
        if matched.selection != entry.selection:
            problems.append(
                f"DRIFT {manifest_path.name}:{entry.raw_line}: file semantics are "
                f"'{matched.selection}' but manifest says '{entry.selection}' "
                f"for '{entry.slug}'")

    # Unmanaged instances: pattern language present but no manifest entry covers it.
    for inst in instances:
        if inst.key() in matched_keys:
            continue
        sev = "ERROR" if inst.deferred else "MISSING"
        problems.append(
            f"{sev} unmanaged instance {inst.file}:{inst.line} '{inst.slug}' — "
            f"{'deferred count with no manifest entry (muse cannot know how many '
             'to propose)' if inst.deferred else 'hardcoded count not ratified in manifest'}")

    # Duplicate slugs within the manifest: two ratified elements cannot share
    # an identity — the muse could not resolve which configuration applies.
    seen_slugs = {}
    for e in entries:
        if e.slug in seen_slugs:
            problems.append(
                f"ERROR duplicate slug '{e.slug}' at lines {seen_slugs[e.slug]} and "
                f"{e.raw_line} — each element needs a unique slug")
        else:
            seen_slugs[e.slug] = e.raw_line

    print(f"# Candidate-proposal audit — {muse_dir.name}")
    print(f"  manifest entries : {len(entries)}")
    print(f"  instances found   : {len(instances)}")
    for info in infos:
        print(f"  {info}")
    if problems:
        print(f"  problems          : {len(problems)}")
        print()
        for p in problems:
            print(f"  {p}")
        return 1
    print("  problems          : 0")
    print("  CLEAN — manifest ratified, all instances anchored and consistent.")
    return 0


def cmd_validate(args) -> int:
    path = Path(args.manifest).resolve()
    entries, errors = parse_manifest(path)
    print(f"# Manifest validation — {path.name}")
    if not entries and errors:
        for e in errors:
            print(f"  ERROR {e}")
        return 1
    print(f"  entries: {len(entries)}")
    ok = not errors
    for e in errors:
        print(f"  ERROR {e}")
    for entry in entries:
        print(f"  ok  {entry.slug} | {entry.count} | {entry.selection} | {entry.source}")
    print("  VALID" if ok else "  INVALID")
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="professor_scan.py",
        description="Deterministic candidate-proposal pattern scanner for Mnemo. "
                    "The Professor proposes; the instructor disposes.")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp, with_out=False):
        sp.add_argument("--muse-dir", required=True, help="muse directory, e.g. mnemo/Clio")
        sp.add_argument("--repo-root", help="repo root for relative paths (default: parent of muse dir)")
        sp.add_argument("--skills-dir", help="shared skills dir (default: <repo-root>/skills)")
        return sp

    sp = sub.add_parser("scan", help="find instances and choice-point opportunities")
    add_common(sp)
    sp.add_argument("--no-skills", action="store_true", help="scan muse files only, skip shared skills")
    sp.add_argument("--json", action="store_true", help="machine-readable output")

    sp = sub.add_parser("draft", help="propose a candidates.manifest for the instructor to ratify")
    add_common(sp)
    sp.add_argument("--out", help="write the draft to this path instead of stdout")

    sp = sub.add_parser("audit", help="verify a muse's candidates.manifest against its files")
    add_common(sp)

    sp = sub.add_parser("validate", help="schema-check a candidates.manifest file")
    sp.add_argument("manifest", help="path to a candidates.manifest")

    args = p.parse_args(argv)
    return {
        "scan": cmd_scan,
        "draft": cmd_draft,
        "audit": cmd_audit,
        "validate": cmd_validate,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())