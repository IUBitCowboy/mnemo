# Lecture: Function Pointers and Signal Handlers — Callbacks and OS Events

## Slide 1: Title Slide
- **Topic:** Function Pointers, qsort(), and POSIX Signal Handlers
- **Course:** C291 — System Programming with C and Linux
- **Timing:** 40-min lecture + 30-min ICEX + 5-min buffer = 75 min

---

## Slide 2: Learning Objectives
By the end of this lecture, you will be able to:

- Declare, assign, and call a function pointer variable
- Define a `typedef` for a function pointer type to reduce syntactic noise
- Explain the callback pattern and implement it by passing a function pointer as a parameter
- Write a comparator function conforming to `qsort()`'s contract and apply `const void *` casting correctly
- Register a signal handler with `signal()` and explain what happens when the OS delivers a signal
- Use `signal(SIGPIPE, SIG_IGN)` and `SIGCHLD` handling to make the httpd v2 server loop robust
- Distinguish `signal()` from `sigaction()` and know when the latter is necessary
- Choose between `fdopen()` and raw `write()` for pipe output and explain the buffering and double-close traps of each

---

## Slide 3: Functions Are Addresses

- **Key Point:** Every function in a C program has an address in memory — the address of its first instruction. A function pointer is a variable that holds that address, allowing you to call a function indirectly, pass it to other functions, or store it in a struct.
- **Code Example:**
```c
#include <stdio.h>

void greet(const char *name) {
    printf("Hello, %s\n", name);
}

int main(void) {
    /* greet is a function — its name is also its address */
    printf("greet lives at: %p\n", (void *)greet);

    /* We can store that address */
    void (*fp)(const char *) = greet;   /* fp is a function pointer */

    /* And call through it */
    fp("world");      /* same as greet("world") */
    (*fp)("world");   /* also valid — explicit dereference */

    return 0;
}
```
- **Speaker Note:** Ask: "Where have you seen functions treated as values before?" If students have used Python or Java lambdas/callbacks, this is the same concept with explicit pointer syntax. The address model is important — a function pointer is just an integer that the CPU jumps to. `(void *)greet` lets us print it with `%p`; omit that cast and some compilers warn. Both `fp(...)` and `(*fp)(...)` are valid C; the former is idiomatic.

---

## Slide 4: Function Pointer Syntax — Parsing the Declaration

- **Key Point:** The declaration `return_type (*name)(param_types)` follows C's inside-out reading rule. The parentheses around `*name` are required — without them you get a function returning a pointer, not a pointer to a function.
- **Code Example:**
```c
/* Read inside-out: "fp is a pointer (*fp) to a function
   that takes (int, int) and returns int" */
int (*fp)(int, int);

/* Common comparator type for sorting */
int (*cmp)(const void *, const void *);

/* Signal handler: takes an int (signal number), returns void */
void (*handler)(int);

/* These look similar but are DIFFERENT things: */
int  *f1(int, int);      /* function returning int* — NOT a function pointer */
int (*f2)(int, int);     /* pointer to function returning int — IS a function pointer */
```
- **Speaker Note:** Write both declarations side-by-side on the board. The placement of `*` is the only difference and students will misread it. The inside-out rule: start at the name, go right as far as possible (parameters), then go left (return type, with the `*` meaning "pointer to"). Force students to parse `void (*handler)(int)` aloud before moving on.

---

## Slide 5: typedef — Cleaning Up Function Pointer Syntax

- **Key Point:** A `typedef` for a function pointer type names the type once and lets you use the clean name everywhere. This is how system headers like `<signal.h>` define `sighandler_t`.
- **Code Example:**
```c
/* Without typedef: noisy and error-prone */
int (*cmp1)(const void *, const void *) = some_comparator;
void sort_array(int *arr, size_t n, int (*cmp)(const void *, const void *));

/* With typedef: clear and reusable */
typedef int  (*Comparator)(const void *, const void *);
typedef void (*SignalHandler)(int);

/* Now declarations read like any other type */
Comparator  cmp2   = some_comparator;
SignalHandler sh    = my_handler;

void sort_array(int *arr, size_t n, Comparator cmp);

/* Assigning NULL is valid — indicates "no function assigned yet" */
Comparator  cmp3 = NULL;
```
- **Speaker Note:** The typedef form is what students will see in production headers and man pages. `sighandler_t` in `<signal.h>` is `typedef void (*sighandler_t)(int)`. Show the `<signal.h>` man page or header. Ask: "What does `Comparator cmp = NULL` mean?" Answer: the pointer holds the null address — dereferencing it (calling `cmp(...)`) would crash, just like any null pointer dereference. Good to check before calling.

