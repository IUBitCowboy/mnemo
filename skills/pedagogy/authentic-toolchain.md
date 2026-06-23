# Authentic Toolchain Exposure

Students should use the same tools that professionals use in industry — not
educational substitutes, simplified versions, or toy environments. The
cognitive cost of learning a tool is justified when the tool is the one
they'll use in practice; it's wasted when the educational tool is discarded
upon graduation.

## Principle

**Use real Git, real Docker, real CI/CD, real testing frameworks.** Not
educational Git alternatives, not sandboxed environments that hide the
complexity. The complexity IS the lesson.

## Evidence

Authentic assessment in computing education (Frontiers in Education, 2021)
emphasizes that assessment should mirror professional practice. ABET
accreditation criteria require students to demonstrate "an ability to apply
design and development principles in the construction of software systems."

The cognitive apprenticeship model (Collins, Brown, Holum, 1989) supports
using authentic tools because the "master's environment" is part of the
apprenticeship — students learn not just the skill but the *context* in which
the skill is practiced.

## Risks

- **Setup friction:** real tools have real setup costs. Guard with pre-class
  setup assignments (graded prerequisite pattern from the decisions log) and
  starter kits that handle boilerplate.
- **Version drift:** professional tools update. Guard by pinning versions in
  requirements.txt and updating at semester boundaries, not mid-semester.
- **Overwhelming complexity:** some professional tools have more features than
  students need. Guard by introducing only the subset needed for the current
  exercise, not the full tool manual.

## When to Use

- Always. This is a baseline principle, not a situational technique.
- The question is not "should we use real tools?" but "which real tools and
  in what order?"

**HIL awareness:** Note in the HIL block which professional tools are
introduced and whether any setup prerequisites are assumed. If an exercise
assumes a toolchain that wasn't set up in a prior exercise, flag it.
