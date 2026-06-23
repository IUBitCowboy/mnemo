# Code Reading Before Code Writing

Most CS courses emphasize writing code. Professional practice emphasizes
*reading* code — developers spend more time reading existing code than
writing new code. Explicitly teach code reading as a skill, not just code
writing.

## Principle

Before asking students to write code that uses a concept, have them read
existing code that demonstrates that concept. Code reading develops:

- **Pattern recognition:** seeing how experienced developers structure solutions
- **Vocabulary:** learning the idioms and conventions of a language/framework
- **Archaeology skills:** navigating an unfamiliar codebase, finding relevant
  code, understanding dependencies
- **Critical reading:** identifying bugs, security issues, and design smells
  in existing code

## Evidence

The history of computing education research (Cambridge Handbook of Computing
Education Research) notes that expert/novice differences in programming were
among the first studied phenomena in CS education research. Experts read code
differently — they recognize patterns, chunk code into meaningful units, and
navigate by structure rather than line-by-line.

Cognitive apprenticeship (Collins, Brown, Holum, 1989) supports this: the
first step in apprenticeship is *observing* the master work (reading expert
code), not *producing* (writing code).

## Implementation Patterns

1. **Grayfield exercise:** give students an existing codebase and ask them to
   find, understand, and modify a specific component (a grayfield exercise)
2. **Code review as reading:** the QA Sentinel role reads teammate code —
   this is code reading with a purpose
3. **Read before write:** before an exercise that writes new code, have
   students read a worked example of similar code
4. **Bug hunting:** give students code with a known bug and ask them to find
   and fix it (error diagnosis as a taught skill)

## When to Use

- Early in the course (grayfield phase): heavy code reading, minimal writing
- Mid-course: balanced reading + writing
- Late course (greenfield phase): primarily writing, but reference prior
  reading for patterns

**HIL awareness:** Note in the HIL block which code is being read and whether
it's expert code (instructor/TA-written) or peer code (student-generated from
a prior exercise). Expert code is higher quality but may not show common
mistakes; peer code is messier but more relatable.
