---
title: "ICEX Submission Checker — Specification"
version: 1.0.0
date: 2026-08-30
author: Mnemo (design), Kurt Seiffert (requirements)
status: locked
related_project: "mnemo/tools/icex_checker"
tags: [spec, c291, icex, grading, ta-tool]
changelog:
  - version: 0.1.0
    date: 2026-08-30
    status: draft
    notes: "Initial spec drafted from ICEX01-FA26-C291 rubric and Canvas submission format"
  - version: 1.0.0
    date: 2026-08-30
    status: locked
    notes: "Resolved three open questions: commit author dates (not repo creation) for repo_history; partial credit for close-match repo names; mechanical-only diff_content_check with TA name verification"
---

# ICEX Submission Checker — Specification

## Purpose

A cross-platform Python CLI tool for teaching assistants (TAs) that performs
an automated preliminary compliance assessment of C291 ICEX assignment
submissions. The tool reads a Canvas-downloaded submission file (HTML
redirect), extracts the pull request URL, queries the GitHub Enterprise API
to verify rubric criteria, and produces a structured report for the TA. The
tool does **not** grade — it surfaces evidence and flags discrepancies for
the TA to review and confirm. The TA makes all grading decisions and writes
all student-facing feedback.

Designed to serve as a template for most C291 ICEX assignments: the rubric
and evidence checks are externalized as a YAML file, so new ICEX assignments
can be assessed by providing a new rubric definition without modifying the
tool's code. The tool's plumbing — submission parsing, GitHub API client,
report formatting, auth, batch mode — stays constant across ICEX; only the
rubric YAML and the checker types it references change per assignment.

**"Do not send an AI to do a computer's job."** All checks are deterministic
API queries and pattern matching. No LLM inference anywhere in the tool.
Where a rubric criterion requires judgment (e.g., "well-written comment"),
the tool checks what it can mechanically (presence, length) and flags the
rest as `needs-review` for the TA. New checker types may be added as future
ICEX require different evidence gathering, but the rubric-to-checker binding
remains data-driven.

## Design Principles

1. **Advisory, not grading.** The tool reports what it checked, what passed,
   what failed, and what it could not check. The TA confirms and refines.
2. **Report what you can't check.** Criteria without an automated checker are
   explicitly listed as "TA review required" — never silently skipped.
3. **Evidence-cited.** Every finding includes the API response data or diff
   excerpt that supports it, so the TA can verify without re-querying.
4. **FERPA-clean.** No student data leaves the TA's laptop. All API calls go
   to github.iu.edu using the TA's own credentials. No cloud LLM involved.
5. **Open-source compatible.** No dependency on Lore Forge, Obsidian,
   1Password, or any personal workflow infrastructure. Standard library +
   `requests` + `PyYAML` only.
6. **Cross-platform.** Runs on macOS, Windows, and Linux with Python 3.9+.
7. **Consistency over speed.** The primary value is consistent evidence
   presentation across TAs, not faster grading.

## Functional Requirements

### FR-1: Read submission file

The tool SHALL accept a path to a Canvas submission HTML file. The file is an
HTML document containing a meta refresh redirect and a visible link to the
student's pull request URL on github.iu.edu.

The tool SHALL parse the HTML to extract the PR URL from both:
- The `<meta http-equiv="Refresh" content="0; url=...">` tag
- The `<a href="...">` link in the body

If both are present and agree, use that URL. If they disagree, flag the
discrepancy and use the meta refresh URL (more reliable for Canvas exports).
If neither is found, report "no PR URL found in submission file" and exit
with code 1.

### FR-2: Validate PR URL format

The tool SHALL validate that the extracted URL:
- Points to `github.iu.edu` (configurable via `--github-host`)
- Matches the PR URL pattern: `github.iu.edu/{owner}/{repo}/pull/{number}`
- Has an HTTPS scheme

If the URL is invalid (wrong host, not a PR URL, malformed), the tool SHALL
report the specific validation failure and exit with code 1.

### FR-3: Query GitHub Enterprise API

