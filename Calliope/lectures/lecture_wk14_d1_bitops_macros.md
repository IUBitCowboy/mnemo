# Lecture: Bit Operations and Macros — Speaking the Language of the Machine

## Slide 1: Title Slide
- **Topic:** Bitwise Operators, Bit-masks, Bit-fields, and Macros
- **Course:** C291 — System Programming with C and Linux
- **Timing:** 40-min lecture + 30-min ICEX + 5-min buffer = 75 min

---

## Slide 2: Learning Objectives
By the end of this lecture, you will be able to:

- Apply all six bitwise operators and predict their results on integer values
- Use the set / clear / test / toggle bit-mask pattern to manage packed flag variables
- Declare bit-fields in structs and explain when they are and are not appropriate
- Define object-like and function-like macros, and identify their classic pitfalls
- Apply `#ifdef` guards to prevent double-inclusion of header files
- Use macros and bit-masks to manage HTTP response options in the httpd project

---

## Slide 3: Bitwise Operators — The Six Operators

- **Key Point:** Bitwise operators work on individual bits of integer values, not on the value as a whole. Every systems programmer needs these at reflex speed.
- **Code Example:**
```c
unsigned int a = 0xA;   // 0000 1010
unsigned int b = 0xC;   // 0000 1100

a & b;    // 0000 1000 = 0x8  — AND:  bits set in BOTH
a | b;    // 0000 1110 = 0xE  — OR:   bits set in EITHER
a ^ b;    // 0000 0110 = 0x6  — XOR:  bits set in ONE but not both
~a;       // 1111 0101 = ...  — NOT:  flip every bit (result is signed-width dependent)
a << 1;   // 0001 0100 = 0x14 — LEFT SHIFT:  multiply by 2
a >> 1;   // 0000 0101 = 0x5  — RIGHT SHIFT: divide by 2
```
- **Speaker Note:** Use hex and binary side-by-side on the board. Students who have not done digital logic will need a moment with NOT — emphasize that ~a on a 32-bit unsigned int flips all 32 bits, not just the meaningful ones. `printf("%#x\n", ~a)` makes this visceral. Ask: "What does left-shifting by 3 do to a number?" Answer: multiplies by 8. Useful for fast power-of-two math.

---

## Slide 4: Bit Shifts — Multiply and Divide by Powers of Two

- **Key Point:** Left shift by N = multiply by 2ᴺ. Right shift by N = divide by 2ᴺ (unsigned). They are also the canonical way to position a single bit at a known offset — the foundation of every flag system.
- **Code Example:**
```c
1 << 0   // 0000 0001 = 1   — bit 0
1 << 1   // 0000 0010 = 2   — bit 1
1 << 2   // 0000 0100 = 4   — bit 2
1 << 7   // 1000 0000 = 128 — bit 7

/* Fast power-of-two arithmetic */
int x = 5;
x << 3;   // 5 * 8  = 40
x >> 1;   // 5 / 2  = 2  (integer division)

/* Never left-shift into the sign bit of a signed type — UB */
unsigned int flags = 0;
flags |= (1u << 31);  // safe: 1u is unsigned
```
- **Speaker Note:** The `(1 << N)` idiom is everywhere in system headers — Linux kernel source, POSIX headers, device driver registers. Students should be able to read `(1 << 4)` and instantly think "bit 4 is set." The UB warning about shifting signed integers into the sign bit is real — use `1u` or `UINT32_C(1)` when building flag constants.

---

## Slide 5: The Bit Mask Pattern — Set, Clear, Test, Toggle

- **Key Point:** Four operations cover every flag-management need. Memorize these; you will write them thousands of times in a systems career.
- **Code Example:**
```c
unsigned int flags = 0;

#define FLAG_VERBOSE   (1u << 0)   // 0001
#define FLAG_CACHED    (1u << 1)   // 0010
#define FLAG_COMPRESS  (1u << 2)   // 0100
#define FLAG_AUTH      (1u << 3)   // 1000

/* SET a bit */
flags |= FLAG_VERBOSE;             // flags = 0001

/* CLEAR a bit */
flags &= ~FLAG_VERBOSE;            // ~FLAG_VERBOSE = 1110; flags = 0000

/* TEST a bit (evaluate as bool) */
if (flags & FLAG_CACHED) { ... }   // non-zero = true

/* TOGGLE a bit */
flags ^= FLAG_COMPRESS;            // flips bit 2 regardless of current state
```
- **Speaker Note:** Drill the patterns verbally: "OR to set, AND-NOT to clear, AND to test, XOR to toggle." The `~FLAG` in the clear operation is the one students fumble — ask them to write `~FLAG_VERBOSE` in binary before they write the `&=` line. Common mistake: using `= FLAG` (assignment, not OR) to set, which clobbers all other bits.

