# C291 Final Exam — Short Answer Questions

**Instructions:** Answer each question completely. For code questions, write correct, compilable C. You do not need to write `#include` directives unless the question specifically asks for them.

---

## Question 16 — Directory Processing
*(opendir / readdir / closedir — httpd v1)*

Write a C function named `print_dir_entries` that accepts a directory path as a `const char *` parameter. The function must:

1. Open the directory and handle the case where it cannot be opened
2. Iterate over every entry, printing each name to stdout on its own line
3. Skip the special entries `.` and `..`
4. Close the directory before returning

You do not need to call `stat()` or distinguish files from subdirectories.

---

## Question 17 — Binary File I/O
*(fread / fwrite)*

The RPG character generator saves crew data to a binary file. Using the struct definition below, write a **single self-contained code snippet** that:

1. Opens the file `"crew.bin"` for binary writing, writes one `Crewmember` record, and closes the file — checking the return value of `fwrite` to confirm exactly one record was written
2. Re-opens the same file for binary reading, reads the record back into a second `Crewmember` variable, and closes the file — checking the return value of `fread` to confirm exactly one record was read

```c
typedef struct {
    char name[32];
    int  rank;
    int  service_num;
} Crewmember;
```

You may initialize the first `Crewmember` with any values you like. Declare all variables.

---

## Question 18 — Formatted File Input
*(fscanf / format specifiers)*

A student roster file named `"roster.txt"` contains one record per line in the following format:

```
Alice 88 1001
Bob 75 1002
Sasha 92 1003
```

Each line contains: a name (single word, no spaces), an integer score, and an integer student ID, separated by whitespace.

Write a C code snippet that:

1. Opens the file for reading with appropriate error handling
2. Reads records in a loop using `fscanf` until end-of-file
3. Prints each record to stdout in the format: `Name: Alice  Score: 88  ID: 1001`
4. Closes the file

Declare all variables. Use a field-width specifier on the name to prevent a buffer overrun.

---

## Question 19 — Macro Bug: Identify, Explain, and Fix
*(Parameter macros / non-idempotent expressions)*

A student defines the following macro and calls it in their RPG generator's dice-rolling code:

```c
#define SQUARE(x)  ((x) * (x))

int n = 5;
int result = SQUARE(n++);
```

The programmer expects `result` to be `25` and `n` to be `6` after these lines run.

**(a)** Write out the exact expansion of `SQUARE(n++)` as the C preprocessor produces it.

**(b)** What are the actual values of `result` and `n`? Explain in two or three sentences why they differ from the programmer's expectation. Use the term **non-idempotent** in your explanation.

**(c)** Rewrite the last two lines at the call site — without changing the macro definition — so the programmer's intent is correctly achieved.

---
---

# Answer Key and Rubric

---

## Question 16 — Model Answer

```c
#include <dirent.h>
#include <stdio.h>
#include <string.h>

void print_dir_entries(const char *path) {
    DIR *dp = opendir(path);
    if (dp == NULL) {
        perror("opendir");
        return;
    }

    struct dirent *entry;
    while ((entry = readdir(dp)) != NULL) {
        if (strcmp(entry->d_name, ".")  == 0 ||
            strcmp(entry->d_name, "..") == 0)
            continue;
        printf("%s\n", entry->d_name);
    }

    closedir(dp);
}
```

**Rubric (8 points):**

| Criterion | Points |
|-----------|--------|
| `opendir()` called with path argument | 1 |
| Return value of `opendir()` checked for `NULL` | 1 |
| `readdir()` used correctly in a loop; loop terminates on `NULL` | 2 |
| `.` and `..` filtered using `strcmp` (not `==` on strings) | 2 |
| `closedir()` called before return | 1 |
| `struct dirent *` declared correctly | 1 |

**Common mistakes:** Using `==` to compare strings instead of `strcmp`; forgetting `closedir()`; not checking `opendir()` return.

---

## Question 17 — Model Answer