The tool SHALL authenticate to the GitHub Enterprise API at
`https://{github_host}/api/v3` using a personal access token provided via:
1. `--token` CLI argument, or
2. `GH_TOKEN` environment variable, or
3. `GITHUB_ENTERPRISE_TOKEN` environment variable

The tool SHALL NOT accept tokens in the rubric file or any file that might be
committed to a repository.

If no token is found, the tool SHALL print a helpful message explaining how to
create a token and exit with code 1.

The tool SHALL use the `gh` CLI as an alternative authentication source: if
no token is provided via CLI or env vars, the tool SHALL attempt to run
`gh auth token` to obtain a token. This allows TAs who already have `gh`
configured to use the tool without additional setup.

### FR-4: Fetch PR data

Using the authenticated API client, the tool SHALL fetch:
- PR metadata (title, body/description, state, created_at, updated_at, head
  branch, base branch, number of commits)
- PR diff (the unified diff of all changes)
- PR comments (review comments and issue comments)
- Repository info (repo name, owner, creation date, default branch)

If the PR is not accessible (404, 403, private repo without access), the tool
SHALL report the HTTP status and error message, provide the PR URL for manual
review, and exit with code 1.

### FR-5: Load rubric definition

The tool SHALL load a rubric definition from a YAML file specified via
`--rubric`. If no `--rubric` is provided, the tool SHALL look for a default
rubric file matching the assignment identifier (see FR-6) in the same
directory as the tool, then in `./rubrics/`.

The YAML rubric format is defined in the Rubric Format section below.

If the rubric file cannot be found or parsed, the tool SHALL report the error
and exit with code 1.

### FR-6: Identify assignment from submission

The tool SHALL extract the assignment identifier from the submission file's
`<title>` tag, which follows the pattern `WeekNN - ICEXNN: Student Name`.
The tool SHALL parse:
- Week number
- ICEX identifier (e.g., `ICEX01`)
- Student name (for display in the report only)

If the title does not match the expected pattern, the tool SHALL warn the TA
but continue processing using the PR URL and rubric provided.

### FR-7: Run rubric checks

For each criterion in the rubric, the tool SHALL run the associated checker
(if one exists for that criterion type) and record:
- Criterion name
- Maximum points
- Assessment: `pass`, `partial`, `fail`, or `needs-review`
- Evidence: specific data from the API response supporting the assessment
- Points recommendation: full, partial (with specific amount), or zero
- Notes: explanation of what was checked and what the TA should verify

Criteria without an automated checker SHALL be reported as
`assessment: needs-review` with a note explaining what the TA should
manually check and the PR URL for direct access.

The checker types and their behavior are defined in the Checker Types
section below.

### FR-8: Generate report

The tool SHALL output a structured report to stdout in human-readable
formatted text (not JSON). The report SHALL include:

1. **Header:** Assignment name, student name, PR URL, assessment timestamp
2. **Summary:** Total points possible, recommended points, criteria counts
   (passed / partial / failed / needs-review)
3. **Per-criterion detail:** For each rubric criterion, the assessment,
   evidence, and TA notes
4. **PR details:** PR title, description (truncated), branch, commit count,
   state (open/merged/closed)
5. **TA action items:** Explicit list of what the TA needs to verify
   manually, with the PR URL repeated for convenience
6. **Raw data path:** If `--save-json` is used, the path to the full JSON
   output for archival

The report SHALL clearly distinguish between automated findings and items
requiring TA judgment.

### FR-9: Save machine-readable output (optional)

When `--save-json` is provided, the tool SHALL write a JSON file containing
the full assessment (all criteria, evidence, PR metadata, and tool version)
to the specified path. This is for archival and batch-processing use.

### FR-10: Batch mode (optional)

When `--batch` is provided with a directory path, the tool SHALL process all
`.html` submission files in that directory, producing one report per file to
stdout (separated by a divider) and optionally saving individual JSON files
to a `--output-dir`. A summary table at the end lists all submissions with
their recommended scores.

## External Behavior

### Input

