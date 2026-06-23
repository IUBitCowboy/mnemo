# Rubric Format Policy

## Principle: Content Over Presentation

Rubrics must be generated as a **structured data block**, not as final HTML.
The muse produces the rubric content — criteria, points, descriptions. The
pipeline transforms that structured data into the published format (HTML
table, Canvas page, PDF) during the galley → publish stage.

**The muse should never emit raw HTML, inline styles, or presentation
markup.** That is a pipeline responsibility. Sending an AI to do a
computer's job.

## Format: Structured Rubric Block

Generate rubrics using this markdown structure:

```markdown
## Rubric ([N] pts)

| Criterion | Points | Description |
|---|---|---|
| [Criterion name] | [N] | [What earns full credit] |
| [Criterion name] | [N] | [What earns full credit] |
| **Total** | **[N]** | |
```

The pipeline will transform this into the appropriate published format with
course-specific branding, styling, and LMS integration.

## Point Allocation (Guideline)

- **In-class exercises:** 10 points total. At least 3 points for a complete
  `CONTRIBUTIONS.md` entry. Remaining 7 points distributed across the major
  technical goals.
- **Project assignments:** Point values are course-specific — defined in the
  muse's project artifact layer.

## Pipeline Responsibility (Step 7 Goal)

The pipeline refactoring (Step 7 of the redesign plan) should:
1. Read the structured rubric block from the galley markdown
2. Transform it into the published format (HTML table with inline styles
   for Canvas, styled table for PDF, etc.)
3. Apply course-specific branding (brand color, font sizing) from the muse's
   configuration — not from the LLM's output
4. Handle alternate row shading, header/footer styling, and responsive layout

This is a boundary correction: the AI's job is to decide *what* the criteria
are and *how many* points each is worth. The pipeline's job is to render
that decision in the correct format for the destination medium.