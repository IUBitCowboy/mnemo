# Mnemo Architecture Review — Context Document

**Created:** 2026-06-19
**Purpose:** Context for a new session focused on redesigning the Mnemo/Clio architecture.
Read this before starting the architecture discussion.

---

## Background

Kurt started using AI for course material generation in September 2025 after taking
IU's GenAI 101 course. He built a Gemini Gem called "Lecture Coach" — a single system
prompt for generating SE1/P465 course materials (slide decks, ICEXs, assignments).

The system evolved through five phases:

### Phase 0: Gemini Gem (Sep–Oct 2025)
- **Persona:** "Lecture Coach" — recovered at `Clio/clio_persona_gemini_original.md`
- 3 roles (Repo Admin, Process Lead, Dev Crew), no Muse framing, no Mnemo meta-layer
- Course-specific to SE1 (Angband, MoJ, grading philosophy all baked in)
- Used for last 7 weeks of FA25
- `decision_log_v1.1.md` (Oct 21, 2025) formalized the Mnemo/Clio split concept

### Phase 1: Git Repo (Oct 22, 2025)
- `GEMS/Mnemo/` structure with empty `Mnemo_instructions.md`
- `decisions_log.md` generalized pedagogical patterns from FA25
- Original Gemini Gem persona was never committed to git (lived in Gemini platform)

### Phase 2: Port to Python CLI (Feb 24, 2026, commit c5a85a8)
- `Clio/clio_persona.md` (329 lines) — now "Clio, Muse of History"
- `tools/chat.py`, `tools/providers.py`, `tools/session.py` — Python CLI replacing Gemini
- 4 roles (added QA Sentinel), Sync Callouts, structured ICEX template
- "Avoid Sycophancy" added as Pillar #6

### Phase 3: Repo Restructure (Feb 25, 2026, commit 5a58429)
- Deleted legacy files, added Calliope, added CLAUDE.md
- Root `clio_persona.md` deleted (described as "old Gemini Gem meta-prompt")
- `Mnemo_instructions.md` deleted (described as "misnamed; was old Calliope v1 persona")

### Phase 4: Decomposition (Feb 25, 2026, commit fbe6331)
- Split monolithic `clio_persona.md` into:
  - `clio_base.md` — ROLE + COURSE CONTEXT + PEDAGOGICAL PILLARS + PEDAGOGICAL ANALYSIS
  - `clio_icex.md` — ICEX workflow, templates, SBP, TA roles
  - `clio_slides.md` — slide deck template
  - `clio_project.md` — project assignment layer with MoJ specifics
- `clio_persona.md` kept as deprecated monolith

---

## The Architecture Problem

The Mnemo/Clio split was planned but never completed. The decomposition (Phase 4)
split by **artifact type** (icex, slides, project), not by **abstraction level**
(pedagogy vs. course context).

### What's in the wrong place

**Pedagogical pillars in `clio_base.md` that belong in Mnemo (cross-course):**
- Evidence-Driven Design
- Cognitive Load Management
- The Historical Hook
- The Ethical Challenge
- Creative Engagement and Easter Eggs
- Avoid Sycophancy
- Pedagogical Analysis (post-generation self-assessment)

These are general pedagogy, not SE-specific. Calliope needs them too.

**Standardized techniques in `clio_icex.md` that should be Mnemo skills:**
- Parallel Processing Kit (4-role model)
- Sync Callouts
- Definition of Done template
- Standard Blocker Protocol (SBP)
- CONTRIBUTIONS.md entry format
- TA Follow-up Guide structure
- Rubric format policy

These are course-agnostic workflows that any muse with team-based exercises would use.

### What correctly belongs to Clio (course-specific)
- The ROLE identity (Muse of History, SE instructional architect)
- COURSE CONTEXT (P465/565, Angband→MoJ arc, team sizes, grading philosophy)
- `clio_project.md` — MoJ-specific project assignment layer
- Course-specific KB injection (e.g., `clio_kb_SP26.md` in the clio course repo)

### What correctly belongs to Calliope
- `calliope_persona.md` — C291-specific role and context (currently monolith)
- C291 KB files (syllabus, objectives, merit badges)
- C291 lectures and ICEXs

---

## Kurt's Vision (from prior sessions)

1. **Mnemo** should hold cross-course pedagogical principles and standardized techniques
   as *skills* that muses can use — not as prompt text baked into each persona.

2. **Muses** (Clio, Calliope) should be course-specific identities + artifact templates
   that *use* Mnemo's pedagogical skills but don't duplicate them.

3. **Architecture evolution:** Expand from generation-only to a full course lifecycle
   agent (generation → analysis → grading assistance → reflection → improvement).
   New tools discussed: `anonymize.py` (FERPA firewall), `categorize.py`,
   `cross_reference.py`, `calibrate.py`, `reflect.py`, `pipeline.py`.

4. **Open-source readiness:** Mnemo must remain independent of Lore Forge, Obsidian,
   and personal infrastructure. The CLAUDE.md still references Lore Forge vault paths.

5. **Calliope decomposition** is time-sensitive — needed before C291 SP26 generation.

---

## Key Files to Read

### In mnemo repo
- `Clio/clio_persona_gemini_original.md` — original Gemini Gem (Sep 2025, "Lecture Coach")
- `Clio/clio_persona.md` — ported monolith (Feb 2026, deprecated)
- `Clio/clio_base.md` — decomposed base layer (current)
- `Clio/clio_icex.md` — ICEX workflow layer (current)
- `Clio/clio_slides.md` — slides layer (current)
- `Clio/clio_project.md` — project assignment layer (current)
- `Calliope/calliope_persona.md` — C291 monolith (needs decomposition)
- `knowledge_base/decisions_log.md` — cross-course pedagogical patterns
- `tools/chat.py` — CLI chat client
- `tools/providers.py` — multi-provider LLM adapters
- `tools/inbox.py` — quick-capture tool
- `tools/mnemo_activate.sh` — shell helpers (651 lines)
- `CLAUDE.md` — repo guidance for Claude Code

### In clio course repo (`~/devops/teaching/SE1/clio/`)
- `CLAUDE.md` — Clio operational context
- `knowledge_base/decisions_log.md` — SE1-specific decisions (1047 lines)
- `knowledge_base/clio_kb_SP26.md` — SP26 course knowledge base
- `sessions/` — timestamped persona snapshots showing evolution
- `cmods/` — generated course artifacts
- `pipeline/` — build scripts (build_canvas_page.sh, hil.py, etc.)

### In Lore Forge vault
- `Projects/mnemo.md` — project KB summary