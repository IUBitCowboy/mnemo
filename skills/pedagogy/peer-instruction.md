# Peer Instruction

Students learn by teaching each other. Team-based exercises where students
hold distinct roles create structured peer instruction: each role requires
understanding a different aspect of the problem, and team members must
explain their work to each other during sync points.

## Evidence

Peer-Led Team Learning (PLTL) in computer science (ResearchGate) showed
"improved student engagement and retention of under-achiever students in
introductory computer courses" and was "as effective in promoting achievement
and retention in computer science education" as in math and science.

Pair programming research (PMC, 2023) confirms that "the driver and the
navigator work together to analyze problems, make proposals to solve the
issues and test the solution design. They are not waiting for instructors
to impart knowledge; instead, they will actively explore possible solutions
and construct meaningful knowledge through peer communications."

The meta-analysis on gamification in higher education (PMC, 2023) found that
"users with a higher education level were found to achieve better learning
outcomes" from collaborative, structured approaches.

## The Pedagogy Behind the Technique

The Parallel Processing Kit (techniques/parallel-processing-kit.md) defines
the *workflow structure* — 4 roles, sync callouts, role rotation. Peer
Instruction is the *pedagogical principle* that makes that structure work:

- **Repo Admin** learns repository hygiene by *doing* it and *explaining* it
  to teammates during sync
- **Process Lead** learns coordination by *running* the sync callouts and
  *documenting* the team's process
- **Dev Lead** learns implementation by *writing* code and *defending* choices
  during code review
- **QA Sentinel** learns quality by *reviewing* others' code and *articulating*
  what they find

Each role is both a task and a teaching opportunity. The sync callouts are
where peer instruction happens — each member explains their piece to the
others.

## Role Rotation as Fading

The policy "no student may hold the same role more than two consecutive weeks"
(from Parallel Processing Kit) is not just about fairness — it's a fading
mechanism. Students who have mastered one role move to a new one, preventing
over-specialization and forcing each student to learn all aspects of the
workflow.

## When to Use

- Any team-based exercise with 3+ members
- Particularly effective when roles require different knowledge (so peers
  must teach each other to converge at sync points)
- Less effective when all roles require the same knowledge (no teaching
  opportunity)

## Failure Modes and Guards

### Pilot/Passenger

One member dominates the entire process — makes all decisions, does all
non-trivial work, and other members become passive riders. This is the most
common team dysfunction in timed exercises.

**Guards:**
- **Multiple roles with rotation:** The 4-role Parallel Processing Kit
  structurally prevents one person from doing everything — each role has
  concurrent work that only that role can do. Mandatory weekly rotation
  prevents the same student from always driving.
- **Decision defense:** At each sync point, the member whose role is most
  relevant to the decision must articulate *why* their approach is correct.
  This forces active engagement, not passive approval.
- **Dissent vote:** Before the team commits to a decision, require one
  member to argue *against* the team's chosen approach. Rotate the dissenter
  role so it doesn't fall to the same person. This prevents groupthink and
  ensures silent members have a structured opportunity to surface concerns.

### Decision Deadlock

Teams with poor communication stall — nobody takes initiative, or two members
disagree and the team can't converge. In a timed exercise, deadlock burns
the clock and produces no artifact.

**Guards:**
- **Process Lead as timer:** The Process Lead is responsible for time-boxing
  decisions. If a discussion exceeds its sync window, the Process Lead calls
  for a decision using a defined protocol: majority vote, with the Dev Lead
  as tiebreaker on technical questions.
- **Structured sync callouts:** The sync points force convergence — each
  member states their status, and the team must agree before proceeding.
  Silence is not consent; the Process Lead must explicitly ask each member.
- **Standard Blocker Protocol fallback:** If a team is truly deadlocked on a technical issue, the
  Standard Blocker Protocol gives them a productive alternative — document
  the blocker, pivot to a support task, and submit an After Action Report. Deadlock becomes
  a learning artifact rather than wasted time.

## References

- "Serious fun: peer-led team learning in CS." (ResearchGate)
- "Adopting distributed pair programming as an effective team learning
  activity: a systematic review." (PMC, 2023)
- Preston, D. (2005). "Pair programming as a model of collaborative learning."
  *Journal of Computing Sciences in Colleges*.

**HIL awareness:** The peer instruction design (role definitions, sync
questions) should be verified in the HIL block to ensure each role has a
genuine teaching opportunity. If one role is trivially easy, the peer
instruction value is lost.
