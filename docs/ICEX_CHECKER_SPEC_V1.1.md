---
title: "ICEX Submission Checker — Specification v1.1 Delta"
version: 1.1.0
date: 2026-08-30
author: Mnemo (design), Kurt Seiffert (requirements)
status: draft
base_spec: ICEX_CHECKER_SPEC.md v1.0.0
related_project: "mnemo/tools/icex_checker"
tags: [spec, c291, se1, icex, pasn, team, grading, ta-tool, v1.1]
changelog:
  - version: 1.1.0
    date: 2026-08-30
    status: draft
    notes: |
      Delta against v1.0.0. Adds: team assignment support, AG assignment mode,
      roster-based attribution, pattern_count checker, manual_review checker,
      LATE detection, canvas_points scaling, ownership_check toggle.
      Codifies: ta_confirm finding flag, added-lines-only diff semantics.
      Defers to v1.2: team-level cross-correlation.
---

# ICEX Submission Checker — Specification v1.1 Delta

**This document is a delta against v1.0.0.** It describes only what changes,
what's added, and what's codified. The v1.0.0 spec remains locked; this
document extends it. All v1.0.0 requirements, edge cases, and success criteria
remain in force unless explicitly superseded here.

## What Changed Since v1.0.0

### Built during v1.0 implementation (now codified)

The following were implemented during the v1.0 build as judgment calls
resolving spec ambiguities. This spec formalizes them so future checkers
and rubrics inherit the conventions.

### D-1: `ta_confirm` Finding Flag

**Problem:** v1.0.0 spec defines `pass` and `needs-review` as separate
assessments, but several checkers (e.g., `pr_exists_with_comment`,
`diff_content_check`) have conditions where the mechanical check passes
*and* a TA judgment is required (e.g., "is the comment well-written?",
"is the replacement the student's actual name?"). The spec placed these
in both `pass` and `needs-review` categories simultaneously.

**Resolution:** The `Finding` object gains a `ta_confirm` boolean flag
(default `False`). When `True`, the finding keeps its mechanical assessment
(`pass`) and its points recommendation — the points signal is NOT lost —
but the confirmation item appears as an explicit checkbox in the report's
TA Action Items section.

**Semantics:**
- `ta_confirm=True` with `assessment="pass"`: mechanical check passed,
  TA must confirm a judgment item. Points recommended = full.
- `ta_confirm=False` with `assessment="needs-review"`: tool could not
  check mechanically. Points recommended = None.
