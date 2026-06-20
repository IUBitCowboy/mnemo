# Lecture 11: The Linux Filesystem & Directory I/O in C

---

## Slide 1: Title Slide

- **Topic:** The Linux Filesystem, `stat()`, and Directory I/O
- **Course:** C291 — System Programming with C and Linux
- **Key Functions:** `stat()` · `lstat()` · `opendir()` · `readdir()` · `closedir()`

---

## Slide 2: Learning Objectives

By the end of this lecture, you will be able to:

- Describe the Linux filesystem layout and identify the seven file types
- Explain file permissions and interpret `ls -l` output in octal terms
- Distinguish hard links from symbolic links using the inode concept
- Call `stat()` and `lstat()`, and interpret the fields in `struct stat`
- Use `S_IS*()` macros to test file type from `st_mode`
- Traverse a directory with `opendir()` / `readdir()` / `closedir()`
- Apply the `errno` / `perror()` pattern to all filesystem calls

---

## Slide 3: The Linux Filesystem Layout

- **Key Point:** In Linux, everything is a file — devices, pipes, and sockets all use the same `open/read/write/close` API.

```
/
├── bin    essential user binaries
├── dev    device files (block, char, etc.)
├── etc    system configuration
├── home   user home directories
├── proc   virtual FS — kernel & process info (no disk I/O)
├── tmp    temporary files (cleared on reboot)
├── usr    installed programs and libraries
└── var    variable data: logs, spool, mail
```

- **Speaker Note:** Emphasize `/proc` — students will use it later when inspecting process state. Also contrast absolute (`/home/user/file`) vs. relative (`../file`) paths.

---

## Slide 4: File Types in Linux

- **Key Point:** The first character of `ls -l` output identifies the file type. `stat()` gives you the same info programmatically via `st_mode`.

| Char | Type              | Example `ls -l` output                        |
|------|-------------------|------------------------------------------------|
| `-`  | Regular file      | `-rw-r--r-- 1 user group 4096 ...`            |
| `d`  | Directory         | `drwxr-xr-x 3 user group  256 ...`            |
| `l`  | Symbolic link     | `lrwxrwxrwx 1 user group   11 ... -> target`  |
| `p`  | Named pipe (FIFO) | `prw-r--r-- 1 user group    0 ...`            |
| `s`  | Socket            | `srwxrwxrwx 1 root root      0 ...`           |
| `b`  | Block device      | `brw-rw---- 1 root disk   8,0 ...`            |
| `c`  | Character device  | `crw-rw-rw- 1 root tty    5,0 ...`            |

- **Speaker Note:** You won't write code for block/char devices or sockets in this course, but students will encounter them with `ls -l /dev`. Focus on `-`, `d`, `l`, and `p` as the four they'll interact with.

---

## Slide 5: File Permissions

- **Key Point:** Every file has three permission groups — owner, group, other — each with read (`r=4`), write (`w=2`), execute (`x=1`) bits.

```
  - r w x   r - x   r - -
  |       | |     | |     |
  owner    group   other
```

- Permission bits add up in octal: `rwx = 7`, `r-x = 5`, `r-- = 4`

```c
chmod 755 script.sh    /* rwxr-xr-x */
chmod 644 data.txt     /* rw-r--r-- */
chmod 600 secret.key   /* rw------- */
```

- In C, permission bits are constants: `S_IRUSR`, `S_IWUSR`, `S_IXUSR` (owner); `S_IRGRP`, `S_IWGRP`, `S_IXGRP` (group); `S_IROTH`, `S_IWOTH`, `S_IXOTH` (other)

- **Speaker Note:** Walk through `755` — most common for executables — and `644` — most common for data files. The `S_I*` constants show up again when reading `sb.st_mode`.

---

## Slide 6: Inodes — Just Enough to Matter

- **Key Point:** An **inode** is the filesystem's metadata record for a file. A directory entry is nothing more than a `name → inode number` mapping.

```
Directory entries:         Inode #4821
┌──────────────────┐      ┌─────────────────────┐
│ docs/report.txt  │─────►│ st_mode  (perms)    │
└──────────────────┘      │ st_uid   (owner)     │
                          │ st_size  (bytes)     │
┌──────────────────┐      │ st_nlink = 2  ◄──── │── two names point here
│ bak/report.txt   │─────►│ data block ptr      │
└──────────────────┘      └─────────────────────┘
```

