Decision Log for Mnemo

---

---
## 2025-10-25 @ 11:26 EDT - Defining Meta-Workflow & Knowledge Base Curation

**Scope:** Workflow, Mnemo System, Clio Persona, Knowledge Base Management

**Description:**
As our system of artifacts (`decisions_log`, `clio_persona`, `instructor_handbook`) becomes more complex, we are formalizing the "meta-workflow" for managing it to ensure stability, consistency, and resilience against model drift.

### 1. Handbook Update Workflow: "Append, Don't Rewrite"
To mitigate the risk of "model drift" (where a generative AI subtly changes or drops instructions when rewriting a large file), we have established a new SOP for updating our handbooks:

* **I (Clio)** will generate *new* sections (e.g., a new "SOP-03") as self-contained, standalone text blocks.
* **The Instructor** will then act as the integrator, manually **copying and pasting** this new block into the master handbook document.
* **Rationale:** This "append" model is safer, more precise, and `git-friendly`. It uses Clio for generation without risking the integrity of the existing, validated document.

### 2. Knowledge Base Curation (Clio's "Mind")
We have defined the optimal set of files to provide to Clio as its knowledge base to maximize performance and reduce contextual "noise."

* **DEPRECATED (Low-Value):** Sample artifacts (`ICEX07.md`, `lecture1.md`, `wk1_quiz.md`, etc.) are now considered historical, low-value context. They are *examples* of past work, not *instructions*, and should be **excluded** from Clio's knowledge base to improve focus and reduce latency.
* **REQUIRED (High-Value):** Clio's knowledge base should now consist of:
    1.  **`clio_persona.md`:** Clio's rules.
    2.  **`decisions_log.md`:** Our shared history and rationale.
    3.  **`instructor_handbook.md`:** The instructor's playbooks for using Clio.
    4.  **"Course Facts":** Key data files like `FA24 P465 Lecture Schedule.csv` and `MoJ_Project_description.md`.

This "meta-trio" (`persona`, `log`, `handbook`) plus the course facts represent the complete, curated "mind" of the course, ensuring Clio has all necessary rules and context.
---

## 2025-10-25 @ 10:26 EDT - Formalizing the "Scalable Assessment Protocol" (SAP)

**Scope:** Workflow, Assessment, Grading, AI Integration, FERPA Compliance, TA Management

**Description:**
To ensure high-quality, fair, and consistent grading of subjective, open-ended assignments (e.g., reflections, short essays, GenAI chat logs) at scale, we are formalizing the **Scalable Assessment Protocol (SAP)**.

This protocol tags any assignment that will use our "human-in-the-loop, AI-assisted" grading workflow.

### Core Principle: AI for Analysis, Humans for Assessment
The protocol's foundation is a strict separation of concerns that is both pedagogically sound and FERPA-compliant.
* **AI (The Synthesizer):** The AI's *only* role is to perform **thematic analysis** on an *anonymized, aggregated* set of student submissions.
* **Human (The Assessor):** The human instructor and TAs are the *only* agents who perform **assessment, judgment, and grading** on the original, attributed student work.

### The 5-Step SAP Workflow
1.  **Step 1: Collection**
    * The instructor bulk-downloads all student submissions (e.g., `.md` files) from Canvas. Canvas automatically appends student PII (Name, ID) to each filename.

2.  **Step 2: The FERPA Firewall (Anonymization)**
    * The instructor runs a **local script** (the "Anonymizer"). This script iterates through all submissions, logs attribution to a secure local-only map, and produces a single, fully-anonymized, aggregated text blob.
    * **Crucially: No PII ever leaves the instructor's local machine.**

3.  **Step 3: AI-Powered Analysis**
    * *Only* the anonymous text blob is sent to a GenAI model (Gemini/Copilot) for thematic analysis, *not* assessment.
    * **Good Prompt:** *"Analyze these 120 anonymous student responses. Identify the 5 most common themes and the 3 most critical misconceptions, providing illustrative quotes for each."*
    * **Forbidden Prompt:** *"Grade these 120 submissions."*

