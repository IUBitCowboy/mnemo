# C291 Final Exam — Multiple Choice

**Instructions:** Choose the single best answer for each question.

---

## Question 1
*(Pointers / Structs — RPG Character Generator)*

In the RPG generator, every crewmember struct holds a pointer to the captain:

```c
typedef struct Crewmember {
    char             name[32];
    int              rank;
    struct Crewmember *captain;
} Crewmember;

Crewmember *cp = malloc(sizeof(Crewmember));
```

After the `malloc`, which of the following correctly reads the `rank` field through the pointer `cp`?

- A) `cp.rank`
- B) `*cp.rank`
- C) `cp->rank`
- D) Both A and C are correct

---

## Question 2
*(Dynamic Memory / Pointers — wc dynamic memory)*

```c
char *word = malloc(32);
strcpy(word, "hello");
free(word);
printf("%s\n", word);
```

What is the most accurate description of this program's behavior?

- A) Always prints `hello` because the memory has not been zeroed yet
- B) Always crashes with a segmentation fault
- C) Undefined behavior — may print garbage, crash, or appear to work depending on allocator state
- D) Compile error: `word` cannot be used after `free()`

---

## Question 3
*(Bit-fields / Structs — httpd response flags)*

```c
typedef struct {
    unsigned keep_alive : 1;
    unsigned text_html  : 1;
    unsigned compressed : 1;
} RespFlags;

printf("%zu\n", sizeof(RespFlags));
```

What does this print on a typical 64-bit Linux system?

- A) `1` — three bits fit in one byte
- B) `3` — one byte per field
- C) `4` — the compiler allocates at least one `unsigned int` worth of storage
- D) `8` — the compiler aligns to pointer size

---

## Question 4
*(pipe() / dup2() — httpd v2)*

In httpd v2, after `fork()`, the child process must make `nc` read its standard input from `pipe_to_nc[0]`. Which call accomplishes this before `exec`?

- A) `pipe(STDIN_FILENO, pipe_to_nc[0])`
- B) `dup(pipe_to_nc[0])`
- C) `dup2(pipe_to_nc[0], STDIN_FILENO)`
- D) `redirect(pipe_to_nc[0], 0)`

---

## Question 5
*(Function Pointers / qsort — RPG Character Generator)*

The RPG generator sorts crewmembers by rank in ascending order using `qsort`. The struct is:

```c
typedef struct { char name[32]; int rank; } Crewmember;
```

Which comparator is both correctly typed for `qsort` and produces ascending order?

- A) `int cmp(void *a, void *b) { return ((Crewmember*)a)->rank - ((Crewmember*)b)->rank; }`
- B) `int cmp(const void *a, const void *b) { return ((Crewmember*)a)->rank - ((Crewmember*)b)->rank; }`
- C) `int cmp(const void *a, const void *b) { return a->rank - b->rank; }`
- D) `int cmp(Crewmember *a, Crewmember *b) { return a->rank - b->rank; }`

---

## Question 6
*(Enumerations — RPG Character Generator)*

```c
typedef enum { SPACER = 2, ENSIGN, LIEUTENANT, COMMANDER } Rank;
Rank r = LIEUTENANT;
printf("%d\n", r);
```

What does this print?

- A) `2`
- B) `3`
- C) `4`
- D) `1`

---

## Question 7
*(Parameter Macros — general)*

```c
#define SQUARE(x)  x * x
int result = SQUARE(3 + 2);
```

What is the value of `result`?

- A) `25`
- B) `13`
- C) `11`
- D) Compile error

---

## Question 8
*(fopen() modes — httpd v2 logging)*

httpd v2 opens its log file at startup so that each run appends new entries without overwriting previous sessions. Which `fopen()` mode string is correct?

- A) `"w"` — write mode
- B) `"r+"` — read/write mode
- C) `"a"` — append mode
- D) `"w+"` — write/read mode

---

## Question 9
*(pipe() / close() — httpd v2)*

In httpd v2, after `fork()` and the `dup2()` calls in the child, the child must close all four original pipe file descriptors before calling `exec`. What is the primary reason?

- A) `close()` is required by POSIX before `exec()` but has no observable effect
- B) Unclosed FDs consume kernel memory and cause a slow memory leak
- C) If the child does not close the write end of `pipe_from_nc`, the parent's `read()` from that pipe will never receive EOF — the server hangs waiting for data that will never arrive
- D) `exec()` fails if any file descriptors other than 0, 1, and 2 are open

---

## Question 10
*(stat() / lstat() — httpd v1)*

In httpd v1, the program calls `lstat()` rather than `stat()` to examine the requested filesystem path. What is the key behavioral difference?

- A) `lstat()` is a faster version of `stat()` for local filesystems
- B) `lstat()` does not follow symbolic links; it reports information about the link itself, whereas `stat()` follows the link and reports information about its target
- C) `lstat()` works on directories and files; `stat()` works only on regular files
- D) `lstat()` returns the same information as `stat()` but uses a different struct layout

---

## Question 11
*(Bitwise Operators / Bit Masks — httpd response flags)*

The httpd response flags module defines:

```c
#define RESP_TEXT_HTML  (1u << 1)
unsigned int options = 0;
```

After some operations, which expression correctly tests whether `RESP_TEXT_HTML` is currently set in `options`?

