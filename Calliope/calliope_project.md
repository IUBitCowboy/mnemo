# PROJECT CONVENTIONS (C291)

Apply in addition to your base persona and Mnemo skills.

## Project Format for C291

- **Problem Statement** — the "quest" description, framed in journey language
- **Skeleton Code** (provided) — starter code to reduce cognitive load, per
  the Cognitive Load Management skill
- **Makefile** (provided) — build infrastructure so students focus on logic,
  not build configuration
- **"Hero's Debugging Log"** — student-maintained record of the debugging
  journey, using the Theory/Experiment table format from the ICEX conventions

## Debugging Log Requirement

Every programming assignment requires `debug_log.md` containing:

1. A log of all significant defects resolved in the program
2. At least one detailed example demonstrating the scientific method of
   debugging (Theory → Experiment → Result → Modified Theory)
3. A `debug_log.md` without a detailed example is considered incomplete and
   equivalent to nothing (zero credit for the log portion)

This is the C291-specific implementation of the Metacognitive Reflection and
Error Diagnosis skills — the debugging log forces students to reflect on
their debugging process, not just report the result.

## Development Environment

- All code must compile and run on the IU Silo clusters using `gcc`
- Repository: `studentID-SP26-C291` with `seiffert-SP26-C291-class` as upstream
- Each assignment on a separate development branch (`wk01`, `wk02`, etc.)
- Submission: Pull Request to main, instructor/TA as reviewer
