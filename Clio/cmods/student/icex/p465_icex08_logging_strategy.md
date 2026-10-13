---
assignment: ICEX08
course: P465
semester: FA26
week: 6
title: "Logging Strategy for the MFE"
version: 1.0.0
date: 2026-09-30
author: Mnemo (Hermes Agent)
status: draft-pending-instructor-review
canvas_html: ../canvas/p465_icex08_logging_strategy.html
canvas_text_lane: "OneDrive Canvas Items/icex08.txt"
tags: [icex08, logging, mfe, individual, canvas-text-entry]
changelog: |
  1.0.0 (2026-09-30) — Initial draft. Submission channel decision: pasted
  markdown to Canvas text entry (instructor call), overriding the PR-URL
  default. Timing decision: in-class ~30-min individual drafting window
  same day as the Week 6 Day 1 logging lecture.
---

# ICEX08 — Logging Strategy for the MFE (P465, FA26 Week 6)

## Design rationale (instructor notes — never pasted into the Canvas page)

**Submission channel — documented deviation from the PR-URL default.**
Kurt's call, verbatim: "Have the students submit their plan as a markdown
text file in Canvas. We can provide the template of the markdown structure."
This is a variant of the transcript-to-Canvas deliberate exception
(`references/submission-channels.md`): a design document, not a terminal
artifact — there is no repo-shaped deliverable, and the individual voice is
the assessment target. Consequences, accepted:

- Not mechanically checkable by ICEX Checker v1.1 — every criterion is
  `manual_review`. TAs eyeball-grade against the published table.
- The template's fixed section headings are the compensation used in place
  of transcript-internal mechanical evidence: they make strategies directly
  comparable across teammates and make omission visible at a glance.

**Timing.** Kurt's call: "In-class window (~30 min) — individual members each
draft their own strategy in class right after the lecture; submit same day."
The lecture is Week 6 Day 1 (Logging); MFE Part 2 is due end of Week 6, so
the exercise is deliberately positioned so each strategy is written before
the team's implementation and can feed it. Note: an earlier Mnemo
recommendation (session 2026-09-28) to run no graded logging ICEX this week
is superseded by this decision.

**Lecture anchoring.** Every criterion traces to the Week 6 Day 1 deck
(`FA26-P465/Lectures/WK06-D1 - Logging.key`, 21 slides, text extracted
2026-09-30): Reasons (s1), Strategies (s6), Details (s7), Levels (s8),
Principles in code (s9), Log Management (s11), Python HOWTO (s15–16).
Prometheus/Grafana detail (s19–21) is deliberately NOT assessed — the MFE is
a short-lived terminal tool, not a monitored service; that content is
deferred to the MoJ Phase 2 observability lecture.

**MFE fidelity.** The event inventory prompt walks the actual MFE contract
from A04 Part 1: monster.txt read → selection → current values → edit →
review → Cancel/Save → monster.txt-v2, one-shot session. The rubric's
"What" criterion requires coverage of lifecycle, program flow, errors, and
the save record — the save is the audit event a logging strategy most owes a
record for.

**Withholding.** The template prompts ask for decisions, not commands; no
recipes are given (retrieval-practice convention). Lecture notes + Python
logging HOWTO are named as lookup sources. The integrity line states the
strategy wording must be the student's own.

**House precedents followed.** 10 pts total, published point table
(ICEX06 pattern — weights are the handout's own this time, not rubric
design), partial credit for honest documented gaps, text paste never
screenshots, dated header echoes the freshness-seal convention adapted to a
text artifact, individual work with team discussion allowed but wording
individual. Symmetry-Principle disclosure line included.

---

## Body (mirrors the Canvas HTML page 1:1)

In this in-class exercise you will work individually. You may exchange brief observations with your teammates, but the strategy and its wording must be your own.

The purpose of this exercise is to design a logging strategy for your team's Monster File Editor (MFE), applying the principles and vocabulary from this week's logging lecture (Week 6, Day 1). Write it so your team could adopt it in the MFE Part 2 build, which is due at the end of Week 6.

<section task>

