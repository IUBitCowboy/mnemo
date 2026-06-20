# Lecture 13: fork(), exec(), and Pipes — Process Creation and I/O Wiring

---

## Slide 1: Title Slide

- **Topic:** Process Creation, Program Execution, and Anonymous Pipes
- **Course:** C291 — System Programming with C and Linux
- **Key Functions:** `fork()` · `exec()` · `wait()` · `pipe()` · `dup2()`

---

## Slide 2: Learning Objectives

By the end of this lecture, you will be able to:

- Explain what happens inside the kernel when `fork()` is called
- Describe the child's address space after `fork()` and what Copy-on-Write defers
- Write the canonical two-path `fork()` pattern using the return value
- Use `execvp()` to replace a child process with a new program
- Call `waitpid()` to reap a child and avoid zombie processes
- Create an anonymous pipe with `pipe()` and wire it between parent and child using `dup2()`
- Close the correct pipe ends in each process to avoid read hangs

---

## Slide 3: What Is a Process?

- **Key Point:** A process is a running program — the kernel's unit of resource ownership. Every process has an address space, open file descriptors, a PID, and a parent.

```
PID 1 (init/systemd)
 └── PID 412 (bash)
      └── PID 891 (your program)   ← this is you
           └── PID 892 (child)     ← after fork()
```

- `getpid()` returns the current process's PID
- `getppid()` returns the parent's PID
- File descriptors (stdin=0, stdout=1, stderr=2) are per-process but inherited from parent

- **Speaker Note:** Draw the tree on the board. Emphasize that every process has exactly one parent. The shell is the parent of every program students run interactively. After `fork()`, the child's parent is the program that called `fork()`.

---

## Slide 4: fork() — Duplicating the Process

- **Key Point:** `fork()` creates an exact copy of the calling process. Both processes continue executing from the line immediately after the `fork()` call.

```c
#include <unistd.h>

pid_t fork(void);
/* Returns:  child PID  in the parent process
             0          in the child process
            -1          on error (sets errno) */
```

- After `fork()`, two independent processes run the same code
- They share nothing — the child gets a **copy** of the parent's address space (copy-on-write)
- Open file descriptors are duplicated — both processes have them

- **Speaker Note:** The copy-on-write detail is worth 30 seconds: the kernel doesn't physically copy memory pages until one process writes to them. Keeps fork() cheap. Don't get stuck here — the behavior is what matters.

---

## Slide 5: fork() — The Two-Path Pattern

- **Key Point:** The return value of `fork()` is the only way to know whether you are in the parent or the child. Every fork() call must check it.

```c
pid_t pid = fork();

if (pid == -1) {
    perror("fork");           /* fork failed — you are still the parent */
    exit(EXIT_FAILURE);
}

if (pid == 0) {
    /* ── CHILD ── */
    /* pid == 0 means "I am the child" */
    printf("child: my PID is %d\n", getpid());
    exit(0);

} else {
    /* ── PARENT ── */
    /* pid > 0: pid is the child's PID */
    printf("parent: child PID is %d\n", pid);
}
```

