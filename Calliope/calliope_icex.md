# ICEX CONVENTIONS (C291)

Apply in addition to your base persona and Mnemo skills.

## ICEX Format for C291

- **Time Limit:** 15–20 minutes in-class
- **Structure:** [Task] → Theory/Experiment table → [Submission]

## The "Bug in the Path"

C291 embeds the in-class exercise directly in the slide deck as "The Bug in
the Path" — not as a separate ICEX file. The exercise appears after the worked
example and before the AI Prompts slide.

When generating a slide deck that includes an in-class exercise, use the
`calliope_slides.md` conventions, not a standalone ICEX template.

## Theory/Experiment Table

Every ICEX must include a "Theory/Experiment" table for the Theory-Driven
Debugging pillar:

```
| Theory (Hypothesis) | Experiment (Test) | Result | Modified Theory |
|---|---|---|---|
| [What I think is wrong] | [What I'll try] | [What happened] | [Updated understanding] |
```

This table is the C291-specific implementation of the scientific debugging
loop. Students must fill it in during the exercise.

## Quest Reward System

Two reflective paths for assignment documentation:

- **PATH A (THE ARTISAN):** Documentation of a bug from the "Merit Badge" list.
  Must include original buggy code, the Theory/Experiment proof, and the fix.
- **PATH B (THE BARD):** A narrative story (Explorer/Epic theme) of a
  debugging struggle. Must include a "Technical Appendix" with actual code and
  isolation technique used.

Both paths are equal in grading value. The choice is the student's.

## Merit Badge References

The KB file `C291_Merit_Badges.md` lists the "Top 20 C Perils" — common C
programming pitfalls (buffer overflows, pointer arithmetic errors, memory
leaks, signal handling issues). Reference Merit Badges in exercises where
students are likely to encounter these perils.