---

## Slide 6: The Callback Pattern

- **Key Point:** A callback is a function you write that you pass to another function to call back at the right moment. The called function doesn't know what you'll do — it just knows the signature. This is the core pattern behind `qsort`, signal handlers, and event-driven programming.
- **Code Example:**
```c
typedef void (*Callback)(int value);

/* A function that applies a callback to each element */
void for_each(int *arr, size_t n, Callback cb) {
    for (size_t i = 0; i < n; i++) {
        cb(arr[i]);    /* call back into the caller's code */
    }
}

/* Two different callbacks — same signature */
void print_value(int v)  { printf("%d\n", v); }
void double_print(int v) { printf("%d\n", v * 2); }

int main(void) {
    int data[] = {3, 1, 4, 1, 5};
    for_each(data, 5, print_value);   /* prints each value */
    for_each(data, 5, double_print);  /* prints each doubled */
    return 0;
}
```
- **Speaker Note:** The key insight: `for_each` is written once and works with any callback conforming to `void f(int)`. The caller supplies the behavior; the library supplies the structure. This is the same model as `qsort` (you supply the comparison logic, the stdlib supplies the sort algorithm) and signal handlers (you supply the response to SIGINT, the kernel supplies the delivery mechanism).

---

## Slide 7: qsort() — The Standard Library Callback

- **Key Point:** `qsort()` sorts any array of any type because you supply the comparison function. It knows nothing about your data — it only knows sizes and how to call your comparator. This is the most important callback in the C standard library.
- **Code Example:**
```c
#include <stdlib.h>

/* Signature — memorize this */
void qsort(void  *base,     /* pointer to first element */
           size_t nmemb,    /* number of elements */
           size_t size,     /* size of each element in bytes */
           int  (*compar)(const void *, const void *));
                            /* your comparator function */

/* Contract: compar(a, b) must return:
     negative  if *a should come BEFORE *b
     zero      if *a equals *b (for sorting purposes)
     positive  if *a should come AFTER *b              */

/* Example: sort an int array ascending */
int cmp_int_asc(const void *a, const void *b) {
    int x = *(const int *)a;
    int y = *(const int *)b;
    return x - y;   /* negative if x < y, 0 if equal, positive if x > y */
}

int arr[] = {5, 2, 8, 1, 9};
qsort(arr, 5, sizeof(int), cmp_int_asc);
/* arr is now: {1, 2, 5, 8, 9} */
```
- **Speaker Note:** The `void *` parameters are what make qsort generic — it can point at any type. qsort will call your comparator with pointers into the array; it is your job to cast them to the right type inside. The `return x - y` trick for integers works when overflow is not a concern (values in a reasonable range); for safety-critical code use `return (x > y) - (x < y)` instead. Ask: "What would the comparator look like for descending order?" Answer: swap a and b, or negate the return.

---

## Slide 8: Writing a Comparator — The void* Cast Pattern

