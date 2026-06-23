# Mnemo Architectural Assessment

**Created:** 2026-06-20
**Assessor:** Hermes Agent (Zoidberg)
**Subject:** Mnemo two-tier AI agent system for university course material generation
**Purpose:** Pre-redesign assessment — identifies what's working, what's straining,
and the core architecture question that drives the redesign.

---

## What's Genuinely Good

### 1. Provider abstraction with cache awareness

`providers.py` cleanly separates Anthropic/Gemini/Ollama. The Anthropic provider
uses `cache_control: ephemeral` on both the system prompt AND the last priming
message — double caching. The shell shows a live cache countdown timer. For a
system that injects 50KB+ of persona+layers as the system prompt, prompt caching
is the difference between affordable and not.

### 2. System prompt vs. KB injection separation

`chat.py` injects context files as synthetic user/assistant exchanges, not
appended to the system prompt. This keeps the system prompt stable and cacheable.
The `mnemo_activate.sh` assembly bakes layers into the system prompt via `cat`,
and KB goes through `--context`. Clean separation — the system prompt stays
constant across sessions with different KB files, so the cache persists.

### 3. The decomposed layer architecture (Phase 4)

Splitting `clio_persona.md` into base + icex + slides + project was the right
instinct. The `_mnemo_discover_layers()` function auto-discovers
`${muse}_*.md` files and the `generation` command selects them. This is
extensible — adding a new artifact type means adding a new file, not editing
a monolith. The provider layer scope system (`*` for cloud providers that can
handle larger prompts, `focused` for Ollama with smaller context windows) is a
pragmatic trade-off that shows real production awareness.

### 4. The HIL provenance pipeline

The `hil.py` system (galley → human_reviewed → approved) in the clio repo is a
genuinely novel approach to AI-assisted content generation audit trails. It's
what makes this publication-worthy — you have evidence of where AI generation
ended and human curation began. The galley edit comments (HTML comments that
survive the pandoc pipeline but are invisible in rendered output) are a clean
way to embed design rationale in the artifact itself.

### 5. Decisions log as institutional memory

The `knowledge_base/decisions_log.md` is excellent. It captures *why* decisions
were made, not just *what*. The SAP (Scalable Assessment Protocol) with its
strict FERPA firewall (anonymize locally, send only anonymous blob to AI, human
grades the original) is a model for responsible AI use in education. The
curriculum factory workflow (RAW → Curated → PPR) with its `diff`-based curation
audit is the kind of evidence-driven design that a SIGCSE paper can point to.

---

## Where It Strains

### 1. The Mnemo/Muse split was planned but never executed

The `SHARED_ASSETS/` directory has the right *intent* — cross-course rubrics and
guides — but it's empty stubs with only READMEs listing "examples of files" that
don't exist. The actual cross-course pedagogy lives inside Clio's files. Mnemo
is currently just the tooling; it has no pedagogical content of its own. The
two-tier architecture is documented in CLAUDE.md and README.md but the upper tier
is hollow.

### 2. Phase 4 decomposition split by artifact type, not abstraction level

`clio_base.md` contains BOTH course-specific context (P465, Angband, MoJ, 75-min
periods, team sizes, grading philosophy, submission methods) AND cross-course
pedagogy (the 7 pillars, pedagogical analysis, session close). These should be
separated by abstraction level — pedagogy goes up to Mnemo, course context stays
in Clio. The decomposition created reusable *templates* (icex, slides, project)
but not reusable *pedagogy*. It was necessary but insufficient.

### 3. `clio_icex.md` is 420 lines of mostly cross-course workflow

The 4-role model (Repo Admin, Process Lead, Dev Lead, QA Sentinel), Sync Callouts,
DoD template, SBP, CONTRIBUTIONS.md format, TA Follow-up Guide structure, rubric
format policy, code review checklist, difficulty scoping guidelines, references
section format — all of these are course-agnostic. Only the Canvas naming
convention (`_MJ` prefix), file path conventions, testing discipline policy, and
API design policy are SE-specific. Calliope needs the same workflow structures
but would have to duplicate 350+ lines to get them.

### 4. Calliope is a monolith with overlapping pedagogy

`calliope_persona.md` (82 lines) defines its own pillars (Spiral Teaching,
Theory-Driven Debugging, AI for Learning) that partially overlap with Clio's:
- "Starter Code" + "Worked Examples" = Cognitive Load Management (Clio Pillar 2)
- "Easter Eggs & Humor" = Creative Engagement (Clio Pillar 5)
- "Pedagogical Self-Analysis" = Pedagogical Analysis (Clio's self-assessment)

This is exactly the duplication the Mnemo layer should prevent. When Calliope
is decomposed, it would either copy Clio's pedagogy (violating DRY) or skip it
(pedagogical inconsistency across courses).

### 5. CLAUDE.md references personal infrastructure

Both the mnemo and clio CLAUDE.md files reference Lore Forge vault paths
(`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Apple Notes`) and
`~/.claude/skills/`. This blocks open-source distribution — a new user can't
clone the repo and run it without your Obsidian vault. The constraint is
documented ("Mnemo must remain independent of Lore Forge") but not enforced —
the references are still there.

### 6. No skill loading mechanism exists yet

The architecture review talks about Mnemo "skills" that muses "use," but the
current assembly mechanism is `cat base.md + layer.md`. There's no concept of
injecting cross-cutting pedagogical modules that apply across all muses. The
shell helpers would need a new assembly step. This is a tooling gap, not a
design gap — the `cat` model already supports it, it just needs more files
prepended.

---

## The Core Architecture Question

The system prompt is assembled by `cat`ing files together. Currently:

```
system_prompt = clio_base.md + clio_icex.md (or slides, project, or all)
```

The redesign needs:

```
system_prompt = [Mnemo pedagogy skills] + [Mnemo technique skills]
              + clio_base.md (lean) + clio_icex.md (lean)
```

The mechanism is already there — `cat` just needs more files prepended. The
question is: **what are the skill files, where do they live, and how does the
shell discover them?**

The answer is in `REDESIGN_PLAN.md`.