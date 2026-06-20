# Lecture: Dynamic Memory — Taking Control of the Heap

## Slide 1: Title Slide
- **Topic:** Dynamic Memory Allocation in C
- **Course:** C291 — System Programming with C and Linux
- **Timing:** 40-min lecture + 30-min ICEX + 5-min buffer = 75 min

---

## Slide 2: Learning Objectives
By the end of this lecture, you will be able to:

- Distinguish stack memory from heap memory and explain when each is appropriate
- Allocate heap memory with `malloc()` and `calloc()`, and always check for `NULL`
- Release heap memory correctly with `free()`, including the `free(NULL)` no-op rule
- Identify dangling pointers and double-free errors and explain why they are undefined behavior
- Use `realloc()` to grow a buffer and explain why it may invalidate existing pointers into the old block
- Detect memory leaks and use `valgrind` to find them
- Allocate and free nodes in a singly-linked list

---

## Slide 3: The Memory Map — Stack vs. Heap

- **Key Point:** A process has (at least) two regions for runtime data: the **stack** (fast, automatic, limited, LIFO) and the **heap** (flexible, manual, large). Every local variable you've written so far lives on the stack and dies when its function returns. Heap memory lives until you explicitly free it.
- **Diagram:**
```
High address
┌─────────────────┐
│   stack         │  ← grows downward; automatic lifetime
│   (local vars,  │
│    stack frames)│
├─────────────────┤
│        ↓        │
│                 │
│        ↑        │
├─────────────────┤
│   heap          │  ← grows upward; manual lifetime
│   (malloc/free) │
├─────────────────┤
│   BSS / data    │  (globals, statics)
├─────────────────┤
│   text (code)   │
└─────────────────┘
Low address
```
- **Speaker Note:** Draw this on the board. Ask: "What happens when a function returns a pointer to one of its local variables?" Answer: the stack frame is gone — the pointer is already dangling. This is the exact motivation for the heap. The heap doesn't belong to any function; it belongs to the process.

---

## Slide 4: malloc() — Requesting a Heap Block

- **Key Point:** `malloc(n)` requests `n` bytes from the heap and returns a `void *` pointer to the start of the block. The contents are **uninitialized** — garbage values lurk. If allocation fails, it returns `NULL`.
- **Code Example:**
```c
#include <stdlib.h>

// Allocate space for 10 ints
int *arr = malloc(10 * sizeof(int));

// arr[0]..arr[9] exist on the heap — but contain garbage
arr[0] = 42;
arr[1] = 7;
// ...
free(arr);
```
- **Speaker Note:** `void *` casts to any pointer type in C — no explicit cast needed. Always use `sizeof(type)` rather than a literal number so the code stays correct when the type changes. Ask: "What's in `arr[2]` right now?" Answer: unknown — could be anything. That's why `calloc` exists.

---

## Slide 5: calloc() — Zero-Initialized Allocation

- **Key Point:** `calloc(n, size)` allocates `n` elements of `size` bytes each and **zeroes every byte**. Use it when you need a clean slate — counters, flag arrays, anything that must start at zero.
- **Code Example:**
```c
// malloc: fast, garbage content
int *a = malloc(10 * sizeof(int));   // a[0]..a[9] = ???

// calloc: slightly slower, zeroed
int *b = calloc(10, sizeof(int));    // b[0]..b[9] = 0

printf("%d\n", b[3]);  // guaranteed: 0
```
- **Speaker Note:** `calloc` is not just "malloc + memset" in terms of ergonomics — it also checks for integer overflow in `n * size` internally, making it safer for large allocations. Rule of thumb: use `calloc` for arrays of values that logically start at zero; use `malloc` when you're about to overwrite every byte anyway (e.g., reading from a file into the buffer).

---

## Slide 6: Always Check for NULL

- **Key Point:** Both `malloc` and `calloc` return `NULL` on failure. Dereferencing `NULL` is undefined behavior — typically a segfault. **Always check before use.**
- **Code Example:**
```c
int *arr = malloc(1000000 * sizeof(int));
if (arr == NULL) {
    fprintf(stderr, "allocation failed\n");
    exit(EXIT_FAILURE);   // or return an error code
}

// Safe to use arr only after the check
arr[0] = 1;
```
- **Speaker Note:** On a modern desktop system with overcommit, `malloc` rarely fails for small allocations — which trains students to skip the check. But on embedded systems, resource-constrained servers, or in security-critical code, this check is non-negotiable. Build the habit now. It also signals intent to a reader: "this pointer might be NULL before this point."

---

## Slide 7: free() — Freeing Nested Heap Allocations