- **Key Point:** Inside a comparator, the `const void *` parameters must be cast to the actual element type before dereferencing. Get the cast right once and the pattern is the same every time.
- **Code Example:**
```c
typedef struct {
    char name[32];
    int  score;
    int  id;
} Student;

/* Sort by score, ascending */
int cmp_by_score_asc(const void *a, const void *b) {
    const Student *sa = (const Student *)a;
    const Student *sb = (const Student *)b;
    return sa->score - sb->score;
}

/* Sort by name, alphabetical */
int cmp_by_name_alpha(const void *a, const void *b) {
    const Student *sa = (const Student *)a;
    const Student *sb = (const Student *)b;
    return strcmp(sa->name, sb->name);   /* strcmp already returns neg/0/pos */
}

Student roster[10];  /* assume populated */

qsort(roster, 10, sizeof(Student), cmp_by_score_asc);
/* roster now sorted lowest to highest score */

qsort(roster, 10, sizeof(Student), cmp_by_name_alpha);
/* roster now sorted A-Z by name */
```
- **Speaker Note:** The cast is the only new syntax — and it's the same cast students already know from dynamic memory: `(const Student *)a`. The `const` is important: qsort's contract says it will not modify the elements through these pointers; the const signals that to the compiler. Connect to the RPG assignment: "How did you sort your crew table for display? Now you can do it in two lines." `strcmp` returning neg/0/pos by convention is why it plugs directly into a comparator — it was designed for this.

---

## Slide 9: Multiple Comparators — qsort's Real Power

- **Key Point:** Because the comparator is passed at call time, you can sort the same array multiple ways without changing the data or writing a new sort function. This is the callback pattern's payoff.
- **Code Example:**
```c
/* Descending score — just negate ascending */
int cmp_by_score_desc(const void *a, const void *b) {
    return cmp_by_score_asc(b, a);   /* swap a and b */
}

/* Sort by ID */
int cmp_by_id(const void *a, const void *b) {
    const Student *sa = (const Student *)a;
    const Student *sb = (const Student *)b;
    return sa->id - sb->id;
}

Student roster[10];

/* High score first for the leaderboard */
qsort(roster, 10, sizeof(Student), cmp_by_score_desc);
print_roster(roster, 10);

/* Then re-sort by ID for the gradebook */
qsort(roster, 10, sizeof(Student), cmp_by_id);
print_roster(roster, 10);
```
- **Speaker Note:** The `cmp_by_score_desc` trick — swapping a and b — is idiomatic C. Ask: "Why does swapping a and b reverse the order?" Because the contract says negative means 'a before b'; if we swap, then what was 'a before b' becomes 'b before a' — i.e., descending. Also ask: "Could you store an array of comparator function pointers and pick one based on a command-line flag?" Yes — and that's a menu-driven sort, exactly the kind of thing their httpd's logging or the RPG assignment's display could use.

---

## Slide 10: Signals — The OS Asynchronous Event Model

- **Key Point:** A signal is an asynchronous notification delivered by the OS (or another process) to a running process. It interrupts whatever the process is doing. Each signal has a default action; you can override it by registering a handler function.
- **Diagram:**
```
Normal execution:
  main() → server_loop() → read_request() → ...

Signal delivery (e.g. user hits Ctrl-C → SIGINT):
  read_request() is interrupted
  CPU jumps to your signal handler function
  handler runs to completion
  execution resumes (or process exits, depending on handler)

Common signals:
  SIGINT  (2)  — Ctrl-C: interactive interrupt
  SIGTERM (15) — polite termination request (kill PID)
  SIGPIPE (13) — write to a pipe with no reader
  SIGCHLD (17) — a child process changed state (exited, stopped)
  SIGSEGV (11) — segmentation fault (usually fatal)
```
- **Speaker Note:** The asynchronous nature is the key mental model shift. A signal can arrive at any point — between any two instructions. This has implications for what is safe to do inside a handler (more on that in a moment). Ask: "What has sent you signals so far in this course?" Ctrl-C (SIGINT) every time they killed a hanging program. The valgrind output showing "Killed" or "Terminated" — that's a signal. The "Segmentation fault" — that's SIGSEGV.

---

## Slide 11: signal() — Registering a Handler

