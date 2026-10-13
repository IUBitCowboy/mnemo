# The Professor — Candidate-Proposal Capability: Design Notes

**Date:** 2026-10-01
**Task:** Hermes kanban t_1accec35 (child of t_3945f290, promoted from Lore Forge
`20260626_hil_candidate_proposal_pattern_clio_prop.md`)
**Status:** Implemented; Clio manifest ratified against live files (audit CLEAN);
The Professor smoke-tested through the real assembly path and live-model
demoed (gemma4:12b-mlx, behavioral checks PASS).

## What The Professor is

The Professor is Mnemo's meta-agent: the agent that designs muses. This work
gave it the candidate-proposal capability — "the muse proposes, the instructor
disposes" applied at the generation level, not just at the galley-review level.

The Professor is itself a muse-directory persona (`Professor/`) following the
standard three-layer convention:

```
Professor/
  professor_base.md       # ROLE + operating principles + constraints
  professor_newmuse.md    # artifact layer: the muse design dialogue
```

Launched like any muse (add the alias to the project `.envrc` /
`~/.mnemo_config` alongside the existing muse aliases):

```
MNEMO_PERSONA_PROFESSOR="/path/to/mnemo/Professor/professor_base.md"
```

then:

```
chat with professor          # skills + base + newmuse layer (provider scope)
generation newmuse           # focused mode (Ollama) — layer now registered
```

## The four capabilities (card acceptance criteria)

1. **Identify elements needing the pattern** — the three ownership questions
   (ownership / review / adjustment) in `professor_base.md`, plus the
   deterministic scanner's choice-point heuristics.
2. **Configure candidate counts per element** — `candidates.manifest` per
   muse; per-element counts, not standardized; `0` disables an element.
3. **Integrate into the muse design dialogue** — `professor_newmuse.md`
   defines the audit → dialogue → ratify → verify → assemble workflow; the
   dialogue question is "which outputs should the instructor review before
   they reach students?"
4. **Auto-detect candidate-proposal opportunities by analyzing skill outputs** —
   `tools/professor_scan.py` (scan / draft / audit / validate), deterministic
   by design: pedagogical-vs-mechanical distinction starts from instructor
   choice-point language, but final judgment stays with The Professor +
   instructor.

## candidates.manifest format

```
# element-slug | candidate-count | single|multiple | source-file | what-the-instructor-chooses
historical-hook | 3 | single | Clio/clio_slides.md | Which origin story anchors Slide 2 of the deck
```

- Counts are per-element and per-muse. Two muses may ratify different counts
  for the same shared-skill element.
- `candidate-count = 0` disables the pattern for that element in this muse.
- Shared Layer-1 skills defer to the muse's manifest (proposing **N
  candidates**); a muse with no manifest gets default count 4.
- The last field ("what the instructor chooses") is the dialogue's real
  deliverable: it tells the muse what ownership means for that element.

## The scanner: tools/professor_scan.py

Deterministic stdlib-only CLI, 33 pytest tests in
`tools/tests/test_professor_scan.py` (synthetic fixtures; suite independent
of live repo state).

- `scan --muse-dir <Muse>` — instances (explicit or manifest-deferred counts)
  + heuristic choice-point opportunities, from muse files + shared skills.
- `draft --muse-dir <Muse> [--out F]` — proposes a manifest from the live scan.
- `audit --muse-dir <Muse>` — manifest vs. files: source existence, anchor
  match, count drift, selection drift, unmanaged instances, duplicate slugs.
  Exit 0 = CLEAN.
- `validate <manifest>` — schema check.

Current live state (2026-10-01): scanning Clio + shared skills finds 6
instances — historical-hook (3), evidence-reflection-question (4),
coaching-question (4, multiple), ai-assistant-prompt (3), hint-set (3),
criteria-and-weighting-scheme (2) — all anchored in `Clio/candidates.manifest`,
audit CLEAN.

## Open questions from the LF task — settled decisions

| Question | Decision | Rationale |
|---|---|---|
| Standardized count (always 4) or per-element? | **Per-element** | The instructor owns each choice; two muses may want different counts for the same element. 4 is only the no-manifest default. |
| Confidence threshold to skip proposal? | **No** | HIL is ownership, not confidence — the muse cannot know instructor intent. |
| Relation to galley → review → approved lifecycle? | **Pre-galley checkpoint** | Candidates are proposed before generation; HIL governs after. Selections are recorded in the HIL block as provenance. |

## Verification evidence

- `pytest tools/tests/test_professor_scan.py` → 33 passed.
- `professor_scan.py audit --muse-dir Clio` → CLEAN (6/6 instances anchored).
- Assembly smoke test: `chat with professor` through the real
  `mnemo_activate.sh` (stubbed chat.py) → 34 skills + base + newmuse layer
  assembled; `generation newmuse` resolves the layer in focused mode.
- Live-model demo: assembled prompt (95,077 chars) + fictional new-course
  scenario → gemma4:12b-mlx proposed 3 muse-identity candidates, a
  per-element count table with rationale, and explicit instructor disposal;
  3/3 behavioral checks PASS.

## Notes and caveats

- `tools/mnemo_activate.sh` gained a one-word addition (`newmuse` in the
  `generation` case + usage strings) so The Professor's layer is selectable
  in focused mode. That file is under active sibling-workstream edits
  (README + technique skills, card t_1880902b) — it is a collision hotspot.
- The technique-skill generalization (prose moving from hardcoded counts to
  manifest-deferred "propose N candidates") is the sibling workstream's
  lane; the manifest format was coordinated via a comment on t_1880902b.
- The scanner treats instructor choice-point language as *opportunities*
  (heuristic, review required), never auto-promoting them to instances —
  final judgment belongs to The Professor + instructor, not the tool.
- The `Clio/candidates.manifest` additions (hint-set, criteria-and-weighting-
  scheme) carry over counts from the shared skills pending
  instructor confirmation at morning review.
- `discovery` treats `candidates.manifest` as a non-persona .md-adjacent
  file; `_mnemo_discover_layers` ignores it (no `.md` suffix) — no assembly
  impact.
- **No commit was made** in this repo. All changes are working-tree only,
  left for Kurt's morning review per the overnight safety rule (cards land
  blocked/reviewable; nothing publishes without instructor sign-off).

## Files added/modified (all working-tree, uncommitted)

```
Professor/professor_base.md           NEW  meta-agent role + principles
Professor/professor_newmuse.md        NEW  design-dialogue artifact layer
Clio/candidates.manifest              NEW  ratified per-muse configuration
tools/professor_scan.py                NEW  scanner CLI (scan/draft/audit/validate)
tools/tests/test_professor_scan.py     NEW  33 pytest tests
tools/mnemo_activate.sh                MOD  +newmuse in generation case (2 lines)
```