Using the markdown template below, design a logging strategy for the MFE. For each bracketed prompt, delete the prompt text and write your own answer in its place. The template's section headings are fixed; the thinking and the wording are yours. Consult your lecture notes and the Python logging HOWTO (https://docs.python.org/3/howto/logging.html).

If a prompt exposes something your team has not decided yet, record it as an open question in the last section rather than inventing a fake answer. What you submit is a strategy — a document. No terminal transcript is required for this ICEX.

### Template (copy into Canvas and fill in)

```markdown
# MFE Logging Strategy — ICEX08

Course: SE1/P465
Date: [today's date]
Author: [your IU username]

## Why the MFE logs

[Name at least two distinct purposes logging serves for the MFE — drawn from
the lecture's "reasons for logging" — and justify each one in MFE terms, not
in generic terms.]

## What the MFE logs

[List the events the MFE should log, worked through the MFE's actual flow:
starting up, reading monster.txt, the selection menu, showing current
values, accepting edits, the review display, validation, and saving
monster.txt-v2. Your inventory must cover each of these four kinds from the
lecture: (1) program lifecycle events, (2) important program-flow points,
(3) errors and unexpected flows, and (4) the save itself — saving
monster.txt-v2 is the act a logging strategy most owes an audit record for.
Name the events concretely, e.g. "user selected monster X from category Y",
not "selection happens".]

## Log details and levels

[State the timestamp format you will use (the lecture named a standard),
what origin information each record carries, and assign a logging level to
at least three of the events above. Justify each level using the lecture's
level definitions — a warning is for unusual events the program can work
around, an error is recoverable, critical is unrecoverable. Consider: what
is a validation failure that the user must fix? What is a save that failed?]

## Python logging plan

[How your team wires it up: (1) logger naming — one root logger or
per-module loggers, and their names; (2) at least one handler and where
records go — console, file, or both — and why that fits a terminal
application; (3) the formatter fields; (4) how the active level is
controlled at runtime so operational choices do not require code changes.]

## Log management

[Where records live and how growth is handled, whether logs are append-only,
and whether anything logged could be sensitive. The MFE is a course tool —
say in one or two sentences what your actual exposure concerns are.]

## Principles applied

[Pick at least two of the lecture's principles of logging in code and state,
concretely, how each one shapes the MFE's source code — for example, how the
code stays readable around the logging calls, or what "report, not analyze"
forbids.]

## Team recommendations and open questions

[Name at least one logging convention your team should adopt in common for
the MFE (naming, format, destination) and at least one thing you are still
unsure about.]
```

### What to submit to Canvas

Paste your completed markdown into the ICEX08 text entry on Canvas. Text only — it is a markdown document, not a screenshot and not a file upload. Keep the template's section headings so the strategy can be compared across teammates.

### How you earn the 10 points

| Evidence in your strategy | Points |
|---|---|
| Template structure followed; header carries today's date and your IU username | 1 |
| Why: two or more distinct purposes, justified in MFE terms | 1 |
| What: event inventory covers lifecycle, program flow, errors/unexpected flows, and the monster.txt-v2 save record, with concrete event names | 2 |
| Details & levels: timestamp format and origin stated; three or more events assigned levels with justification consistent with the lecture's definitions | 2 |
| Python logging plan: logger naming, handler(s) and destination, formatter fields, runtime level control | 2 |
| Management & principles: destination, retention, exposure, append-only reasoning, plus two code principles applied concretely | 1 |
| Individual voice: one shared team convention recommended and one honest open question | 1 |
| **Total** | **10** |

An incomplete section that names its open question honestly is worth more than a confidently vague sentence — say what you do not know yet. A strategy that copies the lecture slide phrases without applying them to the MFE earns little.

Integrity: this is an individual assignment — your strategy is your design. AI tools may be used only under the course AI Use Policy; if you use one, attach `ai_use.md` in the text entry. An agent or an AI tool may explain logging concepts to you, but the strategy decisions, the event inventory, and the wording must be yours.

### If you get stuck

List what you tried, the exact point where you stopped, and what you expected to happen. That is the evidence list that makes a help request answerable — bring it to the TA or instructor during class.

*This page was generated with AI assistance (Mnemo system) and has been reviewed and approved by the instructor.*