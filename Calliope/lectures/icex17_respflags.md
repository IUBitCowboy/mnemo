# ICEX 17: HTTP Response Flags — Bit Masks and Macros in Practice

**Duration:** 30 minutes
**Learning Goals:** Apply the set/clear/test/toggle pattern, use function-like macros, reason about sizeof with bit-fields, build a response header formatter using flags.

---

## Background

You are adding a response options subsystem to httpd v2. Rather than passing a growing list of boolean parameters to the response-building function, you will pack all options into a single `unsigned int` using named bit-mask constants and macro helpers.

---

## Starter Code

Pull from the class repo or copy from `exercises/wk14/icex17/resp_flags.c`:

```bash
git pull upstream main
gcc -g -Wall -Wextra -std=c11 -o resp_flags resp_flags.c
```

```c
#include <stdio.h>
#include <string.h>

/* ---- Response option flags ---- */
#define RESP_KEEP_ALIVE  (1u << 0)
#define RESP_TEXT_HTML   (1u << 1)
#define RESP_TEXT_PLAIN  (1u << 2)
#define RESP_APP_JSON    (1u << 3)
#define RESP_COMPRESSED  (1u << 4)

/* ---- Bit-mask helper macros ---- */
/* Task 1: define IS_SET, SET_OPT, CLR_OPT, TOG_OPT here */

/* ---- Response struct ---- */
typedef struct {
    int          status;
    unsigned int options;
    size_t       body_len;
} HttpResponse;

/* ---- Bit-field version (Task 4) ---- */
typedef struct {
    unsigned keep_alive : 1;
    unsigned text_html  : 1;
    unsigned text_plain : 1;
    unsigned app_json   : 1;
    unsigned compressed : 1;
} RespBitField;

/* ---- Functions to implement ---- */

/* Task 2: format_content_type
   Writes the correct Content-Type header line into buf based on options flags.
   Use IS_SET and the RESP_ constants. Check TEXT_HTML first, then TEXT_PLAIN,
   then APP_JSON. Default to text/plain if none set. */
void format_content_type(unsigned int options, char *buf, size_t bufsz);

/* Task 3: format_connection
   Writes "Connection: keep-alive\r\n" or "Connection: close\r\n"
   depending on whether RESP_KEEP_ALIVE is set. */
void format_connection(unsigned int options, char *buf, size_t bufsz);

/* ---- Provided: print_flags ---- */
void print_flags(unsigned int options) {
    printf("  keep-alive : %s\n", IS_SET(options, RESP_KEEP_ALIVE) ? "yes" : "no");
    printf("  text/html  : %s\n", IS_SET(options, RESP_TEXT_HTML)  ? "yes" : "no");
    printf("  text/plain : %s\n", IS_SET(options, RESP_TEXT_PLAIN) ? "yes" : "no");
    printf("  app/json   : %s\n", IS_SET(options, RESP_APP_JSON)   ? "yes" : "no");
    printf("  compressed : %s\n", IS_SET(options, RESP_COMPRESSED) ? "yes" : "no");
}

int main(void) {
    HttpResponse resp = { 200, 0, 512 };

    /* Set HTML + keep-alive */
    SET_OPT(resp.options, RESP_TEXT_HTML);
    SET_OPT(resp.options, RESP_KEEP_ALIVE);
    printf("After set HTML + keep-alive:\n");
    print_flags(resp.options);

    /* Toggle compressed */
    TOG_OPT(resp.options, RESP_COMPRESSED);
    printf("\nAfter toggle compressed:\n");
    print_flags(resp.options);

    /* Clear keep-alive */
    CLR_OPT(resp.options, RESP_KEEP_ALIVE);
    printf("\nAfter clear keep-alive:\n");
    print_flags(resp.options);

    /* Task 2 & 3 output */
    char hdr[256];
    format_content_type(resp.options, hdr, sizeof(hdr));
    printf("\nContent-Type header: %s", hdr);

    format_connection(resp.options, hdr, sizeof(hdr));
    printf("Connection header:   %s", hdr);

    /* Task 4 */
    printf("\nsizeof(unsigned int):  %zu\n", sizeof(unsigned int));
    printf("sizeof(HttpResponse):  %zu\n",  sizeof(HttpResponse));
    printf("sizeof(RespBitField):  %zu\n",  sizeof(RespBitField));

    return 0;
}
```

---

## Tasks

**Task 1 — Define the four macro helpers**
Define `IS_SET`, `SET_OPT`, `CLR_OPT`, and `TOG_OPT` using the bit-mask patterns from the lecture. All four should work correctly for any `flags` variable and any `bit` constant.

**Task 2 — `format_content_type`**
Use `IS_SET` to check flags and write the appropriate `Content-Type: ...\r\n` string into `buf`. Check `RESP_TEXT_HTML` first, then `RESP_TEXT_PLAIN`, then `RESP_APP_JSON`. Default to `text/plain` if none are set.

**Task 3 — `format_connection`**
Write `Connection: keep-alive\r\n` if `RESP_KEEP_ALIVE` is set, otherwise `Connection: close\r\n`.

**Task 4 — sizeof experiment (written answer in README.md)**
Run the program and observe the sizeof output. Answer the questions in `README.md`.

---

## Expected Output
```
After set HTML + keep-alive:
  keep-alive : yes
  text/html  : yes
  text/plain : no
  app/json   : no
  compressed : no

After toggle compressed:
  keep-alive : yes
  text/html  : yes
  text/plain : no
  app/json   : no
  compressed : yes

After clear keep-alive:
  keep-alive : no
  text/html  : yes
  text/plain : no
  app/json   : no
  compressed : yes

Content-Type header: Content-Type: text/html\r\n
Connection header:   Connection: close\r\n
```

---

## Submission Instructions

1. Branch: `git checkout -b icex17-respflags`
2. Files to submit:
   - `exercises/wk14/icex17/resp_flags.c`
   - `exercises/wk14/icex17/README.md`
3. Commit, push, open a PR to `main`, request TA/instructor review.

> **Check your README renders correctly** by navigating to your branch on `github.iu.edu` — GitHub renders Markdown automatically.

---

## README.md Template

**Name:**
**Date:**

**Task 4 — sizeof observations**

| Type | Expected (sum of fields) | Actual sizeof |
|------|--------------------------|---------------|
| `unsigned int` | 4 | |
| `HttpResponse` | | |
| `RespBitField` | 5 bits = ? bytes? | |

**Q1.** `RespBitField` has five 1-bit fields. What did `sizeof` report? Why isn't it 1 byte?

> *(your answer here)*

**Q2.** If you added a `unsigned ctype : 3` field to `RespBitField`, would `sizeof` change? Make a prediction, then try it.

> *(prediction):*
> *(actual result):*
> *(explanation):*

**Q3.** Given the warning from lecture about bit-fields and wire protocols: would it be safe to use `RespBitField` to parse incoming HTTP request flags directly off the pipe? Why or why not?

> *(your answer here)*

---

## Rubric

| Task | Points | Criteria |
|------|--------|----------|
| Task 1 — Four macro helpers | 2 | All four macros correct; proper parenthesization |
| Task 2 — `format_content_type` | 2 | Correct priority order; default case handled |
| Task 3 — `format_connection` | 2 | Correct string for both flag states |
| Task 4 — sizeof (written) | 2 | Correct sizeof values; explanation references alignment |
| Code quality — no magic numbers, compiles clean with `-Wall -Wextra` | 2 | Zero warnings |
| **Total** | **10** | |
