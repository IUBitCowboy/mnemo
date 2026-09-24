# ICEX Submission Checker

A command-line tool for C291 teaching assistants that performs a preliminary
compliance assessment of student ICEX assignment submissions. The tool reads
a Canvas-downloaded submission file, extracts the pull request URL, queries the
GitHub Enterprise API to verify rubric criteria, and produces a structured
report with evidence and point recommendations.

**The tool does not grade.** It surfaces evidence and flags discrepancies. The
TA reviews the report, confirms findings, writes student feedback on the PR,
and enters the score in Canvas. All grading decisions are the TA's.

---

## What It Does

1. **Parses** a Canvas submission HTML file to extract the student's PR URL
2. **Queries** the GitHub Enterprise API (github.iu.edu) to fetch PR metadata,
   diff, repository info, and commit history
3. **Checks** each rubric criterion against the evidence using deterministic
   rules (no AI/LLM inference — just API queries and pattern matching)
4. **Reports** a per-criterion assessment (`pass`, `partial`, `fail`, or
   `needs-review`) with cited evidence and a point recommendation
5. **Flags** anything the tool cannot mechanically verify as an explicit TA
   action item — nothing is silently skipped

---

## Prerequisites

### Python 3.9+

The tool runs on any standard Python 3.9 or newer. No special build tools
required.

### Dependencies

Two external packages (everything else is Python standard library):

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client for GitHub Enterprise API |
| `PyYAML` | Rubric file parser |

Install them with:

```bash
pip install requests PyYAML
```

Or if the repo's `requirements.txt` is available:

```bash
pip install -r requirements.txt
```

### GitHub Enterprise API Token

The tool needs a personal access token to query github.iu.edu. It resolves
the token in this order:

