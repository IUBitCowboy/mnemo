# ICEX CONVENTIONS (SE1/P465)

Apply in addition to your base persona and Mnemo skills.

**Terminology:** Always use **ICEX** (In-Class Exercise). Never use "ICE."

## ICEX Attendance Policy

In-class exercises are heavily reliant on team attendance. The following
policy applies to all ICEXs:

- **Minimum attendance:** If a team has fewer than 3 members in attendance,
  the team must report the ICEX as a failure by submitting a PR documenting
  the members in attendance in the `CONTRIBUTIONS.md` file. This enables a
  team extension until the end of the week to make up the ICEX.
- **Makeup grading:** Members originally in attendance are eligible for 100%.
  Absent members making up the exercise are given an 85% participation
  coefficient.
- **Remote attendance:** Team members may attend remotely with approval from
  the team.
- **Cadence enforcement:** MoJ ICEXs must be completed on a regular cadence.
  A backlog of missed ICEXs will overwhelm any pedagogical value. The makeup
  process exists to keep students current, not to create indefinite
  extensions.

## Recovery Point and Makeup Workflow

Every ICEX that includes a setup and configuration step should generate a
**recovery point commit** at the end of setup. This commit:

1. Syncs scaffolding code and configuration across team member repos
2. Serves as the rollback point for absent students performing a makeup

**Makeup process for absent students:**
1. Roll working repo back to the recovery point commit
2. Implement an independent solution for the planted bug (if any) on a
   personal bug-fix branch
3. Open a PR to merge the bug-fix branch back to the team's exercise branch
   (Team TA and instructor as reviewers)
4. The PR is **always closed without merging** — the team already has the fix.
   The PR demonstrates the student's individual work.
5. The TA or instructor reviews the PR when evaluating the makeup write-up
   in the student's engineering log reflection

See the Mnemo Planted Bug technique for the full pattern.

## Canvas Naming (MoJ Phase)

All MoJ ICEXs use `_MJ` prefixed numbering independent of course-sequential
numbering. The Canvas title format is:
`Week # | ICEX_MJ## - Title` (e.g., `Week 8 | ICEX_MJ01 - Founding the Ministry`)
Individual extensions: `Week # | ICEX_MJ##-EXT - Title`
File naming: `icex_mj##_title.md` saved to `cmods/student/icex/`

## Testing Discipline Policy

- Test format: GIVEN / WHEN / THEN structure.
- Three-level taxonomy: unit → integration → end-to-end.
- Coverage framing: "what matters" over "what's measurable."
- Mocking introduced at ICEX 13 (when external services appear).
- Test health checked in cycle closes (every 2-3 weeks).
- Regression test coaching habit: TAs ask "what existing test would catch
  this?" when reviewing fixes.

## API Design Policy

- Versioning: API version in URL path (`/api/v1/...`).
- Error response standard: RFC 7807 Problem Details format.
- Pagination: cursor-based for large collections.
- Auth: token-based, introduced when MoJ needs user accounts.
- Contract document: OpenAPI spec as extra-credit exercise.
- OpenAPI EC: students generate spec from their Flask routes.

## Rubric Point Allocations (SE1)

- **ICEXs:** 10 points total. At least 3 points for a complete `CONTRIBUTIONS.md`
  entry. Remaining 7 points distributed across the major technical goals.
- **Projects:** 100 points total. Allocation defined in `clio_project.md`.

---

# ICEX OUTPUT TEMPLATE

Use this template exactly when generating an ICEX. The template embeds
Mnemo skills (SBP, DoD, CONTRIBUTIONS format, Code Review Checklist) inline
so the generated artifact is self-contained.

```markdown
# ICEX [N]: [Exercise Title]

- **Objective:** [Specific skill practiced or artifact produced]
- **Time Limit:** [25–30 minutes in-class — class period is 75 minutes total; ICEX must fit within that with room for intro and wrap-up]; PR due 11:59 PM]
- **Context:** [Bridge from prior lecture or Angband — why this, why now]

---

## Parallel Processing Kit ⚡

> **Attendance pre-flight (Process Lead):** Confirm ≥3 members present before assigning
> roles. If below threshold, follow the ICEX Attendance Policy (report as failure,
> submit PR with CONTRIBUTIONS.md documenting attendance, team gets week extension).
> Remote participation requires team approval.

Assign roles immediately. No student may hold the same role more than two consecutive weeks.

|| Role | Assigned To | First Task ||
||---|---|---|
|| Repo Admin | `@___` | [First concurrent task] |
|| Process Lead | `@___` | [First concurrent task] |
|| Dev Lead | `@___` | [First concurrent task] |
|| QA Sentinel | `@___` | [First concurrent task] |

*5-person teams: Dev Lead is a pair.*
*3-person teams: collapse Repo Admin + Process Lead into one Ops Lead (default). Alternative:
Process Lead + QA Sentinel when repo work is minimal. Never collapse Dev Lead + QA Sentinel.*

---

## Phase 1: Parallel Setup (~X min)

**Repo Admin**
1. [Step]
2. [Generate recovery point commit — tag as `recovery-icex[N]` for makeup reference]

**Process Lead**
1. [Step]
2. [Step]

**Dev Lead**
1. [Step]
2. [Step]

**QA Sentinel**
1. [Step]
2. [Step]

> **⚡ SYNC — Setup Complete** — recovery point committed
> Before proceeding: [what every role must confirm]. All members verify
> they have the recovery point commit. *(~X min)*

---

## Phase 2: [Main Task Title] (~X min)

[Task description with role assignments]

> **⚡ SYNC — DoD Check**
> Walk the Definition of Done together. *(~5 min)*

---

## Definition of Done 🏁

* [ ] **Artifact:** [Core artifact exists]
* [ ] **Functionality:** [It works as specified]
* [ ] **Process:** `CONTRIBUTIONS.md` updated and all members have pulled locally
* [ ] **Submission:** PR open, titled `ICEX [N]: [Title]`, Team TA assigned as Reviewer

---

## CONTRIBUTIONS.md Entry

```markdown
# ICEX [N]: [Exercise Title]
* **Date:** YYYY-MM-DD
* **Team Members Present:** `@user1`, `@user2`, `@user3`, `@user4`
* **Roles:**
    * Repo Admin: `@userX`
    * Process Lead: `@userY`
    * Dev Lead: `@userZ`
    * QA Sentinel: `@userW`
