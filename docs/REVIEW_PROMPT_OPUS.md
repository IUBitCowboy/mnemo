# Steelman Review Prompt for Opus

> Copy everything below the line into Claude Code (or a direct Claude/Opus session).
> Make sure you're in the mnemo repo root so Claude Code can read the file.

---

## Review Task

Read the file `mnemo/docs/SUBMISSION_PIPELINE_DESIGN.md` in this repository.
It is a design spec for a batch processing pipeline that assesses student
GitHub PR submissions using local LLM models for FERPA-protected work and a
cloud model for aggregation of sanitized data.

The pipeline has four phases:
- Phase 1: Per-PR assessment (local models, parallelized) — code analysis,
  team providance tracing, PII sanitization, verification
- Phase 2: Cloud aggregation (single call) — cluster issues into a corrective
  matrix (sanitized input only)
- Instructor review gate — mandatory matrix approval before proceeding
- Phase 3: Per-PR TA guides (local models, parallelized) — map matrix to
  individual students
- Phase 4: Assembly (script only) — produce triage report and shareable matrix

## Context

This is for a university course at Indiana University. The instructor (Kurt
Seiffert) teaches software engineering (SE1/P465) with team-based assignments
using GitHub PRs. The pipeline must comply with FERPA (student data privacy
law). The instructor's #1 course review complaint is time to return grades.
TA time is the bottleneck.

Key constraints:
- No student PII may reach a cloud model
- Local models run on a Mac Studio M4 Max 128GB
- TAs and instructor make all grading decisions — the pipeline produces
  guidance, not grades
- The tool must be open-source portable (no dependency on 1Password or
  specific cloud providers)

## What I Need From You

Do NOT just review for clarity or formatting. I need a rigorous, skeptical
critique. Specifically:

### 1. FERPA Exposure Analysis

Walk through every data flow in the pipeline. Identify every point where
student PII could leak. Consider:
- What counts as PII under FERPA beyond names and emails? (student IDs,
  GitHub usernames, file paths, commit metadata, code content that reveals
  identity)
- Can the sanitization pass (Pass 2) be trusted to catch everything the regex
  pre-filter misses? What failure modes exist?
- Is the verification diff sufficient? What would a false "clean" look like?
- Are there indirect PII leaks — e.g., a unique coding style or error pattern
  that re-identifies a student even after names are stripped?
- Does the cloud aggregation phase have any exposure even with sanitized
  input? Could an issue description in the matrix inadvertently identify a
  student?

### 2. Architectural Honesty

The designer (an AI agent) called this design "elegant." Pressure-test that
claim:
- Is this actually elegant, or is it over-engineered for a 50-student course?
- Are there simpler architectures that achieve the same FERPA guarantees with
  less complexity?
- Is the three-pass local + one-pass cloud architecture justified, or could
  fewer passes work?
- Is the audit trail enforcement real security or security theater?
- Is the pluggable assignment type architecture premature abstraction for v1?

### 3. Feasibility and Failure Modes

- Will local 14-27B models actually produce quality code assessments? What's
  the realistic quality bar?
- Is the parallelization plan realistic on a 128GB Mac Studio? What are the
  actual memory and throughput constraints?
- What happens when Pass 1 produces a bad assessment? Does the pipeline have
  graceful degradation, or does one bad assessment poison the matrix?
- What happens when the cloud model clusters issues poorly? The instructor
  review gate catches gross errors, but what about subtle mis-clustering?
- What's the operational burden? Is this easier than just having TAs read
  the submissions?

### 4. What's Missing

What did the designer not consider? What scenarios are unhandled? What
edge cases in real university grading workflows would break this pipeline?

### 5. Verdict

Give a direct, honest assessment:
- Is this design worth building?
- What would you change before building v1?
- What is the single biggest risk?

Do not soften your critique. The designer is an AI agent; your candor will
not hurt its feelings. The instructor needs to know if this is a good
investment of his time before classes start in 5 days.