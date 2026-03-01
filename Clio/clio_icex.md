# ICEX WORKFLOW

**Terminology:** Always use **ICEX** (In-Class Exercise). Never use "ICE."

**Canvas naming (MoJ phase):** All MoJ ICEXs use `_MJ` prefixed numbering independent
of course-sequential numbering. The Canvas title format is:
`Week # | ICEX_MJ## - Title` (e.g., `Week 8 | ICEX_MJ01 - Founding the Ministry`)
Individual extensions: `Week # | ICEX_MJ##-EXT - Title`
File naming: `icex_mj##_title.md` saved to `cmods/student/icex/`

Every ICEX must follow this structure and include all sections below.

## Parallel Processing Kit (4 Roles)

Define these four roles at the top of every ICEX. Assign setup tasks concurrently. Adapt descriptions to the specific ICEX context.

| Role | Domain | Default Responsibility |
|---|---|---|
| **Repo Admin** | Repository hygiene | Branch creation, PR setup, merge management |
| **Process Lead** | Coordination + documentation | Runs the sync callouts, owns `CONTRIBUTIONS.md`, tracks DoD |
| **Dev Lead** | Primary implementation | Core coding/configuration task for this ICEX |
| **QA Sentinel** | Quality + CI/CD | Tests, linting, pipeline monitoring, runs Code Review Checklist before approving PR |

*On 5-person teams: the Dev Lead role pairs two people.*

*On 3-person teams: collapse **Repo Admin + Process Lead** into a single **Ops Lead** role
by default. This keeps Dev Lead and QA Sentinel separate, preserving code review integrity.
Alternative collapse — **Process Lead + QA Sentinel** — is permitted when the ICEX has
minimal repo work and QA is reviewing only one Dev Lead's output. Never collapse Dev Lead
with QA Sentinel. State the chosen pair explicitly in the ICEX instructions.*

*Course policy: no student may hold the same role more than two consecutive weeks.*

**Attendance pre-flight (include at the top of every ICEX):**
Before assigning roles, the Process Lead confirms attendance. If fewer than 3 members are
present (in-person or approved remote), notify the TA immediately and follow the
ICEX Attendance & Absentee Policy. Remote participation requires a documented email
request to the instructor with the team CC'd — a verbal request is not sufficient.

## Sync Callouts

ICEXs must include explicit **Sync Callouts** — moments where parallel work must converge before the next phase begins. Format:

> **⚡ SYNC — [Checkpoint Name]**
> Before proceeding: [what must be true / what the team verifies together] *(~X min)*

Typical ICEX structure:
1. Role assignment + parallel setup (all 4 roles working concurrently)
2. **⚡ SYNC — Setup Complete** (everyone confirms their piece is in place)
3. Main task (roles may continue in parallel or converge, depending on the exercise)
4. **⚡ SYNC — DoD Check** (team walks the Definition of Done checklist together)
5. CONTRIBUTIONS.md entry + PR submission

## Difficulty & Scoping Guidelines

**These guidelines apply to every ICEX you generate. Enforce them before outputting a draft.**

### Time Budget

| Phase | Target |
|---|---|
| Phase 1 — parallel setup | 8–10 min |
| Phase 2 — main task | 15–20 min |
| Sync callouts + DoD check | ~5 min |
| CONTRIBUTIONS.md entry | 2–3 min |
| **Total in-class window** | **30–35 min** |

### Step-Count Constraints

- Each role in Phase 1: **3–5 concrete, independently executable steps** — no more.
- No role may be blocked on another role before the ⚡ SYNC — Setup Complete checkpoint.
- Phase 2: **one clear deliverable**, not a series of open-ended choices.
- **Total new files created by the team across all roles: ≤ 3.**

### Complexity Signals to Avoid

- Any **design task** — ICEXs execute a defined approach; design happens in lecture or the project.
- More than **one environment-configuration step** per role.
- **External dependencies that may fail** (network calls, third-party APIs) unless that is the explicit subject of the ICEX.
- Steps that require judgment about scope (e.g., "implement the feature as you see fit").

### Pre-Condition Assumptions

State any deviations explicitly in the **Context** block. Default assumptions:

- Team repo exists; previous ICEX PR is merged.
- Student machines have the required toolchain installed (Docker, Python, Node).
- **Do not include install steps** unless the ICEX is explicitly about environment setup.

### Right-Sized ICEX Test

Before finalising an ICEX, verify all four conditions:

1. All 4 roles are active in parallel with **no idle time** during Phase 1.
2. Both SYNCs resolve cleanly with clear, binary criteria.
3. Full DoD is achievable within the window under normal conditions.
4. A student who has done the required reading can complete their role **without guessing**.

---

## CONTRIBUTIONS.md Log Entry

Every ICEX must include a `CONTRIBUTIONS.md` entry block using this exact format:

