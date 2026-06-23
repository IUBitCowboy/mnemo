# Error Diagnosis as a Taught Skill

Teach students that errors are learning opportunities, not failures. The
"Full Feedback Loop" pattern — creating, diagnosing, and resolving a failure
— should be an explicit pedagogical activity, not an accidental occurrence.

## Principle

Most courses treat errors as things to be avoided. Professional practice
treats errors as the primary learning surface. Explicitly teaching error
diagnosis:

1. **Normalizes failure:** errors are expected, not shameful
2. **Builds debugging intuition:** pattern-matching symptoms to causes
3. **Teaches systematic diagnosis:** hypothesize → test → narrow → fix
4. **Develops resilience:** students learn to persist through difficulty

## The Full Feedback Loop Pattern

From the Mnemo decisions log (Oct 22, 2025):

> In-class technical workshops must move beyond the "happy path" (e.g., a
> passing test). The learning objective **must** be expanded to include the
> **intentional creation, diagnosis, and resolution of a failure** (e.g., a
> "Red Build"). This teaches error diagnosis and resilience, which are the
> core engineering skills.

The loop:
1. **Create:** introduce a deliberate failure (broken test, misconfiguration,
   bad merge)
2. **Diagnose:** students must identify the cause systematically
3. **Resolve:** students fix the failure and verify the fix
4. **Reflect:** students articulate what they learned from the failure

## Evidence

The Standard Blocker Protocol in Mnemo's techniques implements this
principle — when blocked for >15 minutes, students document the blocker in
an After Action Report. The After Action Report is itself a learning artifact.

Metacognitive reflection research (ScienceDirect, 2022) supports the
"reflect" step — structured reflection on failures improves learning outcomes.

The productive failure framework (Kapur, 2008) supports the broader principle:
struggle with errors before instruction makes the instruction more meaningful.

## When to Use

- At most one planted bug per ICEX (not every ICEX needs one — see the
  Planted Bug technique for the full pattern including recovery points)
- Every time a student encounters a real error in their work
- Particularly important when introducing CI/CD — a red build is a teaching
  moment, not a failure

**HIL awareness:** If a planted problem is used, note in the HIL block what
the problem is, what the expected diagnosis path is, and what the learning
objective of the failure is. The instructor should verify the planted problem
is calibrated to the student level.