- **Submission file:** HTML file from Canvas submission download. Contains a
  meta refresh redirect to a github.iu.edu PR URL and a visible link with
  the same URL. The `<title>` tag contains `WeekNN - ICEXNN: Student Name`.
- **Rubric file:** YAML file defining the rubric criteria, points, and
  checker types (see Rubric Format section).

### Output

- **Default:** Human-readable text report to stdout
- **With `--save-json`:** JSON file to specified path
- **With `--batch` + `--output-dir`:** One JSON file per submission plus a
  summary JSON

### Invocation

```bash
# Single submission
python3 icex_checker.py <submission.html> --rubric icex01.yaml [--token TOKEN]

# Batch mode
python3 icex_checker.py --batch <submissions_dir> --rubric icex01.yaml \
    --output-dir <output_dir> [--token TOKEN]

# With gh CLI auth (no token needed)
python3 icex_checker.py <submission.html> --rubric icex01.yaml
```

## Rubric Format (YAML)

The rubric is a YAML file with this structure:

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
    params:
      # Checks that the repo has commits prior to semester_start
      # Verifies repo was forked from upstream class repo

  - name: "Create Pull Request"
    points: 2
    checker: pr_exists_with_comment
    params:
      # PR must exist and have a description/comment
      # full: well-written comment (TA judges quality)
      # partial: PR exists but comment is empty or minimal
      min_comment_length: 10  # chars; below this = partial

  - name: "PR URL submitted to Canvas"
    points: 2
    checker: pr_url_valid
    params:
      # URL in submission file resolves to a real, accessible PR
      # in the student's own repo on github.iu.edu
      # full: lands on PR in student repo
      # partial: lands on student repo but not a PR, or is inaccessible

  - name: "Valid Student Repo Established"
    points: 2
    checker: valid_student_repo
    params:
      # Repo is on github.iu.edu
      # Repo name matches expected course pattern (e.g., fa26_c291)
      # Owner (GitHub username) is present in the URL path
      expected_repo_pattern: "fa26_c291"
      github_host: github.iu.edu

  - name: "Committed hello.c correct elements"
    points: 3
    checker: diff_content_check
    params:
      # PR diff must touch hello.c
      # Diff must show a modification to a printf statement
      # The word "World" should be replaced with the student's name
      # (The tool can check that printf was modified and "World" is
      #  no longer present in the changed lines; the TA confirms the
      #  replacement is the student's actual name)
      target_file: "hello.c"
      must_contain_modified: "printf"
      must_not_contain: "World"
