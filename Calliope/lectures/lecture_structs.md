# Lecture: Structs — Bundling Data Like a Systems Programmer

## Slide 1: Title Slide
- **Topic:** Structs in C
- **Course:** C291 — System Programming with C and Linux
- **Timing:** 40-min lecture + 30-min ICEX + 5-min buffer = 75 min

---

## Slide 2: Learning Objectives
By the end of this lecture, you will be able to:

- Define and initialize a `struct` with scalar, array, and nested fields, and apply `typedef` to simplify its type name
- Explain how C lays out struct members in memory, including padding
- Pass structs to functions by value and by pointer, and reason about the cost of each
- Return a struct from a function to package complex results
- Access struct members with both `.` and `->` notation
- Identify why a self-referential struct cannot store itself by value

---

## Slide 3: What Is a Struct?

- **Key Point:** A `struct` is a user-defined type that groups logically related variables of *different* types under one name. The compiler allocates them contiguously in memory.
- **Code Example:**
```c
struct Point {
    int x;
    int y;
};
```
- **Speaker Note:** Ask students: "In Java you'd make a class. What's the same? What's different?" Key difference: no methods, no access control, no implicit `this`. A struct is just shaped memory.

---

## Slide 4: typedef — Giving Your Struct a Clean Name

- **Key Point:** Without `typedef`, the full type name is `struct Point` everywhere. `typedef` creates an alias so you can write just `Point`. The two most common patterns are separate declaration and combined declaration.
- **Code Example:**
```c
/* Pattern 1: separate — declare struct, then typedef */
struct Point {
    int x;
    int y;
};
typedef struct Point Point;

Point p = {3, 4};          // no "struct" keyword needed

/* Pattern 2: combined — typedef at definition (idiomatic C) */
typedef struct {
    int x;
    int y;
} Point;

Point p = {3, 4};          // same result
```
- **Speaker Note:** Ask why Pattern 1 keeps the `struct Point` tag. Answer: self-referential structs *require* a tag because the typedef name isn't visible until the definition closes (show this on the next board sketch — a linked-list node needs `struct Node *next`, not `Node *next`, if using the combined pattern). Pattern 2 is fine for any struct that doesn't reference itself. You'll see both in production C code; students should recognize and read each form. Also note: `typedef` does *not* create a new type — it's purely a name alias; `sizeof(Point) == sizeof(struct Point)`.

---

## Slide 5: Declaring and Initializing Structs

- **Key Point:** You can initialize a struct at declaration with a brace initializer, or assign field-by-field. C99 adds *designated initializers* for clarity.
- **Code Example:**
```c
struct Point p1 = {3, 4};           // positional init
struct Point p2 = {.x = 10, .y = 5}; // C99 designated init
struct Point p3;
p3.x = 7;
p3.y = 2;

printf("p1 = (%d, %d)\n", p1.x, p1.y);
```
- **Speaker Note:** Emphasize `p3` is uninitialized until the assignments — garbage values lurk. Designated initializers are safer when structs grow. Also: `struct Point` is the full type name unless you `typedef`.

---

## Slide 6: Array Fields — Data Lives *Inside* the Struct

- **Key Point:** An array field is stored inline in the struct — not as a pointer. The entire array is part of the struct's body.
- **Code Example:**
```c
struct Student {
    char name[32];   // 32 bytes inline
    int  grades[5];  // 20 bytes inline
    float gpa;       // 4 bytes
};

struct Student alice = {
    .name   = "Alice",
    .grades = {90, 85, 92, 88, 95},
    .gpa    = 0.0f
};

printf("First grade: %d\n", alice.grades[0]);
```
- **Speaker Note:** Draw this on the board: `name[32]` | `grades[20]` | `gpa[4]` all in one block. Compare to Java where a field like `int[] grades` is a *reference* — in C the array is actually *here*. This is why copying a struct copies the array too.

---

## Slide 7: Memory Layout and Padding