* **Summary of Work:** [1-2 sentences]
* **Evidence & Reflection:** [ICEX-specific question]
```

---

## Code Review (QA Sentinel — before approving the PR)

Work through this checklist on your teammate's code before clicking Approve.
If an item fails, leave an inline comment on the relevant line — do not just add a note
in the PR description. Address all comments before merging.

```
□ Does the code do what the PR description says?
□ Are there obvious paths with no error handling or unexpected input?
□ Do the tests cover the new behavior? (happy path at minimum)
□ Would a teammate understand this code in 6 weeks?
□ Any hardcoded values that should be config or constants?
```

---

## Submission

1. PR title: `ICEX [N]: [Exercise Title]`
2. Assign your Team TA as Reviewer
3. Submit the PR URL to Canvas

---

## References

### 📚 Documentation & FAQs
- [Title](url)
- [Title](url)

### 🎓 Tutorials & Walkthroughs
- [Title](url)

### 📋 Standards & Specifications
- [Title](url)

### 🤖 AI Assistant Prompt
[Curated prompt specific to this exercise — see References Section Format technique]

---

## Standard Blocker Protocol

> **If you are individually blocked for > 15 minutes** on an error you cannot solve:
> 1. Notify your team and pivot to a support task (documentation, testing, research).
> 2. Create an individual branch: `aar-icex[N]-<username>`
> 3. Create `aar/AAR-ICEX[N]-<username>.md` using the After Action Report template below.
> 4. Open a PR titled `AAR ICEX [N]: <Brief Blocker Description>`, assign the Instructor as Reviewer.
> 5. Submit this PR URL to Canvas as your on-time submission (worth 5 pts).
> 6. After the instructor provides a hotfix, apply it, meet the Definition of Done, and resubmit the passing PR (worth 5 pts).

### After Action Report Template (Copy into `aar/AAR-ICEX[N]-<username>.md`)

```markdown
# AAR for ICEX [N]: [Blocker Title]

* **Student:** `@your-github-username`
* **Timestamp:** `YYYY-MM-DD @ HH:MM`

---

### Instructor's Diagnostic Hints
* **Hint 1:** [Exercise-specific hint]
* **Hint 2:** [Exercise-specific hint]
* **Hint 3:** [Exercise-specific hint]

---

### 1. The Blocker
*(What is the symptom? What is the exact error message?)*

> [Paste error message or describe symptom]

### 2. The Investigation
*(What exactly did you try? List commands, edits, and resources consulted.)*

* I tried...
* Then I edited...
* This resource suggested...

### 3. The Root Cause Hypothesis
*(What do you think is the real problem? Be specific.)*

> I believe the problem is...

### 4. Evidence
*(Paste full terminal output, code snippets, or screenshots.)*

    [Paste full logs here]

### 5. The "Aha!" Moment (if any)
*(Did you have a moment of clarity while writing this?)*

> [Describe your realization, or N/A]

### 6. The Learning
*(What did you learn? What will you do differently next time?)*

> I learned that...

### 7. The Remaining Question
*(What do you still not understand? What one question do you need answered?)*

> My one question is...
```

---
<!--
## TA Follow-up Guide

- **In-Class Goal:** [TA's #1 priority during the session]
- **Final DoD (11:59 PM):** [What must be submitted]
- **Common Pitfalls:**
  1. **[Blocker]:** Symptom / Fix
  2. **[Blocker]:** Symptom / Fix
- **Coaching Questions:**
  - "[Question probing the why]"
  - "[Question probing team process]"
- **Feed-Forward Prompts:**
  - "[Prompt pointing toward the next topic]"
-->
---
## Rubric ([N] pts)

[Structured markdown table — see Rubric Format Policy in Mnemo skills.
The pipeline transforms this into the published format.]

---
<!--
## Pedagogical Analysis

[One sentence per applicable principle — see Mnemo pedagogical-analysis skill]
-->
```
