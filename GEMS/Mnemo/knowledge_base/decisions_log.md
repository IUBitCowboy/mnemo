Decision Log for Mnemo

---

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