- `st_nlink > 1` means multiple directory entries share this inode — that is a **hard link**
- `rm` decrements `st_nlink`; data is freed only when `st_nlink` reaches 0 **and** no process has the file open

- **Speaker Note:** This one diagram carries Slides 7 and 8. Spend 2 minutes here — students don't need inode internals, just the "name-to-inode" mental model.

---

## Slide 7: Hard Links vs. Symbolic Links

- **Key Point:** Hard links share an inode; symbolic links are a separate inode containing a path string.

| Property               | Hard Link                            | Symbolic (Soft) Link                |
|------------------------|--------------------------------------|-------------------------------------|
| Command                | `ln target linkname`                 | `ln -s target linkname`             |
| Inode                  | Same inode as target                 | New inode; content = path string    |
| `st_nlink` effect      | Increments by 1                      | No change to target's `st_nlink`    |
| Cross-filesystem?      | No                                   | Yes                                 |
| Dangling link possible?| No — inode lives while `nlink > 0`  | Yes — target can be deleted         |
| `stat()` behavior      | Sees the shared inode                | Follows the link to the target      |
| `lstat()` behavior     | Same as `stat()`                     | Sees the link's own inode           |

- **Speaker Note:** Demonstrate with `ln` and `ls -li` (the `-i` flag shows inode numbers) so students can see identical inode numbers for hard links.

---

## Slide 8: Named Pipes (FIFOs) — The Bridge

- **Key Point:** A named pipe is a special file that acts as a one-directional in-kernel channel between two processes. `open()` blocks until both ends connect.

```bash
# Create and use a FIFO from the shell
mkfifo mypipe
cat /etc/passwd > mypipe &   # writer blocks until reader opens
wc -l < mypipe               # reader unblocks the writer
```

```c
/* Write side in C */
int fd = open("mypipe", O_WRONLY);   /* blocks until reader opens */
write(fd, buf, len);
close(fd);
```

- The filesystem entry (`p` type in `ls -l`) is just the rendezvous point — the data never touches disk
- **Coming next lecture:** `fork()` + `pipe()` gives the same channel entirely in memory, with no filesystem file

- **Speaker Note:** This is the conceptual bridge. Stress: same blocking semantics, same one-direction data flow — just no filename. Next class we eliminate the file entirely.

---

## Slide 9: Error Handling — errno & perror()

- **Key Point:** Every filesystem call returns `-1` (or `NULL`) on failure and sets the global `errno`. Call `perror()` immediately after the failure — `errno` is overwritten by the next call.

```c
#include <stdio.h>
#include <stdlib.h>

/* Pattern: check the return value, call perror() with context */

FILE *fp = fopen(argv[1], "r");
if (fp == NULL) {
    perror(argv[1]);          /* prints: filename: No such file or directory */
    exit(EXIT_FAILURE);
}

struct stat sb;
if (stat(path, &sb) == -1) {
    perror(path);             /* prints: path: Permission denied */
    exit(EXIT_FAILURE);
}
```

- Pass the filename or function name as the `perror()` argument — it becomes the prefix in the error message
- **Speaker Note:** Show a live demo — stat a non-existent file, then a directory you don't have permission to enter. Students will use this pattern in the ICEX.

---

## Slide 10: stat() — Querying File Metadata

- **Key Point:** `stat()` fills a `struct stat` with everything the kernel knows about a file. It **follows** symbolic links.

```c
#include <sys/stat.h>

int stat(const char *pathname, struct stat *statbuf);
/* Returns: 0 on success, -1 on error (sets errno) */

int lstat(const char *pathname, struct stat *statbuf);
/* Same, but does NOT follow symlinks — stats the link itself */
```

- Use `lstat()` when you need to know: *"is this entry itself a symlink?"*
- `stat()` on a symlink gives you the target's metadata; `lstat()` gives you the link's metadata (`S_ISLNK()` returns true)

```c
/* Choosing between them */
stat("symlink",  &sb);   /* sb describes the TARGET */
lstat("symlink", &sb);   /* sb describes the LINK   */
```

- **Speaker Note:** The distinction matters in directory traversal — `readdir()` + `lstat()` is the correct pattern when you want to detect symlinks rather than silently following them.

---

## Slide 11: struct stat — Key Fields

- **Key Point:** The two fields you will use in almost every program are `st_mode` (type + permissions) and `st_size`.

