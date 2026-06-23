# Mnemo/Clio Architecture Redesign Plan

**Created:** 2026-06-20
**Status:** Draft for review
**Author:** Kurt Seiffert (with Hermes/Zoidberg)
**Purpose:** Concrete plan for completing the Mnemo/Clio split and decomposing Calliope.

---

## Problem Statement

The Mnemo/Clio split was planned (decision_log_v1.1.md, Oct 2025) but never executed.
The Phase 4 decomposition (Feb 2026) split Clio by **artifact type** (icex, slides,
project), not by **abstraction level** (pedagogy vs. course context). Cross-course
pedagogical pillars and standardized techniques remain embedded in Clio's files.
Calliope is a monolith that would need to duplicate them.

This plan defines the three-layer architecture, the file-level refactoring, and the
Calliope decomposition as concrete deliverables.

---

## Target Architecture

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: Mnemo Skills (cross-course, reusable)       │
│                                                       │
│  skills/pedagogy/*.md   — 7 pillars + analysis        │
│  skills/techniques/*.md — ICEX workflow toolkit       │
│                                                       │
│  Auto-discovered, prepended to every muse's prompt    │
├─────────────────────────────────────────────────────┤
│ Layer 2: Muse Identity (course-specific, lean)       │
│                                                       │
│  Clio/        — SE1/P465 identity + SE-specific      │
│                 artifact conventions                  │
│  Calliope/    — C291 identity + C291-specific         │
│                 artifact conventions                  │
│                                                       │
│  Each muse: _base.md + _icex.md + _slides.md           │
│  (+ _project.md where applicable)                     │
├─────────────────────────────────────────────────────┤
│ Layer 3: Course-Instance KB (per-semester)            │
│                                                       │
│  Lives in course repo (clio/clio_kb_SP26.md, etc.)   │
│  Injected via --context, not in system prompt         │
└─────────────────────────────────────────────────────┘
```

### Design Principles

1. **Skills are self-contained markdown.** Each skill file is a complete,
   self-contained block of instructions. No skill depends on another skill's
   content to make sense (though they may reference each other by name).

2. **Skills are course-agnostic.** No skill file mentions P465, C291, Angband,
   MoJ, or any course-specific detail. Skills use placeholders like
   `[course-specific submission method]` where needed.

3. **Muse base files are lean.** `clio_base.md` becomes ROLE + COURSE CONTEXT
   only. No pedagogical pillars, no analysis template, no session close protocol.
   Those are Mnemo skills loaded automatically.

4. **Muse artifact layers are course-specific conventions.** `clio_icex.md`
   contains only SE1-specific ICEX rules (Canvas naming, file paths, testing
   discipline policy, API design policy). The generic ICEX workflow, 4-role
   model, DoD format, SBP, etc. are Mnemo skills.

5. **Open-source ready.** No skill or muse file references personal infrastructure
  (Lore Forge, Obsidian, 1Password). CLAUDE.md references are cleaned up
  separately (see Phase 3).

6. **Human-in-the-Loop (HIL) provenance is a first-class constraint.** HIL
   tracking — the galley → human_reviewed → approved lifecycle — must be
   embedded in every muse and skill that generates or assembles artifacts.
   This is not an afterthought or a pipeline step bolted on at the end; it
   is a core principle alongside FERPA. Specifically:

   - **Muse generation prompts must include HIL awareness.** When a muse
     generates an artifact (especially across multiple revisions in a
     session), the prompt must instruct the muse to track provenance:
     session ID, turns, model, date. The muse should emit HIL-ready
     markup as part of generation, not as a separate step.

   - **Galley assembly must preserve provenance.** When the instructor or
     an agent assembles a galley copy from a session file, the HIL block
     must be populated with session provenance (session ID, turns used,
     model, date) and the assembly instructions given to the agent.
     In-session prompts that direct galley assembly must be captured as
     part of the provenance record.

   - **Multiple revisions are normal.** An instructor may request several
     versions or changes to an ICEX within a single session. Each version
     is captured in the session file. The HIL markup must record which
     turns contributed to the final galley artifact (e.g., `Q3,Q7,Q12`).

   - **Skills that generate artifacts must reference HIL.** The session-close
     skill, the pedagogical-analysis skill, and any skill that produces
     student-facing content must instruct the muse to emit HIL markup or
     remind the instructor to run `hil.py galley` before extracting.

   - **HIL is enforced at the skill and muse level, not just the pipeline
     level.** The `hil.py` tool in the course repo manages the lifecycle
     transitions, but the *awareness* of HIL obligations lives in the
     prompts. A muse that generates without HIL awareness is a bug.

7. **FERPA firewall is a first-class constraint.** No skill, muse, or tool
   sends student data to a cloud API. The Scalable Assessment Protocol
   (anonymize locally, AI does thematic analysis on anonymized aggregate
   only, human grades the original) is embedded in the architecture. This
   is documented in the existing Key Constraints but must be preserved
   through the refactor — no skill or muse file should weaken the FERPA
   firewall.

---

## Skill Loading Mechanism

### Current Assembly (mnemo_activate.sh)

```bash
# Explicit layer:
cat "$MNEMO_PERSONA" "$MNEMO_ARTIFACT_LAYER" > /tmp/assembled.md

# Provider scope "*" (all layers):
cat "$MNEMO_PERSONA" "${all_layers[@]}" > /tmp/assembled.md
```

### Proposed Assembly

```bash
# New: discover Mnemo skills and prepend
mnemo_skills_dir="$_MNEMO_TOOLS_DIR/../skills"
skill_files=()
for f in "$mnemo_skills_dir"/pedagogy/*.md "$mnemo_skills_dir"/techniques/*.md; do
    [[ -f "$f" ]] && skill_files+=("$f")
done

# Assembled prompt: [skills] + [muse base] + [artifact layers]
cat "${skill_files[@]}" "$MNEMO_PERSONA" "${all_layers[@]}" > /tmp/assembled.md
```

### Two Options for Granularity

**Option A: Auto-load all skills (simplest)**
- All `skills/pedagogy/*.md` and `skills/techniques/*.md` are always prepended.
- No per-muse configuration.
- Risk: larger system prompts (est. +8-10K tokens), some skills irrelevant
  to certain courses (e.g., Parallel Processing Kit for a course without team
  exercises).
- Benefit: zero configuration, muses just work.
- Mitigated by: prompt caching (Anthropic caches the full system prompt).

**Option B: Selective skill loading (manifest)**
- Each muse directory has a `skills.manifest` listing which skills to load.
  ```
  # Clio/skills.manifest
  pedagogy/evidence-driven-design
  pedagogy/cognitive-load-management
  pedagogy/historical-hook
  pedagogy/ethical-challenge
  pedagogy/creative-engagement
  pedagogy/named-principles
  pedagogy/avoid-sycophancy
  pedagogy/pedagogical-analysis
  pedagogy/session-close
  techniques/parallel-processing-kit
  techniques/sync-callouts
  techniques/dod-template
  techniques/sbp
  techniques/contributions-format
  techniques/ta-followup-guide
  techniques/rubric-format
  techniques/code-review-checklist
  techniques/icex-difficulty-scoping
  techniques/references-section
  ```
- More setup per muse, but cleaner prompts.
- Better for open-source where users may have different course structures.
- Assembly reads the manifest and loads only listed skills.

**Recommendation:** Start with **Option A** for v1 (auto-load all). The token
cost is modest relative to the existing system prompt size (~20K already for
Clio base + all layers). Add manifest support in v2 when a third muse is
created or when open-source users need customization. The assembly mechanism
is the only thing that changes; the skill files themselves are identical
under both options.

---

## Phase 1: Extract Mnemo Skills from Clio

### 1.1 Create skills directory structure

```
mnemo/skills/
  pedagogy/
    evidence-driven-design.md
    cognitive-load-management.md
    historical-hook.md
    ethical-challenge.md
    creative-engagement.md
    named-principles.md
    avoid-sycophancy.md
    pedagogical-analysis.md
    session-close.md
  techniques/
    parallel-processing-kit.md
    sync-callouts.md
    dod-template.md
    sbp.md
    contributions-format.md
    ta-followup-guide.md
    rubric-format.md
    code-review-checklist.md
    icex-difficulty-scoping.md
    references-section.md
```

### 1.2 Skill file inventory — what moves where

#### From `clio_base.md` → `skills/pedagogy/`

| Source (clio_base.md lines) | Target skill file | Content | Modifications needed |
|---|---|---|---|
| 27–31 | `evidence-driven-design.md` | Pillar 1: Evidence-Driven Design | Generalize: remove "Assignments" → "artifacts"; keep hooks but make course-agnostic |
| 33–37 | `cognitive-load-management.md` | Pillar 2: Cognitive Load Management | Already generic — move as-is |
| 38–39 | `historical-hook.md` | Pillar 3: The Historical Hook | Already generic — move as-is |
| 41–42 | `ethical-challenge.md` | Pillar 4: The Ethical Challenge | Already generic — move as-is |
| 44–45 | `creative-engagement.md` | Pillar 5: Creative Engagement and Easter Eggs | Already generic — move as-is |
| 47–70 | `named-principles.md` | Pillar 6: Named Engineering Principles | Generalize: the lecture→ICEX threading is SE-specific; keep the principle list (it's industry-standard) but make the threading pattern generic ("lecture → exercise") |
| 72–73 | `avoid-sycophancy.md` | Pillar 7: Avoid Sycophancy | Already generic — move as-is |
| 77–88 | `pedagogical-analysis.md` | Pedagogical Analysis template | Generalize: replace SE-specific analysis items with parameterized versions. "Core Goal" → "[course-specific learning goal]". Keep the format structure. |
| 91–123 | `session-close.md` | Session Close protocol | Already generic — move as-is |

#### From `clio_icex.md` → `skills/techniques/`

| Source (clio_icex.md lines) | Target skill file | Content | Modifications needed |
|---|---|---|---|
| 13–38 | `parallel-processing-kit.md` | 4-role model, attendance pre-flight, role rotation policy | Generalize: remove "ICEX" → "in-class exercise"; remove Canvas-specific submission language. Keep role definitions (they're industry-standard). |
| 40–53 | `sync-callouts.md` | Sync Callout format + typical structure | Already generic — move as-is |
| 54–98 | `icex-difficulty-scoping.md` | Time budget, step-count constraints, complexity signals, right-sized test | Generalize: remove "ICEX" → "in-class exercise". The "30-35 min total" is a default — parameterize as `[target in-class window: default 30-35 min]` |
| 101–116 | `contributions-format.md` | CONTRIBUTIONS.md entry format | Already generic — move as-is |
| 118–128 | `dod-template.md` | Definition of Done checklist | Generalize: the PR submission language is course-specific; keep the format, parameterize the submission line |
| 129–149 | `code-review-checklist.md` | Code Review Checklist for QA Sentinel | Already generic — move as-is. The note about "L4 or L6 should include one slide naming code review as a discipline" is SE-specific — move that to Clio's layer. |
| 152–170 | `references-section.md` | Three-group references format | Already generic — move as-is |
| 173–185 | `sbp.md` | Standard Blocker Protocol | Generalize: remove "ICEX [N]" → "[exercise N]"; remove Canvas reference → "[course LMS]". The branch naming and AAR pattern are generic enough. |
| 188–198 | `ta-followup-guide.md` | TA Follow-up Guide structure | Already generic — move as-is |
| 200–247 | `rubric-format.md` | Rubric format policy (HTML table with inline styles) + point allocation | Generalize: the 10-point ICEX allocation is a default. The HTML format is generic. Move format policy as-is; keep point allocation as a guideline, not a mandate. |
| 250–419 | (stays in Clio) | ICEX output template | This is the assembled template — it stays in Clio because it references Mnemo skills by name (the template embeds SBP, DoD, CONTRIBUTIONS format inline). |

#### From `clio_slides.md` → potential skill

| Source | Target | Content | Notes |
|---|---|---|---|
| 1–10 | (stays in Clio) | Slide deck context + reminders | The "Angband Bridge" requirement is SE-specific. "One Concept Per Slide" is already in cognitive-load-management. "Historical Hook" is already a pedagogy skill. "Key Takeaways + Cliffhanger" is a generic slide pattern. |
| 14–46 | `skills/techniques/slide-deck-template.md` | Slide deck output template | Generalize: remove "CSCI-P465/565" course name. Keep structure. |

#### What stays in Clio (course-specific)

| File | Stays because |
|---|---|
| `clio_base.md` lines 1–22 (ROLE + COURSE CONTEXT) | P465/565, Angband, MoJ, 75-min periods, team sizes, grading philosophy, bridging mandate, abstraction literacy theme |
| `clio_icex.md` Canvas naming convention (lines 5–9) | `_MJ` prefix, `cmods/student/icex/` paths — SE1-specific |
| `clio_icex.md` ICEX output template (lines 250–419) | Assembled template referencing course-specific conventions |
| `clio_project.md` (entire file) | MoJ-specific project assignment layer |
| `clio_slides.md` Angband Bridge requirement (line 10) | SE1-specific |

### 1.3 Lean Clio files after extraction

**`clio_base.md` (target ~50 lines):**
```markdown
# ROLE

You are **Clio**, the Muse of History and the Instructional Architect for
CSCI-P465/565 (Software Engineering) at Indiana University. Your defining
characteristic is that you always situate the present in its history: every
tool, practice, and failure mode has a story, and you use those stories to
make modern engineering legible and memorable.

Your mission is to help the instructor generate course materials — slide
decks, In-Class Exercises (ICEXs), quizzes, and project assignments — that
give students a real, modern software engineering experience. You produce
only clean, well-structured Markdown. You never generate student-facing
content that contains real student names, IDs, or submissions.

---

# COURSE CONTEXT

- **Course:** CSCI-P465 (undergrad) / CSCI-P565 (grad), Software Engineering, IU
- **Audience:** Upper-level undergraduates and Master's students
- **Class Period: 75 minutes.** Hard constraint on all timing.
- **Two-Part Arc:** [Part 1 Grayfield (Angband) / Part 2 Greenfield (MoJ)]
- **Bridging Mandate:** [Connect MoJ to Angband]
- **Course Theme — Abstraction Literacy:** [Full theme text]
- **Team Size:** Default 5, some 4, occasionally 3. ICEXs define 4 parallel roles.
- **Grading Philosophy:** "B for good work, A for good work on time." Late cap 85%.
- **Submission Method:** GitHub Release for projects; Pull Request for ICEXs.
```

**`clio_icex.md` (target ~200 lines):**
- Canvas naming convention (`_MJ` prefix, file paths)
- Testing Discipline Policy (GIVEN/WHEN/THEN, three-level taxonomy, coverage
  framing, mocking at ICEX 13, test health in cycle closes, regression test
  coaching habit)
- API Design Policy (versioning, error response standard, pagination, auth,
  contract document, OpenAPI EC)
- ICEX Output Template (the assembled template — stays because it references
  both Mnemo skills and SE1-specific conventions inline)
- Rubric point allocation (10 pts ICEX, 30 pts project — these are SE1 decisions)

**`clio_slides.md` (target ~15 lines):**
- Angband Bridge requirement
- Course-specific branding ("CSCI-P465/565 Software Engineering")
- Reference to the Mnemo slide deck template skill

**`clio_project.md` (unchanged):**
- Already 100% MoJ-specific. No changes needed.

---

## Phase 2: Calliope Decomposition

### 2.1 Current state

`calliope_persona.md` (82 lines) is a monolith containing:
- ROLE identity (Muse of Epic Poetry, C291 instructional architect)
- KB utilization instructions (C291 syllabus, merit badges, objectives)
- 3 C291-specific pedagogical pillars (Spiral Teaching, Theory-Driven
  Debugging, AI for Learning)
- Student-centered design principles (Starter Code, Worked Examples, Easter
  Eggs — these overlap with Mnemo skills)
- Quest Reward System (C291-specific)
- Material output formats (slide deck structure, ICEX format, project format)
- Pedagogical Self-Analysis (overlaps with Mnemo's Pedagogical Analysis)
- Tone & Narrative guidelines (C291-specific)
- Slide deck template (C291-specific structure with "Cliffhanger")

### 2.2 Decomposition plan

```
Calliope/
  calliope_base.md       — ROLE + COURSE CONTEXT + C291-specific pillars
  calliope_icex.md       — C291 ICEX conventions (Theory/Experiment, Quest
                           Reward System, 15-20 min scoping)
  calliope_slides.md     — C291 slide conventions (Cliffhanger, "Bug in the
                           Path", AI Prompts slide)
  calliope_project.md    — C291 project conventions (Hero's Debugging Log,
                           skeleton code, Makefile)
  calliope_persona.md    — Deprecated monolith (keep for reference, mark
                           deprecated like clio_persona.md)
  KB/                    — C291 course knowledge base (unchanged)
```

### 2.3 File contents

**`calliope_base.md` (~60 lines):**
```markdown
# ROLE

You are **Calliope**, the Muse of Epic Poetry and the Instructional Architect
for C291 (System Programming with C and Linux) at Indiana University. You view
the 15-week semester as an epic journey, starting with the humble "Hello World"
and culminating in the "Hero's Homecoming" — building a functional Linux shell
from scratch.

---

# COURSE CONTEXT

- **Course:** C291, System Programming with C and Linux, Indiana University
- **Audience:** [TBD — undergrad level?]
- **Class Period:** [TBD — 50 min? 75 min?]
- **Arc:** 15 weeks, "Hello World" → Linux Shell (Hero's Homecoming)
- **Submission Method:** [TBD — GitHub? Canvas?]

# KNOWLEDGE BASE UTILIZATION

Consult these files for every response:
- C291_Full_Syllabus.md — 15-week progression and Cliffhangers
- C291_Merit_Badges.md — Top 20 C Perils
- C291_Course_Objectives.md — Technical depth and coverage

---

# C291 PEDAGOGICAL PILLARS

## 1. Spiral Teaching
Revisit complex topics (Git, GCC, Pointers, GDB) multiple times, moving from
functional "how-to" to architectural "why-it-works."

## 2. Theory-Driven Debugging
Enforce the scientific loop: [THEORIZE] → [EXPERIMENT] → [MODIFY] → [TEST] →
[REPEAT]. Incentivize the "Scientific Method" over "Shotgun Debugging."

## 3. AI for Learning First
Act as a mentor, not a ghostwriter. Provide prompts for students to use with
AI to visualize logic (e.g., memory layouts) before writing code.

# TONE & NARRATIVE

- Professional and technical, yet flavored with the language of a journey.
- Use analogies for OS concepts (Virtual Memory as a Vast Library, the Kernel
  as a High King).
- Frame every "Segfault" as a trial to be overcome with logic, never as a
  failure.
```

Note: Student-Centered Design Principles (Starter Code, Worked Examples, Easter
Eggs) are NOT repeated here — they come from Mnemo skills
(`cognitive-load-management.md` and `creative-engagement.md`). The C291
pillars that are genuinely course-specific (Spiral Teaching, Theory-Driven
Debugging, AI for Learning) stay.

**`calliope_icex.md` (~40 lines):**
```markdown
# C291 ICEX CONVENTIONS

Apply in addition to your base persona and Mnemo skills.

## ICEX Format for C291

- **Time Limit:** 15–20 minutes in-class
- **Structure:** [Task] → Theory/Experiment table → [Submission]
- Include a "Theory/Experiment" table in every ICEX for the
  Theory-Driven Debugging pillar.

## Quest Reward System

Two reflective paths for assignments:
- **PATH A (THE ARTISAN):** Documentation of a bug from the "Merit Badge" list.
  Must include original buggy code, the Theory/Experiment proof, and the fix.
- **PATH B (THE BARD):** A narrative story (Explorer/Epic theme) of a debugging
  struggle. Must include a "Technical Appendix" with actual code and isolation
  technique used.
```

**`calliope_slides.md` (~25 lines):**
```markdown
# C291 SLIDE DECK CONVENTIONS

Apply in addition to your base persona and Mnemo skills.

## Slide Deck Structure for C291

- Objectives → Conceptual Theory → Worked Example → "The Bug in the Path"
  (ICEX) → AI Prompts → THE CLIFFHANGER (teaser for next class)

## Key Elements

- Every deck ends with a **Cliffhanger** — an unsolved problem that builds
  anticipation for the next session.
- "The Bug in the Path" is the C291 ICEX embedded in the slide deck (not a
  separate ICEX file).
- Include an **AI Prompts** slide with suggested prompts for students to use
  with AI tools.
```

**`calliope_project.md` (~20 lines):**
```markdown
# C291 PROJECT CONVENTIONS

Apply in addition to your base persona and Mnemo skills.

## Project Format for C291

- Problem Statement
- Skeleton Code (provided)
- Makefile (provided)
- "Hero's Debugging Log" — student-maintained record of debugging journey
```

### 2.4 What Calliope gets from Mnemo skills

| Mnemo skill | How Calliope uses it |
|---|---|
| `evidence-driven-design.md` | Applied to C291 artifacts (metrics: test pass rate, coverage, code quality) |
| `cognitive-load-management.md` | Starter Code + Worked Examples — already in Calliope's current monolith, now comes from Mnemo |
| `historical-hook.md` | Applied to C/Unix topics (history of C, Unix, fork/exec, signals) |
| `ethical-challenge.md` | Applied to systems topics (buffer overflows, privilege escalation, memory safety) |
| `creative-engagement.md` | Easter Eggs + humor — already in Calliope's monolith, now comes from Mnemo |
| `avoid-sycophancy.md` | Universal |
| `pedagogical-analysis.md` | Replaces "Calliope's Reflection" with the standardized analysis format. C291-specific analysis items defined in `calliope_base.md`. |
| `session-close.md` | Universal — same weekly checklist + load order protocol |
| `parallel-processing-kit.md` | C291 uses team exercises — the 4-role model applies (may need adaptation for C291's different team structure) |
| `rubric-format.md` | HTML rubric format — same Canvas pipeline requirement |
| `dod-template.md` | Definition of Done — adapted for C291 submission methods |
| `ta-followup-guide.md` | TA structure — if C291 has TAs (TBD) |

### 2.5 Calliope-specific pedagogical analysis items

The `pedagogical-analysis.md` skill will be parameterized so each muse can
define its course-specific analysis dimensions:

```markdown
# PEDAGOGICAL ANALYSIS (from Mnemo skill)

After generating any student-facing artifact, append a Pedagogical Analysis
section. For each principle below that applies, write one sentence explaining
how it was applied.

## Standard dimensions (from Mnemo):
- **Core Goal:** Does this simulate a real [course domain] task?
- **Cognitive Load Management:** How does scaffolding keep focus on the core
  objective?
- **Historical Context:** Does it reference the origin or history of a tool or
  concept?
- **Creative Engagement:** Does it use narrative, humor, or an Easter Egg?
- **Avoid Sycophancy:** (self-check — did you open with praise?)

## Course-specific dimensions (defined by muse):
<-- Clio would inject: Developer Workflow Competency, Ethical Challenge,
    Named Engineering Principles -->
<-- Calliope would inject: Spiral Teaching (which revisit?), Theory-Driven
    Debugging (which loop?), AI for Learning First (which AI prompt?) -->
```

Each muse's base file includes a `## PEDAGOGICAL ANALYSIS — COURSE DIMENSIONS`
section that lists the course-specific analysis items. The Mnemo skill provides
the format; the muse provides the dimensions.

---

## Phase 3: Open-Source Cleanup

### 3.1 CLAUDE.md references to remove

**mnemo/CLAUDE.md** (lines 4–11):
- Remove Lore Forge vault path reference
- Remove `~/.claude/skills/` reference
- Add note: "CLAUDE.md is an operational realization; the open-source codebase
  has no dependency on any personal infrastructure."

**clio/CLAUDE.md** (lines 5–8):
- Same cleanup — remove Lore Forge vault path
- Remove `~/.claude/skills/` reference

### 3.2 1Password references

The `mnemo_activate.sh` and `mnemo_config.example` reference 1Password `op`
CLI for API key access. This is Kurt's personal credential gating mechanism.
For open-source:
- Keep the `access` command and `MNEMO_OP_*` config as an **optional** feature
- Document that API keys can also be set via standard environment variables
  (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) without 1Password
- The config example should show both methods

### 3.3 README.md updates

- Update repository structure section to reflect `skills/` directory
- Add a "Creating a New Muse" section with the decomposition pattern
- Add Calliope to the structure listing

---

## Phase 4: Tooling Changes

### 4.1 mnemo_activate.sh assembly modification

Add skill discovery and prepending to the `chat()` function:

```bash
# In chat(), before the existing assembly logic:

# Discover Mnemo skills (auto-load all for v1)
local mnemo_skills_dir="$_MNEMO_TOOLS_DIR/../skills"
local skill_files=()
if [[ -d "$mnemo_skills_dir" ]]; then
    for f in "$mnemo_skills_dir"/pedagogy/*.md "$mnemo_skills_dir"/techniques/*.md; do
        [[ -f "$f" ]] && skill_files+=("$f")
    done
fi

# Modify assembly to prepend skills:
if [[ -n "$MNEMO_ARTIFACT_LAYER" ]]; then
    assembled_persona="/tmp/${base_name}+${layer_name}.md"
    cat "${skill_files[@]}" "$MNEMO_PERSONA" "$MNEMO_ARTIFACT_LAYER" > "$assembled_persona"
else
    # ... (same pattern for all-layers and focused modes)
    cat "${skill_files[@]}" "$MNEMO_PERSONA" "${all_layers[@]}" > "$assembled_persona"
fi
```

### 4.2 Config for skill loading scope (future)

```bash
# mnemo_config.example
MNEMO_SKILLS_SCOPE="all"    # all | manifest | none (default: all)
```

When `MNEMO_SKILLS_SCOPE=manifest`, read `skills.manifest` from the muse
directory. When `all`, load everything. When `none`, load no skills (bare muse).

### 4.3 `_mnemo_discover_layers` update

The function currently discovers `${muse}_*.md` excluding `_base` and
`_persona`. After decomposition, Calliope will have `calliope_icex.md`,
`calliope_slides.md`, `calliope_project.md` — these will be auto-discovered
the same way. No change needed if naming convention is followed.

### 4.4 Update CLAUDE.md repository structure

Update the repo structure block in `mnemo/CLAUDE.md` and `README.md` to
include the `skills/` directory.

---

## Implementation Order

### Step 1: Create skill files (extract from Clio)
- [ ] Create `mnemo/skills/pedagogy/` and `mnemo/skills/techniques/` directories
- [ ] Extract 9 pedagogy skill files from `clio_base.md`
- [ ] Extract 10 technique skill files from `clio_icex.md`
- [ ] Create `mnemo/skills/techniques/slide-deck-template.md` from `clio_slides.md`
- [ ] Generalize all skill files (remove course-specific references)

### Step 2: Refactor Clio files (make lean)
- [ ] Rewrite `clio_base.md` to ROLE + COURSE CONTEXT only
- [ ] Rewrite `clio_icex.md` to SE1-specific conventions only
- [ ] Rewrite `clio_slides.md` to SE1-specific conventions only
- [ ] `clio_project.md` — no changes (already course-specific)
- [ ] Add course-specific pedagogical analysis dimensions to `clio_base.md`

### Step 3: Decompose Calliope
- [ ] Write `calliope_base.md` (ROLE + COURSE CONTEXT + C291 pillars + tone)
- [ ] Write `calliope_icex.md` (C291 ICEX conventions)
- [ ] Write `calliope_slides.md` (C291 slide conventions)
- [ ] Write `calliope_project.md` (C291 project conventions)
- [ ] Mark `calliope_persona.md` as deprecated
- [ ] Add C291-specific pedagogical analysis dimensions to `calliope_base.md`

### Step 4: Update tooling
- [ ] Modify `mnemo_activate.sh` to discover and prepend skill files
- [ ] Update `mnemo_config.example` with skill loading config
- [ ] Update `README.md` with new structure and "Creating a New Muse" section

### Step 5: Open-source cleanup
- [ ] Clean Lore Forge/Obsidian references from `mnemo/CLAUDE.md`
- [ ] Document both API key methods (1Password + env vars) in README
- [ ] Verify no skill or muse file references personal infrastructure

### Step 6: Verification
- [ ] Start a Clio session and verify skills are loaded (check assembled prompt
      in /tmp)
- [ ] Generate a test ICEX with Clio to verify output quality is maintained
- [ ] Start a Calliope session and verify skills + C291 layers assemble correctly
- [ ] Verify prompt caching still works (check usage stats for cache_read tokens)
- [ ] Run through the typical workflow: `chat with clio`, `generation icex`,
      `generation focus on`, verify full pipeline
- [ ] Verify HIL awareness: generated artifacts include HIL-ready markup;
      galley assembly from session preserves provenance

### Step 7: Pipeline Tools Review and Enhancement

The current pipeline tools (`pipeline/` in the clio repo) handle deterministic
conversions — pandoc for Markdown → HTML/Canvas, PDF generation. This phase
reviews and enhances them for the refactored architecture.

**Current pipeline tools:**
- `build_canvas_page.sh` — Markdown → Canvas-ready HTML (pandoc + inline styles)
- `build_pdf.sh` — Markdown → PDF
- `build_slides.sh` — Markdown → slide deck
- `build_kit.sh` — Build student starter kits
- `hil.py` — HIL provenance tagger (galley → review → approved lifecycle)
- `normalize_md.py` — Markdown normalization before pandoc
- `strip_vtt.py` — VTT transcript stripping for KB ingestion

**Pipeline enhancements to evaluate:**

1. **Galley → publish pipeline review.** Review the current workflow from
   session file → galley extraction → human review → approved artifact →
   publish (Canvas HTML, PDF, slides). Identify friction points and
   automate where deterministic tools suffice. The principle: "don't send
   an AI to do a computer's job" — use pandoc, scripts, and deterministic
   tools for format conversion, not LLMs.

2. **Canvas integration improvements.** Evaluate better Canvas publishing:
   - Direct Canvas API integration (push HTML pages, announcements,
     assignments without manual copy-paste)
   - Canvas-ready HTML template improvements (accessibility, responsive)
   - Batch publishing of multiple artifacts from a single `cmods/` directory

3. **Keynote-ready PPTX generation.** Evaluate the slide pipeline:
   - Current `build_slides.sh` output quality and Keynote compatibility
   - Consider `marp`, `reveal.js`, or direct `python-pptx` for Keynote-ready
     PPTX with proper master slides, speaker notes, and Clio's slide
     template conventions (Historical Hook, Cliffhanger, AI Prompts slide)
   - The goal: `build_slides.sh cmods/instructor/lectures/lec07.md` produces
     a `.pptx` that opens cleanly in Keynote with minimal manual cleanup

4. **HIL pipeline integration.** Ensure the pipeline tools respect HIL
   status — only `approved` artifacts should be publishable via the
   build scripts. The pipeline should refuse to build `galley` or
   `human_reviewed` artifacts (or at minimum warn loudly).

   **Design question — HIL as MCP?** The HIL lifecycle (galley →
   human_reviewed → approved) is a write-enforcement pattern that
   aligns with the Lore Forge hybrid principle: MCP for writes, CLI
   for reads. Options:
   - (a) A separate Mnemo pipeline MCP that operates on course repo
     `cmods/` directories, enforcing HIL state transitions and
     provenance (session ID, turns, assembly instructions).
   - (b) Keep `hil.py` as a CLI tool — the eval showed Bash-only
     scored well on guard compliance. Muse HIL awareness (from skills)
     handles prompt-side enforcement.
   - (c) Hybrid — CLI for file operations (move files, edit HTML
     comments), MCP for state transition validation and audit log.

   This decision depends on where `hil.py` lives after cross-course
   generalization (item 5 below). If `hil.py` moves to
   `mnemo/pipeline/`, the MCP question follows naturally. If it stays
   course-repo-specific, MCP doesn't make sense (each course repo
   would need its own MCP server).

   The HIL state machine also needs formal design — the current
   `hil.py` has a simple 3-state flow, but HIL principle 6 in the
   REDESIGN_PLAN implies richer provenance (session ID, turns, model,
   date, assembly instructions). That design work happens here.

   **HIL integrity and forgery prevention (raised Jun 22):** The
   current HIL block is an HTML comment in the markdown — anyone with
   file edit access can modify it. For a single-instructor system this
   is adequate, but for The Professor as a distributed tool or courses
   where TAs have write access, this is a vulnerability. Options:
   - (a) Hash-based integrity: SHA-256 of artifact content + session
     metadata, stored in the HIL block. Tampering invalidates the hash.
   - (b) Signed HIL blocks: muse signs with a key; instructor verifies.
   - (c) Git-based provenance: HIL block is a pointer to a git commit.
     The git history IS the provenance; the HIL block links to it.
   - (d) Out-of-band registry: HIL state in a separate `.hil_registry`
     file maintained by pipeline tools, not embedded in the artifact.
   - (e) Embedded HTML comments (current approach) — adequate for
     single-instructor, single-machine systems.

   Also: the current implementation uses embedded HTML comment blocks
   throughout the artifact (not just a header block). The design should
   formalize both the header HIL block (session provenance) and the
   inline galley edit comments (instructor notes on specific sections).

5. **Cross-course pipeline generalization.** The pipeline tools currently
   live in the clio (SE1) course repo. Evaluate which tools are
   course-agnostic (pandoc conversion, HIL, normalize) vs. course-specific
   (Canvas naming, IU branding). Course-agnostic tools should move to
   Mnemo's `SHARED_ASSETS/` or a new `mnemo/pipeline/` directory so any
   muse's course repo can use them.

- [ ] Review current pipeline tools and document which are course-agnostic vs. SE1-specific
- [ ] Evaluate Canvas API direct-push integration
- [ ] Evaluate PPTX/Keynote slide generation options (marp, python-pptx, reveal.js)
- [ ] Add HIL status check to build scripts (refuse to build non-approved artifacts)
- [ ] Move course-agnostic pipeline tools to Mnemo `SHARED_ASSETS/` or `mnemo/pipeline/`
- [ ] Document the galley → publish workflow in README

---

## Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| Skill extraction changes Clio's output quality | High — Clio has been generating good artifacts all semester | Keep original files in git; do a side-by-side generation comparison before deleting old content |
| System prompt too large with skills prepended | Medium — est. +8-10K tokens | Prompt caching absorbs the cost; Anthropic supports 200K context. For Ollama, use `MNEMO_LAYER_SCOPE_OLLAMA=focused` (already default). |
| Skill files too generic to be useful | Medium — risk of diluting specific guidance | Each skill file includes concrete examples and format templates, not just abstract principles |
| Calliope decomposition incomplete for SP26 | High — time-sensitive | Phase 2 is scoped small (~145 lines total across 4 files). Can be done in one session. |
| mnemo_activate.sh modification breaks existing workflow | Medium | Test in a branch; the change is additive (prepend files), not destructive |
| HIL awareness lost during refactor | High — HIL provenance is a core principle; a muse that generates without HIL awareness is a bug | Add HIL awareness to the session-close skill and all artifact-generating skills; verify in Step 6 that generated artifacts include HIL-ready markup |
| Pipeline tools break when moved cross-course | Medium — course-specific assumptions (Canvas naming, IU branding) may be embedded in scripts | Audit each pipeline tool in Step 7; only move course-agnostic tools; keep course-specific wrappers in each course repo |

---

## Publication Implications

For SIGCSE or IEEE Transactions on Education, this architecture is the
contribution:

1. **Three-layer separation** (pedagogy / course identity / instance KB) as a
   reusable pattern for AI-assisted course material generation.

2. **Skill-based composition** — pedagogical principles as modular, composable
   prompt components rather than monolithic prompts.

3. **HIL provenance pipeline** — the galley → review → approve lifecycle as
   evidence of AI-human collaboration boundaries.

4. **Provider-agnostic design** — the same muse works across Anthropic, Gemini,
   and local Ollama with appropriate caching strategies for each.

5. **Evolutionary narrative** — from Gemini Gem monolith → decomposed layers →
   skill-based architecture. The five-phase evolution is itself a case study.

The architecture decision to split by abstraction level (not artifact type) is
the key insight. Phase 4's artifact-type split was necessary but insufficient —
it created reusable *templates* but not reusable *pedagogy*.