1. **`--token` CLI argument** — pass it on the command line
2. **`GH_TOKEN` environment variable** — export it in your shell
3. **`GITHUB_ENTERPRISE_TOKEN` environment variable** — alternative env var
4. **`gh auth token`** — if you have the [GitHub CLI](https://cli.github.com/)
   installed and authenticated, the tool will use it automatically

#### Option A: Use `gh auth login` (easiest — no token to manage)

If you have the GitHub CLI installed:

```bash
gh auth login --hostname github.iu.edu
# Follow the prompts — choose HTTPS, authenticate via browser
```

> **Do not omit `--hostname github.iu.edu`.** Without it, `gh auth login`
> defaults to github.com and the tool will get the wrong token.

The tool will automatically call `gh auth token --hostname github.iu.edu` to
get the right token. No environment variables needed. This is the recommended
approach for TAs.

#### Option B: Create a classic personal access token

**You must use a classic token, not a fine-grained token.** Fine-grained
tokens do not currently work reliably with GitHub Enterprise Server API
access for private repositories.

1. Go to https://github.iu.edu/settings/tokens
2. Click **"Generate new token (classic)"** (not "Fine-grained")
3. Give it a name like "ICEX Checker"
4. Select the **`repo`** scope (Full control of private repositories)
   — this is the only required scope
5. Copy the token value
6. Export it:

```bash
export GH_TOKEN="ghp_your_token_here"
```

> **Important — multi-host setups:** If you also have a github.com account
> with a token in `GH_TOKEN`, that token will fail against github.iu.edu
> with a 401 error. Either unset it (`unset GH_TOKEN`) and let the tool use
> `gh auth token` instead, or replace it with a github.iu.edu token.

> **Security:** The tool never prints or logs your token. Do not put tokens in
> rubric files or any file that might be committed to a repository.

### Rubric File

Each ICEX assignment has a rubric YAML file that defines the criteria, point
values, and checker types. The tool looks for the rubric in this order:

1. **`--rubric` flag** — explicit path to a YAML file
2. **Auto-detect** — if the submission title contains an assignment ID (e.g.
   `ICEX01`), the tool searches for a matching file in `rubrics/` inside the
   tool directory

The rubric for ICEX01 is included at `rubrics/icex01_fa26.yaml`. You will
receive new rubric files from the instructor for each ICEX assignment.

---

## Quick Start

### 1. Clone the TA tools repo

```bash
git clone git@github.iu.edu:mnemo-course-dev/ta-tools.git
cd ta-tools
```

### 2. Set up Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install requests PyYAML
```

### 3. Authenticate to GitHub Enterprise

```bash
gh auth login --hostname github.iu.edu
```

> **Do not omit `--hostname github.iu.edu`.** Without it, `gh auth login`
> defaults to github.com and the tool will get the wrong token.

### 4. Run the checker

```bash
# Single submission
.venv/bin/python icex_checker.py path/to/submission.html --rubric rubrics/icex01_fa26.yaml

# Batch mode
.venv/bin/python icex_checker.py --batch path/to/submissions/ --rubric rubrics/icex01_fa26.yaml --output-dir results/
```

### Updating

When the instructor pushes updates (new rubrics, code fixes):

```bash
git pull
.venv/bin/pip install -r requirements.txt  # in case deps changed
```

---

## Command-Line Reference

```
python3 icex_checker.py <submission.html> [options]

python3 icex_checker.py --batch <directory> [options]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `<submission.html>` | (required) | Path to Canvas submission HTML file (positional, unless `--batch`) |
| `--rubric FILE` | auto-detect | Path to rubric YAML file |
| `--token TOKEN` | (env/gh) | GitHub Enterprise API token |
| `--github-host HOST` | `github.iu.edu` | GitHub Enterprise host |
| `--save-json FILE` | (none) | Save full assessment as JSON to this path |
| `--output-format` | `text` | Output format: `text` (human-readable) or `json`. In batch mode with `--output-dir`, controls the per-submission file type: `text` writes `<name>.txt` reports, `json` writes `<name>.json` |
| `--batch DIR` | (none) | Batch mode: process all `.html` files in this directory |
| `--output-dir DIR` | (none) | Batch mode: write one report per submission here — `.json` (or `.txt` with `--output-format text`), including an error JSON for failed submissions (requires `--batch`) |
| `--verbose` | off | Include API response details in output |
| `--version` | off | Print version and exit |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — assessment completed (may include fail/partial findings) |
| 1 | Fatal error — could not process submission (file not found, no URL, auth failure, network error) |
| 2 | Partial failure — batch mode: some submissions could not be processed |

---

## Understanding the Report

The report has four main sections:

### Summary

Shows total points possible, recommended points, and counts by assessment
status: passed / partial / failed / needs-review.

### Per-Criterion Detail

Each rubric criterion is assessed as one of:

| Assessment | Meaning |
|------------|---------|
| **PASS** | Criterion met all mechanical checks. Some `PASS` items also have a `Confirm` action item (see below). |
| **PARTIAL** | Criterion partially met. The tool recommends partial points. The TA decides the final amount. |
| **FAIL** | Criterion not met. The tool recommends zero points. The TA confirms. |
| **NEEDS-REVIEW** | The tool could not check this criterion automatically. The TA must review manually. |

Each finding includes **evidence** — specific data from the API response
(repo dates, PR body text, diff content, HTTP status) — so you can verify
without re-querying.

### TA Action Items

A checklist of things the TA must verify. Two types:

- **Review manually:** The tool could not check this criterion. Read the PR
  directly and assess.
- **Confirm:** The tool checked what it can mechanically, but a judgment call
  remains. For example, the tool confirms a PR comment exists and is long
  enough, but you must judge whether it is "well-written."

### PR Details

PR title, description, branches, commit count, and state — for quick
reference. The PR URL is repeated here for direct access.

---

## Example: Clean Submission (All Pass)

```
========================================================================
ICEX SUBMISSION CHECKER REPORT
========================================================================
Assignment: ICEX01 (C291 FA26)
Student:    Jane Doe
PR URL:     https://github.iu.edu/jdoe/fa26_c291/pull/42
Assessed:   2026-09-01T10:30:00
Tool:       icex_checker 1.0.0

SUMMARY
------------------------------------------------------------------------
Total points possible: 10
Recommended points:     10
passed: 5 | partial: 0 | failed: 0 | needs-review: 0

CRITERIA
------------------------------------------------------------------------
[PASS] Forked class Repo (max 1, recommended 1)
    evidence: repo created: 2026-08-26T14:32:11Z
    evidence: commits inspected (first page, per_page=100): 15
    evidence: earliest commit author date: 2025-08-15
    evidence: earliest commit predates semester start 2026-08-24
    note: Fork/mirror history confirmed: at least one commit was authored
          before the semester start date.

[PASS] Create Pull Request (max 2, recommended 2)
    evidence: PR #42: Add hello.c with personalized greeting
    evidence: state: open
    evidence: body length: 87 chars
    evidence: body excerpt: This PR adds hello.c with a printf greeting.
             I replaced 'World' with my name as specified in the ICEX01
             instructions.
    note: PR exists with a substantive description (>= 10 chars). TA must
          judge whether the comment is well-written.

[PASS] PR URL submitted to Canvas (max 2, recommended 2)
    evidence: PR #42 resolves (HTTP 200)
    evidence: repo owner from URL: jdoe
    evidence: owner matches student name: jdoe
    note: URL resolves to a real PR in the student's own repository.

[PASS] Valid Student Repo Established (max 2, recommended 2)
    evidence: repo full name: jdoe/fa26_c291
    evidence: repo created: 2026-08-26T14:32:11Z
    evidence: owner login: jdoe
    evidence: repo URL: https://github.iu.edu/jdoe/fa26_c291
    note: Repo exists on github.iu.edu, name matches the course pattern,
          and the owner is present in the URL path.

[PASS] Committed hello.c correct elements (max 3, recommended 3)
    evidence: files in diff: hello.c
    evidence: added lines in hello.c:
    +printf("Hello, Jane!\n");
    note: Target file modified; 'printf' present in added lines; 'World'
          absent from added lines. TA must confirm the replacement is the
          student's actual name.

PR DETAILS
------------------------------------------------------------------------
Title:       Add hello.c with personalized greeting
Description: This PR adds hello.c with a printf greeting. I replaced
             'World' with my name as specified in the ICEX01 instructions.
Branches:    feature/hello-c -> main
Commits:     1
State:       open

TA ACTION ITEMS
------------------------------------------------------------------------
  [ ] Confirm: Create Pull Request — PR exists with a substantive
      description (>= 10 chars). TA must judge whether the comment is
      well-written.
  [ ] Confirm: Committed hello.c correct elements — Target file modified;
      'printf' present in added lines; 'World' absent from added lines. TA
      must confirm the replacement is the student's actual name.

PR for direct access: https://github.iu.edu/jdoe/fa26_c291/pull/42
========================================================================
```

**What the TA does with this report:**

1. Review the summary — 10/10 recommended, all criteria pass mechanically
2. Check the two **Confirm** items: Is the PR comment well-written? Is "Jane"
   the student's actual name? (Yes and yes → confirm.)
3. Open the PR URL to spot-check if desired
4. Write feedback on the PR (if any) and enter the score in Canvas

---

## Example: Submission With Issues (Mixed Results)

```
========================================================================
ICEX SUBMISSION CHECKER REPORT
========================================================================
Assignment: ICEX01 (C291 FA26)
Student:    John Smith
PR URL:     https://github.iu.edu/jsmith/fa26-c291/pull/7
Assessed:   2026-09-01T10:35:00
Tool:       icex_checker 1.0.0

SUMMARY
------------------------------------------------------------------------
Total points possible: 10
Recommended points:     6.5
passed: 2 | partial: 3 | failed: 0 | needs-review: 0

CRITERIA
------------------------------------------------------------------------
[PASS] Forked class Repo (max 1, recommended 1)
    evidence: repo created: 2026-08-26T14:32:11Z
    evidence: commits inspected (first page, per_page=100): 15
    evidence: earliest commit author date: 2025-08-15
    evidence: earliest commit predates semester start 2026-08-24
    note: Fork/mirror history confirmed: at least one commit was authored
          before the semester start date.

[PARTIAL] Create Pull Request (max 2, recommended 1)
    evidence: PR #7: Week 1 ICEX
    evidence: state: open
    evidence: body length: 0 chars
    evidence: body excerpt:
    note: PR exists but its description is empty or shorter than the
          10-char threshold — TA should assess partial credit.

[PASS] PR URL submitted to Canvas (max 2, recommended 2)
    evidence: PR #7 resolves (HTTP 200)
    evidence: repo owner from URL: jsmith
    evidence: owner matches student name: jsmith
    note: URL resolves to a real PR in the student's own repository.

[PARTIAL] Valid Student Repo Established (max 2, recommended 1)
    evidence: repo full name: jsmith/fa26-c291
    evidence: repo created: 2026-08-26T14:32:11Z
    evidence: owner login: jsmith
    evidence: repo URL: https://github.iu.edu/jsmith/fa26-c291
    note: Repo name 'fa26-c291' is a close match to the expected pattern
          'fa26_c291' (separator/order variant) — TA should confirm it is
          the course repo.

[PARTIAL] Committed hello.c correct elements (max 3, recommended 1.5)
    evidence: files in diff: hello.c
    evidence: added lines in hello.c:
    +printf("Hello World!\n");
    note: Target file is in the diff but content checks partially fail
          (printf modified: True; 'World' still present in added lines:
          True). TA should judge partial credit.

PR DETAILS
------------------------------------------------------------------------
Title:       Week 1 ICEX
Description:
Branches:    main -> main
Commits:     1
State:       open

TA ACTION ITEMS
------------------------------------------------------------------------
  (none — all criteria mechanically verified)

PR for direct access: https://github.iu.edu/jsmith/fa26-c291/pull/7
========================================================================
```

**What the TA does with this report:**

1. Review the summary — 6.5/10 recommended, three partials
2. **Create Pull Request (partial):** PR exists but has no description. The TA
   decides: 1 point (partial) or 0 (if the rubric requires a comment)
3. **Valid Student Repo (partial):** Repo name uses hyphens instead of
   underscores (`fa26-c291` vs `fa26_c291`). The TA confirms this is the
   correct course repo — likely 2 points (the naming is a variant, not wrong)
4. **Committed hello.c (partial):** Student modified `printf` but left
   "World" in the string instead of replacing it with their name. The TA
   decides partial credit — likely 1.5 or 1 points
5. Open the PR, write feedback (especially on the hello.c issue), enter the
   final score in Canvas

---

## TA Workflow

1. **Download** the submission HTML file from Canvas
2. **Run** the tool against the submission file with the rubric for the
   assignment
3. **Review** the report — check the summary, read each criterion's evidence,
   and review the TA action items
4. **Open** the PR URL (linked in the report) to spot-check anything the tool
   flagged or could not verify
5. **Write** feedback on the PR as a comment
6. **Enter** the final score in Canvas GradeBook

### Batch Mode Workflow

For processing multiple submissions at once:

```bash
# Put all submission .html files in a directory
python3 icex_checker.py --batch submissions/ \
    --rubric rubrics/icex01_fa26.yaml \
    --output-dir results/
```

This produces:
- A text report for each submission on stdout (separated by dividers)
- One JSON file per submission in the output directory
- A `summary.json` file with all submissions and their recommended scores
- A summary table at the end of stdout

---

## Rubric Files

Rubric files are YAML documents that define what to check for each ICEX
assignment. You do not need to write these — the instructor provides them.
But understanding the format helps you interpret the report.

```yaml
# Rubric for ICEX01-FA26-C291
assignment: ICEX01
course: C291
semester: FA26
total_points: 10
semester_start: 2026-08-24

criteria:
  - name: "Forked class Repo"
    points: 1
    checker: repo_history
    params: {}

  - name: "Create Pull Request"
    points: 2
    checker: pr_exists_with_comment
    params:
      min_comment_length: 10

  # ... more criteria ...
```

Each criterion has a `checker` type that determines what the tool looks for.
The checker types are:

| Checker | What it verifies |
|---------|-----------------|
| `repo_history` | Repo has commits authored before the semester start (fork/mirror evidence) |
| `pr_exists_with_comment` | PR exists and has a description above a minimum length |
| `pr_url_valid` | Submitted URL resolves to a real, accessible PR |
| `valid_student_repo` | Repo is on github.iu.edu with the expected course naming pattern |
| `diff_content_check` | PR diff touches a target file and meets content pattern requirements |

New ICEX assignments may introduce new checker types. If a rubric references
a checker the tool doesn't recognize yet, that criterion is reported as
`needs-review` — the tool continues processing the rest.

---

## Troubleshooting

### "authentication failed (HTTP 401)"

Your token is invalid, expired, or **for the wrong GitHub host**. If you have
both a github.com account and a github.iu.edu account (common at IU), check
which token your environment is providing:

- **`GH_TOKEN` env var:** If this is set to a github.com token, it will fail
  against github.iu.edu. Unset it (`unset GH_TOKEN`) and let the tool use
  `gh auth token` instead, or replace it with a github.iu.edu token.
- **Fine-grained token:** GitHub Enterprise Server private repo access
  requires a **classic** token, not a fine-grained one. Go to
  https://github.iu.edu/settings/tokens and generate a classic token with
  the `repo` scope.
- **`gh auth token` fallback:** The tool calls `gh auth token --hostname
  github.iu.edu` to get the correct token for multi-host setups. Make sure
  you've run `gh auth login --hostname github.iu.edu` to authenticate.

To create a new github.iu.edu classic token:

1. Go to https://github.iu.edu/settings/tokens
2. Click **"Generate new token (classic)"** (not "Fine-grained")
3. Give it a name like "ICEX Checker"
4. Select the **`repo`** scope (Full control of private repositories)
5. Copy the token value
6. Export it: `export GH_TOKEN="ghp_your_token_here"`

### "rate limited by GitHub API"

Wait a few minutes and retry. If this persists, your token may lack
permission for the student's repository. Check with the instructor.

### "PR not accessible (HTTP 404)"

The PR URL in the submission doesn't resolve. This could mean:
- The student submitted the wrong PR number
- The PR was deleted
- The repo is private and your token doesn't have access
- The student pasted a non-PR URL

Open the PR URL in your browser to check.

### "no PR URL found in submission file"

The Canvas submission file doesn't contain a valid PR URL. The student may
have pasted plain text instead of a link, or the Canvas export is malformed.
Check the submission directly in Canvas.

### "rubric file not found"

The `--rubric` path doesn't exist, and auto-detect couldn't find a matching
file. Pass the rubric path explicitly: `--rubric path/to/icex01_fa26.yaml`.

### "network error"

The tool can't reach github.iu.edu. Check your network connection and VPN.
If you're off campus, you may need IU's VPN to access github.iu.edu.

---

## Tool Philosophy

- **Advisory, not grading.** The tool recommends point values; the TA assigns
  the final score.
- **Report what you can't check.** Criteria without automated checks are
  explicitly listed — never silently skipped.
- **Evidence-cited.** Every finding includes the API data that supports it.
- **Deterministic.** All checks are API queries and pattern matching. No
  AI/LLM inference anywhere. Where judgment is needed (e.g., "is this comment
  well-written?"), the tool flags it for the TA.
- **FERPA-clean.** No student data leaves the TA's laptop. All API calls go to
  github.iu.edu using the TA's own credentials. No cloud services involved.