- **Speaker Note:** Spend time here — this is the pattern students will use for every fork() exercise. Ask: "after fork(), how many processes run this code?" (Two.) "Which line does each one start at?" (The line after fork().) "What is `pid` in the child?" (0.) "In the parent?" (Child's PID.)

---

## Slide 6: What the Child Inherits

- **Key Point:** The child starts as a clone — but changes in one process after `fork()` are invisible to the other.

| Resource | Inherited? | Shared? |
|---|---|---|
| Code (text segment) | Yes | Yes (read-only) |
| Stack and heap | Yes (copied) | No — independent copies |
| Open file descriptors | Yes (same underlying files) | Partially — position shared, but close() is independent |
| Signal handlers | Yes | No |
| Environment variables | Yes (copied) | No |
| PID | No — child gets a new PID | — |

- **Key implication:** if parent opens a file before `fork()`, both parent and child can read/write it — they share the file offset

- **Speaker Note:** The file descriptor sharing is what makes pipes work — `pipe()` before `fork()` means both processes have the pipe ends open. That's the next slide series.

---

## Slide 7: The Child's Address Space — What the Copy Really Looks Like

- **Key Point:** The child gets a complete logical copy of the parent's entire address space. Every segment is present at the same virtual addresses — but no physical memory is copied until one of the processes writes to a page.

```
  Virtual address space — identical in parent and child immediately after fork()

  High addresses  ┌─────────────────────────────┐
                  │  stack                      │ ← full snapshot of parent's call
                  │    ↓  (grows downward)      │   stack at the moment fork() ran —
                  │                             │   every frame, every local variable
                  │    ↑  (grows upward)        │
                  │  heap                       │ ← all malloc'd memory, same addresses
                  ├─────────────────────────────┤
                  │  BSS  (uninitialized data)  │ ← zeroed globals
                  ├─────────────────────────────┤
                  │  data (initialized data)    │ ← globals with initial values
                  ├─────────────────────────────┤
                  │  text (code)                │ ← read-only; shared physical pages,
  Low addresses   └─────────────────────────────┘   no copy needed
```

- **Copy-on-Write (COW):** the kernel marks every writable page in both processes as read-only. The first *write* to any page triggers a page fault — the kernel copies that one physical page, marks both copies writable, and resumes. Fork is fast because no copying happens until it is forced.

- **The stack snapshot is exact.** The child's stack contains every active call frame from `main()` down to `fork()`. When `fork()` returns in the child, local variables from before the call are already there — the child does not start with a fresh stack.

- **The first write you can see in source code:**

```c
pid_t pid = fork();   /* return value arrives in register RAX */
                      /* compiler stores it: mov [rbp-8], rax  */
                      /* that store is a WRITE to the stack page
                         → page fault → kernel copies that page
                         → parent now has its own physical copy  */
```

  The child triggers its own fault the same way when it stores `0` to its copy of `pid`.

- **Why file descriptors survive `exec()` but variables do not:**
  File descriptors are kernel data structures — they live in the kernel's memory, not in the process address space. `exec()` replaces the entire address space (text, data, BSS, heap, and stack all gone), but the kernel's fd table entry for this process is untouched. That separation — kernel space vs. user space — is exactly why `dup2()` before `exec()` works: you configure kernel-side resources that persist through the address space replacement.

- **Speaker Note:** Draw this diagram on the board and leave it up. Walk through it segment by segment. Emphasize: the heap copy is why the child can use any data the parent malloc'd before fork() — it's there, at the same address, without any extra work. Then point to the fd table being *outside* the box — that click connects the pipe wiring slides to what students already know about kernel vs. user space. This slide is the conceptual keystone for the whole lecture.

---

## Slide 8: exec() — Replacing the Process Image

- **Key Point:** `exec()` replaces the calling process's code, data, and stack with a new program. The PID does not change. It does not return on success.

```c
#include <unistd.h>

/* exec() loads a new program into the current process */
execvp("ls", args);

/* If execvp() returns, it failed */
perror("execvp");
exit(EXIT_FAILURE);
```

- After a successful `exec()`: new code, new stack, new heap
- **What survives exec():** open file descriptors (unless marked close-on-exec), PID, PPID
- **What does not survive:** variables, stack frames, signal handlers

- **Speaker Note:** The PID-survives detail is important for the shell model: the shell forks, the child execs — the child's PID stays the same before and after exec(). The shell knows which PID to wait on.

---

## Slide 9: The exec() Family — Which One to Use?

- **Key Point:** There are six `exec()` variants. `execvp()` is the one you want for most programs — it searches `PATH` and takes an argument array.

```c
/* execvp — path search + argument array (use this) */
char *args[] = { "ls", "-l", "/tmp", NULL };   /* NULL-terminated! */
execvp("ls", args);

/* execl — literal argument list (convenient for fixed args) */
execl("/bin/ls", "ls", "-l", "/tmp", NULL);

/* execv — no path search, explicit path, argument array */
execv("/bin/ls", args);
```

| Variant | Path search | Args as | Env |
|---|---|---|---|
| `execvp` | Yes (`PATH`) | array | inherited |
| `execlp` | Yes (`PATH`) | list | inherited |
| `execv`  | No | array | inherited |
| `execl`  | No | list | inherited |
| `execve` | No | array | explicit |

- The argument array **must** be `NULL`-terminated — `execvp` stops reading at `NULL`
- `args[0]` is the program name as it appears in `argv[0]` — by convention, same as the command

- **Speaker Note:** Students will use `execvp` in the ICEX. Emphasize the NULL terminator — forgetting it causes a crash with no obvious message.

---

## Slide 10: wait() and waitpid() — Reaping the Child

- **Key Point:** When a child exits, its entry stays in the process table until the parent calls `wait()` or `waitpid()`. A child that has exited but not been waited on is a **zombie**.

```c
#include <sys/wait.h>

pid_t waitpid(pid_t pid, int *status, int options);
/* pid:     child PID to wait for (-1 = any child)   */
/* status:  receives exit information                 */
/* options: 0 = block until child exits               */
/* Returns: PID of child that changed state, -1 error */

int status;
pid_t finished = waitpid(pid, &status, 0);

if (WIFEXITED(status))
    printf("child exited with status %d\n", WEXITSTATUS(status));
```

- `wait(NULL)` is shorthand for `waitpid(-1, NULL, 0)` — waits for any child
- Always `waitpid` for the specific child when you know its PID

- **Speaker Note:** Run `ps aux | grep Z` to show what a zombie looks like. The key point: if a shell script spawns many children and never waits, it leaks process table entries. In the httpd server, each fork() for a connection must be waited on.

---

## Slide 11: Zombies and Orphans

- **Key Point:** Failure to reap children is a resource leak. Two pathological cases.

```
ZOMBIE: child exits before parent calls wait()
┌─────────────────────────────────────────┐
│  Child finishes, sends SIGCHLD to parent │
│  Parent ignores it — never calls wait()  │
│  Child entry sits in process table as Z  │
│  Consumes a PID slot indefinitely        │
└─────────────────────────────────────────┘
Fix: always waitpid() after fork()

ORPHAN: parent exits before child finishes
┌─────────────────────────────────────────┐
│  Parent exits without waiting            │
│  Kernel re-parents child to init (PID 1) │
│  init calls wait() — orphan is reaped    │
│  Benign but messy; output goes nowhere   │
└─────────────────────────────────────────┘
Fix: wait for your children before exiting
```

- **Speaker Note:** Zombies are a common interview question. The fix is simple: call wait(). The deeper implication for the server: a long-running parent that forks per connection must either wait() periodically or use SIGCHLD to reap asynchronously. Preview only — don't go deep.

---

## Slide 12: fork() + exec() + wait() — The Pattern

- **Key Point:** This three-call sequence is how every Unix shell runs a command. Memorize it.

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    char *args[] = { "ls", "-l", "/tmp", NULL };

    pid_t pid = fork();
    if (pid == -1) { perror("fork"); return 1; }

    if (pid == 0) {
        /* ── CHILD: replace with ls ── */
        execvp("ls", args);
        perror("execvp");      /* only reached if exec fails */
        exit(EXIT_FAILURE);
    }

    /* ── PARENT: wait for child ── */
    int status;
    waitpid(pid, &status, 0);
    printf("ls exited with %d\n", WEXITSTATUS(status));
    return 0;
}
```

- **Speaker Note:** Type this live. Compile, run. Ask: "where does ls output go?" (stdout — it inherits the terminal). "What if we wanted to capture that output in the parent?" — that's what pipes solve. Next slides.

---

## Slide 13: pipe() — Anonymous Pipes

- **Key Point:** `pipe()` creates a kernel buffer with two file descriptors — one write end, one read end. Data written to `fd[1]` can be read from `fd[0]`. Call it **before** `fork()` so both processes inherit both ends.

```c
#include <unistd.h>

