## Slide: Building Paths Safely with snprintf()

- **Key Point:** `snprintf()` builds a string into a fixed buffer with a size limit — it will never overflow the buffer, and it returns the number of characters that *would* have been written, so you can detect truncation.

```c
char path[1024];

/* snprintf(buffer, max_bytes, format, ...) */
snprintf(path, sizeof(path), "%s/%s", argv[1], ep->d_name);
lstat(path, &sb);

/* strcat() does the same job but has no size limit — dangerous */
strcpy(path, argv[1]);   /* no bounds check */
strcat(path, "/");       /* no bounds check */
strcat(path, ep->d_name);/* no bounds check — buffer overflow waiting to happen */
```

- `sizeof(path)` is the key argument — `snprintf` writes at most that many bytes including the null terminator, so `path` is always a valid C string
- If the result is truncated, `snprintf` returns a value `>= sizeof(path)` — you can check it:

```c
int n = snprintf(path, sizeof(path), "%s/%s", argv[1], ep->d_name);
if (n >= (int)sizeof(path)) {
    fprintf(stderr, "path truncated: %s/%s\n", argv[1], ep->d_name);
    continue;
}
```

- **Speaker Note:** `strcat()` works here because filenames are short, but it is a habit that kills you the moment a path is longer than expected. `snprintf()` is the one-call replacement for `strcpy` + `strcat` + bounds checking — worth the muscle memory now.
