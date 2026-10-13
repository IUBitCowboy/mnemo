# LMS Page Templates

Templates for LMS-destined page content — rendered page bodies the instructor
pastes into the LMS rich-text editor (HTML view) after the deterministic build
pipeline converts them. Use the template for the requested page type; do not
mix types in one file. Course-specific conventions live in each muse's page
layer; this file is generic.

## General Rules (all templates)

1. **Markdown only.** The muse never emits HTML or inline styles — the build
   pipeline does styling. Emitting styled markup is a boundary error.
2. **HIL block first.** Every generated page starts with the HIL comment block
   (same lifecycle as all artifacts: galley → human_reviewed → approved):
   ```markdown
   <!-- hil
   mnemo_session:
   mnemo_model:
   generated_date: YYYY-MM-DD
   hil_status: ai_draft
   reviewed_by:
   review_date:
   -->
   ```
   For extracted-session artifacts, Clio fills provenance via `hil.py galley`.
3. **Title label second.** Immediately after the HIL block:
   ```markdown
   <!-- canvas-title: <the LMS page title> -->
   ```
   This label is what status tooling reads. Write it as the *exact* LMS display
   title, following the course KB's title conventions. If the KB was not loaded
   this session, omit the comment rather than inventing a title.
4. **Page body = the template below.** Section order is fixed; empty
   instructor-fill sections stay present but empty so the shell's shape is
   reviewable.
5. **Never generate multiple recurring instances in one run** (a semester of
   weekly overviews, a stack of announcements). Generate the requested
   instance only.
6. **`<!-- standing -->` / `<!-- instance -->` section markers** separate
   reusable blocks from per-instance blocks wherever a page type repeats.
7. **Student-facing pages carry an AI-use disclosure line** the instructor
   confirms at review, naming the muse and the generating model explicitly
   (model name required, not just tool name).

---

## Type 1: Weekly Module Overview

Fully pre-generated from the course KB and lecture plan. Everything factual —
objectives, readings, deliverables, points, deadlines — comes from the KB.
If a value is not in the KB, write `[due date: see KB]`; do not invent it.

```markdown
<!-- hil block -->
<!-- canvas-title: Week [N] | Weekly Module Overview -->

# Week [N]: [Week Title]

## Introduction

[2–4 sentences orienting the week: where it sits in the course arc, what
changes for students this week, what the sessions establish. No new facts —
rendered from the KB's week plan.]

**Day 1 — [Session Title]**

[Paragraph: what that day's lecture + in-class exercise cover and why, in
student-facing prose drawn from the KB.]

**Day 2 — [Session Title]**

[Same.]

## Weekly Learning Objectives

By the end of this week, you will be able to:

- [Objective — drawn from the KB's week plan only]
- [Objective]
- [Objective]

## Readings and Resources

**Day 1 — [Session Title]**

- [Resource name](url) — [one-line reason it matters for this week]
- [Resource name](url) — [one-line reason]

**Day 2 — [Session Title]**

- [Resource name](url) — [one-line reason]
- [Resource name](url) — [one-line reason]

## To-Do

**Individual**

- `[ARTIFACT_ID]` — [Name] ([points], due [day]) — [one-line what + how to
  submit]. 
- [Each individual deliverable from the KB]

**Team — Best**

- `[ARTIFACT_ID]` — [Name] ([points], due [day]) — [one-line what + how to
  submit].

**Team — Assignment**

- `[ARTIFACT_ID]` — [Name] ([points], due [day]) — [one-line what].

[Optional **[Course-Level-Specific] Graduate Component** section when the
course KB defines graduate-student deliverables for this week.]
```

Conventions: group To-Do exactly as Individual / Team — Best / Team —
Assignment (course-specific groupings come from the muse page layer); keep
artifact IDs backticked and verbatim from the KB; never renumber them.

---

## Type 2: Canonical Reference Page

Fully generated once, standing — not week-bound. Persistence is structural:
the page identity persists; individual sections update in place when the
truth they restate changes; unrelated sections stay untouched.

```markdown
<!-- hil block -->
<!-- canvas-title: [Standing Page Title] -->

# [Standing Page Title]

[A 1–3 sentence orientation: who this applies to, when it applies from.]

---

## [Section 1 — e.g., Purpose / Scope]

[Stable prose. Each section owns exactly one standing truth.]

---

## [Section 2 — e.g., Requirements]

[Structure: prose + one table if the KB defines dimensional comparisons
(situation → consequence pairs), else prose + lists.]

---

## [Section N — e.g., Process / Deadline / Scoring]

[Stable prose. Points, dates, and policy wording come from the KB only.]

— [Instructor sign-off, per course convention]
```