```c
struct stat {
    mode_t  st_mode;    /* file type bits + permission bits  */
    ino_t   st_ino;     /* inode number                      */
    nlink_t st_nlink;   /* number of hard links              */
    uid_t   st_uid;     /* owner user ID                     */
    gid_t   st_gid;     /* owner group ID                    */
    off_t   st_size;    /* total size in bytes               */
    time_t  st_atime;   /* last access time                  */
    time_t  st_mtime;   /* last modification time            */
    time_t  st_ctime;   /* last status change time           */
};
```

- `st_size` is `0` for directories on most filesystems — use `st_blocks` if you need disk usage
- `st_ctime` is *not* creation time — it is the last time permissions, owner, or link count changed

- **Speaker Note:** Have students predict what `st_nlink` is for a fresh, empty directory (answer: 2 — the entry in its parent and its own `.` entry).

---

## Slide 12: S_IS*() Macros — Testing st_mode

- **Key Point:** Never inspect `st_mode` bits directly — use the POSIX macros. Pass `sb.st_mode` as the argument.

```c
/* File type macros */
S_ISREG(m)    /* regular file   */
S_ISDIR(m)    /* directory      */
S_ISLNK(m)    /* symbolic link  */
S_ISFIFO(m)   /* named pipe     */
S_ISSOCK(m)   /* socket         */

/* Usage */
struct stat sb;
stat(path, &sb);

if      (S_ISREG(sb.st_mode))  printf("regular file\n");
else if (S_ISDIR(sb.st_mode))  printf("directory\n");
else if (S_ISLNK(sb.st_mode))  printf("symlink\n");

/* Testing permission bits */
if (sb.st_mode & S_IRUSR)  printf("owner can read\n");
if (sb.st_mode & S_IXUSR)  printf("owner can execute\n");
```

- **Speaker Note:** Point out that `S_ISLNK()` only returns true when used with `lstat()` — `stat()` resolves the link first, so `st_mode` reflects the target.

---

## Slide 13: stat() — Complete Example

- **Key Point:** A minimal but complete `stat()` program illustrating argument checking, error handling, type detection, and field access.

```c
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s path\n", argv[0]);
        return 1;
    }

    struct stat sb;
    if (stat(argv[1], &sb) == -1) {
        perror(argv[1]);
        return 1;
    }

    printf("inode:  %llu\n",  (unsigned long long)sb.st_ino);
    printf("size:   %lld\n",  (long long)sb.st_size);
    printf("links:  %u\n",    (unsigned)sb.st_nlink);

    if      (S_ISREG(sb.st_mode)) printf("type: regular file\n");
    else if (S_ISDIR(sb.st_mode)) printf("type: directory\n");
    else if (S_ISLNK(sb.st_mode)) printf("type: symlink\n");

    return 0;
}
```

- **Speaker Note:** The casts on `st_ino`, `st_size`, and `st_nlink` avoid format-string warnings across platforms — the underlying types vary by architecture.

---

## Slide 14: Directory I/O — The Trio

- **Key Point:** Directories are opened like files but read with a dedicated API. Think of `DIR *` exactly like `FILE *` — a stream handle.

```c
#include <dirent.h>

DIR *opendir(const char *name);
/* Returns a DIR* stream, or NULL on error */

struct dirent *readdir(DIR *dirp);
/* Returns a pointer to the next entry, or NULL at end-of-directory */
/* Return value is valid until the next readdir() call on the same DIR* */

int closedir(DIR *dirp);
/* Returns 0 on success, -1 on error — always close */
```

- Typical loop pattern:

```c
DIR *dp = opendir(argv[1]);
if (dp == NULL) { perror(argv[1]); return 1; }

struct dirent *ep;
while ((ep = readdir(dp)) != NULL) {
    /* process ep */
}
closedir(dp);
```

- **Speaker Note:** Stress the `NULL` check on `opendir` — students will forget it. Also note that `readdir()` is not thread-safe; for multithreaded code use `readdir_r()`.

---

## Slide 15: struct dirent — Key Fields

- **Key Point:** You will use `d_name` in almost every program. Treat `d_type` as a fast hint — verify with `stat()` when portability matters.

```c
struct dirent {
    ino_t   d_ino;     /* inode number of this entry  */
    char    d_name[];  /* null-terminated filename    */  /* ← always use this */
    uint8_t d_type;    /* file type hint              */  /* ← may be DT_UNKNOWN */
};
```