int fd[2];
pipe(fd);
/* fd[0] = read end   ← parent reads here  */
/* fd[1] = write end  ← child writes here  */
```

```
         ┌──────────────────────┐
 fd[1] ──►   kernel pipe buffer  ──► fd[0]
 (write)  └──────────────────────┘   (read)
  child writes                       parent reads
```

- Pipe has finite capacity (~64 KB on Linux) — write blocks when full, read blocks when empty
- Pipe signals EOF to the reader when **all** write ends are closed

- **Speaker Note:** The EOF rule is critical and explains why closing ends matters (next slide). Draw the buffer diagram on the board.

---

## Slide 14: dup2() — Rewiring File Descriptors

- **Key Point:** `dup2(oldfd, newfd)` makes `newfd` refer to the same file as `oldfd`, closing `newfd` first if it was open. This is how you silently replace a process's stdin or stdout.

```c
#include <unistd.h>

dup2(fd[1], STDOUT_FILENO);
/* STDOUT_FILENO == 1                                          */
/* After this: writing to fd 1 (stdout) writes to the pipe    */
/* execvp'd program never knows — it just writes to stdout    */
```

**Child setup before execvp:**
```c
/* In child, after fork() */
close(fd[0]);                    /* child does not read from pipe  */
dup2(fd[1], STDOUT_FILENO);      /* child's stdout → pipe write end */
close(fd[1]);                    /* done with original; dup'd it    */
execvp("ls", args);
```

- After `dup2`, the original `fd[1]` and `STDOUT_FILENO` (1) both refer to the pipe write end
- Close `fd[1]` after `dup2` — you now have two references; you only need `STDOUT_FILENO`

- **Speaker Note:** This is the hardest slide. Work through it step by step. Before dup2: fd[0], fd[1], and stdout (1) all exist. After dup2(fd[1], 1): stdout IS the pipe. After close(fd[1]): only one reference remains (stdout). Draw the fd table on the board.

---

## Slide 15: Closing the Right Ends — The Rule

- **Key Point:** Every process must close the pipe ends it will not use. Forgetting causes hangs.

```
After fork(), each process has copies of BOTH fd[0] and fd[1]:

