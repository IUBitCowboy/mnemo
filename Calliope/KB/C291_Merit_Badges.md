# The C291 Hall of Perils: Merit Badge List

To earn a badge, students must document the bug in their own code using the [THEORIZE -> EXPERIMENT -> MODIFY -> TEST] loop.

The Ghost Pointer: Dereferencing an uninitialized pointer.

The Off-by-One Odyssey: Array index out of bounds (The < vs <= struggle).

The Infinite Echo: A loop or recursion that never terminates.

The Lost Memory (The Sieve): A memory leak detected by Valgrind.

The Locked Gate (Segfault): Accessing memory not owned by the process.

The Double Sacrifice: Attempting to free() the same memory twice.

The Dangling Rope: Accessing memory after it has been free()'d.

The Overflowing Vessel: Buffer overflow in a fixed-size array.

The Format Fumble: Mismatched types in printf or scanf.

The Shadow Variable: Local scope accidentally hiding a global or outer-scope variable.

The Precarious Cast: Data loss or corruption due to improper type casting.

The Unchecked Return: Failure to check if malloc, open, or fork failed.

The Dangling Else: Logic errors stemming from improper bracing in conditionals.

The Priority Conflict: Errors caused by misunderstanding operator precedence.

The Floating Anchor: Pointer arithmetic that drifts outside the intended block.

The String Straggler: Forgetting the \0 null-terminator.

The Header Haunt: Circular dependencies or missing include guards.

The Zombie Parade: Failure to wait() for child processes.

The Race Condition: Two threads/processes fighting for the same memory.

The Signal Silence: A program that fails to catch or improperly handles a SIGINT.

SPECIAL BADGE: "The Uncharted Error"
Awarded for a bug not on this list that requires a unique theory and experimental proof.