```markdown
#### ICEX [Number]: [Exercise Title]
* **Date:** YYYY-MM-DD
* **Team Members Present:** `@github-user1`, `@github-user2`, ...
* **Roles:**
    * Repo Admin: `@github-userX`
    * Process Lead: `@github-userY`
    * Dev Lead: `@github-userZ`
    * QA Sentinel: `@github-userW`
* **Summary of Work:** [1-2 sentences on what was accomplished]
* **Evidence & Reflection:** [ICEX-specific open-ended question inserted here]
```

## Definition of Done (DoD)

Every ICEX must include a DoD checklist:

```
* [ ] Artifact: [the core technical artifact exists]
* [ ] Functionality: [the artifact works as specified]
* [ ] Process: CONTRIBUTIONS.md is updated and all members have pulled it locally
* [ ] Submission: PR is open, titled correctly, and Team TA is assigned as Reviewer
```

## Code Review Checklist

Every ICEX PR must be reviewed by the QA Sentinel using this checklist before approval.
This formalizes the existing 2-reviewer requirement into a taught practice.
The checklist is named "code review" in the artifact — not "PR review" — so students build
the vocabulary. L4 (testing) or L6 (security) should include one slide naming code review
as a discipline and referencing this checklist.

```
Code Review Checklist (QA Sentinel — complete before approving the PR)

□ Does the code do what the PR description says?
□ Are there obvious paths with no error handling or unexpected input?
□ Do the tests cover the new behavior? (happy path at minimum)
□ Would a teammate understand this code in 6 weeks?
□ Any hardcoded values that should be config or constants?
```

If any item fails: leave a specific inline comment on the relevant line in GitHub, do not
approve until addressed. This is the practice, not a gatekeeping exercise.

---

## References Section

Every ICEX must include a **References** section with links organized into three groups.
Populate with current, relevant links at generation time. Do not use placeholder URLs.

**Group 1 — Documentation & FAQs**
Official documentation, API references, and framework guides for the tools used in the ICEX.
At least 2 links required. Examples: Flask docs, pytest docs, GitHub Actions docs.

**Group 2 — Tutorials & Walkthroughs**
Step-by-step guides, blog posts, or video tutorials that show how to do the task.
May be empty if no suitable tutorials exist, but prefer at least 1 when possible.
Examples: Real Python articles, official "getting started" tutorials.

**Group 3 — Standards & Specifications**
RFCs, official specifications, PEPs, OWASP advisories, IEEE/IETF standards.
Include these whenever the ICEX involves a pattern with a named standard behind it.
Examples: RFC 7807 (error responses), PEP 8 (style), OWASP Top 10, BDD/Gherkin spec.
May be empty for purely implementation-focused ICEXs.

---

## Standard Blocker Protocol (SBP)

Include this section verbatim in every ICEX:

> **If you are individually blocked for > 15 minutes** on an error you cannot solve:
> 1. Notify your team and pivot to a support task (documentation, testing, research).
> 2. Create an individual branch: `aar-icex[N]-<username>`
> 3. Create `aar/AAR-ICEX[N]-<username>.md` using the AAR template.
> 4. Open a PR titled `AAR ICEX [N]: <Brief Blocker Description>`, assign the Instructor as Reviewer.
> 5. Submit this PR URL to Canvas as your on-time submission (worth 5 pts).
> 6. After the instructor provides a hotfix, apply it, meet the DoD, and resubmit the passing PR (worth 5 pts).

---

# TA ROLES

TAs are **Team Coaches**. They encourage, share experience, and help teams unblock. They have no authority beyond applying the provided rubrics.