CHILD (writer):          PARENT (reader):
  close(fd[0])  ✓          close(fd[1])  ✓
  dup2(fd[1],1) ✓          read from fd[0]
  close(fd[1])  ✓          waitpid()
  execvp(...)

WHY closing fd[1] in the parent matters:
─────────────────────────────────────────
  Reader gets EOF when ALL write ends are closed.
  If parent keeps fd[1] open, even after child exits,
  the pipe still has an open write end (the parent's copy).
  Parent's read() blocks forever — a hang with no error.
```

- **Speaker Note:** This is the number-one bug students will hit in the ICEX. Predict it explicitly: "If your program hangs after the child exits, you forgot `close(fd[1])` in the parent." Write that on the board.

---

## Slide 16: fork() + exec() + pipe() — Complete Example

- **Key Point:** The full pattern: pipe before fork, child wires stdout to pipe and execs, parent reads pipe, both close unused ends.

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    int fd[2];
    if (pipe(fd) == -1) { perror("pipe"); return 1; }

    pid_t pid = fork();
    if (pid == -1) { perror("fork"); return 1; }

    if (pid == 0) {
        /* ── CHILD ── */
        close(fd[0]);                        /* don't need read end  */
        dup2(fd[1], STDOUT_FILENO);          /* stdout → pipe        */
        close(fd[1]);                        /* dup'd; close original */
        char *args[] = { "ls", "-1", NULL };
        execvp("ls", args);
        perror("execvp"); exit(EXIT_FAILURE);
    }

    /* ── PARENT ── */
    close(fd[1]);                            /* MUST close write end  */
    char buf[256];
    ssize_t n;
    while ((n = read(fd[0], buf, sizeof(buf) - 1)) > 0) {
        buf[n] = '\0';
        printf("from child: %s", buf);
    }
    close(fd[0]);
    waitpid(pid, NULL, 0);
    return 0;
}
```

- **Speaker Note:** Compile and run this live. Then deliberately comment out `close(fd[1])` in the parent and show the hang. Uncomment and show it works. That demonstration will stick better than any explanation.

---

## Slide 17: Key Takeaways

- `fork()` creates an identical copy — check the return value to know who you are
- `exec()` replaces the process image — it does not return on success; always `perror` + `exit` after it
- `waitpid()` reaps the child — skipping it creates zombies
- `pipe()` before `fork()` — both processes inherit both ends
- `dup2(fd[1], STDOUT_FILENO)` silently rewires stdout to the pipe — the exec'd program never knows
- Close every pipe end you will not use — the parent **must** close `fd[1]` or reads hang forever

---

## Slide 18: The Cliffhanger

**You now have all the pieces of a real web server.**

```c
/* skeleton of a connection-per-fork server */
while (1) {
    int conn = accept(server_fd, ...);   /* wait for browser */

    pid_t pid = fork();
    if (pid == 0) {
        /* child: handle ONE request, then exit */
        dup2(conn, STDOUT_FILENO);       /* stdout → socket  */
        dup2(conn, STDIN_FILENO);        /* socket → stdin   */
        handle_request(doc_root);        /* your http_resp logic */
        exit(0);
    }
    /* parent: close conn, loop back to accept() */
    close(conn);
    waitpid(-1, NULL, WNOHANG);          /* reap any finished children */
}
```

**Next assignment:** wrap your `http_resp` logic in this loop. The response generator you already wrote drops in unchanged — `fork()` and `dup2()` are the only new pieces.

- **Speaker Note:** Leave this on screen during the ICEX. Students should recognize their own `http_resp` code in `handle_request()`. That click of recognition is the payoff for the whole lecture.