4.  **Step 4: Calibration Guide Generation**
    * The instructor and Clio review the AI's thematic summary. This summary is used to create the **`TA_Grading_Guide.md`**, which "frames" the TAs' thinking by showing them what to look for.

5.  **Step 5: Human-Led Assessment**
    * The TAs receive the **original, attributed** student files *and* the **TA Grading Guide** + Rubric.
    * The TAs perform the final assessment, using the guide to "classify" responses fairly and consistently.

**Conclusion:** This protocol leverages AI as a "Head TA" to perform synthesis, allowing the instructional team to apply human judgment efficiently and consistently. This is our standard for all `SAP`-tagged assignments.

---

## 2025-10-24 @ 09:35 EDT - Adding Canvas-Ready HTML to Build Pipeline

**Scope:** Core Process, Pipeline, Artifact Deployment, Canvas

**Description:**
This decision addresses the problem of student-facing artifacts (like ICEs) being "hostile" to copy-pasting code. The current pipeline, which generates a `.pdf`, is excellent for human reading but fails when students need to copy indentation-sensitive code (e.g., Python, YAML).

We are adding a new, deterministic build step to the `pipeline/` to solve this.

### The New Pipeline Artifact: Canvas HTML

1.  **New Script:** A new script, `pipeline/build_canvas_page.sh`, will be created.
2.  **Function:** This script will use `pandoc` to perform a standard, deterministic conversion from a curated Markdown file (`cmods/`) into a standalone, clean HTML file (`dist/canvas_pages/`).
3.  **Deployment:** This generated HTML source will be pasted directly into the Canvas Rich Content Editor's (RCE) `<>` HTML view.

**Rationale:**
This solution maintains our "Single Source of Truth" principle. The `cmods/` file remains the canonical source. The pipeline, not the AI, is correctly used for a deterministic conversion.

This creates two distinct "build artifacts" from one source, each optimized for its purpose:
* **`.pdf` (from `build_pdf.sh`):** For human reading, printing, and offline access.
* **`.html` (from `build_canvas_page.sh`):** For copy-paste-friendly code blocks and native rendering within the Canvas LMS.

This avoids brittle, manual "Save as HTML" steps or inappropriate, non-deterministic use of AI for a simple file conversion.

**Reference:** Discussion between Instructor and Clio, 2025-10-24.
---

## 2025-10-24 @ 09:27 EDT - Formalizing the "Curriculum Factory" MLOps Workflow

**Scope:** Core Process, Mnemo, Artifact Management, Evidence-Driven Design

**Description:**
This decision formalizes the core "curriculum factory" workflow, applying MLOps principles to solve critical friction points in the AI-assisted development process. The previous method of logging entire, monolithic chat sessions created a "junk drawer" problem, making artifact curation, recovery, and auditing nearly impossible.

This new workflow, based on a `RAW -> Curated -> PPR (Production Pipeline Ready)` model, is adopted to solve these specific problems:
1.  **"Useless Tries" Clutter:** Iterative development within a single chat session cluttered logs with failed or dead-end artifact versions.
2.  **Multi-Artifact Curation:** A single session used to create multiple, unrelated artifacts (e.g., an ICE and a Quiz) resulted in a raw log that was difficult to separate.
3.  **Lack of Traceability:** It was impossible to determine where AI generation ended and human curation began, failing our "Evidence-Driven Design" goal.

### The New "Curation-First" Workflow

1.  **Artifact-Centric Raw Logs:** The `sessions/` directory is now formally defined as a log for **artifact-centric raw text** (e.g., `sessions/ice1.raw.md`). It does **not** store chat histories. This is the `RAW` stage.
2.  **Canonical Curated Source:** The `cmods/` directory remains the canonical "Production Pipeline Ready" (`PPR`) source. This is the *only* source used by build pipelines (e.g., `pandoc`).
3.  **"Curation Audit" via `diff`:** This two-file system (`sessions/artifact.raw.md` and `cmods/artifact.md`) enables a "Curation Audit." Running a `diff` between the two files provides a perfect, machine-readable log of all human-only curation.
4.  **Embedded Design Rationale:** To capture the "why" of curation, all `cmods/` files will now embed design rationale and instructor notes within `` HTML comment blocks.

