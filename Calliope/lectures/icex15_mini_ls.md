# ICEX 15: Mini `ls` — Filesystem Metadata in Action

**Duration:** 25–30 minutes  
**Learning Goals:** Call `lstat()` on a file and directory entries, populate a `FileInfo` struct from `struct stat`, and traverse a directory with `opendir()` / `readdir()` / `closedir()`.

---

## Background

You are implementing a stripped-down version of `ls` that accepts a single argument — either a file or a directory. If it is a file, print one line of metadata. If it is a directory, print one line per entry.

The output format is fixed and provided for you. Your job is to get the data into the `FileInfo` struct so the provided `print_entry()` can display it.

Expected output for a directory argument:

```
reg       Apr 09 14:22       clients.dat
reg       Apr 09 14:22       clients_sample.csv
dir       Mar 28 09:05       docs
lnk       Apr 01 11:30       latest -> release
```

---

## Starter File

The skeleton file is in `exercises/wk11/icex15/mini_ls.c` in the class repo.

```bash
git pull upstream main
cd exercises/wk11/icex15/
gcc -g -Wall -o mini_ls mini_ls.c
./mini_ls .
./mini_ls mini_ls.c
```

---

## Tasks

**Task 1 — Single file**  
When `argv[1]` names a regular file (or symlink), print exactly one entry line for it.

**Task 2 — Directory**  
When `argv[1]` names a directory, iterate its entries (skip `.` and `..`) and print one line per entry.

**Task 3 — Written answer in README.md**  
Answer the questions in `exercises/wk11/icex15/README.md`.

---

## The One Tricky Part

`readdir()` gives you only the filename — not a full path. You must build the full path before calling `lstat()`:

```c
char path[1024];
snprintf(path, sizeof(path), "%s/%s", argv[1], ep->d_name);
lstat(path, &sb);
```

If you call `lstat(ep->d_name, &sb)` directly, it will look in the current working directory, not the directory you opened.

---

## README.md Questions

**Q1.** Why does the skeleton use `lstat()` instead of `stat()`? What would be different in the output if you switched to `stat()`?

**Q2.** Run your program on `/dev`. What file types do you see? What would you need to add to `fill_info()` to handle them?

**Q3.** *(Stretch)* How would you modify the program to sort entries alphabetically? What data structure would you need?

---

## Submission

```bash
git checkout -b icex15-mini-ls
git add exercises/wk11/icex15/
git commit -m "icex15: mini ls"
git push -u origin icex15-mini-ls
```

Open a PR on `github.iu.edu` and request a review from your TA or instructor.

---

## Rubric

| Task | Points | Criteria |
|------|--------|----------|
| Task 1 — single file: lstat + FileInfo populated correctly | 3 | Correct type, date, and name for a file argument |
| Task 2 — directory loop: opendir/readdir/closedir | 2 | All non-dot entries printed; DIR* closed |
| Task 2 — full path built with snprintf before lstat | 2 | lstat succeeds on entries in a non-cwd directory |
| Task 2 — `.` and `..` skipped | 1 | Neither appears in output |
| Task 3 — written answers Q1–Q2 | 2 | Correct explanations |
| **Total** | **10** | |
| **Stretch — Q3 written answer** | **+2 EC** | Correct description of sorting approach |