- **Key Point:** `signal(signum, handler)` tells the OS: when signal `signum` arrives, call `handler` instead of taking the default action. Two special values: `SIG_IGN` (ignore) and `SIG_DFL` (restore default).
- **Code Example:**
```c
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

/* The handler signature is fixed: takes int (signal number), returns void */
void handle_sigint(int sig) {
    /* sig tells you which signal was delivered (useful if one handler
       handles multiple signals) */
    write(STDOUT_FILENO, "\nCaught SIGINT — shutting down.\n", 32);
    /* Note: printf is NOT async-signal-safe — use write() in handlers */
    _exit(0);   /* _exit() is async-signal-safe; exit() is not */
}

int main(void) {
    signal(SIGINT,  handle_sigint);   /* override Ctrl-C */
    signal(SIGTERM, handle_sigint);   /* same handler for kill PID */
    signal(SIGPIPE, SIG_IGN);         /* ignore broken pipes */

    /* SIG_DFL restores the default action */
    /* signal(SIGINT, SIG_DFL); */

    printf("Running — press Ctrl-C to test handler\n");
    while (1) { pause(); }   /* sleep until a signal arrives */
    return 0;
}
```
- **Speaker Note:** The async-signal-safety rule: inside a signal handler you may only call functions listed as async-signal-safe in the POSIX standard. `printf`, `malloc`, `free` are NOT on that list — they use internal locks and can deadlock if interrupted mid-call. `write()`, `_exit()`, and setting a `volatile sig_atomic_t` flag are safe. The cleanest pattern: set a flag in the handler, check the flag in the main loop, do the real work there. Show this pattern on the next slide.

---

## Slide 12: The Safe Handler Pattern — volatile sig_atomic_t

- **Key Point:** The safest signal handler sets a flag and returns immediately. The main loop checks the flag. This keeps all non-async-signal-safe work out of the handler.
- **Code Example:**
```c
#include <signal.h>
#include <stdio.h>

/* volatile: tells compiler "this may change without warning — don't optimize away reads"
   sig_atomic_t: guaranteed to be readable/writable atomically on this platform */
volatile sig_atomic_t keep_running = 1;

void handle_sigint(int sig) {
    (void)sig;          /* suppress unused-parameter warning */
    keep_running = 0;   /* set flag — that's all */
}

int main(void) {
    signal(SIGINT, handle_sigint);

    printf("Server running. Ctrl-C to stop.\n");
    while (keep_running) {
        /* do server work — check keep_running each iteration */
    }
    /* Reached when SIGINT arrives */
    printf("Shutting down cleanly.\n");
    /* free resources, close files, flush logs */
    return 0;
}
```
- **Speaker Note:** `volatile` is essential here — without it the compiler may cache `keep_running` in a register and never re-read it from memory, so the loop never sees the change. `sig_atomic_t` is typically `int` but is guaranteed to be atomically readable on the platform. Ask: "What if the signal arrives between checking `keep_running` and the next iteration?" The loop exits on the next check — at most one extra iteration. For an HTTP server that's fine.

---

## Slide 13: SIGPIPE and SIGCHLD — The httpd Server's Two Signal Problems