```

### Criterion Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Human-readable criterion name (from the rubric) |
| `points` | yes | Maximum points for this criterion |
| `checker` | yes | Checker type name (see Checker Types) |
| `params` | no | Checker-specific parameters |

### Partial Credit Specification

Each checker may recommend partial credit. The rubric YAML defines the
partial credit thresholds in the `params` section. The tool reports the
recommended point value; the TA confirms or adjusts.

## Checker Types

### `repo_history`

Verifies that the student repository has commit history predating the
semester start date (indicating a fork/mirror from the class repo).

**Important:** Students create their repo fresh during Week 1 (step 34-42
of ICEX01 instructions) and push via `git push --mirror`, which preserves
all original commit author dates from the class repo. Therefore the
**repo creation date** will be during Week 1 (not before semester start),
but the **commit author dates** will predate the semester. The checker
must look at commit author dates, not the repo creation date.

**API calls:**
- `GET /repos/{owner}/{repo}` — repo metadata (for display in report)
- `GET /repos/{owner}/{repo}/commits` — commit history (first page,
  check `commit.author.date` on each commit)

**Assessment logic:**
- `pass`: Repo exists and has at least one commit with
  `commit.author.date` before `semester_start`
- `fail`: Repo exists but all commit author dates are after
  `semester_start`, or repo has zero commits
- `needs-review`: API call fails (private repo, 404, etc.)

**Evidence:** Repo creation date (for context), earliest commit author
date, total commit count.

### `pr_exists_with_comment`

Verifies that a pull request exists and has a description/comment.

**API calls:**
- `GET /repos/{owner}/{repo}/pulls/{number}` — PR metadata
- (PR body is included in the PR metadata response)

**Assessment logic:**
- `pass`: PR exists and body length >= `min_comment_length`
- `partial`: PR exists but body is empty or shorter than
  `min_comment_length`
- `fail`: PR does not exist (404)
- `needs-review`: PR exists and has a body >= `min_comment_length` — TA
  must judge if the comment is "well-written"

**Evidence:** PR number, PR title, PR body (truncated to 200 chars), body
length, PR state (open/merged/closed).

**Note:** The tool cannot assess comment *quality* — only presence and
length. The "well-written" judgment is always TA-reviewed.

### `pr_url_valid`

Verifies that the URL in the submission file resolves to a real, accessible
PR in the student's own repository.

**API calls:**
- `GET /repos/{owner}/{repo}/pulls/{number}` — verify PR exists

**Assessment logic:**
- `pass`: API returns 200 for the PR endpoint
- `partial`: URL points to the student's repo but not a valid PR (e.g.,
  404 on the PR number), or URL points to a different location
- `fail`: URL is completely inaccessible (404 on repo, network error)
- `needs-review`: URL resolves but points to a repo that doesn't match the
  student's identity (TA should verify ownership)

**Evidence:** HTTP status code, resolved URL, repo owner/repo from URL.

### `valid_student_repo`

Verifies that the repository meets the course naming and hosting
requirements.

**API calls:**
- `GET /repos/{owner}/{repo}` — repo metadata

**Assessment logic:**
- `pass`: Repo is on `github.iu.edu`, repo name matches
  `expected_repo_pattern`, and owner (GitHub username) is present in the
  URL path
- `partial`: Repo is on `github.iu.edu` but repo name doesn't match the
  expected pattern (TA should check if it's a valid variant)
- `fail`: Repo is not on `github.iu.edu` or doesn't exist
- `needs-review`: Repo exists but the owner doesn't appear to be a student
  (TA should verify)

**Evidence:** Repo full name (`owner/repo`), repo URL, creation date, owner
login.

### `diff_content_check`

Verifies that the PR diff contains expected changes to a specific file.

**API calls:**
- `GET /repos/{owner}/{repo}/pulls/{number}` — PR metadata (accept header
  for diff: `application/vnd.github.v3.diff`)

**Assessment logic:**
- `pass`: Target file is in the diff, contains `must_contain_modified`
  pattern in changed lines, and does NOT contain `must_not_contain` in
  changed lines
- `partial`: Target file is in the diff but content checks partially fail
  (e.g., printf modified but "World" still present)
- `fail`: Target file is not in the diff, or diff is empty
- `needs-review`: Content checks pass mechanically but TA must verify the
  replacement is the student's actual name (not a random word)

**Evidence:** List of files in diff, relevant diff hunks for the target
file (truncated to 500 chars), check results for each pattern.

**Note:** The tool deliberately does NOT attempt to extract the replacement
word and compare it to the student's name from the submission title. Name
parsing is fragile (Unicode, nicknames, middle names, transliteration)
and confirming the replacement is the student's actual name is the TA's
pedagogical judgment. The tool checks the mechanical requirements
(printf modified, "World" gone) and flags `needs-review` with the diff
excerpt so the TA can verify the name at a glance.

## Edge Cases and Failure Modes

### EF-1: Submission file not found or not HTML

The tool SHALL report "submission file not found" or "submission file does
not appear to be HTML" and exit with code 1.

### EF-2: No PR URL in submission file

The tool SHALL report "no PR URL found in submission file" and exit with
code 1. This handles submissions where the student pasted text instead of a
URL, or the Canvas export is malformed.

### EF-3: PR URL points to wrong host

The tool SHALL report "PR URL points to {host}, expected {github_host}" and
exit with code 1. This catches students who submitted a link to public
GitHub instead of github.iu.edu.

### EF-4: GitHub API authentication failure (401)

The tool SHALL report "authentication failed" with instructions for creating
a token and exit with code 1.

### EF-5: GitHub API rate limit (403)

The tool SHALL report "rate limited by GitHub API" with the reset time if
available and exit with code 1.

### EF-6: PR not accessible (404 or 403)

The tool SHALL report "PR not accessible" with the HTTP status, provide the
PR URL for manual TA review, and exit with code 1. This handles deleted
PRs, private repos the TA doesn't have access to, and wrong PR numbers.

### EF-7: Network error

The tool SHALL report "network error: {error details}" and exit with code 1.
This covers DNS failures, connection refused, timeout, and VPN-related
issues.

### EF-8: Rubric file not found or invalid YAML

The tool SHALL report "rubric file not found" or "rubric file is invalid
YAML: {parse error}" and exit with code 1.

### EF-9: Unknown checker type in rubric

The tool SHALL report "unknown checker type '{type}' for criterion '{name}'"
and mark that criterion as `needs-review`. The tool SHALL NOT exit with an
error — it continues processing other criteria. This allows rubrics to
reference checkers that haven't been implemented yet without breaking the
tool.

### EF-10: Empty batch directory

The tool SHALL report "no .html submission files found in {directory}" and
exit with code 0 (not an error — just nothing to do).

### EF-11: Some submissions fail in batch mode

The tool SHALL continue processing remaining submissions, collect failures,
and report a summary at the end with per-submission status. Exit code 0 if
all processed (even if some had assessment failures), exit code 2 if some
could not be processed at all (file not found, no URL, etc.).

## Success Criteria

1. **SC-1:** Given a valid submission HTML file with a real PR URL, the tool
   extracts the correct PR URL from the meta refresh tag.
2. **SC-2:** Given a PR URL, the tool authenticates to the GitHub Enterprise
   API and fetches PR metadata, diff, and repository info.
3. **SC-3:** Given the ICEX01 rubric YAML, the tool runs all five criteria
   and produces a report with per-criterion assessment and evidence.
4. **SC-4:** Criteria without automated checkers are reported as
   "needs-review" with TA guidance — never silently skipped.
5. **SC-5:** The report includes the PR URL for direct TA access.
6. **SC-6:** The tool correctly identifies partial credit cases (e.g., PR
   exists but comment is empty → partial for "Create Pull Request").
7. **SC-7:** The tool handles inaccessible PRs gracefully (reports the
   error, provides URL, exits cleanly).
8. **SC-8:** The tool runs on Python 3.9+ with only `requests` and
   `PyYAML` as external dependencies.
9. **SC-9:** Authentication works via `--token`, `GH_TOKEN` env var, or
   `gh auth token` fallback.
10. **SC-10:** In batch mode, the tool processes all `.html` files in a
    directory and produces a summary table.
11. **SC-11:** The rubric YAML is human-readable and modifiable without
    touching Python code.
12. **SC-12:** The tool does not print or log the API token value at any
    point.

## Script Interface Contract

### CLI

```
python3 icex_checker.py <submission.html> [--rubric FILE] [--token TOKEN]
    [--github-host HOST] [--save-json FILE] [--output-format text|json]
    [--batch DIR] [--output-dir DIR] [--verbose] [--version]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `<submission.html>` | (required) | Path to Canvas submission HTML file (positional, unless `--batch`) |