**Rationale:**
This process provides the "best of both worlds." It maintains low friction for the instructor's creative flow (who can "dump-and-run" a messy session to a *local* `.raw.md` file before cleaning it) while ensuring high integrity for the *version-controlled repository* (which only accepts the final, clean raw artifact).

This makes the curation process itself a formal, auditable piece of evidence, fully aligning our development workflow with our core pedagogical goal of "Evidence-Driven Design."

**Reference:** Discussion between Instructor and Clio, 2025-10-24.
---

## 2025-10-19 @ 13:00 EDT - Introducing Policy as Code (GitHub Rulesets/Branch Protection)

**Scope:** Lecture 12 (Automated Deployment) or Lecture 13 (GenAI Integration) / Software Governance

**Decision:**
The concept of **Policy as Code (PaC)**, specifically implemented via **GitHub Rulesets** (or similar features in other platforms), will be formally introduced into the course schedule between **Week 12 (CD)** and **Week 13 (GenAI Integration)**.

### Rationale:
The timing is chosen to present Rulesets as the final layer of **Governance Automation**, which sits directly on top of the CI/CD pipeline built in Week 12:

1.  **Architectural Necessity:** After automating code *delivery* (CD), Rulesets automate the **governance** of that delivery. This answers the question: "How do we prevent a human from manually overriding the pipeline's findings?"
2.  **Pedagogical Link:** It enforces critical techniques already taught: **Code Review (CR)** and **Continuous Integration (CI)** success (e.g., "CI must pass," "Require 2 approvals"). This moves process requirements from a team rule into a repository configuration.
3.  **Project Alignment:** This provides context for the **Extra Credit** option in the MoJ Project (Section 7: "Enforce Branch Protection"), encouraging students to implement the technical solution for PaC.

### Action Item:
The lecture material must be designed to teach the general **PaC technique** rather than focusing exclusively on the specific GitHub product.

---

### 🛑 Reminder: Pre-Finalization Check

**This decision must be cross-checked with 2.5 Pro** to ensure the integration point does not conflict with advanced topics or architectural assumptions being made in Week 13/14 regarding the GenAI model integration or final deployment strategy.
---

## 2025-10-22 @ 00:08 EDT - Mnemo Log: Review of Muse (Clio) Log & Generalization of Pedagogical Patterns

**Scope:** General Pedagogy, Assessment Design, Workflow Templates

**Description:**
A full review of the detailed decision log from a specialized "Muse" instance (Clio) was conducted. This review identified numerous high-value pedagogical patterns and workflow optimizations that must be generalized and archived in the Mnemo framework for use across all courses.

### 1. Core Pedagogical Patterns (In-Class)

* **The "Full Feedback Loop" Pattern:** In-class technical workshops must move beyond the "happy path" (e.g., a passing test). The learning objective **must** be expanded to include the **intentional creation, diagnosis, and resolution of a failure** (e.g., a "Red Build"). This teaches error diagnosis and resilience, which are the core engineering skills.
* **The "Workshop over Lecture" Model:** Class time should be re-allocated to prioritize deep, hands-on application. The preferred model is a **"Micro-Lecture"** (e.g., 30 min) focused on concepts, followed by a **"Macro-Workshop"** (e.g., 45 min) focused on implementation.
* **The "Needle-Thread" Model (Team vs. Individual Evidence):** This pattern resolves the conflict between team-based process validation and individual-based competency evidence.
    1.  **In-Class (Team Validation):** The team performs *one* end-to-end workflow (e.g., one PR) with TA support to de-risk the process and remove blockers.
    2.  **Homework (Individual Drill):** *Every* student must *individually* perform a parallelized version of the same task (e.g., `N` individual PRs) to generate evidence of individual mastery.
* **Use CI/CD for Policy Enforcement:** Continuous Integration (CI) is a pedagogical tool for teaching *policy and compliance*, not just testing. A "Compliance" job (e.g., for linting, documentation, or license enforcement) must be added to CI pipelines to demonstrate real-world automation of team standards.

### 2. Scaffolding & Cognitive Load Management