Every ICEX and project assignment must include a **TA Follow-up Guide** with:
- In-class goal (the TA's #1 priority during the session)
- Final DoD (what must be true by 11:59 PM)
- 2–3 common pitfalls with symptoms and fixes
- 2–3 coaching questions for the next team meeting
- 1–2 feed-forward prompts pointing toward the next topic

---

# RUBRICS

## Rubric Format Policy (Single Target: Canvas HTML)

All rubrics must be generated as a **raw HTML `<table>` block with inline styles**, embedded directly in the Markdown file. This is the single source of truth — the Canvas pipeline (`build_canvas_page.sh`) passes it through as-is.

**Never use Markdown pipe tables or Pandoc grid tables for rubrics.**

Standard rubric table structure:

```html
<table style="width:100%; border-collapse:collapse; font-size:0.9em;">
  <thead>
    <tr style="background-color:#990000; color:#ffffff;">
      <th style="padding:8px; text-align:left; width:40%;">Criterion</th>
      <th style="padding:8px; text-align:center; width:15%;">Points</th>
      <th style="padding:8px; text-align:left;">Description</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background-color:#f3f2eb;">
      <td style="padding:8px; border-bottom:1px solid #ccc;"><strong>Criterion Name</strong></td>
      <td style="padding:8px; text-align:center; border-bottom:1px solid #ccc;">N</td>
      <td style="padding:8px; border-bottom:1px solid #ccc;">Description of what earns full credit.</td>
    </tr>
    <tr>
      <td style="padding:8px; border-bottom:1px solid #ccc;"><strong>Criterion Name</strong></td>
      <td style="padding:8px; text-align:center; border-bottom:1px solid #ccc;">N</td>
      <td style="padding:8px; border-bottom:1px solid #ccc;">Description of what earns full credit.</td>
    </tr>
  </tbody>
  <tfoot>
    <tr style="background-color:#990000; color:#ffffff;">
      <td style="padding:8px;"><strong>Total</strong></td>
      <td style="padding:8px; text-align:center;"><strong>10</strong></td>
      <td style="padding:8px;"></td>
    </tr>
  </tfoot>
</table>
```

Alternate row shading: odd rows use `background-color:#f3f2eb` (cream), even rows use no background color.

## Rubric Point Allocations — ICEX

- **ICEXs:** 10 points total. At least 3 points for a complete `CONTRIBUTIONS.md` entry. Remaining 7 points distributed across the major technical goals.

---

# ICEX OUTPUT TEMPLATE

Use this template exactly when generating an ICEX.

```markdown
### ICEX [N]: [Exercise Title]

- **Objective:** [Specific skill practiced or artifact produced]
- **Time Limit:** [25–30 minutes in-class — class period is 75 minutes total; ICEX must fit within that with room for intro and wrap-up]; PR due 11:59 PM]
- **Context:** [Bridge from prior lecture or Angband — why this, why now]

---

### Parallel Processing Kit ⚡

> **Attendance pre-flight (Process Lead):** Confirm ≥3 members present before assigning
> roles. If below threshold, notify the TA immediately and follow the ICEX Attendance Policy.
> Remote participation requires a prior email to the instructor with the team CC'd.

Assign roles immediately. No student may hold the same role more than two consecutive weeks.

| Role | Assigned To | First Task |
|---|---|---|
| Repo Admin | `@___` | [First concurrent task] |
| Process Lead | `@___` | [First concurrent task] |
| Dev Lead | `@___` | [First concurrent task] |
| QA Sentinel | `@___` | [First concurrent task] |

*5-person teams: Dev Lead is a pair.*
*3-person teams: collapse Repo Admin + Process Lead into one Ops Lead (default). Alternative:
Process Lead + QA Sentinel when repo work is minimal. Never collapse Dev Lead + QA Sentinel.*

---

### Phase 1: Parallel Setup (~X min)

**Repo Admin**
1. [Step]
2. [Step]

**Process Lead**
1. [Step]
2. [Step]

**Dev Lead**
1. [Step]
2. [Step]

**QA Sentinel**
1. [Step]
2. [Step]

> **⚡ SYNC — Setup Complete**
> Before proceeding: [what every role must confirm] *(~X min)*

---

### Phase 2: [Main Task Title] (~X min)

[Task description with role assignments]

> **⚡ SYNC — DoD Check**
> Walk the Definition of Done together. *(~5 min)*

---

### Definition of Done 🏁

* [ ] **Artifact:** [Core artifact exists]
* [ ] **Functionality:** [It works as specified]
* [ ] **Process:** `CONTRIBUTIONS.md` updated and all members have pulled locally
* [ ] **Submission:** PR open, titled `ICEX [N]: [Title]`, Team TA assigned as Reviewer

---

### CONTRIBUTIONS.md Entry

```markdown
#### ICEX [N]: [Exercise Title]
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

### Code Review (QA Sentinel — before approving the PR)

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

### Submission

1. PR title: `ICEX [N]: [Exercise Title]`
2. Assign your Team TA as Reviewer
3. Submit the PR URL to Canvas

---

### References

#### 📚 Documentation & FAQs
- [Title](url)
- [Title](url)

#### 🎓 Tutorials & Walkthroughs
- [Title](url)

#### 📋 Standards & Specifications
- [Title](url)

---

### Standard Blocker Protocol (SBP)

> **If you are individually blocked for > 15 minutes** on an error you cannot solve:
> 1. Notify your team and pivot to a support task (documentation, testing, research).
> 2. Create an individual branch: `aar-icex[N]-<username>`
> 3. Create `aar/AAR-ICEX[N]-<username>.md` using the AAR template.
> 4. Open a PR titled `AAR ICEX [N]: <Brief Blocker Description>`, assign the Instructor as Reviewer.
> 5. Submit this PR URL to Canvas as your on-time submission (worth 5 pts).
> 6. After the instructor provides a hotfix, apply it, meet the DoD, and resubmit the passing PR (worth 5 pts).

---

### TA Follow-up Guide

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

---

### Rubric (10 pts)

[HTML table with inline styles — see Rubric Format Policy]

---

### Pedagogical Analysis

[One sentence per applicable principle]
```
