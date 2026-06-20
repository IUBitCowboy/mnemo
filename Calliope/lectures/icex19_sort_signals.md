# ICEX 19: Sort and Survive — qsort Comparators and Signal Handlers

**Duration:** 30 minutes
**Learning Goals:** Write multiple qsort comparators with correct void* casting, use the flag-based signal handler pattern, and apply SIGPIPE handling in the context of the server.

---

## Background

Two independent exercises: the first builds qsort muscle memory using a struct you've seen before; the second wires a clean-shutdown signal handler into a small server skeleton.

---

## Starter Code

```bash
git pull upstream main
# exercises/wk15/icex19/sort_signals.c
gcc -g -Wall -Wextra -std=c11 -o sort_signals sort_signals.c
```

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>

/* ---- Data ---- */
typedef struct {
    char name[32];
    int  score;
    int  id;
} Student;

static Student roster[] = {
    {"Zheng",   88, 1003},
    {"Amara",   95, 1001},
    {"Riley",   72, 1007},
    {"Devon",   88, 1002},
    {"Sasha",   61, 1009},
    {"Morgan",  95, 1005},
};
static const size_t ROSTER_LEN = sizeof(roster) / sizeof(roster[0]);

/* ---- Task 1: Comparators ----------------------------------------
   Implement all three. Follow the const void * cast pattern. */

/* Sort by score ascending (lowest first) */
int cmp_score_asc(const void *a, const void *b);

/* Sort by score descending (highest first) */
int cmp_score_desc(const void *a, const void *b);

/* Sort alphabetically by name (A-Z) */
int cmp_name_alpha(const void *a, const void *b);

/* ---- Task 2: Signal handler infrastructure ---------------------- */

/* Declare keep_running with the correct type and qualifiers */
/* YOUR CODE HERE */

/* Handle SIGINT and SIGTERM: clear keep_running, return */
void handle_shutdown(int sig);

/* ---- Provided: print_roster ---- */
void print_roster(const Student *r, size_t n, const char *label) {
    printf("\n%s:\n", label);
    printf("  %-20s %5s %6s\n", "Name", "Score", "ID");
    printf("  %-20s %5s %6s\n", "----", "-----", "--");
    for (size_t i = 0; i < n; i++) {
        printf("  %-20s %5d %6d\n", r[i].name, r[i].score, r[i].id);
    }
}

/* ---- Task 3: mini server loop ---- */
void run_server(void) {
    printf("\nMini server running (PID %d). Press Ctrl-C to stop.\n",
           getpid());
    int tick = 0;
    while (/* Task 3: use keep_running here */ 1) {
        sleep(1);
        printf("  tick %d\n", tick++);
    }
    printf("Server stopped after %d ticks.\n", tick);
}

int main(void) {
    /* Task 1: sort and display three ways */
    qsort(roster, ROSTER_LEN, sizeof(Student), cmp_score_asc);
    print_roster(roster, ROSTER_LEN, "By score (low to high)");

    qsort(roster, ROSTER_LEN, sizeof(Student), cmp_score_desc);
    print_roster(roster, ROSTER_LEN, "By score (high to low)");

    qsort(roster, ROSTER_LEN, sizeof(Student), cmp_name_alpha);
    print_roster(roster, ROSTER_LEN, "Alphabetical by name");

    /* Task 2: register signal handlers */
    signal(SIGINT,  handle_shutdown);
    signal(SIGTERM, handle_shutdown);
    signal(SIGPIPE, SIG_IGN);

    /* Task 3: run the server loop until signal */
    run_server();

    return 0;
}
```

---

## Tasks

**Task 1 — Three comparators**

Implement `cmp_score_asc`, `cmp_score_desc`, and `cmp_name_alpha`. Rules:
- Cast `const void *` to `const Student *` inside each
- `cmp_score_desc` must reuse `cmp_score_asc` (swap the arguments — one line)
- `cmp_name_alpha` uses `strcmp` on the name field

**Task 2 — Signal handler**

Declare `keep_running` with the correct type (`volatile sig_atomic_t`) and initial value. Implement `handle_shutdown` to clear it. It must be async-signal-safe (no printf, no malloc).

**Task 3 — Fix run_server**

Replace the literal `1` in the while condition with `keep_running`. Run the program, let the sort output print, then Ctrl-C the server loop. Observe the "stopped after N ticks" message — proof the handler ran and the main loop exited cleanly rather than being killed.

---

## Expected Output (abbreviated)

```
By score (low to high):
  Name                 Score     ID
  ----                 -----     --
  Sasha                   61   1009
  Riley                   72   1007
  Zheng                   88   1003
  Devon                   88   1002
  Amara                   95   1001
  Morgan                  95   1005

By score (high to low):
  Morgan                  95   1005
  Amara                   95   1001
  ...

Alphabetical by name:
  Amara                   95   1001
  Devon                   88   1002
  ...

Mini server running (PID 12345). Press Ctrl-C to stop.
  tick 0
  tick 1
  tick 2
^C
Server stopped after 3 ticks.
```

---

## Submission Instructions

1. Branch: `git checkout -b icex19-sort-signals`
2. Files: `exercises/wk15/icex19/sort_signals.c`
3. Commit, push, open PR to `main`, request review.

---

## Rubric

| Task | Points | Criteria |
|------|--------|----------|
| Task 1 — `cmp_score_asc` | 2 | Correct cast; correct return value sign |
| Task 1 — `cmp_score_desc` and `cmp_name_alpha` | 2 | desc reuses asc; alpha uses strcmp |
| Task 2 — `keep_running` declaration and `handle_shutdown` | 2 | Correct type/qualifiers; handler is async-signal-safe |
| Task 3 — `run_server` loop and clean exit message | 2 | Loop exits on signal; shutdown message prints |
| Compiles clean `-Wall -Wextra`; no UB (valgrind clean) | 2 | Zero warnings; zero valgrind errors |
| **Total** | **10** | |
