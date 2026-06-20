# ICEX 12 — The Growable Roster

**Name:**
**Student ID:**
**Date:**

---

## Task 4 — Pointer Invalidation

After adding the snapshot code and running the program, answer the following questions.

**Q1.** What did your program print for the `snapshot == r.data?` line?

> *(your answer here)*

**Q2.** Did the block move? If it did, explain *why* `realloc` had to move it rather than expand in place.

> *(your answer here)*

**Q3.** If you had continued to use `snapshot` after `roster_push` triggered a `realloc` that moved the block — for example, `printf("%d\n", *snapshot)` — what would that be an example of, and why is it dangerous?

> *(your answer here)*

**Q4.** Fill in the table below. Run your program enough times (at least 3 runs) to observe whether the block always moves or sometimes stays in place.

| Run | `snapshot` address | `r.data` address after push | Block moved? |
|-----|--------------------|-----------------------------|--------------|
| 1   |                    |                             |              |
| 2   |                    |                             |              |
| 3   |                    |                             |              |

---

## Task 5 — valgrind Output

Paste the **HEAP SUMMARY** and **ERROR SUMMARY** sections from your `valgrind` run below.

```
(paste valgrind output here)
```

**Q1.** What does "in use at exit: 0 bytes in 0 blocks" mean?

> *(your answer here)*

**Q2.** What does "0 errors from 0 contexts" mean?

> *(your answer here)*

**Q3.** If you had forgotten to call `roster_free`, what would the HEAP SUMMARY have shown instead?

> *(your answer here)*