---

## Slide 6: HTTP Response Flags — Bit Masks in Context

- **Key Point:** The httpd v2 server needs to track response options — content type, keep-alive, compression. A single `unsigned int` with named flag bits is cleaner and cheaper than a struct of booleans.
- **Code Example:**
```c
/* Response option flags for httpd */
#define RESP_KEEP_ALIVE   (1u << 0)
#define RESP_TEXT_HTML    (1u << 1)
#define RESP_TEXT_PLAIN   (1u << 2)
#define RESP_APP_JSON     (1u << 3)
#define RESP_COMPRESSED   (1u << 4)

typedef struct {
    int          status;
    unsigned int options;    /* bit-packed option flags */
    size_t       body_len;
} HttpResponse;

HttpResponse resp = { 200, 0, 0 };

/* Signal this is an HTML response with keep-alive */
resp.options |= RESP_TEXT_HTML | RESP_KEEP_ALIVE;

/* Check before adding Content-Encoding header */
if (resp.options & RESP_COMPRESSED) {
    /* append compression header */
}
```
- **Speaker Note:** Connect to the existing httpd v1 code — right now content-type is probably a hardcoded string. This pattern lets the response-building function adapt based on flags passed in, without a tangle of boolean parameters. Ask: "How many distinct options can you pack into an unsigned int?" Answer: 32 (or 64 with uint64_t). That's far more than any HTTP response needs.

---

## Slide 7: Bit-fields in Structs — Packing Multiple Values

- **Key Point:** A bit-field declares a struct member with an explicit width in bits. The compiler packs them together. Useful for readability when working with hardware registers or tightly-packed protocol data you control.
- **Code Example:**
```c
typedef struct {
    unsigned keep_alive : 1;   /* 1 bit */
    unsigned compressed : 1;   /* 1 bit */
    unsigned ctype      : 3;   /* 3 bits — up to 8 content types */
    unsigned version    : 2;   /* 2 bits — HTTP 1.0, 1.1, 2.0 */
    unsigned            : 0;   /* force alignment to next unit boundary */
} RespFlags;

RespFlags f = {0};
f.keep_alive = 1;
f.ctype      = 2;   /* e.g., 2 = text/html */

printf("keep_alive: %u\n", f.keep_alive);
printf("sizeof RespFlags: %zu\n", sizeof(RespFlags));  /* likely 4 */
```
- **Speaker Note:** Show `sizeof` — students expect it to be 1 byte but it's typically 4 (one `unsigned int` worth). Bit-fields give you named access to sub-integer values without manual shifting. Ask: "Could you use bit-fields for an IP header?" Technically yes, but lead into the next slide with that question.

---

## Slide 8: Bit-fields — The Warnings

- **Key Point:** Bit-fields are convenient for code you control, but **never use them for wire protocol parsing or binary file I/O**. Field order, padding, and size are implementation-defined — what your compiler produces may not match what the network expects.
- **Code Example:**
```c
/* The IPv4 header has a 4-bit version and 4-bit IHL field.
   Tempting to write: */
struct BadIpHeader {
    unsigned version : 4;
    unsigned ihl     : 4;
    /* ... */
};
/* DO NOT DO THIS — bit order within a byte is compiler/arch defined.
   On a little-endian machine this may pack ihl first, version second,
   which is the opposite of the wire format.                          */

/* Correct approach: read the byte, then extract with masks */
uint8_t byte0 = buf[0];
uint8_t version = (byte0 >> 4) & 0x0F;
uint8_t ihl     =  byte0       & 0x0F;
```
- **Speaker Note:** This is a real-world war story — developers have shipped broken network code because they trusted bit-fields to match wire format. The rule: bit-fields are for your own internal data structures; bitwise operators + masks are for anything that touches the wire, a file, or hardware registers. The httpd assignment is fine using bit-fields for internal response flags; it would be wrong to use them to parse the raw TCP stream.

---

## Slide 9: Object-like Macros — Named Constants

