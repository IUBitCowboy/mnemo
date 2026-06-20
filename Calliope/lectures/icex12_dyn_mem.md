# ICEX: The Growable Roster — Dynamic Arrays in Action

**Duration:** 30 minutes
**Learning Goals:** Allocate with `malloc`/`calloc`, grow a buffer with `realloc`, observe pointer invalidation, free correctly, and use `valgrind` to verify clean memory.

---

## Background

You are building a dynamically-sized roster that can hold any number of student IDs without knowing the count at compile time. You will implement a simple growable array — the same pattern used inside `getline`, `std::vector`, and virtually every real-world C container.

---

## Starter Code

The supplied file is in `exercises/wk10/icex12/roster_dyn.c` in the class repository.

```bash
# Pull the starter file from the class repo
git pull upstream main

# Compile
gcc -g -Wall -Wextra -std=c11 -o roster_dyn.o roster_dyn.c
```

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INITIAL_CAP 4

typedef struct {
    int   *data;      // heap-allocated array of student IDs
    size_t size;      // number of elements currently stored
    size_t capacity;  // number of elements allocated
} DynRoster;

/* ---- Functions you implement ---- */

/* Task 1: Initialise a DynRoster.
   Allocate an int array of INITIAL_CAP elements (zeroed).
   Set size = 0, capacity = INITIAL_CAP. */
void roster_init(DynRoster *r);

/* Task 2: Append a student ID to the roster.
   If size == capacity, double the capacity with realloc before appending.
   Update size after the append. */
void roster_push(DynRoster *r, int id);

/* Task 3: Free the roster's heap data and zero all fields. */
void roster_free(DynRoster *r);

/* ---- Provided helpers — do not modify ---- */

void roster_print(const DynRoster *r) {
    printf("Roster (%zu/%zu): ", r->size, r->capacity);
    for (size_t i = 0; i < r->size; i++) {
        printf("%d ", r->data[i]);
    }
    printf("\n");
}

int main(void) {
    DynRoster r;
    roster_init(&r);

    /* Add 10 students — this will force at least one realloc */
    for (int id = 1001; id <= 1010; id++) {
        roster_push(&r, id);
        roster_print(&r);
    }

    /* Task 4 — see README.md */

    roster_free(&r);
    return 0;
}
```

---

## Tasks

**Task 1 — `roster_init`**
Implement `roster_init`. Use `calloc` so that unused slots are zeroed. Run the program; it should crash or produce wrong output until Task 2 is done.

**Task 2 — `roster_push`**
Implement `roster_push`. When `size == capacity`, double `capacity` and call `realloc`. Use a temporary pointer for the `realloc` return — do not overwrite `r->data` before checking for `NULL`. Run the program; the print output should show the roster growing correctly.

**Task 3 — `roster_free`**
Implement `roster_free`. Free `r->data`, then set `r->data = NULL`, `r->size = 0`, `r->capacity = 0`. Run `valgrind --leak-check=full ./roster_dyn` — the goal is 0 errors and 0 bytes leaked.

**Task 4 — Pointer Invalidation (written answer in README.md)**
Before calling `roster_free`, add this code immediately after the loop:
```c
int *snapshot = r.data;          // pointer into the current block
roster_push(&r, 9999);           // may trigger a realloc
printf("snapshot == r.data? %s\n",
       snapshot == r.data ? "YES (no move)" : "NO  (block moved — snapshot is dangling!)");
```
Run it several times. Answer the questions in `README.md`.

**Task 5 — valgrind (written answer in README.md)**
Run `valgrind --leak-check=full --track-origins=yes ./roster_dyn.o` on your completed program. Paste the HEAP SUMMARY and ERROR SUMMARY lines into `README.md` and explain what they mean.

---

## Expected Final Output

A correct run (capacities will double: 4 → 8 → 16):
```
Roster (1/4):  1001
Roster (2/4):  1001 1002
Roster (3/4):  1001 1002 1003
Roster (4/4):  1001 1002 1003 1004
Roster (5/8):  1001 1002 1003 1004 1005
...
Roster (10/16): 1001 1002 1003 1004 1005 1006 1007 1008 1009 1010
```

---

## Submission Instructions

1. Work in a feature branch:
   ```bash
   git checkout -b icex12-dynroster
   ```
2. Your submission directory must contain exactly two files:
   - `exercises/wk10/icex12/roster_dyn.c` — your completed implementation
   - `exercises/wk10/icex12/README.md` — your written answers for Tasks 4 and 5
3. Commit both files:
   ```bash
   git add exercises/wk10/icex12/roster_dyn.c exercises/wk10/icex12/README.md
   git commit -m "icex12: dynamic roster"
   ```
4. Push and open a Pull Request to your `main` branch on `github.iu.edu`:
   ```bash
   git push -u origin icex12-dynroster
   ```
   Then open a PR on GitHub and **request a review** from your TA or instructor. Grading happens in the PR.

> **If you don't have the class repo configured as `upstream`**, you can copy `roster_dyn.c` directly from the class repo on `github.iu.edu` and paste it into the file manually.

> **Verify your README renders correctly** by navigating to your branch on `github.iu.edu` — GitHub renders Markdown automatically.

---

## README.md Template

See `exercises/wk10/icex12/README.md` (provided separately).

---

## Rubric

| Task | Points | Criteria |
|------|--------|----------|
| Task 1 — `roster_init` | 2 | Allocates with `calloc`, sets `size = 0`, `capacity = INITIAL_CAP` |
| Task 2 — `roster_push` | 2 | Doubles capacity via `realloc` with temp pointer, increments `size` |
| Task 3 — `roster_free` | 2 | Frees data, nulls pointer, zeros fields; valgrind reports 0 leaks |
| Task 4 — Pointer invalidation (written) | 2 | Correct explanation of when/why the block moves and what that means for `snapshot` |
| Task 5 — valgrind (written) | 2 | Correct interpretation of HEAP SUMMARY and ERROR SUMMARY |
| **Total** | **10** | |