- **Key Point:** When a struct holds a *pointer* to another heap-allocated struct, free the inner allocation first, then the outer. Set each pointer to `NULL` immediately after freeing it. Because `free(NULL)` is a no-op, you never need an `if`-check before calling `free` — null-initialized pointers are always safe to pass to it.
- **Code Example:**
```c
typedef struct { char street[64]; char city[32]; } Address;
typedef struct { char name[32];   Address *addr;  } Person;

// Two heap allocations: one for Person, one for Address
Person *p = malloc(sizeof(Person));
p->addr   = malloc(sizeof(Address));
strcpy(p->name,         "Alice");
strcpy(p->addr->street, "1 Main St");
strcpy(p->addr->city,   "Bloomington");

// Free inner first, then outer
free(p->addr);
p->addr = NULL;    // ← null immediately; free(p->addr) is now safe to call again

free(p);
p = NULL;

// Not every Person has an address on file:
Person *p2 = malloc(sizeof(Person));
p2->addr   = NULL;         // no address — pointer is NULL
// ...
free(p2->addr);            // free(NULL) — no-op, no crash, no if-check needed
free(p2);
```
- **Speaker Note:** The rule is: free in *reverse allocation order* — innermost heap pointer first, then its owner. Ask: "What if we freed `p` first and then tried to free `p->addr`?" Answer: `p` is gone — reading `p->addr` through the freed pointer is undefined behavior before we ever reach the inner free. The `p2` example shows `free(NULL)` earning its keep: a Person whose `addr` was never populated can be freed with exactly the same two lines of cleanup code, no conditional required. Pause here and ask: "What would happen if we skipped `p->addr = NULL` after the first free?" — that sets up the next slide perfectly.

---

## Slide 8: Dangling Pointer — The Crash

- **Key Point:** The most common outcome of using a dangling pointer is an immediate **segmentation fault**. This is actually the *best case* — a crash is loud, reproducible, and debuggable. It also confirms something important: freed memory is not erased; it is simply returned to the allocator and eventually overwritten when reused. Whether you crash depends on whether the OS has reclaimed that page.
- **Code Example:**
```c
int *p = malloc(sizeof(int));
*p = 99;
printf("before free: %d\n", *p);

free(p);
// p still holds the old address — the int was NOT zeroed or erased

printf("after free:  %d\n", *p);  // UB — likely crash
```
- **Terminal Output:**
```
before free: 99
Segmentation fault (core dumped)
```
- **Speaker Note:** Run this live if possible — the segfault is visceral and memorable. Explain what "core dumped" means (a snapshot of process memory written to disk for post-mortem debugging with `gdb`). Then ask: "Why did it crash *this* time? The memory was there a moment ago." The answer connects to a principle already introduced in class: memory is not erased on free — the allocator just marks the block available. The segfault happened because the OS detected the process accessing a page it no longer owns. Crucially: this only happens *sometimes*. If the allocator hasn't returned that page to the OS yet, the read may silently succeed and return garbage — or worse, return data that looks correct. That's the scenario on the next slide.

---

## Slide 9: Dangling Pointers

- **Key Point:** A **dangling pointer** holds the address of memory that has already been freed. The pointer value still *looks* valid — it is just no longer yours. Using it is undefined behavior: the allocator may have given that block to someone else.
- **Code Example:**
```c
// Same Person/Address from last slide — but we forgot to null p->addr
free(p->addr);
// p->addr still holds the old Address block's address

// Somewhere else in the program, another malloc reuses that block:
Address *office = malloc(sizeof(Address));   // may land at the same address!
strcpy(office->city, "Indianapolis");

// Back in our code — p->addr is dangling, pointing at office's memory:
printf("%s\n", p->addr->city);  // prints "Indianapolis" ← not Alice's data!
strcpy(p->addr->city, "Chicago"); // silently corrupts office's record

// The fix: one line after free prevents all of this
// free(p->addr);
// p->addr = NULL;   ← dangling read → immediate null-pointer crash instead
```
- **Speaker Note:** Walk through this step by step. The reason this bug is so dangerous is the example above: it doesn't crash — it silently reads or writes someone else's data, producing wrong answers that may not surface until much later. The `= NULL` fix doesn't prevent the misuse; it converts it from a *silent* corruption into an *immediate* null-pointer crash that shows up in testing. A crash you can find and fix; silent data corruption in production is a nightmare. Ask: "Would valgrind catch the dangling read?" Yes — this is exactly what the "invalid read" error in valgrind output means.

---

## Slide 10: Double Free

