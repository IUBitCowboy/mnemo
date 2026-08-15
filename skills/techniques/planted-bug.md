# Planted Bug

A technique for embedding error diagnosis into in-class exercises. The planted
bug serves double duty: it teaches debugging as a distinct skill, and it
creates a recovery point for students who miss the in-class session.

## Pattern

1. **Setup phase:** The exercise has a setup and configuration step including
   scaffolding code or configuration files. Students generate a commit at this
   point to sync across team member repos. This commit is the **recovery point**.
2. **Plant the bug:** After the recovery point, introduce at most one deliberate
   bug into the exercise (a broken test, a misconfiguration, a logic error).
   The bug should be calibrated to the exercise's learning objective — not a
   trivial typo, not an impossible puzzle.
3. **Diagnose and resolve:** The team works together to identify, diagnose, and
   fix the bug as part of the exercise.
4. **Reflect:** The CONTRIBUTIONS.md entry or an engineering log reflection
   asks students to articulate what the bug was, how they found it, and what
   they learned.

## Recovery Point and Makeup Workflow

The recovery point commit (before the bug is introduced) enables a structured
makeup process for absent students:

1. The absent student rolls their working repo back to the recovery point.
2. The student implements their own solution for the planted bug on a personal
   bug-fix branch.
3. The student opens a PR to merge their bug-fix branch back to the team's
   exercise branch. Team TA and instructor are reviewers.
4. The PR is always **closed without merging** — the team already has the fix.
   The PR exists to demonstrate the student's individual work.
5. The TA or instructor reviews the PR when evaluating the makeup write-up in
   the student's engineering log reflection.

This process ensures a makeup student engages with the team integration and
core lesson of the exercise, not just the surface task.

## When to Use

- At most one planted bug per ICEX. Not every ICEX needs one.
- Always tag the recovery point commit explicitly in the exercise instructions
  so absent students can find it.
- Particularly valuable for MoJ ICEXs where regular cadence is critical —
  backlog of missed exercises overwhelms pedagogical value.

## When Not to Use

- ICEXs focused on pure exploration or reading (no setup commit to recover to)
- ICEXs where the setup phase is trivial (the recovery point adds no value)
- ICEXs where a planted bug would distract from the primary learning objective

## Relationship to Other Skills

- **Error Diagnosis as a Taught Skill:** The planted bug is the primary
  implementation of the error diagnosis pedagogy.
- **Debugging & Fault Localization:** (Clio-specific analysis dimension) The
  planted bug is what this dimension checks for.
- **Productive Failure Design:** The bug creates a controlled failure that
  students must work through — a productive struggle, not an overwhelming one.

**HIL awareness:** If a planted bug is used, note in the HIL block: what the
bug is, what the expected diagnosis path is, what the learning objective of
the failure is, and the recovery point commit identifier.
