# Abstraction Literacy

Information technology is layers of abstractions built on top of each other.
When working at a layer, an engineer must understand what that layer
abstracts, what value it adds over the layer below, and when to drop down to
the lower layer.

## Principle

At every major technology introduction:

1. **Name the layer below:** what does this technology sit on top of?
2. **Name what it abstracts:** what complexity does it hide from you?
3. **Name what it adds:** what value does it provide over working with the
   raw layer?
4. **Name when to drop down:** when does the abstraction leak or fail, and
   what does the engineer need to know about the layer below?

## Example

**Flask (web framework) sits on top of HTTP:**
- Layer below: HTTP — request/response, methods, headers, status codes
- What it abstracts: socket handling, request parsing, response formatting
- What it adds: routing, templating, session management
- When to drop down: debugging a 500 error requires understanding HTTP status
  codes; performance tuning requires understanding socket behavior

## Evidence

This principle aligns with the "making thinking visible" approach from
cognitive apprenticeship (Collins, Brown, Holum, 1989) — naming the
abstraction layers makes the expert's mental model visible to the student.

It also supports near transfer (Yale Poorvu Center): by explicitly naming
the abstraction relationship, students can apply the same analytical framework
to new technologies they encounter after the course.

## Course-Specific vs. General

This skill was originally a course theme for a software engineering course. It
is elevated
to a general pedagogy skill because *any course that introduces layered
technologies* benefits from this approach:

- OS course: system calls abstract hardware; virtual memory abstracts
  physical memory
- Networks course: TCP abstracts IP reliability; HTTP abstracts TCP streams
- Databases course: SQL abstracts file I/O; ORMs abstract SQL
- AI/ML course: frameworks abstract gradient computation; transformers
  abstract sequence modeling

## When to Use

- Every time a new framework, library, or tool is introduced
- When students are confused about "why does it work this way?" — the answer
  is usually in the abstraction layer below
- When comparing two tools (Flask vs. React, SQL vs. NoSQL) — ground the
  comparison in what each abstracts and what values each prioritizes

**HIL awareness:** The abstraction analysis (layer below, what it abstracts,
what it adds) should be documented in the HIL block for instructor review.
The instructor should verify the abstraction framing is accurate before
publishing — a wrong abstraction story is worse than no story.