- `d_type` constants: `DT_REG`, `DT_DIR`, `DT_LNK`, `DT_FIFO`, `DT_SOCK`, `DT_UNKNOWN`
- **Portability caveat:** Some filesystems (older ext2, network filesystems) return `DT_UNKNOWN` — always fall back to `lstat()` when `d_type == DT_UNKNOWN`

```c
if (ep->d_type == DT_UNKNOWN) {
    lstat(fullpath, &sb);
    /* use S_IS*() on sb.st_mode */
}
```

- **Speaker Note:** On the IU Linux servers (ext4), `d_type` is reliable. But writing portable code means handling `DT_UNKNOWN` — good habit to establish now.

---

## Slide 16: ⚠ The . and .. Gotcha

- **Key Point:** `readdir()` always returns `.` (current directory) and `..` (parent directory). Failing to skip them causes infinite recursion or double-counting.

```c
/* ❌ Bug: recurses into . and .. forever */
while ((ep = readdir(dp)) != NULL) {
    process(ep->d_name);   /* stat(), recurse, etc. */
}

/* ✅ Fix: skip . and .. explicitly */
while ((ep = readdir(dp)) != NULL) {
    if (strcmp(ep->d_name, ".")  == 0) continue;
    if (strcmp(ep->d_name, "..") == 0) continue;
    process(ep->d_name);
}

/* ✅ Alternative: skip all dotfiles at once */
while ((ep = readdir(dp)) != NULL) {
    if (ep->d_name[0] == '.') continue;
    process(ep->d_name);
}
```

- Use the `d_name[0] == '.'` shortcut only if you also want to skip hidden files (`.bashrc`, `.git`)

- **Speaker Note:** This is the number-one first-attempt bug on the ICEX. Call it out explicitly so they don't waste 10 minutes debugging an infinite loop.

---

## Slide 17: Complete readdir() Example

- **Key Point:** Combining `opendir()` / `readdir()` / `lstat()` into a minimal directory listing program.

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>

int main(int argc, char *argv[]) {
    if (argc != 2) { fprintf(stderr, "usage: %s dir\n", argv[0]); return 1; }

    DIR *dp = opendir(argv[1]);
    if (dp == NULL) { perror(argv[1]); return 1; }

    struct dirent *ep;
    struct stat    sb;
    char           path[1024];

    while ((ep = readdir(dp)) != NULL) {
        if (ep->d_name[0] == '.') continue;

        snprintf(path, sizeof(path), "%s/%s", argv[1], ep->d_name);
        if (lstat(path, &sb) == -1) { perror(path); continue; }

        char type = S_ISDIR(sb.st_mode) ? 'd' : '-';
        printf("%c  %8lld  %s\n", type, (long long)sb.st_size, ep->d_name);
    }

    closedir(dp);
    return 0;
}
```

- **Speaker Note:** Note that we build the full path with `snprintf` before calling `lstat()` — `readdir()` only gives us the filename, not the path. This is a common mistake on the ICEX.

---

## Slide 18: Key Takeaways

- **Everything is a file** — the same API spans regular files, directories, pipes, and devices
- **Inodes hold metadata** — directory entries are just `name → inode` mappings; hard links share an inode, symlinks are a new inode containing a path
- **`stat()` follows symlinks; `lstat()` does not** — use `lstat()` in directory traversal
- **`st_mode` encodes both type and permissions** — use `S_IS*()` macros for type, `S_I*` constants for permission bits
- **The `opendir/readdir/closedir` loop** — always skip `.` and `..`; always close the `DIR*`
- **Check every return value** — call `perror()` with context immediately after any failure

---

## Slide 19: The Cliffhanger

**Named pipes gave us two key insights:**

1. Two independent processes can share a data channel through a filesystem rendezvous point
2. The channel blocks — the writer waits for a reader, the reader waits for data

**Next lecture:** We eliminate the filesystem entirely.

```c
int fd[2];
pipe(fd);      /* fd[0] = read end, fd[1] = write end */
fork();        /* child inherits both ends */
/* parent writes to fd[1], child reads from fd[0] */
/* exec() lets us attach fd[0] to stdin of a new program */
```

> *The pipe has no name, no file, no disk — just two file descriptors and the kernel buffer between them.*

- **Speaker Note:** Leave this on screen while students start the ICEX. The `pipe()` signature is intentionally provocative — they should be curious about `fork()` going in.
