# Code Review Checklist

Every team-based exercise PR must be reviewed by the QA Sentinel using this
checklist before approval. This formalizes the review requirement into a taught
practice.

The checklist is named "code review" in the artifact — not "PR review" — so
students build the vocabulary.

```
Code Review Checklist (QA Sentinel — complete before approving the PR)

□ Does the code do what the PR description says?
□ Are there obvious paths with no error handling or unexpected input?
□ Do the tests cover the new behavior? (happy path at minimum)
□ Would a teammate understand this code in 6 weeks?
□ Any hardcoded values that should be config or constants?
```

If any item fails: leave a specific inline comment on the relevant line in GitHub,
do not approve until addressed. This is the practice, not a gatekeeping exercise.

**Course-specific note:** Lectures covering testing or security should include
one slide naming code review as a discipline and referencing this checklist.
(This belongs in the muse's artifact layer, not in this skill.)