- **Key Point:** Two signals are directly relevant to the httpd v2 server loop. Both have clean solutions that build directly on the patterns just introduced.
- **Code Example:**
```c
/* SIGPIPE — browser disconnects while we're writing the response */
signal(SIGPIPE, SIG_IGN);
/* write() now returns -1 with errno == EPIPE instead of killing the server */

/* SIGCHLD — nc child process exits; kernel notifies parent */
/* Without handling: zombie processes accumulate */
/* Option 1: ignore SIGCHLD — kernel auto-reaps children (Linux) */
signal(SIGCHLD, SIG_IGN);

/* Option 2: explicit reap in handler — portable, gives you exit status */
void handle_sigchld(int sig) {
    (void)sig;
    int status;
    /* WNOHANG: don't block if no child has exited yet */
    while (waitpid(-1, &status, WNOHANG) > 0) {
        /* reap all exited children */
    }
}
signal(SIGCHLD, handle_sigchld);
```
- **Speaker Note:** Connect SIGPIPE explicitly to slide 12 of last lecture — "this is the line I told you to add; now you know exactly what it does and why." For SIGCHLD: without reaping, each exited nc becomes a zombie (process table entry that can't be removed). `waitpid(-1, ...)` with `-1` means "any child." `WNOHANG` is essential inside the signal handler — without it the handler would block waiting for a child that hasn't exited yet, which could cause the server to hang. Option 1 (ignore) is simpler; Option 2 is what you use when you care about the exit status.

---

## Slide 14: sigaction() — The POSIX-Correct Alternative

- **Key Point:** `signal()` has portability quirks — on some systems the handler is reset to `SIG_DFL` after the first delivery, requiring re-registration. `sigaction()` is the POSIX standard, has consistent behavior across platforms, and is what production code uses.
- **Code Example:**
```c
#include <signal.h>

struct sigaction sa;
sa.sa_handler = handle_sigint;     /* the handler function */
sigemptyset(&sa.sa_mask);          /* no additional signals blocked during handler */
sa.sa_flags = SA_RESTART;          /* restart interrupted syscalls automatically */

sigaction(SIGINT,  &sa, NULL);     /* NULL: don't need old action */
sigaction(SIGTERM, &sa, NULL);

/* SA_RESTART: without this flag, a signal that arrives during read() or write()
   causes them to return -1 with errno == EINTR.
   With SA_RESTART, the kernel automatically retries the syscall.
   For our server loop this is almost always what we want.             */
```
- **Speaker Note:** Students will see `sigaction` in man pages, system headers, and production code — they need to recognize it. The `sigemptyset` + `SA_RESTART` pattern is the standard boilerplate. The practical difference from `signal()` for this course is small; the conceptual takeaway is: "signal() is fine for simple cases; sigaction() is what you use when you need to be right." For the httpd project, either works; `sigaction` with `SA_RESTART` is the better choice because it handles interrupted `read()` calls without extra errno checks.

---

## Slide 15: Pulling It Together — The Hardened Server Loop

- **Key Point:** With function pointers, signal handlers, and the patterns from wk14, the httpd v2 `main()` reads like a specification: set up signals, open the log, run the loop.
- **Code Example:**
```c
int main(int argc, char *argv[]) {
    const char *port    = (argc > 1) ? argv[1] : "8080";
    const char *log_dir = (argc > 2) ? argv[2] : "logs";

    /* Signal setup */
    signal(SIGPIPE, SIG_IGN);              /* ignore broken pipes */
    signal(SIGCHLD, SIG_IGN);             /* auto-reap nc children */
    signal(SIGINT,  handle_sigint);        /* clean shutdown on Ctrl-C */
    signal(SIGTERM, handle_sigint);        /* clean shutdown on kill */

    FILE *logfp = open_log(log_dir);
    fprintf(stderr, "httpd v2 on port %s\n", port);

    /* The loop runs until keep_running is cleared by SIGINT/SIGTERM */
    while (keep_running) {
        int to_nc[2], from_nc[2];
        if (create_pipes(to_nc, from_nc) < 0) continue;

        pid_t pid = spawn_nc(port, to_nc, from_nc);
        if (pid < 0) continue;

        char buf[BUF_SIZE];
        ssize_t n = read_request(from_nc[0], buf, BUF_SIZE);
        if (n > 0) handle_request(to_nc[1], buf, logfp);

        close(to_nc[1]);       /* EOF → nc closes connection */
        close(from_nc[0]);
        waitpid(pid, NULL, 0);
    }

    fprintf(logfp, "=== httpd v2 stopped ===\n");
    fclose(logfp);
    return 0;
}
```
- **Speaker Note:** This is the completed v2 skeleton. Every concept from the last three weeks appears here: structs, dynamic memory (inside handle_request), bit-masks (in the response options), fork/exec, pipes, macros, and now signal handlers. Ask: "Which line from this lecture prevents silent server crashes?" `signal(SIGPIPE, SIG_IGN)`. "Which pattern lets the server shut down cleanly?" The `keep_running` volatile flag pattern from Slide 12.

---

## Slide 16: File Descriptors vs. FILE* — fdopen() and Raw write()

- **Key Point:** Your v1 handler used `printf` and `fprintf` — stdio functions that expect a `FILE *`. Your v2 handler receives a raw Unix file descriptor (`int`). These are two different I/O layers. You have two choices: use `write()` directly on the FD, or use `fdopen()` to wrap the FD in a `FILE *` and keep your existing stdio calls.
- **Code Example:**
```c
/* --- Option A: raw write() ------------------------------------ */
/* Build the full response into a buffer first, send in one shot */
void handle_request(int write_fd, const char *req, FILE *logfp) {
    char resp[BUF_SIZE];
    int  len = snprintf(resp, sizeof(resp),
                   "HTTP/1.1 200 OK\r\n"
                   "Content-Type: text/html\r\n"
                   "Content-Length: 5\r\n\r\n"
                   "hello");
    write(write_fd, resp, len);   /* one syscall, no buffering */
}

/* --- Option B: fdopen() --------------------------------------- */
/* Wrap the FD — keeps your v1 fprintf/fwrite calls intact       */
void handle_request(int write_fd, const char *req, FILE *logfp) {
    FILE *out = fdopen(write_fd, "w");
    if (!out) { perror("fdopen"); return; }

    fprintf(out, "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n");
    fprintf(out, "<html><body>hello</body></html>\r\n");

    fclose(out);   /* flushes stdio buffer AND closes write_fd   */
    /* DO NOT call close(write_fd) after fclose — double-close!  */
}
```
- **Speaker Note:** Two subtle traps to call out explicitly. (1) **stdio buffering**: `fdopen()` wraps the FD in a buffered stream. If you never call `fclose()` or `fflush()`, the response may sit in the buffer and never reach nc — the browser hangs. The rule: always `fclose()` the `fdopen()`'d stream before `waitpid()`. (2) **Double-close**: `fclose()` closes the underlying FD. If you also call `close(write_fd)` afterwards you are double-closing — undefined behavior (see the dynamic memory lecture). Pick one layer and stay in it. The `write()` path avoids both traps at the cost of building the response in a buffer first — which you're already doing with `snprintf` for `Content-Length` anyway, so it's a natural fit. Either approach is acceptable in the assignment; just don't mix them on the same FD.

---

## Slide 17: Key Takeaways + What's Next

**Takeaways:**
- A function pointer is a variable holding a function's address: `return_type (*name)(params)`; `typedef` makes the type reusable
- `qsort()` is the canonical callback: you supply the comparator, the stdlib supplies the algorithm; the `const void *` cast is the one new syntax
- Signal handlers are function pointers registered with the OS via `signal()` or `sigaction()`
- Inside a handler: only async-signal-safe operations — set a `volatile sig_atomic_t` flag and return; do real work in the main loop
- `SIGPIPE SIG_IGN` + `SIGCHLD SIG_IGN` + a `keep_running` flag covers the three signal needs of httpd v2
- `sigaction()` is the POSIX-correct form; `SA_RESTART` handles interrupted syscalls automatically
- `fdopen()` wraps a raw FD in a `FILE *` for stdio convenience — always `fclose()` before `waitpid()`, never `close()` the same FD afterwards; raw `write()` avoids both traps at the cost of building responses in a buffer first

**Next:** File I/O — `open()`, `read()`, `write()`, `stat()`. The httpd server needs to read files from disk and serve them. The system call interface is the same pipe-and-fd model you already know.

> *"A function pointer is just a variable that holds a 'what to do.' A signal handler is just a function pointer registered with the OS. Once you see both as the same pattern — store an address, call it later — neither is mysterious."*

---

> **In-class exercise:** See `icex19_sort_signals.md`

**Duration:** 30 minutes
**Learning Goals:** Write multiple qsort comparators with correct void* casting, use the flag-based signal handler pattern, and apply SIGPIPE handling in the context of the server.

---

## Background

Two independent exercises: the first builds qsort muscle memory using a struct you've seen before; the second wires a clean-shutdown signal handler into a small server skeleton.

---

## Starter Code

```bash
git pull upstream main
# exercises/wk15/icex15a/sort_signals.c
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

1. Branch: `git checkout -b icex15a-sort-signals`
2. Files: `exercises/wk15/icex15a/sort_signals.c`
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