- **Key Point:** The compiler inserts *padding* bytes between fields to satisfy alignment requirements. An `int` must start at a 4-byte boundary; a `double` at an 8-byte boundary.
- **Code Example:**
```c
struct Padded {
    char   c;   // 1 byte @ offset 0
                // [3 bytes padding]
    int    i;   // 4 bytes @ offset 4
    double d;   // 8 bytes @ offset 8
};
// Total: 16 bytes (NOT 13)

struct Packed {
    int    i;   // 4 bytes @ offset 0
    char   c;   // 1 byte  @ offset 4
    double d;   // 8 bytes @ offset 8 (1 + 3 pad)
};
// Also 16 bytes — field order matters for padding!
```
- **Speaker Note:** Draw the byte boxes on the board. Alignment rule of thumb: a field of size N must start at an address divisible by N (up to the platform's max alignment). Struct size is also padded at the end so that arrays of structs stay aligned.

---

## Slide 8: sizeof() Surprises

- **Key Point:** Always use `sizeof(struct T)` — never manually add up field sizes. The result can surprise you due to padding.
- **Code Example:**
```c
struct Padded {
    char   c;
    int    i;
    double d;
};

printf("char:   %zu\n", sizeof(char));    // 1
printf("int:    %zu\n", sizeof(int));     // 4
printf("double: %zu\n", sizeof(double)); // 8
printf("sum:    %zu\n", 1 + 4 + 8);     // 13 — WRONG!
printf("actual: %zu\n", sizeof(struct Padded)); // 16
```
- **Speaker Note:** This is a classic interview question and a real source of bugs in network protocols and binary file I/O. Ask: "What if you `fwrite` a struct and read it on a machine with different alignment rules?" (Foreshadow: portable serialization is hard.) `__attribute__((packed))` exists but has tradeoffs.

---

## Slide 9: Passing Structs to Functions — The Value Copy

- **Key Point:** Passing a struct by value copies the *entire* struct onto the stack. Modifications inside the function do **not** affect the caller's copy.
- **Code Example:**
```c
void zero_gpa(struct Student s) {
    s.gpa = 0.0f;   // modifies the LOCAL copy only
}

int main(void) {
    struct Student alice = {.name="Alice", .gpa=3.8f};
    zero_gpa(alice);
    printf("%.1f\n", alice.gpa);  // still 3.8 — the bug!
    return 0;
}
```
- **Speaker Note:** This is THE classic struct mistake. Ask: "Where have you seen this before?" (Answer: scalars in functions.) The mental model is identical — C is always pass-by-value. The cost angle: `struct Student` is ~56 bytes — every call copies 56 bytes onto the stack.

---

## Slide 10: Stack Frames and the Cost of Copies

- **Key Point:** Each function call creates a stack frame. Passing a large struct by value grows that frame by the full size of the struct — for every call.
- **Code Example:**
```c
// By value: copies sizeof(struct Student) bytes per call
void print_student_v(struct Student s) { ... }

// By pointer: copies only sizeof(struct Student *) bytes = 8 bytes
void print_student_p(const struct Student *s) {
    printf("%s: %.1f\n", s->name, s->gpa);
}
```
- **Speaker Note:** Sketch two stack frames side-by-side: one with a 56-byte local copy, one with an 8-byte pointer. The `const` keyword signals intent — "I need to read this, not change it." For small structs (≤ 2 fields, ≤ 16 bytes) the difference is trivial; for larger structs it matters. This is why the Linux kernel passes big structs by pointer everywhere.

---

## Slide 11: Returning Structs — Packaging Complex Results

- **Key Point:** A function can return a struct, allowing it to return multiple values as a single logical unit. C copies the struct back to the caller.
- **Code Example:**
```c
struct Point midpoint(struct Point a, struct Point b) {
    struct Point mid;
    mid.x = (a.x + b.x) / 2;
    mid.y = (a.y + b.y) / 2;
    return mid;
}

int main(void) {
    struct Point p1 = {0, 0};
    struct Point p2 = {4, 6};
    struct Point m  = midpoint(p1, p2);
    printf("Midpoint: (%d, %d)\n", m.x, m.y);
    return 0;
}
```
- **Speaker Note:** Before C structs, the only way to return "two values" was out-parameters (pointer args) or global variables — both ugly. Modern compilers often optimize small struct returns into registers (RVO). This pattern shows up everywhere in systems code for returning status + result pairs.

---

## Slide 12: Struct Pointers and the Arrow Operator

- **Key Point:** When you have a pointer to a struct, use `->` to access members. It is exactly shorthand for `(*ptr).field`.
- **Code Example:**
```c
struct Student alice = {.name="Alice", .gpa=3.8f};
struct Student *sp = &alice;

// Two equivalent ways to access:
printf("%.1f\n", (*sp).gpa);  // dereference, then dot
printf("%.1f\n", sp->gpa);    // arrow: cleaner, preferred

// Mutation through pointer works:
sp->gpa = 3.9f;
printf("%.1f\n", alice.gpa);  // 3.9 — same object!
```
- **Speaker Note:** `(*sp).gpa` has operator-precedence traps — `.` binds tighter than `*`, so you *need* the parens. `->` was invented to make this idiomatic. Ask: "When would you prefer `->` over `.`?" Answer: whenever you have a pointer. Build the habit now — it will matter critically with malloc next lecture.

---

## Slide 13: Dot vs Arrow — Decision Rule

- **Key Point:** The rule is simple: if the variable IS a struct, use `.`; if the variable IS a pointer TO a struct, use `->`.
- **Code Example:**
```c
struct Point p   = {1, 2};    // p  is a struct
struct Point *pp = &p;        // pp is a pointer to a struct

p.x   = 10;    // correct: p is a struct
pp->x = 10;    // correct: pp is a pointer
(*pp).x = 10;  // also correct, but verbose

// Common mistake:
// pp.x = 10;   ERROR: pp is a pointer, not a struct
// p->x = 10;   ERROR: p is a struct, not a pointer
```
- **Speaker Note:** Compiler errors like `error: request for member 'x' in something not a structure` almost always mean you used `.` when you should have used `->`, or vice versa. Teach them to read the error and check the type of the variable on the left side.

---

## Slide 14: Structs Within Structs

- **Key Point:** A struct can contain other structs as fields. Access nested members by chaining `.` (or mixing `.` and `->` as appropriate).
- **Code Example:**
```c
struct Address {
    char street[64];
    char city[32];
    int  zip;
};

struct Person {
    char           name[32];
    struct Address addr;      // Address stored inline
};

struct Person bob = {
    .name = "Bob",
    .addr = {.street="1 Main St", .city="Bloomington", .zip=47401}
};

printf("%s lives in %s\n", bob.name, bob.addr.city);

struct Person *pp = &bob;
printf("ZIP: %d\n", pp->addr.zip);  // -> then .
```
- **Speaker Note:** Note the mixed `->addr.zip` — one `->` because `pp` is a pointer, then `.zip` because `addr` is a struct (not a pointer). `sizeof(struct Person)` = 32 + sizeof(Address) inline. Nested structs are common in OS data structures: think `struct task_struct` in the Linux kernel.

---

## Slide 15: The Self-Referential Struct Problem

- **Key Point:** A struct cannot contain an instance of *itself* — that would require infinite size. It *can* contain a **pointer** to itself. But useful self-referential structs require heap allocation — coming next lecture.
- **Code Example:**
```c
// ILLEGAL — infinite size, won't compile:
struct BadNode {
    int         data;
    struct BadNode next;   // ERROR: incomplete type
};

// LEGAL — pointer has fixed size (8 bytes on 64-bit):
struct Node {
    int         data;
    struct Node *next;     // pointer to the same type — OK!
};

// But what do you set next to?
struct Node n1 = {42, NULL};  // NULL for now — no heap yet
// n1.next = ???               // We need malloc. Next lecture.
```
- **Speaker Note:** This is the cliffhanger. A `struct Node *` is 8 bytes regardless of what `struct Node` looks like — the pointer's size is fixed. But to chain nodes together, you need to allocate nodes dynamically. End with: "We have the type. We have the pointer. Next time: where does the memory come from?"

---

## Slide 16: Key Takeaways + Cliffhanger

**Takeaways:**
- A `struct` groups related data of mixed types; `typedef` gives it a clean single-word name
- Array fields are stored inline — not as pointers
- The compiler inserts padding — always use `sizeof()`, never assume
- Passing by value copies the whole struct; pass a pointer for efficiency or mutation
- Return a struct to give back multiple values cleanly
- Use `.` on a struct variable, `->` on a struct pointer (`->` = `(*p).`)
- Structs can nest; a struct can hold a *pointer* to itself, but not itself

**Next time:** We have self-referential structs with `struct Node *next` — but `next` points at... what, exactly? Stack memory runs out. We need to request memory at runtime, keep it alive as long as we want, and free it when done. Enter `malloc`, `free`, and the heap.

> *"Our struct knows the shape of the data it wants to hold. Now it needs somewhere to put it."*


---
<!--
## Calliope's Reflection

**Syllabus Alignment:** This lecture sits in Phase 2 (Weeks 6–9): Memory Management, Structs, and File I/O. Structs are the gateway concept — students must internalize value semantics and memory layout before `malloc` makes sense. The self-referential cliffhanger creates a genuine need for heap allocation rather than introducing it abstractly.

**Theory-Driven Debugging:** Parts 4 and 5 of the ICEX enforce the theorize-then-observe loop explicitly. Students predict `sizeof` before running it and predict whether `alice.name` changes before testing — the methodology is baked into the exercise, not bolted on.

**Why These Analogies:** Comparing `struct Student` array fields to Java references directly attacks the most dangerous assumption transfer students bring: that a field holding an array is a pointer to it. The stack-frame size diagram (slide 9) makes the cost of value-copying visceral rather than theoretical. The cliffhanger (`struct Node *next` pointing at nothing) creates genuine cognitive tension — students will arrive at next class *wanting* `malloc`.

-->