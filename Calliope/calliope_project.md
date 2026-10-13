# PROJECT CONVENTIONS (C291)

Apply in addition to your base persona and Mnemo skills.

## Assignment Structure

C291 has three assignment phases with distinct rules:

### Author Phase (W1–10): Hand-Written Assignments

- **A00–A04:** hand-written C programs, pseudocode-first per existing
  practice. Students write pseudocode in `README.md` before writing
  code. AI is Socratic-interlocutor only — no AI-generated code may be
  submitted.
- Every assignment requires `debug_log.md` containing at least one
  detailed example demonstrating the scientific method of debugging
  (Theory → Experiment → Result → Modified Theory).
- A `debug_log.md` without a detailed example is considered incomplete
  (zero credit for the log portion).
- Pseudocode-first is mandatory: the `README.md` pseudocode is
  submitted before the implementation. This is the "explain the code"
  assessment invariant applied to the author phase.

### Transitional Assignment (W12): A05-T (my_wc)

- Student writes the core implementation by hand.
- An agent generates a competing implementation from the same
  specification.
- Deliverable includes a comparison against the audit rubric: both
  versions evaluated on all five criteria, with the student's
  assessment of which is better and why.
- This is the bridge between author and auditor phases — the student
  is both author and auditor on the same specification.

### Auditor Phase (W13–15): A06 Capstone (httpd audit)

- Agent generates the HTTP server code; student audits, repairs, and
  defends.
- Student must produce a working, secure version of the server,
  documented with sanitizer evidence (ASan/valgrind) for every repair.
- **Accept/reject log:** every accepted agent chunk needs one sentence
  of justification. Every rejection needs the reason. This is code
  review made structural — the SE theme delivered as practice.
- **Predict-before-run protocol:** before executing agent code, the
  student writes expected behavior for a given input. This is the
  cheapest known antidote to confirmation-bias rubber-stamping.
- **Oral defense:** 15-minute individual interview during finals week.
  Student explains their repairs, their reasoning, and answers
  questions about the code. This is the "explain the code" assessment
  invariant applied to the auditor phase — and it cannot be faked with
  generated output.

## HTTP Server Evolution

The capstone HTTP server evolves from single-file to multi-file project:

- **A05 (HTTP v1):** Single file, stdin/stdout, `fretrv()` provided —
  same as SP26
- **A07/A08 (HTTP v1.5):** Split into multi-file — header parsing,
  response generation, file retrieval in separate `.c` files with a
  shared `httpd.h`. Students learn header files (declarations vs.
  definitions), multi-file compilation/linking via Makefile, source
  organization by responsibility.
- **A09 (HTTP v2):** Add fork/exec/pipes for netcat, directory listing.
  Multi-file structure gains real complexity — process management
  separate from HTTP parsing.

**Pedagogical rationale:** Multi-file teaches architectural
comprehension — the field-research insight that separated Emma (success
case) from her colleagues. You can't compartmentalize code without
understanding component boundaries.

## Audit Rubric

The 5-criterion rubric from the base persona (compile, tests,
boundaries, memory, readability) is introduced at Ceremony 1 (Week 3)
and used all semester. Every assignment that involves evaluating code —
student's own or an agent's — must include the relevant rubric criteria
in the assignment specification.

## Assignment Submission

- All code must compile and run on the IU Silo clusters using `gcc`
  with `-Wall -Wextra`
- Repository: `<student>/SSYY-C291` (e.g., `seiffert/fa26_c291`) with
  `LUDDY-C-UNIX/C291_seiffert_class` as upstream
- Each assignment on a separate development branch (`wk01`, `wk02`,
  etc.)
- Submission: commit URL submitted to Canvas. Pull Request to main,
  instructor/TA as reviewer.
- IU AutoGrader handles automated tests (~85–90 pts). Hand grading for
  style, comments, pseudocode, and debug log (~10–15 pts). 10
  AutoGrader submissions per day allowed.

## BREV (Bi-Weekly Review)

15-minute TA meetings assessing comprehension of two prior programs.
Directly implements the "student must be able to explain the code"
assessment invariant.

**Format:** Student sits with TA, opens their code, and explains what
it does and why it works at an architectural level. TA may ask the
student to modify code in response to a prompt (e.g., "handle an empty
input") or to explain or design a test.

**BREV Rubric (4 criteria, 10 points per session):**

| Criterion | Points | Description |
|---|---|---|
| Code Explanation | 4 | Student explains what the code does and why it works, at an architectural level (not line-by-line narration). |
| Code Modification | 3 | Student correctly modifies code in response to a TA prompt. |
| Test Design | 2 | Student explains or designs a test — what to test, why, expected behavior. |
| Oral Exam Review | 1 | (Exam-following BREV only) Student answers questions about their exam responses and reasoning. |

Three BREV sessions include oral review of the preceding take-home exam.

## Debugging Log Requirement

Every programming assignment requires `debug_log.md` containing:

1. A log of all significant defects resolved in the program
2. At least one detailed example demonstrating the scientific method of
   debugging (Theory → Experiment → Result → Modified Theory)
3. A `debug_log.md` without a detailed example is considered incomplete
   and equivalent to nothing (zero credit for the log portion)

This is the C291-specific implementation of the Metacognitive
Reflection and Error Diagnosis skills — the debugging log forces
students to reflect on their debugging process, not just report the
result. In the auditor phase, the debug log also records
accept/reject decisions for agent-generated code.

## AI Use Disclosure Field

Every generated assignment must include:

```markdown
## AI Use Policy
[State the AI policy for this assignment. Options:]
- AI-free: no AI tools permitted. (Default for author phase.)
- Socratic only: AI may explain concepts and show illustrative
  examples. No AI-generated code may be submitted. (Default for
  author phase assignments.)
- Gated delegation: AI may generate code for constructs that have
  passed their gate ceremony. All AI-generated code must be logged
  in the accept/reject log. (Auditor phase.)
- Bug Forge/Bugsmith permitted: [for WEVL exercises — see
  calliope_icex.md]

Students must attach `ai_use.md` disclosing any AI tool used:
**Tool used:** [tool name]
**Model used:** [model name]
**What I asked:** [description]
**What AI produced:** [description]
**What I changed:** [description]
```