| `--rubric` | auto-detect | Path to rubric YAML file |
| `--token` | (env/gh) | GitHub Enterprise API token |
| `--github-host` | `github.iu.edu` | GitHub Enterprise host |
| `--save-json` | (none) | Save full assessment as JSON to this path |
| `--output-format` | `text` | Output format: `text` (human-readable) or `json` |
| `--batch` | (none) | Batch mode: process all .html files in this directory |
| `--output-dir` | (none) | Batch mode: write JSON files here (requires `--batch`) |
| `--verbose` | false | Include API response details in output |
| `--version` | false | Print version and exit |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — assessment completed (may include fail/partial findings) |
| 1 | Fatal error — could not process submission (file not found, no URL, auth failure, network error) |
| 2 | Partial failure — batch mode: some submissions could not be processed |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GH_TOKEN` | GitHub Enterprise API token (checked if `--token` not provided) |
| `GITHUB_ENTERPRISE_TOKEN` | Alternative env var for token |

### Authentication Resolution Order

1. `--token` CLI argument
2. `GH_TOKEN` environment variable
3. `GITHUB_ENTERPRISE_TOKEN` environment variable
4. `gh auth token` CLI command (if `gh` is installed and authenticated)

## Non-Goals

- **No grading.** The tool recommends point values; the TA assigns the
  final score in Canvas GradeBook.
- **No student-facing output.** The report is for the TA only. The TA
  writes all student feedback via PR comments.
- **No Canvas API integration.** FERPA prohibits AI tools from accessing
  Canvas. The TA enters scores manually.
- **No LLM inference.** All checks are deterministic API queries and
  pattern matching. No cloud or local model calls.
- **No student data storage.** The tool does not persist student data
  beyond the optional `--save-json` output, which the TA manages.
- **No automated PR commenting.** The TA writes all PR comments manually.
- **No support for SE1/P465 ICEX.** The tool is designed for C291's
  individual-submission model. SE1 uses team submissions with a different
  pipeline. Cross-course compatibility is a non-goal for v1.

## File Location

The tool SHALL live at `mnemo/tools/icex_checker/` with this structure:

```
tools/icex_checker/
  icex_checker.py          # Main CLI entry point
  checkers.py              # Checker implementations
  rubric.py                # Rubric YAML loader and validator
  report.py                # Report formatter (text and JSON)
  github_client.py         # GitHub Enterprise API client
  __init__.py
  rubrics/
    icex01_fa26.yaml       # ICEX01 rubric for FA26
  tests/
    test_submission_parser.py
    test_rubric_loader.py
    test_checkers.py
    test_report.py
    test_github_client.py
    fixtures/
      sample_submission.html
      icex01_rubric.yaml
