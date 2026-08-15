# References Section Format

Every exercise must include a **References** section with two parts: curated
links for direct reference, and a curated AI prompt that guides students
toward effective AI use while reinforcing AI literacy principles.

## Part 1: Link Groups

Organize links into three groups. Populate with current, relevant links at
generation time. Do not use placeholder URLs.

**Group 1 — Documentation & FAQs**
Official documentation, API references, and framework guides for the tools used
in the exercise. At least 2 links required. Examples (will vary by course):
Flask docs, pytest docs, GitHub Actions docs.

**Group 2 — Tutorials & Walkthroughs**
Step-by-step guides, blog posts, or video tutorials that show how to do the task.
May be empty if no suitable tutorials exist, but prefer at least 1 when possible.
Examples: Real Python articles, official "getting started" tutorials.

**Group 3 — Standards & Specifications**
RFCs, official specifications, PEPs, OWASP advisories, IEEE/IETF standards.
Include these whenever the exercise involves a pattern with a named standard
behind it. Examples: RFC 7807 (error responses), PEP 8 (style), OWASP Top 10,
BDD/Gherkin spec. May be empty for purely implementation-focused exercises.

## Part 2: AI Assistant Prompt

Include a curated AI prompt that students can use when they need help with the
exercise. The prompt must be specific to this exercise's content (not a generic
"explain X") and must model the AI literacy principles taught in the course:

- **Calibrated trust:** the prompt should ask the AI to explain its reasoning,
  not just produce an answer — so the student can evaluate whether the
  reasoning is sound
- **Output verification:** the prompt should include a verification step
  (e.g., "show me how I would test this" or "what are the assumptions you're
  making?")
- **No ghostwriting:** the prompt should ask for explanation or guidance, not
  a complete solution to the exercise itself

Example structure:

```markdown
### 🤖 AI Assistant Prompt

If you're stuck, try this prompt with an AI assistant:

> I'm working on [exercise-specific task]. I understand [what you know so far].
> Can you explain [specific concept or where you're stuck]? Walk me through
> your reasoning so I can follow it. What assumptions are you making, and how
> would I verify your answer against the actual documentation?

Verify any AI suggestion against the documentation links above before applying it.
```

## Template

```markdown
## References

### 📚 Documentation & FAQs
- [Title](url)
- [Title](url)

### 🎓 Tutorials & Walkthroughs
- [Title](url)

### 📋 Standards & Specifications
- [Title](url)

### 🤖 AI Assistant Prompt
[curated prompt specific to this exercise — see above]
```
