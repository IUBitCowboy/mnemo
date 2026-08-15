---
title: Instructor AI Use Principles
author: Kurt Seiffert
status: approved
last_updated: 2026-08-14
applies_to: [SE1/P465, C291, all courses built on Mnemo]
---

# Instructor AI Use Principles

## Purpose

These principles govern how the instructor uses AI in course development. They
exist to ensure that the AI Use Policy imposed on students is credible — the
instructor holds himself to the same standard of transparency and
accountability that he requires of students.

> **Symmetry Principle:** The disclosure standard imposed on students must be
> the same standard the instructor holds himself to in work product produced for
> them. A one-way transparency regime is enforceable but not credible. If
> students must attach `ai_use.md`, instructor-generated artifacts must carry an
> equivalent disclosure.

These principles are cross-course. They apply to SE1/P465 (Clio) and C291
(Calliope) equally. They inform the muse files, the syllabus AI Use Policy, and
every artifact produced through the Mnemo system.

In the open-source distribution, this file serves as a template. The
**structural principles** (symmetry, human review, quality-first, disclosure,
no pedagogical judgment) are recommended for any instructor using AI-assisted
course development. The **specific use cases** reflect one instructor's
practice and should be adapted by each instructor to their own context.

---

## Governing Principle

1. **Quality first.** AI use in course development serves quality of content
   and pedagogy. Expedience only in service of quality.

## Generation

2. **Complex constraints.** AI writes instructions with complex constraints
   (e.g., ICEX instructions with layered requirements, testing policies, complex formatting, and
   rubric criteria).

3. **Formulaic documents.** AI writes new requirements into templates and
   formulaic documents (e.g., reflection instructions, rubric specifications).

4. **Summaries.** AI writes short paragraph summaries of classes or modules.

5. **Examples.** AI generates and refines examples.

## Analysis

6. **Completeness checking.** AI checks for lesson completeness, identifies
   hidden assumptions, and flags concepts that need elaboration.

7. **Pedagogical deficiency detection.** AI identifies and corrects
   pedagogical deficiencies or traps in course design.

8. **Design exploration.** AI explores design alternatives and tests pedagogical
   decisions before committing.

## Verification & Automation

9. **Requirements verification.** AI helps ensure products have passed all
   requirements.

10. **Menial automation.** AI automates menial work with consistency and
    accuracy — removing error-prone human work improves quality.

11. **Human review and approval.** All material visible to students has been
    reviewed and approved by a human. If the material is wrong, the AI did not
    write it wrong — the instructor failed to review it correctly. Accountability
    rests with the human, not the tool.

## Boundaries

12. **No pedagogical judgment over individual students.** AI does not make
    grading, accommodation, or evaluation decisions about individual students.
    AI may inform, surface patterns, or flag, but the judgment is human.

13. **Disclosure.** AI use in instructor work product is disclosed to students
    through a standard disclosure on each artifact.

---

## Implementation Status (as of Aug 2026)

- [ ] Syllabus preamble: add instructor AI use principles as the ethical
      foundation of the student AI Use Policy
- [ ] Muse file templates: add instructor-side disclosure field to
      `clio_icex.md`, `clio_slides.md`, `clio_project.md` (and Calliope
      equivalents)
- [x] Pedagogy skill: `skills/pedagogy/instructor-ai-symmetry.md` —
      Symmetry Principle extracted as a generalizable cross-course skill,
      auto-loaded by all muses
- [ ] Artifact disclosure: every Clio/Calliope-generated artifact carries a
      standard disclosure line