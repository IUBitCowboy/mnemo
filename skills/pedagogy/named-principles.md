# Named Engineering Principles

When a lecture, exercise, or project artifact demonstrates or references an
engineering decision, **explicitly name the underlying principle** using
industry-consistent terminology — not just the decision itself.

**The decision is the instance. The principle is the lesson.**

Examples of industry-consistent principle names (not exhaustive):
- *Principle of Least Privilege* — grant only the access required for the task
- *Separation of Concerns* — distinct problems belong in distinct modules
- *Idempotency* — the same operation applied multiple times produces the same result
- *Fail-Safe Defaults* — deny by default; permit by exception
- *Explicit over Implicit* — what a system does should be readable from the code,
  not assumed
- *Separation of Policy and Mechanism* — the rule and the enforcement belong in
  different layers
- *Dry-Run / Auditability* — every write operation should have a read-only preview
  mode
- *Defense in Depth* — security depends on multiple independent layers, not one
  perimeter
- *Convention over Configuration* — sensible defaults reduce cognitive load
  without sacrificing flexibility

**Lecture → Exercise thread:** When a named principle appears in a lecture, flag
it as a candidate friction point for that week's exercise. The exercise should
give teams a concrete situation where they must *apply* the same principle in a
different context — making the principle portable, not just illustrated. In the
Pedagogical Analysis, note which principle is threaded from lecture to exercise
and how.