```

## Dependencies

- Python 3.9+ (stdlib: `argparse`, `json`, `os`, `re`, `sys`, `html`,
  `datetime`, `pathlib`, `subprocess`, `dataclasses`)
- `requests` (HTTP client) — already in `requirements.txt`
- `PyYAML` (YAML parser) — **new dependency, must be added to
  `requirements.txt`**

No other external dependencies. The tool SHALL NOT use `beautifulsoup4` —
HTML parsing uses stdlib `html.parser` and regex for the meta refresh tag,
which is sufficient for the Canvas submission format.

## Build Handoff Notes

**Division of labor:**
- **Mnemo (course architecture agent, GLM 5.2)** owns the pedagogical
  design: rubric structure, checker semantics, report format, TA workflow
  alignment, and C291 assessment invariant compliance.
- **Zoidberg (default profile, GLM 5.3)** owns technical implementation:
  TDD build, cross-platform testing, API client correctness, error
  handling, and spec compliance verification.
- **Kurt Seiffert (instructor)** makes all final decisions on both sides.

**Build methodology:** TDD per the test-driven-development skill.
Spec-build-evaluate-loop is available but not required — this is a
deterministic tool (no LLM inference), so the independent-evaluator
pattern is less critical. Standard TDD with good test coverage is
sufficient. Tests should mock the GitHub API (using `unittest.mock` or
`responses` library) rather than hitting the real API.

**What Mnemo will review post-build:**
1. Report format serves the TA workflow (evidence is citable, TA action
   items are explicit, `needs-review` items are never silently skipped)
2. Checker semantics match the rubric intent (especially the
   commit-author-date logic for `repo_history` and the mechanical-only
   approach for `diff_content_check`)
3. The tool does not make pedagogical judgments (no quality assessment
   of PR comments, no name verification in hello.c)
4. Rubric YAML is human-readable and modifiable without code changes

**What Zoidberg should verify:**
1. All functional requirements (FR-1 through FR-10) implemented
2. All edge cases (EF-1 through EF-11) handled gracefully
3. All success criteria (SC-1 through SC-12) met
4. Cross-platform: runs on macOS, Windows, Linux with Python 3.9+
5. Only `requests` + `PyYAML` as external dependencies
6. No API token is ever printed or logged
7. Exit codes match the Script Interface Contract