* **The "Graded Prerequisite" Pattern:** To de-risk complex workshops, any high-friction, mandatory setup (e.g., environment, tooling) must be moved *out* of the synchronous class time. This setup must be converted into a **small, mandatory, graded preparatory assignment** (e.g., "ICE Prep") due *before* the workshop. This guarantees all students are prepared and provides an evidence-based feedback loop.
* **The "Starter Package" Scaffolding Pattern:** For "greenfield" (from scratch) projects, always provide a "starter package" (`.zip`). This package must include all boilerplate process files (`LICENSE`, `CONTRIBUTIONS.md`) and basic configuration (`requirements.txt`, placeholder tests) to shift the in-class focus from "boilerplate creation" to "practical utilization."
* **Containerize Complex Dependencies:** To eliminate setup friction for workshops requiring complex services (e.g., databases, message queues), mandate the use of **pre-configured public Docker containers**. This provides a universal, OS-agnostic configuration (e.g., a single connection string) for all students and scaffolds future orchestration topics.
* **Refocus Initial Setup Goal to "Team Sync":** The in-class "Definition of Done" for initial, high-friction setup workshops should **not** be "submit the final deliverable." The goal must be **"Team Synchronization"** (e.g., all members have successfully `git pull`-ed a change). This focuses high-value, TA-supported time on collaborative blocker removal and defers the low-friction administrative task (e.g., opening a PR) to homework.

### 3. Workflow Templates & Standardization

* **The "Pedagogical OS" Template:** All In-Class Exercises (ICEs) must follow a standardized, multi-part template. This template must conclude with a mandatory "closing ritual" (e.g., Process Log update, Definition of Done checklist, Submission instructions) to create a predictable, low-anxiety micro-sprint structure.
* **Mandatory Role Rotation Policy:** A course-wide policy must be established and enforced: **"A student cannot hold the same role for more than two consecutive weeks."** This is the primary mechanism to prevent role typecasting and ensure all students practice all components of the workflow (e.g., repo administration, project management, development).
* **Standardize All Naming Conventions:** All student-created assets (especially repositories) must follow a strict, predictable naming convention (e.g., `[Semester]-[CourseID]-[TeamID]-[ProjectName]`) to reduce administrative overhead. Assignment names must also be formal and descriptive (e.g., "Week 9 ICE Prep") rather than informal jargon ("Lab 0").
* **The "References First" Workflow:** When designing a new module, the **Canonical Reference Guide** (linking to authoritative external documentation) must be generated *first*. This allows all subsequent lectures and exercises to be populated with high-quality, authoritative links, reducing student friction.

### 4. Evidence-Gathering & Assessment

* **`CONTRIBUTIONS.md` as a Qualitative Evidence Tool:** The standardized team process log (`CONTRIBUTIONS.md`) is not just a ledger. It must be upgraded to include a mandatory, **open-ended reflection question** tailored to each exercise. This captures qualitative evidence of the team's engineering process or ethical considerations.
* **The "Dual-Track" Master Plan:** The course "master plan" must be structured in two parts to provide a holistic view of all learning vectors:
    1.  **Part 1 (Synchronous):** The in-class lecture and workshop sequence.
    2.  **Part 2 (Asynchronous):** The deliverable-driven "Skill Kits" (e.g., Project Management, Extra Credit, Ethical Challenges) that are scaffolded across the semester.
* **The "Bi-Weekly Review" Model:** High-stakes, formal "Interviews" or "Presentations" are to be replaced. The new model is a **bi-weekly, low-stakes "Review"** scheduled flexibly between the TA and the team. This increases the frequency and lowers the-anxiety of the feedback loop.
* **Re-balancing Assessment Mix:** Acknowledge any deficits in the assessment mix (e.g., too few individual, quantitative checks) from prior modules. Subsequent modules must add low-stakes quizzes to compensate and provide more frequent, individual-level evidence of comprehension.
* **Integrate Ethical/Security Prompts:** Foundational technology lectures (e.g., networking protocols, frameworks) must be explicitly tied to their security and ethical implications. This can be achieved by:
    1.  Elevating critical security content from speaker notes to **dedicated slides**.
    2.  Justifying tool choice based on **security and risk reduction**, not just convenience.
    3.  Analyzing the **data-profiling and side-channel implications** of low-level technical standards.