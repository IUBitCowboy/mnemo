Late Policy & The "Hero's Grace"

Late Submissions: Doing the work correctly is 85% of the work and being on time is 15%. All work submitted past the due date or extension, will be capped at 85% score. 

Extensions: A student may request an AUTOMATIC one week extension of an assignment by sending an email message to the instructor PRIOR to the assignment due date. The email message documents the request and the instructor will add a note to the Canvas grade book to acknowledge the receipt of the request. 

Any extra credit in an assignment will NOT be capped by the late policy. Legitimate extra effort is never late.

Student requested resubmissions will be treated like a late submission and will be capped at 85%. (Instructor requested resubmissions are not capped.)

Weekly Programming: Conduct & Submission

Development Environment: All code must compile and run on the IU Silo clusters using gcc.

Debugging Log: Each programming assignment needs to have a debug_log.md that contains a log of all significant defects resolved in the program including at least one detailed example demonstrating the scientific method of debugging. A debug_log.m without a detailed example is considered incomplete and equivalent to nothing. 

The Repository Quest: 

The student will use one private code repository homed in github.iu.edu with the name studentID-SP26-C291 and will use seiffert-SP26-C291-class repository as an upstream repository. Students will pull any starter material from the upstream repository.

Each assignment will created on a separate development branch in the repository. Students should commit intermediate trials and any new submissions to the AG. 

The course instructor and all course TA’s will be added as collaborator to the repository. 

Each assignment contains all code and development elements in a separate directory of the form wk01, wk02, etc.

To submit a programming assignment:

1) The student must create a PullRequest to merge the development bench to the main branch. The student must request a review from the instructor or a TA. 

2) The student must then paste the URL link to the PR into the Canvas assignment page.

Once the student has a PR approval from an instructor or TA, the student can complete the merge and close the PR.

Resubmissions will require a new PR and updating the Canvas assignment with the new PR URL. 

Auto-Grading Standards: 

The course uses the AG [link provided later]. The AG will run a series of tests and report scores on each rubric point identified in the assignment specification. The total of these tests scores will be known as the AG-score. The AG-score will represent 85% of the total assignment points. 

The AG supports a mechanism for hand grading, which the TA’s will perform. Hand grading includes the following:

Reviewing submitted code for adequate code comments and symbol names.

Review the debug_log.md for completeness to ensure adequate debugging processes.  

Hand grading score will be no more than 15% of the assignment.

Assignment Score: 

The assignment score entered in the Canvas grade book will be the sum of the AG-score and the hand grading score. 

Resubmissions of programming assignments will only update the AG-score. Resubmissions will NOT have the hand grading regraded.

A complete submitted debug_log.md is 10% of the assignment. 

Academic Integrity: All code submitted must have been authored and entered by the student. The student is not allowed to copy any code from other students or generative AI. 

Students may use generative AI to assist with debugging as long as the session is documented in the debug_log.md. Students will be provided with specific generative AI guidelines for assignments. 

Students are encouraged to communicate on programming assignments and even share example code applied to a different problem than the assignment problem.

