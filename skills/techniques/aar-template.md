# After Action Report Template

The After Action Report (AAR) is the learning artifact produced when a student
invokes the Standard Blocker Protocol. It documents the blocker, the
investigation, the diagnosis, and the lesson — turning a stuck moment into
evidence of engineering process.

## Template

Generate the AAR template section in every exercise that includes the Standard
Blocker Protocol. The instructor's diagnostic hints section is exercise-specific
— populate it with 2–3 hints calibrated to the likely failure points of this
particular exercise.

```markdown
# AAR for [Exercise N]: [Blocker Title]

* **Student:** `@your-github-username`
* **Timestamp:** `YYYY-MM-DD @ HH:MM`

---

### Instructor's Diagnostic Hints
* **Hint 1:** [Exercise-specific hint for likely failure point]
* **Hint 2:** [Exercise-specific hint for likely failure point]
* **Hint 3:** [Exercise-specific hint for likely failure point]

---

### 1. The Blocker
*(What is the **symptom**? What is the **exact** error message?)*

> [Paste error message or describe symptom]

### 2. The Investigation
*(What **exactly** did you try? List the commands you ran, files you edited,
and resources you consulted.)*

* I tried...
* Then I edited...
* This resource suggested...

### 3. The Root Cause Hypothesis
*(Based on your investigation, what do you **think** is the real problem? Be
specific.)*

> I believe the problem is...

### 4. Evidence
*(Paste the full terminal output, relevant code snippets, or screenshots that
support your hypothesis.)*

    [Paste full logs here]

### 5. The "Aha!" Moment (if any)
*(Did you have a moment of clarity or discover the solution just as you were
writing this?)*

> [Describe your realization, or N/A]

### 6. The Learning
*(What new, specific thing did you learn? What will you do **differently**
next time?)*

> I learned that...

### 7. The Remaining Question
*(What do you **still** not understand? What is the **one key question** you
need answered to get unblocked?)*

> My one question is...
```

## Design Notes

- **Sections 1–4 are diagnostic.** They capture the engineering process: what
  happened, what was tried, what the hypothesis is, and what evidence supports
  it. This is the "scientific method" structure from the Error Diagnosis skill.
- **Section 5 ("Aha!") is metacognitive.** It captures the moment of insight —
  students often solve their own problem while writing the investigation
  section. This is a productive failure outcome: the struggle of documenting
  the blocker leads to the resolution.
- **Section 6 is the transferable lesson.** This is what the instructor
  evaluates — not whether the student fixed the bug, but whether they learned
  something they can apply next time.
- **Section 7 gives the instructor the hook for the hotfix.** The student's
  one remaining question tells the instructor exactly what to address in the
  PR review.
- **Instructor's Diagnostic Hints are exercise-specific.** The muse populates
  these with 2–3 hints for the most likely failure points. These hints are
  not solutions — they point toward the right diagnostic area.

## When to Use

- Every exercise that includes the Standard Blocker Protocol
- The template is embedded in the ICEX so students can copy it directly
