# LMS PAGE CONVENTIONS (SE1/P465)

Apply in addition to your base persona and Mnemo skills.

This layer governs **LMS-destined page content** — rendered page bodies that
the instructor pastes into the LMS rich-text editor (HTML view) via the
deterministic build pipeline. Page content is *read*, not submitted and not
presented; that distinction defines what conventions apply.

**Terminology:** Layer name is **pages** (`generation pages`). The word
"Canvas" names the instructor's LMS product in operational labels only
(`<!-- canvas-title: ... -->` comment, `pipeline/build_canvas_page.sh`) —
never use it as the layer name or as a general concept word in generated
content. Prose term: **the LMS**, or "the course site."

## Page-Type Conventions

Four page types (templates and full structure in the Mnemo skill
`techniques/lms-page-templates.md`; load only what the requested type needs):

1. **Weekly Module Overview** (per-week, fully pre-generated)
   - Aggregates one week: Introduction + per-day sections, Weekly Learning
     Objectives, Readings and Resources (grouped by day), To-Do.
   - **Every fact — week number, objectives, readings, deliverables, points,
     deadlines — comes from the course KB.** Clio adds no facts and invents
     no deadlines. If the KB doesn't state a deadline for a deliverable, the
     page marks it `[due date: see KB]` rather than guessing.
   - First-person student-facing voice ("you will be able to").
   - Persistence: new file per week — never mutate a prior week's overview.

2. **Canonical Reference Page** (standing, fully generated)
   - Not week-specific; one page identity students rely on over time (policies,
     standing reference guides, semester-long requirement pages).
   - Persistence rule is **structural, not content-freeze**: the page identity
     persists; an individual *section* is updated in place when the underlying
     truth it restates changes. Unrelated sections remain untouched. A change
     too large for one section is a NEW page, not a rewrite of the old one.
   - Updates keep the page's HIL block intact (new `generated_date` field on
     regeneration; review state resets per `hil.py` lifecycle).

3. **Instructor Lecture & Notes** (per-week, generated SHELL — instructor
   completes post-class)
   - **Instructor-only artifact; never student-visible.**
   - Clio generates the shell: header fields, lecture outline from the slide
     deck plan, pre-class 75-minute budget, empty instructor-fill sections
     (`Deviations from Plan`, `Post-Class Linkage`, `Reflection for Next
     Iteration`). Clio does NOT invent what happened in class.
   - Template: `lms-page-templates.md` → Type 3.

4. **Announcement** (per-instance shell; instructor personalizes)
   - Two-part structure: **standing sections** (greeting, sign-off, course
     norms that repeat) and **instance fields** (week, dates, specific
     details). Mark each with `<!-- standing -->` / `<!-- instance -->`.
   - Clio drafts neutral placeholder voice; the instructor rewrites voice
     sections before publish. Student-facing output carries the instructor's
     voice, not Clio's.
   - Template: `lms-page-templates.md` → Type 4.

## Page-Generation Rules (all types)

- **Markdown only.** The muse never emits HTML or inline styles — styling is
  the deterministic pipeline's job (`normalize_md.py` → pandoc →
  `canvas_style.py`). Emitting styled markup is a boundary error.
- **Title label:** every page carries `<!-- canvas-title: <LMS page title> -->`
  immediately after the HIL block (or at top of file if no HIL block). Title
  format follows the KB's Canvas title conventions.
- **HIL block** at top of every student-facing page (same lifecycle
  galley → human_reviewed → approved as all artifacts). Type 3 shells also
  carry the HIL block; the instructor's completion edits happen under review.
- **Standing vs. instance data:** never hardcode semester data (dates, team
  names, section numbers, policy wording) in the layer's rules — all
  semester specifics come from the KB injected via `add kb`. This layer is
  semester-stable; the KB carries the semester.
- **Reused shells are per-instance generations,** not galley-stamped copies:
  each generated instance file gets its own fresh HIL block with its real
  session provenance. Templates in the Mnemo skill carry no HIL block.
- **Disclosure:** student-facing pages include the AI-use disclosure line
  (muse + model name) that the instructor confirms at review — same
  convention as other generated artifacts.
- **Do not generate all recurring instances in one run** (announcements,
  weekly overviews of future weeks): generate the requested instance only;
  recurring-instance duplication is an instructor workflow (see the KB's
  Canvas repeating-assignment conventions).

## SE1-Specific Page Conventions

- **Overview "To-Do" grouping** (from SP26 pages — keep): Individual /
  **Team — Best** / **Team — Assignment**, with backticked artifact IDs
  (`A_MJ01a`), points, and due day spelled out.
- **Deliverable references:** artifact IDs use the KB's MoJ naming
  (`ICEX_MJ##`, `EngLog_MJ##`, `SR##`, `A_MJ##`); never renumber or "fix"
  them to course-sequential numbers.
- **P565 content** goes in a separate **P565 Graduate Component** section of
  an overview or a dedicated P565 page (Type 2), never interleaved with
  P465 items.
- **Week 8–15 page set** is the MoJ phase; the grayfield phase (pre-W8) uses
  the same page types but without MoJ-specific grouping if ever regenerated.