- **Key Point:** `#define` creates a text substitution rule processed before compilation. Object-like macros give meaningful names to constants and eliminate magic numbers throughout your code.
- **Code Example:**
```c
/* httpd constants — no magic numbers in code */
#define HTTP_PORT        8080
#define BUF_SIZE         4096
#define MAX_HEADERS      32
#define MAX_PATH_LEN     256
#define LOG_DIR          "logs"

#define HTTP_200  "HTTP/1.1 200 OK"
#define HTTP_400  "HTTP/1.1 400 Bad Request"
#define HTTP_404  "HTTP/1.1 404 Not Found"
#define HTTP_500  "HTTP/1.1 500 Internal Server Error"

#define CRLF      "\r\n"
#define HDR_END   "\r\n\r\n"

/* Usage — readable, maintainable */
write(fd, HTTP_200, strlen(HTTP_200));
write(fd, CRLF, strlen(CRLF));
```
- **Speaker Note:** Contrast with `const` variables: macros have no type, no storage, no address — they are purely textual. A `const int BUF_SIZE = 4096` has a memory address; `#define BUF_SIZE 4096` does not. Both eliminate magic numbers; prefer `const` when you need the type system's help, prefer `#define` for string literals and when the constant must be usable in array size declarations in C89/C90. Ask: "What happens if you `printf("%d\n", BUF_SIZE)` — where does the 4096 come from?" Answer: the preprocessor replaced the token before the compiler saw it.

---

## Slide 10: Function-like Macros — Parameterized Substitution

- **Key Point:** A macro with parenthesized parameters acts like an inline function — but it is pure text substitution with no type checking, no stack frame, and no call overhead. Useful for small, performance-critical operations.
- **Code Example:**
```c
/* Bit mask helpers */
#define IS_SET(flags, bit)   ((flags) &  (bit))
#define SET_BIT(flags, bit)  ((flags) |= (bit))
#define CLR_BIT(flags, bit)  ((flags) &= ~(bit))
#define TOG_BIT(flags, bit)  ((flags) ^= (bit))

/* General utility */
#define MAX(a, b)   ((a) > (b) ? (a) : (b))
#define MIN(a, b)   ((a) < (b) ? (a) : (b))
#define ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))

/* Usage */
unsigned int opts = 0;
SET_BIT(opts, RESP_TEXT_HTML);
if (IS_SET(opts, RESP_KEEP_ALIVE)) { /* ... */ }
```
- **Speaker Note:** Walk through `IS_SET(opts, RESP_TEXT_HTML)` expanding to `((opts) & (RESP_TEXT_HTML))`. Emphasize that every parameter and the whole expression should be wrapped in parentheses — not doing so is the source of the pitfalls on the next slide. `ARRAY_LEN` is a classic macro that cannot be a function (sizeof is a compile-time operator).

---

## Slide 11: Function-like Macro Pitfalls

- **Key Point:** Two classic bugs: **operator precedence** (forgotten parentheses) and **double evaluation** (side-effecting arguments evaluated multiple times). Both are silent and produce wrong answers.
- **Code Example:**
```c
/* Pitfall 1: missing parentheses around parameters */
#define BAD_SQUARE(x)  x * x
BAD_SQUARE(1 + 2)     /* expands to: 1 + 2 * 1 + 2 = 5 — wrong! */

#define GOOD_SQUARE(x)  ((x) * (x))
GOOD_SQUARE(1 + 2)    /* expands to: ((1+2) * (1+2)) = 9 — correct */

/* Pitfall 2: double evaluation with side effects */
#define MAX(a, b)  ((a) > (b) ? (a) : (b))

int i = 3, j = 5;
int m = MAX(i++, j++);
/* expands to: ((i++) > (j++) ? (i++) : (j++))
   j++ is evaluated TWICE if j > i — j ends up as 7, not 6 */

/* Fix: use an inline function for anything with side effects */
static inline int max_int(int a, int b) { return a > b ? a : b; }
```
- **Speaker Note:** Show BAD_SQUARE live — type it, predict the output, run it. The surprise is memorable. Then show the double-evaluation bug with actual values. The lesson: function-like macros are safe for simple expressions with no side effects. The moment you pass `i++`, `malloc()`, or a function call as an argument, use an `inline` function instead. C99 and later support `static inline` which gives macro-like inlining without the pitfalls.

---

## Slide 12: Conditional Compilation and Header Guards

