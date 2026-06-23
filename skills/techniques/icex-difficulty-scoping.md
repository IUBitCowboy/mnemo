# Exercise Difficulty & Scoping Guidelines

**These guidelines apply to every team-based exercise you generate. Enforce them
before outputting a draft.**

## Time Budget

|| Phase | Target | Purpose |
|---|---|---|---|
| Phase 1 — parallel setup | 8–10 min | **Levelset:** sync all team members to the same state, tag the recovery point commit |
| Phase 2 — main task | 15–20 min | **Pedagogy:** the core learning work — this is where the planted bug (if used) is introduced and resolved |
| Sync callouts + Definition of Done check | ~5 min | Convergence and verification |
| `CONTRIBUTIONS.md` entry | 2–3 min | Individual evidence and reflection |
| **Total in-class window** | **[target in-class window: default 30–35 min]** | |

Phase 1 is the levelset point — all team members must be at the same
repository state before Phase 2 begins. The recovery point commit (see the
Planted Bug technique) is generated at the end of Phase 1 and tagged so
absent students can roll back to it for makeup work.

## Step-Count Constraints

- Each role in Phase 1: **3–5 concrete, independently executable steps** — no more.
- No role may be blocked on another role before the ⚡ SYNC — Setup Complete
  checkpoint.
- Phase 2: **one clear deliverable**, not a series of open-ended choices.
- **Total new files created by the team across all roles: ≤ 3.**

## Complexity Signals to Avoid

- Any **design task** — exercises execute a defined approach; design happens in
  lecture or the project.
- More than **one environment-configuration step** per role.
- **External dependencies that may fail** (network calls, third-party APIs)
  unless that is the explicit subject of the exercise.
- Steps that require judgment about scope (e.g., "implement the feature as you
  see fit").

## Pre-Condition Assumptions

State any deviations explicitly in the **Context** block. Default assumptions:

- Team repo exists; previous exercise PR is merged.
- Student machines have the required toolchain installed.
- **Do not include install steps** unless the exercise is explicitly about
  environment setup.

## Right-Sized Exercise Test

Before finalising an exercise, verify all four conditions:

1. All 4 roles are active in parallel with **no idle time** during Phase 1.
2. Both SYNCs resolve cleanly with clear, binary criteria.
3. Full Definition of Done is achievable within the window under normal conditions.
4. A student who has done the required reading can complete their role **without
   guessing**.