- A) `options && RESP_TEXT_HTML`
- B) `options & RESP_TEXT_HTML`
- C) `options | RESP_TEXT_HTML`
- D) `options ^ RESP_TEXT_HTML`

---

## Question 12
*(realloc() / Dynamic Memory — wc dynamic memory)*

In the dynamic wc implementation, the word buffer is grown with `realloc()`:

```c
char *old_ptr = words;          /* save a pointer into the array */
words = realloc(words, new_cap * sizeof(char *));
```

If `realloc()` succeeds and moves the block to a new address, what is the state of `old_ptr`?

- A) Automatically updated to point to the new block
- B) Set to `NULL` by `realloc()`
- C) A dangling pointer — using it is undefined behavior
- D) A valid pointer to a copy of the original data

---

## Question 13
*(Structs / typedef — RPG Character Generator)*

The RPG generator needs a self-referential struct where each `Crewmember` holds a pointer to another `Crewmember`. Which declaration is correct?

- A) `typedef struct { char name[32]; Crewmember *captain; } Crewmember;`
- B) `typedef struct Crewmember { char name[32]; struct Crewmember *captain; } Crewmember;`
- C) `typedef struct Crewmember { char name[32]; Crewmember *captain; } Crewmember;`
- D) `struct Crewmember { char name[32]; struct Crewmember *captain; }; typedef Crewmember Crewmember;`

---

## Question 14
*(snprintf() — httpd v1)*

In httpd v1, a filesystem path is built with:

```c
char path[256];
int n = snprintf(path, sizeof(path), "%s%s", doc_root, req_path);
```

The combined string would be 300 characters. Which statement correctly describes the result?

- A) `snprintf` writes all 300 characters, silently overflowing `path`
- B) `snprintf` writes 255 characters plus a null terminator into `path` and returns `300`
- C) `snprintf` writes nothing and returns `-1`
- D) `snprintf` writes 256 characters and returns `256`

---

## Question 15
*(fork() — httpd v2)*

In httpd v2, the server calls `fork()` to spawn an `nc` subprocess. After `fork()` returns, how does the **parent** process identify itself?

- A) `fork()` returns `-1` in the parent and `0` in the child
- B) `fork()` returns `0` in both processes; the parent checks `getpid()`
- C) `fork()` returns the child's PID (a positive integer) in the parent and `0` in the child
- D) `fork()` returns the parent's PID in the child and `0` in the parent

---

---

# Answer Key

| Q | Answer | Topic | Program |
|---|--------|-------|---------|
| 1 | **C** | Struct pointer access (`->`) | RPG generator |
| 2 | **C** | Dangling pointer / UB after `free` | wc dynamic memory |
| 3 | **C** | `sizeof` with bit-field struct | httpd flags / RPG |
| 4 | **C** | `dup2()` for pipe redirection | httpd v2 |
| 5 | **B** | `qsort` comparator signature + `const void *` cast | RPG generator |
| 6 | **C** | Enum with explicit starting value (2+2=4) | RPG generator |
| 7 | **C** | `#define` parameter macro expansion (3+2\*3+2=11) | general |
| 8 | **C** | `fopen()` append mode | httpd v2 |
| 9 | **C** | Unclosed pipe ends prevent EOF, server hangs | httpd v2 |
| 10 | **B** | `lstat()` does not follow symlinks | httpd v1 |
| 11 | **B** | Bitwise AND to test a flag | httpd flags |
| 12 | **C** | `realloc()` may move block — old pointer dangles | wc dynamic memory |
| 13 | **B** | Self-referential struct requires tag name for internal pointer | RPG generator |
| 14 | **B** | `snprintf` truncates and returns would-be length | httpd v1 |
| 15 | **C** | `fork()` return: child PID to parent, `0` to child | httpd v2 |

---

# Rationale Notes (for instructor use)

**Q2** — Common wrong answer is A. Many students believe "freed memory is zeroed," which is the exact misconception the dynamic memory lecture addressed. The correct framing is undefined behavior, not "probably works."

**Q3** — Common wrong answers are A (1 byte) or B (3 bytes). Students often assume bit-fields are packed to the minimum byte count. The actual answer (4 bytes — one `unsigned int` unit) connects directly to the `sizeof` experiment in ICEX 12.

**Q5** — Option A is the most tempting wrong answer: the logic is right but `void *` (not `const void *`) fails the `qsort` contract. Option C is wrong because you cannot dereference `const void *` directly. Option D has the correct logic but wrong parameter types — `qsort` won't accept it.

**Q7** — `SQUARE(3+2)` expands to `3+2*3+2`. Operator precedence: `2*3=6`, so `3+6+2=11`. Students who answer `25` forgot to parenthesize the macro argument; those who answer `13` likely computed `(3+2)*(3) + 2`.

**Q9** — Option D is a plausible distractor for students who confuse `exec` semantics with file descriptor inheritance. `exec` *does* inherit open FDs by default (that's the mechanism we exploit for `nc`). The real reason to close is pipe reference counting for EOF delivery.

**Q13** — Option A fails because the `typedef` name `Crewmember` is not in scope inside the anonymous struct body. Option C has the same problem — `Crewmember` is not yet defined when `Crewmember *captain` is parsed. Option D is syntactically invalid (`typedef struct_tag alias` requires `struct`). Only B uses the struct tag `struct Crewmember` for the internal pointer, which is defined at the point of use.