- **Key Point:** Calling `free()` on the same pointer twice corrupts the allocator's internal bookkeeping. It is undefined behavior and a real class of **security vulnerability** (heap exploitation via CVE). The one-line discipline from Slide 7 — `p->addr = NULL` immediately after `free` — completely eliminates it.
- **Code Example:**
```c
// Slide 7 showed us the correct pattern:
free(p->addr);
p->addr = NULL;     // ← this one line is the entire fix

free(p->addr);      // called again — free(NULL) is a no-op; nothing happens
free(p->addr);      // called a third time — still fine

// Without the NULL assignment:
free(p->addr);
// p->addr still holds the old address...
free(p->addr);      // DOUBLE FREE — undefined behavior
                    // may crash, may silently corrupt the allocator,
                    // may be exploited to execute arbitrary code
```
- **Terminal Output (typical double-free crash):**
```
free(): double free detected in tcache 2
Aborted (core dumped)
```
- **Speaker Note:** Modern glibc detects many double-frees and aborts with this message — show it. But "detects many" is not "detects all"; subtle cases still slip through, which is why double-free is a CVE class rather than just a crash. Bring it back to Slide 7 explicitly: the `= NULL` after every `free` is the one habit that prevents dangling-pointer reads, dangling-pointer writes, *and* double-free — three bug classes, one line of discipline. Ask: "What is the cost of `p->addr = NULL`?" One assignment. "What is the cost of not doing it?" Potentially everything on these last three slides.

---

## Slide 11: LIVE DEMO — Hunting Memory Leaks with valgrind

- **Key Point:** This demo resolves last lecture's cliffhanger: we build a linked list with heap-allocated nodes, then use `valgrind` to find — and fix — two memory leaks: one obvious, one subtle. Students see `valgrind` workflow for the first time here; the formal reference card follows on Slide 15.
- **Demo Program:** `demos/wk10/leak_hunt.c` (pre-loaded in terminal)
- **Demo Flow (~8 min):**

**Step 1 — Read the code together (2 min)**
Walk through `leak_hunt.c` on screen. Point out:
- `typedef struct Node` with `int id` and `char *label` (heap-allocated string via `malloc` + `strcpy`)
- `create_node()` makes **two** allocations per node: one for the `Node`, one for the `label`
- `main()` builds a 5-node list, prints it, then calls `free(head)` — just the head node
Ask: "How many `malloc` calls happened? How many `free` calls?" (10 mallocs, 1 free)

**Step 2 — First valgrind run (2 min)**
```bash
gcc -g -Wall -o leak_hunt leak_hunt.c
valgrind --leak-check=full ./leak_hunt
```
Expected output highlights:
```
LEAK SUMMARY:
   definitely lost: 9 blocks
```
Walk the class through the summary. "9 blocks lost — we freed 1 node but not its label, and we didn't free the other 4 nodes or their labels."

**Step 3 — Fix the obvious leak (2 min)**
Replace `free(head)` with a proper traversal loop:
```c
Node *cur = head;
while (cur != NULL) {
    Node *next = cur->next;
    free(cur);
    cur = next;
}
```
Recompile and re-run valgrind:
```
LEAK SUMMARY:
   definitely lost: 5 blocks
```
"Better — the nodes are freed. But what about the labels?" Point at `create_node` — each `label` was a separate `malloc`. Freeing the node doesn't free the string inside it.

**Step 4 — Fix the subtle leak (2 min)**
Add one line before `free(cur)`:
```c
    free(cur->label);
    free(cur);
```
Recompile and re-run valgrind:
```
HEAP SUMMARY: in use at exit: 0 bytes in 0 blocks
ERROR SUMMARY: 0 errors from 0 contexts
```
"That's what clean looks like. Every `malloc` paired with exactly one `free`."

- **Speaker Note:** This demo is the single most important 8 minutes of the lecture. Students see the full workflow: write code → compile with `-g` → run under valgrind → read the output → fix → repeat. Emphasize that the subtle leak (inner `label` not freed) is the *exact same pattern* as Slide 7's `Person.addr` — a pointer field inside a struct that was separately allocated. Ask at the end: "What would have happened if we freed `cur->label` *after* `free(cur)`?" Answer: dangling pointer read to get the label address — UB (Slide 8). Save-then-free, innermost-first — same rules, same reasons.

---

## Slide 12: realloc() — Growing a Buffer

