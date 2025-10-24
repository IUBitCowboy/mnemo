### Core Curriculum Production Workflow (The "Curriculum Factory")

This section defines the mandatory, MLOps-inspired workflow for generating, curating, and storing all curriculum artifacts. This process ensures 100% traceability from raw AI generation to the final, student-facing product.

The workflow is built on a "Curation-First" model that separates the **raw artifact log** (`sessions/`) from the **curated, production-ready source** (`cmods/`).

#### 1\. The `RAW -> Curated -> PPR` Pipeline

All artifacts **must** exist in two distinct, version-controlled forms:

1.  **The Raw Artifact Log (`sessions/`)**

      * **Purpose:** This directory is the "receiving dock" for *finished raw goods* from the AI.
      * **Content:** A file in this directory (e.g., `sessions/week_09/ice1.raw.md`) must contain *only* the final, usable, AI-generated markdown for a **single artifact**.
      * **Exclusions:** This directory **must not** contain "junk" iterations, "useless tries," or entire conversational histories. The AI chat window is the "workbench" for iteration; this directory is for the finished raw part *only*.

2.  **The Curated Source (`cmods/`)**

      * **Purpose:** This is the canonical, "Production Pipeline Ready" (PPR) source code for your curriculum. This is the *only* directory that build scripts (e.g., `pipeline/`) should read from.
      * **Content:** A file in this directory (e.g., `cmods/week_09/ICE/ice1.md`) is the *human-curated* version of its raw counterpart. This is where you will add instructor notes, fix typos, and make pedagogical tweaks.

#### 2\. The Curation Workflow

The standard workflow for creating any new artifact is:

1.  **Iterate:** Work with the AI in the chat "workbench" until you have a final, usable block of text for an artifact (e.g., an ICE).
2.  **Snapshot Artifact:** Copy *only* that final, good artifact text.
3.  **Save Raw:** Paste this block into its "raw" file (e.g., `sessions/ice1.raw.md`).
4.  **Save PPR:** Immediately copy this new file to its canonical `cmods/` location (e.g., `cmods/week_09/ICE/ice1.md`).
5.  **Curate:** Make all human edits and add design rationale (see below) to the `cmods/` version *only*.
6.  **Commit:** Commit *both* files (`sessions/ice1.raw.md` and `cmods/week_09/ICE/ice1.md`) in the same commit.

This workflow guarantees a "Curation Audit." At any time, running `diff sessions/ice1.raw.md cmods/week_09/ICE/ice1.md` will provide a perfect log of all human-only curation.

#### 3\. Embedded Design Rationale

To preserve the pedagogical "why" alongside the curricular "what," all human-curated `cmods/` files **must** begin with an "Instructor Notes" block.

This block **must** be formatted as an HTML comment (\`\`) so that it is invisible to students and all build pipelines (Pandoc, Canvas, etc.).

**Standard Template (to be pasted at the top of all `cmods/` files):**

```markdown
### [Start of Student-Facing Artifact]
...
```