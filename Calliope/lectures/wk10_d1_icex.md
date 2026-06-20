# ICEX: The Student Roster — Structs in Action

**Duration:** 30 minutes
**Learning Goals:** Define and initialize structs, access fields with `.` and `->`, pass by value vs pointer, return a struct, spot a padding surprise.

---

## Background

You are building a minimal student roster for a course. Each student has a name, a student ID, and five lab scores. You will implement several functions to operate on this data.

---

## Starter Code
The starter file is already in the class repository at:

```
exercises/wk10/icex11/roster.c
```

If your `upstream` remote is configured correctly, pull it down:

```bash
git pull upstream main
```

If you have not configured `upstream`, you can copy the file directly — navigate to `exercises/wk10/icex11/roster.c` on [github.iu.edu](https://github.iu.edu), click **Raw**, and paste the contents into your local file at the same path.

---

## Tasks

### Part 1 — Implement `print_student` (5 min)
Print the student's name, ID, and all five lab scores on one line. Use `->` notation since the parameter is a pointer.

Expected output:
```
Alice (1001): labs = [88, 92, 75, 95, 84]
Bob   (1002): labs = [70, 65, 80, 72, 68]
```

---

### Part 2 — Implement `compute_stats` (8 min)
Loop through `s.labs` (use `.` — `s` is a struct, not a pointer) to find the sum, highest, and lowest. Compute the float average. Return the completed `struct Stats`.

---

### Part 3 — Implement `set_lab_score` (5 min)
Validate the lab index, then update the score through the pointer. Verify: Bob's average should improve after the update.

---

### Part 4 — The sizeof Experiment (5 min)
Run the program and look at the sizeof output.

Record your answers in the **Theory/Experiment table** in `README.md` (column headers are already there — fill in your theory before running, then the actual result after).

**Hint:** Draw the byte layout of `struct Stats` by hand. Where does the `float` sit? Where does the first `int` start?

---

### Part 5 — The Hidden Bug (7 min)

Notice that `compute_stats` takes `struct Student` **by value**. Add a `printf` inside `compute_stats` to try to change `s.name`:

```c
strcpy(s.name, "HACKED");
```

Then print `alice.name` back in `main`. Does it change? **Why or why not?**

Record your answers in the **Observation table** in `README.md`.

---

## Expected Final Output
```
Alice (1001): labs = [88, 92, 75, 95, 84]
Bob   (1002): labs = [70, 65, 80, 72, 68]
Alice avg=86.8 hi=95 lo=75
Bob   avg=76.0 hi=95 lo=65

--- sizeof experiment ---
sizeof(char):          1
sizeof(int):           4
sizeof(float):         4
sizeof(struct Stats):  12
Manual sum (f+i+i):    12
```

*(Note: Stats happens to have no padding on most platforms — a good counterexample that not all structs are padded. Ask: what would happen if you added a `char` field?)*

---

## Submission Instructions

### What to Submit

Work in a **feature branch** — do not commit directly to `main`:

```bash
git checkout -b icex11
```

Complete both deliverables:

| File | What goes in it |
|---|---|
| `exercises/wk10/icex11/roster.c` | Your completed implementation (Tasks 1–3, plus the Task 5 modification) |
| `exercises/wk10/icex11/README.md` | Your written answers for Tasks 4 and 5 |

Commit and push when you are done:

```bash
git add exercises/wk10/icex11/roster.c exercises/wk10/icex11/README.md
git commit -m "icex11: structs roster exercise"
git push -u origin icex11
```

Then open a **Pull Request** from your `icex11` branch to your own `main` branch on GitHub and **request a review** from your TA or instructor. Grading takes place on the PR — **do not merge before it is graded**.

Copy the PR URL. Go to the assignment in Canvas and paste the URL to submit your work to Canvas.

---

## Rubric

**Total: 10 points** (2 points per task)

| Task | Points | Full Credit Criteria |
|---|---|---|
| Task 1 — `print_student` | 2 | Output matches expected format exactly; `->` used correctly throughout |
| Task 2 — `compute_stats` | 2 | Correct average, highest, and lowest; `struct Stats` returned by value; `.` used on the value parameter |
| Task 3 — `set_lab_score` | 2 | Bounds check present; score updated through pointer; Bob's average reflects the change |
| Task 4 — sizeof Experiment | 2 | README table filled in with both a theory and the actual result; explanation addresses padding (or lack thereof) for `struct Stats` |
| Task 5 — Hidden Bug | 2 | README confirms `alice.name` is unchanged; explanation correctly invokes pass-by-value; pointer alternative correctly predicted |
| **Total** | **10** | |