C291 Master Syllabus: The Hero’s Journey through SystemsCourse OverviewTitle: C291 System Programming with C and LinuxDuration: 15 Weeks (Starting Jan 12)Schedule: Twice weekly, 75-minute sessions.Break: Spring Break occurs between Week 9 and Week 10.Final Capstone: A functional "Simple Shell" written in C, due Week 15.Student Profile (The Starting Line)Prerequisites: Completion of CSCI-A 201, C 200, C 211, or INFO-I 211.Prior Knowledge: Logic in high-level languages (Java/Python) using modern IDEs.Assumed Gaps: ZERO experience with manual memory management (pointers), the Linux CLI, Vim, or low-level compilation (GCC/Make).Grading & EvaluationWeekly Programming Assignments: 40%Weekly Quizzes/Exercises: 20%Mid-term Exam (Week 9): 20%Final Shell Capstone: 20%Late Policy & The "Hero's Grace"Standard Policy: Doing the work correctly is 85% of the work; being on time is 15%. All work submitted past the due date or approved extension will be capped at an 85% maximum score.Extensions: A student may request an AUTOMATIC one-week extension by emailing the instructor PRIOR to the original due date.Extra Credit: Any designated extra credit in an assignment is NOT capped by the late policy.Resubmissions: Student-requested resubmissions are treated as late and capped at 85%. Instructor-requested resubmissions are not capped.Weekly Programming: Conduct & SubmissionDevelopment Environment: All code must compile and run on the IU Silo clusters using gcc.Debugging Log: Each assignment requires a debug_log.md. It must include at least one detailed example of the Scientific Method of Debugging ([THEORIZE] -> [EXPERIMENT] -> [MODIFY] -> [TEST]). Incomplete logs result in zero credit for the assignment.The Repository Quest:Repo Name: studentID-SP26-C291 (Private, on github.iu.edu).Upstream: seiffert-SP26-C291-class for starter material.Structure: Separate development branches for each assignment. Directories named wk01, wk02, etc.Submission Process: 1. Create a Pull Request (PR) from dev branch to main.2. Request instructor/TA review.3. Paste PR URL into Canvas.4. Merge only AFTER approval.Auto-Grading (AG):AG-Score (85%): Automated tests for functional rubric points.Hand Grading (15%): Review of comments, symbol names, and debug_log.md depth.Academic Integrity: All logic must be student-authored. AI is permitted only for assistance with debugging, and such sessions must be documented in the debug_log.md.The Weekly RoadmapPhase 1: The Awakening (Tools & Fundamentals)Week 1: The Call to AdventureDay 1: The Portal. Setup SSH (Silo), GitHub, and CLI basics (mkdir, ls, cat, man).Day 2: The Scribe’s Tools. vim basics, hello_world.c, gcc basics. Branching and PRs.The Cliffhanger: How does the machine make decisions when we aren't there to watch it?Week 2: The Rules of the RealmDay 1: Logic & Flow. Conditionals (if/switch), Iteration (while/for), and Relational Operators.Day 2: The Test of Character. Bash test harnesses, shell redirection (>, <), and exit codes.The Cliffhanger: What is actually happening inside the hardware when we store a number?Week 3: The Language of the MachineDay 1: The Anatomy of Data. Scalar types, sizes. Binary, Hex, 2’s Complement. ASCII/UTF.Day 2: The Voice of the Machine. Formatted I/O (printf/scanf). Input validation and buffering.The Cliffhanger: How do we build walls around our logic to keep it clean and reusable?Week 4: The Map and the TerritoryDay 1: The Sacred Geometry of Memory. Functions (Call by value), Scope, and the Memory Map. stderr.Day 2: Linear Paths. Arrays (1D) and C-Strings. string.h and the Null Terminator.The Cliffhanger: One-dimensional paths are simple. How do we navigate a world that has multiple dimensions?Phase 2: The Labyrinth (Structures & Pointers)Week 5: The Craft of the ArchitectDay 1: High-Order Structures. Multi-dimensional arrays. Passing arrays to functions. Makefiles basics.Day 2: The Great Mystery: Pointers. Address-of (&) and Dereference (*). Pointer/Array duality.The Cliffhanger: We can point to a variable. But what if we need to point to the pointer itself?Week 6: The Depth of KnowledgeDay 1: The Double Mirror. Double pointers. Command line arguments (argc, argv). Call by reference.Day 2: Creating Entities. struct definitions, typedef, and nested structures. Modularity.The Cliffhanger: How do we manipulate the very bits and switches that define memory?Week 7: Imagine No LimitsDay 1: The Infinite Well. Dynamic Memory (malloc, calloc, realloc, free). valgrind for leaks.Day 2: The Modern Vision. Introduce VS Code remote editing. Scientific Method debugging workshop.The Cliffhanger: What happens when we look beyond our code and into the Ledger of the Operating System?Week 8: The Hidden PatternsDay 1: Shape-shifters. enum, union, and Macro functions. Alignment and padding.Day 2: The Bit-Wise Forge. Bit-masks, operators, and bit-fields. Low-level data packing.The Cliffhanger: You have mastered the single program. But your program is alone.Phase 3: The Mid-Term TrialWeek 9: The Trial of the Senses (MID-TERM WEEK)Assessment: Online Mid-term (Canvas). Covers Weeks 1-8. No programming assignment.Day 1: The Oracle's Lens. gdb and visualizing code execution in VS Code.Day 2: The Ledger of the Realm. Linux Filesystem layout, metadata (stat), and permissions.The Cliffhanger (Pre-Break): When you return, we will learn how to create life—the fork().--- SPRING BREAK ---Phase 4: The Convergence (Processes & Systems)Week 10: The Multiplication of SelfDay 1: The Fork in the Road. fork(), Copy-on-Write, Parent/Child relationship.Day 2: The Duty of the Parent. wait(), waitpid(), and exit(). Zombies/Orphans.Week 11: The TransformationDay 1: The Great Metamorphosis. The exec() family. Replacing the process image.Day 2: The Atmosphere. Environment variables and the PATH.Week 12: The Whispers in the WindDay 1: The Messenger. Signals (signal, sigaction). Handling Ctrl+C and SIGALRM.Day 2: The Redirected Path. dup() and dup2(). Redirection to files.Phase 5: The Trials & The HomecomingWeek 13: The Great ConnectionDay 1: The Pipeline. pipe(). Connecting stdout to stdin.Day 2: The Shared Secret. Advanced IPC (FIFOs, Shared Memory intro).Week 14: The ConvergenceDay 1: The Weaver’s Loom. POSIX Threads (pthreads), Race conditions, and Mutexes.Day 2: The Tiny Machines. Embedded considerations. Defensive programming.Week 15: The Hero’s HomecomingDay 1: The Final Blueprint. Integrating parsing, fork/exec, and pipes.Day 2: The Epic’s End. Final Shell Demonstrations.