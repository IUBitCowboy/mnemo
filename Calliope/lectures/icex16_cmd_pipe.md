# ICEX 16: Command Tap — Capturing Child Output with a Pipe

**Duration:** 25–30 minutes  
**Learning Goals:** Call `pipe()` before `fork()`, wire a child's stdout to the pipe write end using `dup2()`, exec a command with `execvp()`, read the child's output in the parent, and `waitpid()` to reap the child cleanly.

---

## Background

The shell does this every time you run a pipeline like `ls | wc -l` — it creates a pipe, forks a child for each command, and uses `dup2()` to connect stdout of one to stdin of the next. In this exercise you implement that plumbing for a single command: your program forks a child, execs `ls -1` on a directory given as `argv[1]`, captures its output through a pipe, and prints each line back in the parent with a line number prefix.

---

## Starter File

The skeleton is in `exercises/wk12/icex16/cmd_pipe.c` in the class repo.

```bash
git pull upstream main
cd exercises/wk12/icex16/
gcc -g -Wall -o cmd_pipe cmd_pipe.c
./cmd_pipe /tmp
```

Expected output (will vary by directory):
```
[1] file_a.txt
[2] file_b.c
[3] subdir
Child exited with status 0
```

---

## The One Rule You Must Not Forget

After `fork()`, the parent holds a copy of the pipe's write end (`fd[1]`). The parent must close it before reading:

```c
close(fd[1]);   /* parent: MUST do this before read() */
```

If you skip this, your parent's `read()` will block forever — even after the child exits — because the pipe still has an open write end (the parent's copy). If your program hangs, this is why.

---

## Tasks

**Task 1 — Create the pipe**  
Call `pipe(fd)` before `fork()`. Check the return value.

**Task 2 — Fork**  
Call `fork()`. Check all three return cases (-1, 0, >0).

**Task 3 — Child: wire stdout and exec**  
In the child branch: close the read end, `dup2` the write end to `STDOUT_FILENO`, close the original write end, then `execvp("ls", ...)`. Add `perror` + `exit` after `execvp` in case it fails.

**Task 4 — Parent: read and print**  
In the parent branch: close the write end, then call the provided `print_numbered()` helper which reads from `fd[0]` and prints numbered lines. Then `waitpid()` for the child.

**Task 5 — Written answers in README.md**

---

## README.md Questions

**Q1.** What happens if you forget `close(fd[1])` in the parent before calling `print_numbered()`? Try it — comment out that line, recompile, and run. Describe what you observe and explain why it happens.

**Q2.** After `dup2(fd[1], STDOUT_FILENO)`, how many file descriptors refer to the pipe write end? Why do you then close `fd[1]`?

**Q3.** *(Stretch)* The provided `print_numbered()` reads in chunks up to 256 bytes at a time. If a line is longer than 256 bytes, it will be split across two reads. How would you modify the approach to guarantee whole-line reads?

---

## Submission

```bash
git checkout -b icex16-cmd-pipe
git add exercises/wk12/icex16/
git commit -m "icex16: command tap via fork/exec/pipe"
git push -u origin icex16-cmd-pipe
```

Open a PR on `github.iu.edu` and request a review from your TA or instructor.

---

## Rubric

| Task | Points | Criteria |
|------|--------|----------|
| Task 1 — `pipe()` called and return value checked | 1 | `perror` + exit on failure |
| Task 2 — `fork()` called with all three cases handled | 2 | -1 exits; 0 is child path; >0 is parent path |
| Task 3 — child closes `fd[0]`, `dup2`s `fd[1]` to stdout, closes `fd[1]`, `execvp` | 4 | Correct order; `perror`+`exit` after `execvp` |
| Task 4 — parent closes `fd[1]` before reading, calls `print_numbered`, `waitpid` | 2 | Write end closed first; child reaped |
| Task 5 — written answers Q1–Q2 | 1 | Correct explanations |
| **Total** | **10** | |
| **Stretch — Q3 written answer** | **+2 EC** | Correct description of line-buffered approach |