- **Key Point:** `#ifdef` / `#ifndef` directives let the preprocessor include or skip blocks of code. The most critical use: **header guards** that prevent a header file from being included more than once in a translation unit.
- **Code Example:**
```c
/* httpd.h */
#ifndef HTTPD_H      /* if HTTPD_H is not yet defined... */
#define HTTPD_H      /* define it (so subsequent includes are skipped) */

#include <stddef.h>

#define HTTP_PORT   8080
#define BUF_SIZE    4096

typedef struct {
    int          status;
    unsigned int options;
    size_t       body_len;
} HttpResponse;

void send_response(int fd, const HttpResponse *resp, const char *body);

#endif /* HTTPD_H */  /* end of the guarded block */
```
- **Speaker Note:** Ask: "What happens without the guard if two .c files both include httpd.h and one includes the other?" Answer: the struct and function declarations appear twice in one compilation unit — multiply-defined symbol errors. The guard pattern is so standard it's worth committing to muscle memory. Also mention `#pragma once` — it's widely supported, simpler, but not in the C standard. Professional codebases use the `#ifndef` form for portability.

---

## Slide 13: Bringing It Together — httpd v2 Header

- **Key Point:** Everything from this lecture converges in the httpd v2 header: constants, flags, bit-mask helpers, and guards. This is what a real system header looks like.
- **Code Example:**
```c
#ifndef HTTPD_H
#define HTTPD_H

#include <stddef.h>

/* Server constants — no magic numbers in .c files */
#define HTTP_PORT     8080
#define BUF_SIZE      4096
#define LOG_DIR       "logs"
#define HDR_END       "\r\n\r\n"

/* HTTP status line macros */
#define HTTP_200  "HTTP/1.1 200 OK"
#define HTTP_404  "HTTP/1.1 404 Not Found"
#define HTTP_500  "HTTP/1.1 500 Internal Server Error"

/* Response option flags */
#define RESP_KEEP_ALIVE  (1u << 0)
#define RESP_TEXT_HTML   (1u << 1)
#define RESP_TEXT_PLAIN  (1u << 2)
#define RESP_APP_JSON    (1u << 3)

/* Bit-mask helpers */
#define IS_SET(f, b)   ((f) &  (b))
#define SET_OPT(f, b)  ((f) |= (b))
#define CLR_OPT(f, b)  ((f) &= ~(b))

typedef struct {
    int          status;
    unsigned int options;
    size_t       body_len;
} HttpResponse;

#endif /* HTTPD_H */
```
- **Speaker Note:** Show this as a live file students can use directly in the assignment. Point out: every magic number from v1 is now named; the options field replaces however they were tracking content type before; the helpers make the calling code in the .c file readable. The next lecture wires nc into this framework.

---

## Slide 14: Key Takeaways + What's Next

**Takeaways:**
- Six bitwise operators: `&` `|` `^` `~` `<<` `>>` — know them at reflex speed
- Bit-mask pattern: OR to set, AND-NOT to clear, AND to test, XOR to toggle
- Bit-fields: convenient for internal structs you control; **never** for wire formats or binary I/O — bit ordering is implementation-defined
- Object-like macros eliminate magic numbers; function-like macros act inline — parenthesize everything, never pass side-effecting arguments
- Header guards (`#ifndef NAME_H / #define NAME_H / #endif`) prevent double-inclusion

**Next:** We have the vocabulary and the flag system. Tomorrow we wire netcat into the server: two pipes, one subprocess, and a deadlock you need to understand before you can prevent it.

> *"Bit operations are the vocabulary of hardware. Macros are the shorthand of systems programmers. Learn both or spend your career reading other people's code without understanding it."*

---

> **In-class exercise:** See `icex17_respflags.md`

**Duration:** 30 minutes
**Learning Goals:** Apply the set/clear/test/toggle pattern, use function-like macros, reason about sizeof with bit-fields, build a response header formatter using flags.

---

## Background

You are adding a response options subsystem to httpd v2. Rather than passing a growing list of boolean parameters to the response-building function, you will pack all options into a single `unsigned int` using named bit-mask constants and macro helpers.

---

## Starter Code

Pull from the class repo or copy from `exercises/wk14/icex14a/resp_flags.c`:

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

1. Branch: `git checkout -b icex14a-respflags`
2. Files to submit:
   - `exercises/wk14/icex14a/resp_flags.c`
   - `exercises/wk14/icex14a/README.md`
3. Commit, push, open a PR to `main`, request TA/instructor review.

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