- `ta_confirm=True` with `assessment="fail"`: mechanically failed with
  strong deterministic evidence, TA confirms before finalizing. Used when
  the tool has high confidence the criterion is not met (e.g., wrong-
  submission detection: roster says student X, all commits are student Y's).
  Points recommended = 0.
- `ta_confirm` is never set with `assessment="partial"`.

**Report rendering:** TA Action Items has two types:
- `[ ] Review manually:` — for `needs-review` findings (tool couldn't check)
- `[ ] Confirm:` — for `ta_confirm=True` findings (tool checked, TA judges)

### D-2: Added-Lines-Only Diff Checking

**Problem:** v1.0.0 spec says `must_not_contain` checks "no longer present
in the changed lines." A literal reading checks all diff lines including
removed (`-`) lines. But the removed line `-printf("Hello World!\n");`
contains "World" — so a correct submission that replaced "World" with the
student's name would false-fail because "World" appears in the removed line.

**Resolution:** Both `must_contain_modified` and `must_not_contain` in
`diff_content_check` check **added lines only** (lines starting with `+`
in the diff, excluding the `+++` file header). Removed lines (`-`) are the
old content and must NOT be checked. This is the correct semantic: the
tool verifies what the student *added*, not what they removed.

### D-3: `manual_review` Checker Type

**Added:** A checker that returns `needs-review` with a custom label from
`params.label`. Used for criteria the tool cannot check mechanically (AG
scores, handgrading, style judgments). The label appears in the report's
TA Action Items and in the criterion's notes.

**Params:**
- `label` (required): Human-readable instruction for what the TA should enter

### D-4: `pattern_count` Checker Type

**Added:** A checker that counts regex pattern occurrences in the added
lines of a target file and compares against an expected count.

**Params:**
- `target_file` (required): Full repo path as it appears in the diff
- `pattern` (required): Regex pattern to search for
- `expected_count` (required): The count to compare against
- `comparison` (optional): `"exact"` (default), `"at_least"`, or `"at_most"`

**Assessment:**
- `pass`: Count meets the comparison condition
- `fail`: Count does not match, or target file not in diff
- `needs-review`: API error prevents fetching the diff

**Counting:** Uses `re.findall` per added line, summing total occurrences
across all added lines (not lines-with-matches). A line with two matches
counts as 2.

**Evidence:** Reports the pattern, the count found, and the comparison
condition.

## New Features in v1.1

### V1-1: Team Assignment Support

**Motivation:** SE1/P465 has team assignments (Team Best and Team
Collaboration) where multiple students contribute to a shared repository.
The tool must verify per-student attribution within a team PR and support
team-aware rubric configuration.

#### Rubric Fields

The rubric YAML gains optional top-level fields:

| Field | Default | Description |
|-------|---------|-------------|
| `type` | `icex` | Assignment type: `icex`, `pasn`, or `team` |
| `canvas_points` | = `total_points` | Points the assignment is worth in Canvas (for scaling) |
| `ag_max_points` | (none) | Maximum AG score (for `pasn` and `icex` with AG) |
| `handgrading_points` | 0 | Maximum handgrading score |
| `ag_url` | (none) | URL to the AG project for this assignment |
| `roster_file` | (none) | Path to team roster file (CSV: `team,iu_username`) |
| `ownership_check` | `student` | Who owns the repo: `student`, `team`, or `none` |

#### `ownership_check` Toggle

Controls the `pr_url_valid` checker's name-matching behavior:

- **`student`** (default, C291): Repo owner should match the submitting
  student. Uses roster lookup (if available) or name heuristic (fallback).
  Mismatch → `needs-review` with `ta_confirm`.
- **`team`** (SE1 team assignments): Repo owner is the team. The tool
  parses the trailing team identifier from the repo name (e.g., `team01`
  from `fa26_se1_team01`) and matches it case-insensitively against the
  roster's `team` column. The tool verifies the submitting student is a
  member of that team via roster lookup. No name-matching against the
  repo owner.
- **`none`**: Skip ownership verification entirely. Just verify the PR
  resolves.

#### Canvas Filename Username Extraction

Canvas names submission downloads as
`{iu_username}_{LATE?}_{canvas_id}_link.html`. The tool extracts the IU
username from the filename for roster lookup. This is deterministic — no
name-matching required.

**Degradation:** If the filename does not match the expected pattern, the
tool falls back to evidence-only mode (list commit authors, flag
`needs-review`). The tool does NOT crash on unrecognized filenames.

**Validation:** The filename pattern should be validated against real
Canvas exports before locking. If Canvas changes the naming convention,
the parse should degrade gracefully.

### V1-2: `commit_author_check` Checker Type

**Purpose:** Verify that the submitting student contributed commits to the
PR they submitted. Catches the "wrong submission" case (student submits the
PR they approved, not the one they created).

**API calls:**
- `GET /repos/{owner}/{repo}/pulls/{number}/commits` — list PR commits
  with `author.login` (GitHub username) per commit

**Attribution chain:**
1. Parse IU username from submission filename
2. Look up GitHub login in roster file (`roster_file` path)
3. Compare GitHub login against `author.login` values from PR commits

**Assessment:**
- `pass`: Submitting student's GitHub login appears as a commit author
- `needs-review`: Roster unavailable OR filename pattern unrecognized →
  tool lists all commit author logins as evidence, TA confirms at a glance
- `fail`: Student's GitHub login does NOT appear in commit authors AND
  roster was available → likely wrong submission (student submitted the
  PR they approved, not the one they created). Flag with `ta_confirm`.

**Evidence:** List of commit author logins, submitting student's GitHub
login (from roster), match/no-match result.

**Degradation:** Without a roster, the checker lists commit authors as
evidence and returns `needs-review` — the TA verifies manually. The tool
never guesses.

### V1-3: LATE Submission Detection

**Purpose:** Detect "LATE" in the submission filename and flag the late
policy in the report.

**Implementation:** At parse time, check if the filename contains "LATE"
(case-insensitive). If so, set `is_late=True` on the `Submission` object.

**Report behavior (AG assignments):** When `is_late=True`:
- Handgrading criteria are auto-zeroed in the report (evidence shows
  "Late submission: handgrading = 0 per course policy")
- AG score criteria still prompt the TA to enter the AG score (AG score
  is NOT zeroed for late submissions)
- A prominent banner appears in the report: "LATE SUBMISSION — handgrading
  zeroed per course policy"

**Report behavior (ICEX assignments):** Same banner. ICEX assignments
without handgrading are unaffected by the late flag (the late penalty is
expressed through the scaling, not through zeroing components).

**Exit code:** Unchanged — LATE is a flag, not an error.

### V1-4: AG Assignment Report Mode

**Purpose:** Reports for AG-based assignments (ICEX with AG, PASN) show
AG-specific sections.

**When `type` is `pasn` or when `ag_max_points` is present:**

The report adds:
1. **AG Score section:** Shows `ag_max_points`, the AG URL, and a TA action
   item to enter the AG score. If `--ag-score N` is provided, shows the
   entered value with range validation (`0 ≤ N ≤ ag_max_points`).
2. **Handgrading section:** Shows `handgrading_points` and a TA action
   item (if `handgrading_points > 0`). Auto-zeroed if LATE.
3. **Combined total:** `AG score + handgrading score` on the AG's 100-point
   scale.
4. **Canvas score:** If `canvas_points` differs from `total_points`, shows
   the scaled score: `canvas_score = (AG_total / total_points) * canvas_points`.

**`--ag-score N` CLI flag (single-submission mode only):**
- Accepts an integer AG score
- Range-checks: `0 ≤ N ≤ ag_max_points`; out-of-range is a fatal error
  (exit 1) with a clear message
- In batch mode: ignored (each submission has a different AG score);
  batch reports leave `ag_score: null`

### V1-5: Resubmission TA Prompt

**Purpose:** Remind the TA to check Canvas gradebook for prior submissions.

**Implementation:** The TA Action Items section always includes (for AG
assignments):
- "Check Canvas gradebook for prior submissions. If resubmission: do not
  overwrite prior handgrading score. Enter updated AG score in Canvas."

This is a static prompt, not automated detection (Canvas API is FERPA-
prohibited for AI tools per v1.0.0 non-goals).

### V1-6: Team Best Attribution Check

**Motivation:** In Team Best assignments, every team member must create
their own version of the deliverable (individual branch → PR to the feature
branch). The team selects the best version for grading. A submitted PR URL
might be the team's chosen version, not the submitting student's own work.
The tool must verify the student attempted the work by checking that they
have a PR (open, closed, or merged) in the team repo.

**New checker: `team_best_attribution`**

**API calls:**
- `GET /repos/{owner}/{repo}/pulls?state=all&per_page=100` — list all PRs
  (open, closed, and merged) in the team repo (first page only, matching
  the `repo_history` pagination convention)

**Attribution chain:**
1. Parse IU username from submission filename
2. Look up GitHub login in roster file
3. List all PRs in the team repo (all states)
4. Filter for PRs where `user.login` matches the student's GitHub login
5. Display the student's PRs with their state (open/closed/merged)

**Assessment:**
- `pass`: Student has at least one PR (any state) in the team repo.
  Evidence includes the PR number, title, and state. `ta_confirm` if the
  student has only closed-unmerged PRs (attempted but not merged — TA
  should check if the work was incorporated another way).
- `fail`: Student has NO PRs in the team repo AND roster was available.
  Strong signal the student did not participate. Flag with `ta_confirm`
  (TA confirms before finalizing — edge case: student may have committed
  directly to a branch without a PR, though the exercise requires a PR).
- `needs-review`: Roster unavailable or repo PRs endpoint inaccessible →
  tool lists what it can and TA verifies manually.

**Evidence:** Total PR count in repo, student's PR count, list of
student's PRs with number/title/state, all team members' PR counts (for
context — not a gradeable signal, but helps the TA spot imbalance).

**Relationship to V1-2 (`commit_author_check`):** These checkers compose.
`commit_author_check` verifies the student's commits are on the *submitted*
PR. `team_best_attribution` verifies the student has *any* PR in the repo.
If `commit_author_check` fails (student didn't author commits on the
submitted PR), `team_best_attribution` answers the follow-up: did they
do their own work elsewhere? A student who submitted a teammate's PR but
has their own PR elsewhere shows `fail` on `commit_author_check` and
`pass` on `team_best_attribution` — the report tells the full story.

**Rubric field:** `team_mode: team_best` activates this checker.

### V1-7: Team Collaboration Attribution (DEFERRED to v1.2)

**Deferred because:** The designation YAML format and Team Collaboration
exercise design are not yet built. Specifying a checker for vaporware
risks locking the wrong format. This will be specced alongside Kurt's
exercise design for next semester.

**Anticipated design (not locked):**
- Team includes a fenced ```yaml block in the submitted PR body with
  deliverable designations: name, responsible members (≥2 per deliverable)
- Tool parses the YAML, verifies coverage: every roster member designated
  on ≥1 deliverable, every deliverable has ≥2 responsible members
- Cross-referencing commits to deliverables requires an optional `files:`
  list per deliverable in the YAML — without it, coverage checks only
- Malformed YAML → `needs-review`, not `fail`
- Under-contribution flagged; over-contribution never flagged
## Edge Cases (v1.1 additions)

### EF-12: Roster file not found

If `roster_file` is specified but the file cannot be found or parsed, the
tool SHALL warn the TA, skip roster-dependent checkers (`commit_author_check`,
`ownership_check: team`), and continue processing with evidence-only
fallbacks. The tool SHALL NOT exit with an error — the roster is a
convenience, not a requirement.

### EF-13: Canvas filename does not match expected pattern

If the submission filename does not match
`{username}_{LATE?}_{id}_link.html`, the tool SHALL warn the TA, skip
username extraction, and fall back to evidence-only mode for
roster-dependent checkers. Processing continues.

### EF-14: Merged PR

The tool SHALL handle merged PRs correctly. Merged PRs have `state: closed`
and `merged: true` in the API response. Diffs are still fetchable. The
report SHALL show "State: merged" (not just "closed"). All checkers
operate on merged PRs the same as open PRs.

### EF-15: `--ag-score` out of range

If `--ag-score N` is provided and `N < 0` or `N > ag_max_points`, the tool
SHALL report "AG score {N} is out of range (0-{ag_max_points})" and exit
with code 1.

### EF-16: `--ag-score` in batch mode

If `--ag-score` is provided with `--batch`, the tool SHALL ignore the flag
and print a warning. Batch mode does not accept a single AG score for
multiple submissions.

## Success Criteria (v1.1 additions)

- **SC-13:** Given a team assignment rubric with `ownership_check: team`
  and a roster file, the tool verifies the submitting student is a team
  member and lists PR commit authors for attribution.
- **SC-14:** Given a submission filename containing "LATE", the tool flags
  the late policy in the report and auto-zeroes handgrading for AG
  assignments.
- **SC-15:** Given a `pattern_count` criterion, the tool counts regex
  occurrences in added lines and compares against the expected count
  using the specified comparison mode.
- **SC-16:** Given a `manual_review` criterion, the tool reports
  needs-review with the label from params as the TA action item.
- **SC-17:** Given `--ag-score N` in single-submission mode, the tool
  validates the range and includes the score in the AG report section.
- **SC-18:** The tool handles merged PRs identically to open PRs for all
  checkers.
- **SC-19:** The tool degrades gracefully when the roster file is missing
  or the filename pattern is unrecognized — no crash, evidence-only
  fallback.
- **SC-20:** The `ta_confirm` flag produces explicit checkbox action items
  in the report for mechanical passes requiring TA judgment.
- **SC-21:** Given a Team Best rubric with `team_mode: team_best` and a
  roster, the tool lists all PRs in the team repo and identifies whether
  the submitting student has any PR (open, closed, or merged).

## Non-Goals (v1.1)

- **No team-level cross-correlation.** Detecting missing team members,
  contribution imbalance across team PRs, or aggregation across
  submissions is deferred to v1.2.
- **No Team Collaboration designation parsing.** The designation YAML
  format and Team Collaboration exercise design are not yet built.
  Deferred to v1.2, to be specced alongside the exercise design.
- **No AG API integration.** The AG platform's OAuth2/Google federation
  and user-mapping complexity are not justified for v1.1. Manual entry
  via `--ag-score` or TA action items is sufficient.
- **No Canvas API.** Resubmission detection remains a TA manual check
  (FERPA prohibits AI tools from accessing Canvas).
- **No automated PR commenting.** TAs write all PR feedback manually.

## Checker Types Summary (v1.1)

| Checker | v1.0 | v1.1 | Purpose |
|---------|------|------|---------|
| `repo_history` | ✓ | — | Fork/mirror history (C291 only) |
| `pr_exists_with_comment` | ✓ | — | PR exists with description |
| `pr_url_valid` | ✓ | extended | `ownership_check` toggle added |
| `valid_student_repo` | ✓ | — | Repo naming pattern |
| `diff_content_check` | ✓ | codified | Added-lines-only semantics formalized |
| `manual_review` | new | ✓ | TA manual entry (AG scores, handgrading) |
| `pattern_count` | new | ✓ | Regex count in added lines |
| `commit_author_check` | new | ✓ | Per-student attribution via roster |
| `team_best_attribution` | new | ✓ | Team Best: student has any PR in team repo |
| `team_collaboration` | deferred | v1.2 | Designation YAML + coverage checks |

## Rubric Format Changes (v1.1)

### New Top-Level Fields

```yaml
type: team              # icex | pasn | team (default: icex)
canvas_points: 10       # Canvas score scale (default: = total_points)
ag_max_points: 85       # AG platform max score
handgrading_points: 15  # Handgrading max (0 if none)
ag_url: https://...     # AG project URL for TA reference
roster_file: /path/to/roster.csv  # Optional team roster
ownership_check: team   # student | team | none (default: student)
team_mode: team_best    # team_best (v1.1) | team_collaboration (v1.2)
```

### Roster File Format

CSV with two columns: `team,iu_username`. Example:

```csv
team01,jsmith
team01,jdoe
team01,rhaldhah
team02,akumar
team02,bliu
```

The IU username is the GitHub login on github.iu.edu. Display names are
not needed — the tool never matches on them.

## Build Notes

**Division of labor (unchanged):**
- Mnemo owns pedagogical design, checker semantics, spec
- Daedalus (new coder agent) or Zoidberg owns TDD implementation
- Kurt makes all final decisions

**TDD requirement:** All new checkers and features must be built
test-first. Merged-PR fixtures must be added to the test suite. Roster
loader tests must cover missing file, malformed CSV, and normal cases.
Filename parsing tests must cover the degradation path.

**Backward compatibility:** v1.0.0 rubrics (ICEX01, ICEX02, PASN01) must
work unchanged with v1.1 code. New fields are optional with sensible
defaults. chimeric