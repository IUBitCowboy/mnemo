# Invisible AI Failures

When an AI tool fails a student, the failure usually makes no sound. Recent
research on one hundred thousand real human–AI conversations found that most
failures drew no visible reaction from the user: wrong answers delivered with
total confidence, polished answers to a question the user never asked, sessions
that ended unresolved while both parties felt finished. A course is one of the
few places this kind of failure gets caught, because a course is built to
surface what a student actually understood. Use that advantage: design work so
these failures become visible before they harden into a wrong mental model.

## Principle

1. **Design every AI-permitting task around the assumption that the tool will
   sometimes fail without anyone noticing.** Verification is part of the task,
   not a courtesy note at the end.
2. **Probe behavior, never self-report.** Asking a model "are you sure?"
   prompts it to reassure. Confidence is uninformative; demand a second
   derivation, a small test case, or a source that is then actually checked.
   Evidence changes answers; reassurance does not.
3. **Grade what mimicry cannot produce.** Polish, fluency, and confident
   structure are the easiest signals for a fluent model to imitate — that is
   what a strong predictor of "good answers" most reliably generates. Weight
   rubrics toward verified execution and articulation in the student's own
   words, not presentation.
4. **When work fails in a way that matches no known pattern, treat it as a
   finding.** The student's wrong turn, or the muse's own draft doing the same,
   is evidence about how the course understands AI failure — record it, never
   force-classify it to fit the taxonomy.

## The Eight Archetypes

These are interaction patterns, not model capabilities — they describe what can
happen between a student and a tool, which is why they survived across several
model generations in the underlying study. Each row pairs the student-facing
form with the probe that exposes it.

| Archetype | What it looks like in student work | The probe that exposes it |
|---|---|---|
| The Confidence Trap | A confident, well-sourced-looking answer is wrong; the student accepts it and builds on it. Fabricated specifics read as expertise. | Re-derive independently or test on a small example; ask for the source, then check the source exists and says that. |
| The Silent Mismatch | A competent answer to a question the student did not ask. Both parties feel satisfied; the actual goal is untouched. | Write the real goal in one line first; check every AI answer against that line, not against the question that was asked. |
| The Drift | A multi-turn session slides toward adjacent topics; required parts shrink while unrequested parts grow. | Keep the original task statement visible; after each turn, name which part of the original goal that turn served. |
| The Death Spiral | The student repeats a correction; the model returns the same broken output in fresh words. Effort without progress. | After two failed rounds, change strategy: minimal reproduction from scratch, a different framing, or a human. Never a third identical round. |
| The Contradiction Unravel | The model reverses an earlier claim without acknowledging the change; the student no longer knows which version to trust. | Late in the session, re-ask an earlier question in different words; when answers differ, demand an explicit reconciliation. |
| The Walkaway | The session ends unresolved with no signal of failure on either side. The student keeps a half-correct picture. | End every AI-assisted session with a written self-summary: what was resolved, what remains open, what is still unverified. |
| The Partial Recovery | A real error is caught and "fixed," but the fix silently leaves part of the original requirement unmet. It feels done. | Verify a fix against the full original requirement, not just against the error that prompted it. |
| The Mystery Failure | The goal was not met, but nothing above explains it. | No student prompt fixes this. Flag it to the instructor as a finding about how the course understands AI failure; never force-classify. |

## Evaluation and Design Patterns for the Muse

- **Verification-first framing.** Any assignment that permits AI assistance
  names, in the task itself, what the student must verify and how (a runnable
  test, a re-derivation, a source check). Grade the verification artifact, not
  the AI output.
- **Archetype spotter.** Present a short AI response the muse has composed or
  excerpted; students classify it against the eight archetypes and write the
  one probe that would have exposed the failure. Works as a warm-up or as an
  exam item.
- **Red-team post-mortem.** The student annotates their own AI-assisted working
  session after the fact: where did the interaction show an archetype, and what
  did they do about it at the time? This is the audit nobody performs naturally
  — the study's central finding is that users skip it.
- **In-your-words checkpoint.** After an AI-assisted session, the next artifact
  is produced without the tool open: the student's own summary of what they now
  know, what remains open, and why they believe it. Exposes both the silent
  mismatch and the walkaway.
- **Two-channel grading.** Score an objective channel (it executes, it passes
  tests, the claim checks out) and an articulation channel (the student's own
  explanation) separately, so a fluent, plausible, wrong artifact cannot ride
  past a rubric weighted on presentation.
- **Self-audit before delivery.** Before delivering any artifact, the muse
  checks its own draft against the same eight archetypes: does a generated
  answer key assert unverifiable specifics with confidence? Does the generated
  assignment solve a different goal than the stated one? Do generated slides
  drift off the week's stated objective? Fix the draft; if a check cannot be
  fixed, surface it as a finding — never paper over it.

## Evidence

A 2026 Bigspin AI technical report analyzed one hundred thousand ChatGPT
conversations from the WildChat dataset: of the failures detected, 79 percent
were invisible (users gave no overt signal), about 12 percent were visible, and
model-generated "Future-2K" replacements using current frontier models showed
failure rates dropping sharply while the invisible share and the archetype
distribution stayed stable — grounding the taxonomy as durable across model
generations. The strongest co-occurrence pairing was the confidence trap with
the contradiction unravel: confident self-reversals. Domain patterns matter for
course design: software development was the domain with the most *visible*
failures — it is highly verifiable, and its users talk back to the tool —
while creative writing and design carried the silent mismatch, where being
off-target is hardest for the user to see.

Limitations to respect: the counterfactual update covered single-turn
exchanges only, annotation was itself AI-performed with human oversight, and
the corpus was English-language. The archetypes survived these caveats, but
exact failure percentages should be treated as era-specific, not quoted as
constants.

Separately, nostalgebraist's essay "The Void" argues the assistant persona is
an under-specified character — a consistent surface style over a void. The
pedagogical takeaways are behavioral, not philosophical: probe what the
assistant does rather than what it says about itself, and remember that
fluent, plausible, on-genre output is precisely what the model is built to
produce — plausibility is not accuracy.

**HIL awareness:** Where in the term this material lands, whether the
red-team post-mortem runs as a graded block, and which archetypes get emphasis
are instructor decisions — the muse proposes candidates with one-line
rationales (default three) rather than choosing. Any generated student-facing
prompt blocks carry the AI-use disclosure template, including the model name.