```c
Crewmember crew = {"Kirk", 3, 100001};
Crewmember loaded;

/* --- Write --- */
FILE *fp = fopen("crew.bin", "wb");
if (!fp) { perror("fopen write"); return; }

size_t written = fwrite(&crew, sizeof(Crewmember), 1, fp);
if (written != 1)
    fprintf(stderr, "fwrite: expected 1, wrote %zu\n", written);
fclose(fp);

/* --- Read back --- */
fp = fopen("crew.bin", "rb");
if (!fp) { perror("fopen read"); return; }

size_t nread = fread(&loaded, sizeof(Crewmember), 1, fp);
if (nread != 1)
    fprintf(stderr, "fread: expected 1, got %zu\n", nread);
fclose(fp);
```

**Rubric (8 points):**

| Criterion | Points |
|-----------|--------|
| `fopen` with `"wb"` mode for binary write | 1 |
| `fwrite(&crew, sizeof(Crewmember), 1, fp)` — correct argument order | 2 |
| Return value of `fwrite` checked against `1` | 1 |
| `fopen` with `"rb"` mode for binary read | 1 |
| `fread(&loaded, sizeof(Crewmember), 1, fp)` — correct argument order | 2 |
| Return value of `fread` checked against `1` | 1 |

**Common mistakes:** Swapping the `size` and `count` arguments; using `"w"` / `"r"` (text mode) instead of `"wb"` / `"rb"`; not checking `fread`/`fwrite` return values; passing `crew` instead of `&crew`.

---

## Question 18 — Model Answer

```c
FILE *fp = fopen("roster.txt", "r");
if (!fp) {
    perror("fopen");
    return;
}

char name[64];
int  score, id;

while (fscanf(fp, "%63s %d %d", name, &score, &id) == 3) {
    printf("Name: %s  Score: %d  ID: %d\n", name, score, id);
}

fclose(fp);
```

**Rubric (8 points):**

| Criterion | Points |
|-----------|--------|
| `fopen` with `"r"` mode; return checked | 1 |
| `fscanf` used (not `scanf` or `fgets`+`sscanf`) | 1 |
| Format string `"%s %d %d"` or equivalent whitespace-separated | 1 |
| Field-width specifier on `%s` (`%63s` or similar) to prevent overrun | 2 |
| `&score` and `&id` passed by address; `name` passed without `&` | 2 |
| Loop termination condition checks return value `== 3` | 1 |

**Common mistakes:** Checking `!= EOF` instead of `== 3` for the loop condition (fails on malformed input); omitting `&` on `score` or `id`; adding `&` to `name`; no width specifier on `%s`.

**Note on `== 3`:** `fscanf` returns the number of items successfully matched. Checking `== 3` is more robust than checking `!= EOF` because it also exits the loop on a partial or malformed line.

---

## Question 19 — Model Answer

**(a) Expansion:**

```c
((n++) * (n++))
```

**(b) Actual values and explanation:**

`result = 30`, `n = 7`.

`n++` is **non-idempotent**: each time it is evaluated it both produces a value and increments `n` as a side effect. Because `x` appears twice in the macro body, `n++` is evaluated twice — once yielding `5` (n becomes 6), then again yielding `6` (n becomes 7), so the product is `5 * 6 = 30` and `n` ends up at `7` rather than `6`. A function would evaluate the argument exactly once before entering the body; a macro provides no such guarantee.

**(c) Corrected call site:**

```c
int result = SQUARE(n);   /* pass stable value — result = 25 */
n++;                       /* increment exactly once — n = 6  */
```

**Rubric (8 points):**

| Criterion | Points |
|-----------|--------|
| **(a)** Correct expansion showing `n++` in both operand positions | 2 |
| **(b)** Correct values: `result = 30`, `n = 7` | 2 |
| **(b)** Uses **non-idempotent** correctly and explains the double-evaluation side effect | 2 |
| **(c)** Separates the macro call from the increment so each happens exactly once | 2 |

**Common mistakes:** Writing the expansion as `(n * n)` (forgetting the `++`); stating `n = 6` or `result = 25` for the actual values; describing the problem as "operator precedence" rather than double evaluation of a side-effecting argument.

---

## Exam Point Summary

| Section | Questions | Points |
|---------|-----------|--------|
| Multiple Choice | 15 | 45 |
| Short Answer — Code | 16, 17, 18 | 24 |
| Short Answer — Correction | 19 | 8 |
| **Total** | **19** | **77** |