- **Key Point:** `realloc(ptr, new_size)` resizes a previously allocated block. If the heap has room to grow in place, it does; otherwise it allocates a new block, copies the data, and frees the old one. Returns a pointer to the (possibly new) block.
- **Code Example:**
```c
// Start with a buffer for 4 ints
int *buf = malloc(4 * sizeof(int));
buf[0] = 1; buf[1] = 2; buf[2] = 3; buf[3] = 4;

// Need 8 ints now — grow the buffer
buf = realloc(buf, 8 * sizeof(int));
if (buf == NULL) { exit(EXIT_FAILURE); }

buf[4] = 5; buf[5] = 6; buf[6] = 7; buf[7] = 8;
free(buf);
```
- **Speaker Note:** This is the core of how `stdio`'s `getline`, many string builders, and virtually all growable-array implementations work. A common pattern: start small (capacity = 4 or 8), double on overflow — amortized O(1) append. `realloc(NULL, size)` behaves like `malloc(size)`, which can simplify some init code.

---

## Slide 13: realloc() — The Pointer Invalidation Trap

- **Key Point:** If `realloc` moves the block, **every pointer into the old block is immediately dangling**. The old address is gone. This is the most common `realloc` bug.
- **Code Example:**
```c
int *buf    = malloc(4 * sizeof(int));
int *danger = &buf[2];       // pointer INTO the buffer

printf("before: buf=%p  danger=%p\n", (void*)buf, (void*)danger);

buf = realloc(buf, 1000 * sizeof(int));  // likely moves!

printf("after:  buf=%p  danger=%p\n", (void*)buf, (void*)danger);
// danger still points at the OLD address — dangling!

*danger = 99;  // UB: old block may be reused or freed
```
- **Speaker Note:** Show this running — the addresses often differ. The rule: after any `realloc`, recompute all interior pointers from the new base. This is also why you should **never** write `ptr = realloc(ptr, new_size)` — if `realloc` returns `NULL` (failure), you've overwritten `ptr` and lost your only reference to the old block. Always use a temp: `tmp = realloc(ptr, new_size); if (tmp) ptr = tmp;`

---

## Slide 14: Memory Leaks — Other Common Patterns

- **Key Point:** A **memory leak** occurs when allocated memory is no longer reachable but was never freed. In short-lived programs the OS cleans up; in long-running programs, leaks accumulate and eventually exhaust memory.
- **Code Example:**
```c
// Leak per iteration — a common pattern in student code
for (int i = 0; i < 1000; i++) {
    int *tmp = malloc(256 * sizeof(int));
    // ... use tmp ...
    // forgot free(tmp) — leaks 1 KB per iteration
}

// Leak via lost pointer
int *p = malloc(100);
p = malloc(200);   // original 100-byte block is now unreachable — leaked
free(p);           // only frees the 200-byte block
```
- **Speaker Note:** The second example — overwriting a pointer before freeing it — is subtle and easy to miss in a code review. Ask: "How do you find leaks?" Introduce `valgrind` on the next slide.

---

## Slide 15: valgrind — Quick Reference

- **Key Point:** `valgrind --leak-check=full` instruments your binary at runtime to detect memory errors: leaks, invalid reads/writes, use-after-free, double-free. It's available on silo. Use it before every submission.
- **Code Example:**
```bash
# Compile with debug symbols
gcc -g -Wall -o myprog myprog.c

# Run under valgrind
valgrind --leak-check=full --track-origins=yes ./myprog

# Clean output looks like:
# HEAP SUMMARY: in use at exit: 0 bytes in 0 blocks
# ERROR SUMMARY: 0 errors from 0 contexts
```
- **Speaker Note:** This is a reference card — students already saw valgrind in action during the demo. Point out the flags they should memorize: `--leak-check=full` and `--track-origins=yes`. Remind them: "0 errors from 0 contexts" is the goal for every submission. Compile with `-g` or valgrind can't show source lines. If a student says "my program runs fine," the answer is always: "What does valgrind say?"

---

## Slide 16: Key Takeaways + What's Next

**Takeaways:**
- The heap gives you memory with manual lifetime — `malloc`/`calloc` to allocate, `free` to release
- Always check `malloc`/`calloc` return for `NULL`; `free(NULL)` is a safe no-op
- Set pointers to `NULL` after `free` to prevent dangling-pointer and double-free bugs
- `realloc` may move the block — all interior pointers must be recomputed; never lose the old pointer by overwriting it before checking the `realloc` return
- Every `malloc` needs exactly one `free`; leaks accumulate in long-running programs
- `valgrind` finds what your eyes miss — run it before every submission

**Next time:** We have heap-allocated nodes, structs, and pointers. The next piece: sorting, searching, and organizing these structures — and the standard library tools that help.

> *"The stack is borrowed; the heap is owned. Own it carefully."*
