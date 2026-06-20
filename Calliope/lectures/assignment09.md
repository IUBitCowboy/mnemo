# Assignment 09: HTTP Server v2 — Real Network I/O with Netcat

This assignment evolves your HTTP response generator (`http_resp`) into a genuine network server. You will wrap the v1 request-handling logic in a per-connection loop that spawns `nc` as a subprocess, connects it to your program through two pipes, and processes real HTTP requests from a browser or `curl`. The core logic you wrote in v1 — path resolution, directory listing, file serving, error responses — carries over largely unchanged.

Later assignments will replace `nc` with a proper socket listener. The architecture you build here prepares you for that transition.

---

# Background

## HTTP Exchange — Unchanged from v1

The HTTP request/response format is the same as in Assignment 08. The only difference is *where* the bytes come from and go to: in v1 they came from stdin and went to stdout; in v2 they travel over pipes connected to an `nc` subprocess that handles the actual network socket.

Review the HTTP background and response format sections of Assignment 08 if you need a refresher.

## How Netcat Bridges the Network

`nc` (netcat) listens on a TCP port. When a client connects, it forwards bytes from the network to its `stdout` and bytes from its `stdin` back to the network. Your program exploits this by:

1. Creating two pipes: one to carry data **to** `nc`'s stdin (your response), one to carry data **from** `nc`'s stdout (the client's request)
2. Forking and exec'ing `nc -l <port>` with stdin and stdout redirected to those pipe ends
3. Reading the HTTP request from the pipe, calling your v1 handler, writing the response back through the other pipe
4. Waiting for `nc` to exit (the client connection closed), then repeating

```
Browser ──TCP──► nc stdin ◄── pipe_to_nc[1]   ◄── your program (writes response)
Browser ◄─TCP── nc stdout ──► pipe_from_nc[0] ──► your program (reads request)
```

---

# What's New in v2

- **Port parameter** — `nc` needs a port to listen on; you accept it as a positional argument
- **Two-pipe subprocess model** — `pipe()`, `fork()`, `dup2()`, `execlp()`, `close()` wired together correctly
- **Per-connection loop** — `nc` exits after each connection; your program re-forks it for the next
- **Log file** — all operational logging moves from stderr to `./logs/http_v2.log`; stderr is reserved for `DEBUG:` output only
- **SIGPIPE handling** — required; the server must not crash when a client drops a connection mid-response

---

# Refactoring from v1

You are not rewriting from scratch. The changes to your v1 code are localized:

| Component | v1 | v2 |
|-----------|----|----|
| `main()` | Parse args, call handler once | Parse args, open log, loop calling handler per connection |
| `handle_request()` | Reads from `stdin`, writes to `stdout` | Reads from pipe FD, writes to pipe FD |
| Logging destination | `stderr` | `./logs/http_v2.log` (file) |
| `handle_request()` signature | `(const char *doc_root)` | `(int read_fd, int write_fd, const char *doc_root, FILE *logfp)` |

Everything inside `handle_request()` — path building, `lstat()`, file serving, directory listing, error responses — is unchanged except that `fprintf(stdout, ...)` / `printf(...)` become `write()` calls or `fdopen()`-wrapped `fprintf()` calls to `write_fd`.

---

# Functions Reference

The table below lists every system call and library function required by this assignment. The autograder does not check for specific function names — it uses functional tests — but your implementation must use these correctly to pass those tests.

| Function | Header | Purpose |
|----------|--------|---------|
| `pipe` | `<unistd.h>` | Create the two pipe pairs | 
| `fork` | `<unistd.h>` | Spawn the nc subprocess |
| `dup2` | `<unistd.h>` | Redirect nc's stdin and stdout to pipe ends |
| `execlp` | `<unistd.h>` | Replace child process image with nc |
| `close` | `<unistd.h>` | Close unused pipe ends in parent and child |
| `waitpid` | `<sys/wait.h>` | Reap the nc child; check exit status |
| `read` | `<unistd.h>` | Read HTTP request bytes from pipe |
| `write` | `<unistd.h>` | Write HTTP response bytes to pipe |
| `signal` | `<signal.h>` | Install SIGPIPE handler |
| `stat` / `lstat` | `<sys/stat.h>` | Check path existence and type |
| `opendir` | `<dirent.h>` | Open directory for listing |
| `readdir` | `<dirent.h>` | Iterate directory entries |
| `closedir` | `<dirent.h>` | Close directory stream |
| `snprintf` | `<stdio.h>` | Build paths and HTML safely |
| `strftime` | `<time.h>` | Format modification timestamps |
| `sscanf` | `<stdio.h>` | Parse method, path, version from request line |

---

# Requirements

## Command-Line Interface

```
./http_v2 <documentRoot> <port>
```

Both arguments are required. Your program must log both to the log file on startup.

```bash
# Example
./http_v2 /home/user/www 8080
```

**Positional argument order:** `documentRoot` first, `port` second. Defaults are not required; exit with a usage message if either argument is missing.

## Log File

All operational log output goes to `./logs/http_v2.log`, opened in **append mode** at startup. You may assume the `./logs/` directory exists. Log entries must include:

- Startup: configured `documentRoot` and `port`
- Per connection: parsed method, path, and HTTP version
- Per connection: full filesystem path resolved
- Per connection: response status code and reason
- Per directory response: each entry name and size

**stderr is reserved exclusively for `DEBUG:` prefixed messages.** No operational log output, no HTTP response content, and no error messages should appear on stderr. If you add temporary debug `fprintf(stderr, ...)` calls during development, prefix them with `"DEBUG: "`. Remove or gate them before submission.

## Netcat Subprocess

For each incoming connection, your program must:

1. Create two pipe pairs with `pipe()`:
   - `pipe_to_nc[2]` — parent writes the HTTP response; nc reads it as stdin
   - `pipe_from_nc[2]` — nc writes the HTTP request as stdout; parent reads it

2. `fork()`. In the **child**:
   - `dup2(pipe_to_nc[0], STDIN_FILENO)` — nc reads from the response pipe
   - `dup2(pipe_from_nc[1], STDOUT_FILENO)` — nc writes to the request pipe
   - Close all four original pipe FDs
   - `execlp("nc", "nc", "-l", port, (char *)NULL)`

3. In the **parent**:
   - Close `pipe_to_nc[0]` and `pipe_from_nc[1]` — unused ends **must** be closed
   - Read the HTTP request from `pipe_from_nc[0]`
   - Call your request handler, which writes the response to `pipe_to_nc[1]`
   - Close `pipe_to_nc[1]` — signals EOF to nc, which closes the client connection
   - Close `pipe_from_nc[0]`
   - `waitpid()` for the nc child; check and log the exit status

> **Why closing unused pipe ends matters:** If the parent holds `pipe_from_nc[1]` open, `read()` from `pipe_from_nc[0]` will never return EOF — the server hangs waiting for data that never arrives, and every subsequent connection will fail.

## Reading the HTTP Request

Read from the pipe FD in a loop, accumulating bytes into a buffer. After each `read()`, null-terminate and check for `"\r\n\r\n"` using `strstr()`. Stop when:
- The header terminator is found
- `read()` returns 0 (pipe closed — client dropped connection)
- The buffer is full

Pass the accumulated buffer to your request parser (`sscanf` for method/path/version).

## Writing the HTTP Response

Your response-writing code writes to `pipe_to_nc[1]` rather than stdout. Two options:

- Use `write(pipe_to_nc[1], buf, len)` for raw output
- Use `fdopen(pipe_to_nc[1], "w")` to get a `FILE *` and keep your v1 `fprintf` calls — remember to `fclose()` the stream before calling `waitpid()`

Either approach is acceptable. Do not mix both on the same FD.

## Per-Connection Loop

`nc -l` exits after a single connection. Your `main()` must loop: after `waitpid()` returns, re-enter the top of the loop and fork `nc` again for the next connection. The server runs indefinitely until killed.

```
while (1) {
    create pipes
    spawn nc
    read request
    handle request
    close pipe_to_nc[1]   ← EOF signal to nc
    close pipe_from_nc[0]
    waitpid               ← reap nc before next iteration
}
```

The order matters. Closing `pipe_to_nc[1]` before `waitpid()` ensures nc can finish forwarding the response before you wait for it to exit.

## SIGPIPE

Install a SIGPIPE handler **before** entering the server loop. If a client drops the connection while your program is writing the response, the write to `pipe_to_nc[1]` generates SIGPIPE. Without handling it, the server process terminates.

At minimum: `signal(SIGPIPE, SIG_IGN)` suppresses the signal so `write()` returns `-1` with `errno == EPIPE` instead of terminating the process. Check `write()` return values and log the broken pipe condition.

See Extra Credit for a more robust handler approach.

---

# Programming Constraints

All v1 constraints apply:

- No global variables except constants. All working state is locally scoped or passed as parameters
- `#define` or `const` for all constants — buffer sizes, port defaults, status strings, log format strings. No magic numbers
- `main()` follows a driver architecture — delegate to separate functions for: pipe creation, nc spawning, request reading, request handling, each response type
- `snprintf` (never `strcat` or `strcpy`) for all path and string construction into fixed-size buffers
- Build the directory listing HTML body into a buffer before emitting headers, so `Content-Length` is known first
- Short comment block above each function: description, parameters, return value
- Header comment block: your name, program description, assignment number

Additional constraints for v2:

- All unused pipe ends **must** be closed in both parent and child
- Always check the return value of `waitpid()`; log the exit status
- Always check the return value of `write()`; a negative return on the response pipe means the client disconnected
- `SIGPIPE` must be handled before the server loop begins
- All operational log output to `./logs/http_v2.log`; stderr only for `DEBUG:` prefixed messages

---

# Testing with curl

Use `curl` to test your server locally on silo. Open two terminal sessions.

```bash
# Terminal 1 — start the server
./http_v2 /path/to/testroot 8080

# Terminal 2 — basic GET request
curl -v http://localhost:8080/

# Request a specific file
curl -v http://localhost:8080/index.html

# Trigger a 404
curl -v http://localhost:8080/no_such_file.html

# Trigger a 501 (non-GET method)
curl -v -X POST http://localhost:8080/

# Multiple sequential requests — all three must succeed
for i in 1 2 3; do
    curl -s http://localhost:8080/ > /dev/null && echo "request $i ok"
done

# Check for zombie processes (should see none)
ps aux | grep -E '[Z]'

# Watch the log file in real time
tail -f ./logs/http_v2.log
```

> **Port conflicts:** If port 8080 is already in use on silo, choose another port above 1024. Pick a number unlikely to collide with classmates — your student ID's last 4 digits make a reasonable choice.

---

# Rubric

| Test | Condition | Points |
|:-----|:----------|-------:|
| test1 | Compiles without warnings (`-Wall`) | 5 |
| test2 | Returns HTTP 501 for a non-GET method via curl (`-X POST`) | 5 |
| test3 | Returns HTTP 404 when requested path does not exist | 5 |
| test4 | Accepts `documentRoot` and `port` as positional arguments; logs both to `./logs/http_v2.log` on startup | 5 |
| test5 | Logs parsed method, path, and HTTP version to log file per request | 5 |
| test6 | Logs full filesystem path resolved for response to log file | 5 |
| test7 | File response: correct `HTTP/1.1 200 OK` status line | 5 |
| test8 | File response: `Content-Length` header matches actual file size | 10 |
| test9 | File response: `Content-Type: text/html` header present | 5 |
| test10 | File response: body matches file contents | 10 |
| test11 | Server listens on port specified at command line; `curl http://localhost:<port>/` returns HTTP 200 | 5 |
| test12 | Three sequential `curl` requests all return HTTP 200 without the server hanging between them | 10 |
| test13 | No zombie `nc` processes remain after a request completes (`ps` check) | 5 |
| test14 | Each request produces a log entry in `./logs/http_v2.log` | 5 |
| Handgrading | Code quality: comment block above each function, `#define` constants, no magic numbers, meaningful variable names | 5 |
| Handgrading | Logging discipline: all operational output in log file; stderr contains only `DEBUG:` prefixed messages; no HTTP content on stderr | 5 |
| Handgrading | `README.md`: pseudocode for the server loop and pipe setup; test plan with one line per rubric test describing how you verified it | 5 |
| **Total** | | **100** |
| ECtest1 | Named parameters: `./http_v2 -d <documentRoot> -p <port>` accepted and function correctly | 5 |
| ECtest2 | `./logs/` directory created at startup if it does not already exist | 5 |
| ECtest3 | SIGPIPE handled with a log entry and `volatile sig_atomic_t` flag rather than `SIG_IGN`; server continues normally after broken pipe | 5 |

---

# Implementation Order

Work through these in sequence — each step leaves you with something testable before you tackle the next.

1. **CLI parsing + log file open + startup log** → test4; confirms both args parsed and log file created
2. **Port your v1 `handle_request` logic** — change its signature to accept `read_fd`, `write_fd`, `logfp`; redirect all output to `write_fd`. Test it with a single hardcoded request string to confirm v1 behavior still works before adding the subprocess layer
3. **Single-connection pipe + nc spawn** — `create_pipes()`, `spawn_nc()`, `read_request()`, one call to `handle_request()`, then exit → test11; first real `curl` should return a response
4. **Wrap in the per-connection loop** → test12; three sequential `curl` requests must all succeed
5. **`waitpid()` + zombie check** → test13
6. **Confirm log entries per request** → test14
7. **Logging discipline** — audit every `fprintf`/`printf`; ensure nothing operational hits stderr

## Test Resources

Reuse or adapt your v1 `testroot/` directory:
- A small `index.html` of known size
- A subdirectory with a few files
- A non-existent path name for 404 testing

Create a `requests/` directory for curl one-liners (or adapt to curl commands directly). See the curl examples above.

## Commit Milestones

Commit after each implementation step above. The git history makes it easy to bisect if a later change breaks an earlier test.

---

# Submission

Submit your source file named **`http_v2.c`** to the Autograder:

> **Autograder URL:** `[TBD]`

Your submission directory must be `exercises/A09/` and must contain:

- `http_v2.c` — your implementation
- `README.md` — pseudocode for the server loop and pipe setup; one-line test plan per rubric test
- `testroot/` — your local test document root

Commit everything and post your commit URL to the Canvas assignment:

> **Canvas URL:** `[TBD]`