Update rule: when regenerating a Type 2 page, carry the HIL block forward,
update `generated_date`, and let the instructor re-run review. Never delete or
rewrite a section you were not asked to change.

---

## Type 3: Instructor Lecture & Notes (shell)

**Instructor-only; never student-visible.** Clio generates the shell; the
instructor completes the marked sections after class. Clio does NOT invent
what happened in class.

```markdown
<!-- hil block -->
<!--
## AI Assistance Disclosure (instructor-facing)

Shell generated by [muse name] ([model name]) on YYYY-MM-DD; instructor
completes post-class sections. Reviewed by instructor before archival.
-->

# Lecture [N]: [Title]

- **Course:** [course ID — from muse base]
- **Week:** [N]
- **Date delivered:** [YYYY-MM-DD]
- **Delivery status:** `Prepared` (instructor updates to `Delivered`,
  `Delivered-with-deviations`, or `Missed` post-class)

---

## Lecture Outline

[Pre-generated from the lecture plan / slide deck — slide titles plus one
line each on purpose. This section is real content, not a placeholder.]

1. **[Slide/segment title]** — [one-line purpose]
2. **[Slide/segment title]** — [one-line purpose]
3. ...

---

## Pre-Class Plan

[Class-length budget split — filled from muse base + KB plan. For a 75-minute
period with an in-class exercise this session, e.g.: ~10 min lecture intro,
~25–30 min exercise window, ~5 min wrap-up; lecture-only days: 75 min lecture
with instructor prompts.]

| Segment | Minutes | Notes |
|---|---|---|
| [Segment] | [X] | [What to have ready] |
| [Segment] | [X] | [What to have ready] |

---

## Deviations from Plan <!-- instructor fills post-class -->

*What actually happened:*

>

*What to change next time:*

>

<!-- instance: this section is always instructor-completed -->

---

## Post-Class Linkage <!-- instructor fills post-class -->

- **Recording:** [URL, or omit — if the course does not record lectures,
  state "Not recorded."]
- **Slide PDF:** [path or URL to the deck PDF]
- **Related in-class exercise:** [exercise ID from the KB, e.g. `ICEX_MJ##`]

---

## Reflection for Next Iteration <!-- instructor-only freeform -->

>

<!--
## Instructor note — [topic] (revised YYYY-MM-DD)

[When a substantive edit is made to this shell's plan sections, summarize
what changed and why here — galley edit comment convention.]
-->
```

Not a TA guide: when a lecture session has TA involvement, the TA Follow-up
Guide is a separate artifact under the ta-followup-guide technique.

---

## Type 4: Announcement (shell; instructor personalizes)

Two-part structure: standing sections repeat across announcements of the same
kind; instance fields change every time. Clio drafts neutral placeholder
voice; the instructor rewrites voice sections before publish — student-facing
output carries the instructor's voice, not the muse's.

```markdown
<!-- hil block -->
<!-- canvas-title: [Announcement LMS title] -->

<!-- ═══ STANDING SECTIONS — repeat across announcements; instructor edits
     voice/personalization but not the policy content (policy content lives
     in Type 2 pages announcements may link to). ═══ -->

<!-- standing -->
# [Announcement Title]

<!-- standing: greeting — neutral default; instructor personalizes -->
Hey everyone,

<!-- standing: sign-off — neutral default; instructor personalizes -->
— [Instructor name]

<!-- ═══ INSTANCE — replace per announcement ═══ -->

## The Short Version <!-- instance -->

[1–3 sentence summary of the announcement — the part students read first.]

## Details <!-- instance -->

[Structured body: short sections or a table where a situation/consequence
mapping exists. Dates, deadlines, and policy wording from the KB only.]

## Links and References <!-- instance -->

- [Standing policy this announcement operationalizes — link the Type 2 page,
  don't restate it]
- [Any week-specific artifact being announced]

<!-- ═══ PERSONALIZATION CHECKLIST — instructor-only; remove this block
     before publish ═══ -->
<!--
## Personalization Checklist (do before publish)

- [ ] Voice: greeting, sign-off, and any first-person asides read as the
      instructor's voice, not a neutral draft
- [ ] Dates and deadlines in the Details section are correct for THIS
      announcement
- [ ] Links resolve to the intended pages
- [ ] Standing policy content matches the canonical Type 2 page (link, don't
      diverge)
- [ ] HIL block updated; AI-use disclosure confirmed
- [ ] This checklist comment removed before the instructor pastes into the
      LMS
-->
```

Reuse rule: when generating a new announcement of the same kind, the standing
sections stay and the instance fields regenerate — this is the in-prompt
equivalent of the instructor's LMS "duplicate assignment" workflow. One
instance per generation; the muse never batch-generates a semester of
announcements.
