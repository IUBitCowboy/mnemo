# Lecture: httpd v2 — Two Pipes, Netcat, and the Deadlock You Need to Understand

## Slide 1: Title Slide
- **Topic:** Netcat IPC Architecture — Wiring the Real Network into httpd
- **Course:** C291 — System Programming with C and Linux
- **Timing:** 40-min lecture + 30-min ICEX + 5-min buffer = 75 min

---

## Slide 2: Learning Objectives
By the end of this lecture, you will be able to:

- Describe what netcat does at the stdin/stdout level and why it is a useful network shim
- Set up two anonymous pipes and connect them to a child process's stdin and stdout via `dup2()`
- Reason through the circular-wait deadlock scenario for bidirectional pipe communication
- Explain why sequential read-then-write is safe for HTTP GET requests and when it would not be
- Implement a byte-accumulating read loop that terminates on the HTTP header delimiter `\r\n\r\n`
- Structure a per-connection server loop that re-forks netcat for each incoming request

---

## Slide 3: Where We Are — httpd v1

- **Key Point:** The existing httpd v1 is already a correct HTTP server — it just uses stdin and stdout as its network interface. The OS, `nc`, and pipes will supply the real network connection. Almost no parsing logic needs to change.
- **Diagram:**
```
httpd v1 (current):

Browser ──[TCP/IP]──► ??? (no network layer)

stdin  ──► httpd ──► stdout
           │
           └──► stderr (log)

Testing was done by piping a request file:
  cat request.txt | ./httpd > response.txt
```
- **Speaker Note:** Ask students to pull up their v1 source mentally. The `read()`/`fgets()` from stdin, the `write()`/`printf()` to stdout — none of that changes. What we are adding is a network front-end. Netcat is that front-end, and our job today is to learn how to control it from our process using pipes.

---

## Slide 4: What Netcat Does — and Why It's the Right Tool

- **Key Point:** `nc -l PORT` listens on a TCP port. When a client connects, it relays: client → nc's stdout, nc's stdin → client. It is a bidirectional byte relay between the network and its own stdin/stdout. That makes it a perfect drop-in network layer for a server that already speaks HTTP on stdin/stdout.
- **Diagram:**
```
nc -l 8080:

Browser ──[TCP]──► nc ──► nc's stdout  (HTTP request bytes flow out here)
Browser ◄──[TCP]── nc ◄── nc's stdin   (HTTP response bytes flow in here)

nc exits when the browser closes the connection.
```
- **Speaker Note:** nc is doing the hard part — TCP handshake, socket management, buffering. We don't need to know any of that. We just need to talk to nc's stdin and stdout, which we already know how to do. The question is: how do we control nc's stdin and stdout from inside our own process? Answer: pipes and `dup2()`.

---

## Slide 5: The Two-Pipe Architecture

- **Key Point:** Two pipes are needed — one for each direction of communication. A pipe is unidirectional; you need one pipe for parent→nc and one for nc→parent.
- **Diagram:**
```
pipe_to_nc[2]:    parent writes to [1], nc reads from [0]  (→ nc's stdin)
pipe_from_nc[2]:  nc writes to [1],    parent reads from [0] (← nc's stdout)

                     ┌─────────────────────────────────┐
                     │           Parent Process         │
                     │                                  │
                     │  write(pipe_to_nc[1], ...)       │
                     │  read(pipe_from_nc[0], ...)      │
                     └──────────┬──────────▲────────────┘
                                │          │
                    pipe_to_nc  │          │  pipe_from_nc
                    [1]→[0]     │          │  [1]→[0]
                                ▼          │
                     ┌──────────────────────────────────┐
                     │         Child: nc -l 8080        │
                     │                                  │
                     │  STDIN  = pipe_to_nc[0]          │
                     │  STDOUT = pipe_from_nc[1]        │
                     └──────────────────────────────────┘
                                  │        ▲
                              TCP │        │ TCP
                                  ▼        │
                              Browser (HTTP client)
```
- **Speaker Note:** Draw this on the board. Students need to hold four file descriptors in their heads simultaneously. Key insight: after fork(), both parent and child have copies of all four FDs. We must close the unused ends — in the child, close `pipe_to_nc[1]` and `pipe_from_nc[0]`; in the parent, close `pipe_to_nc[0]` and `pipe_from_nc[1]`. Failing to close unused ends is the most common pipe bug.

---

## Slide 6: Setting Up the Pipes — Code

- **Key Point:** Create both pipes before forking. After fork, each process closes the ends it does not use. In the child, `dup2()` wires the pipe ends to stdin and stdout before exec.
- **Code Example:**
```c
int pipe_to_nc[2];    /* parent writes [1], child reads [0] */
int pipe_from_nc[2];  /* child writes [1], parent reads [0] */

if (pipe(pipe_to_nc) < 0 || pipe(pipe_from_nc) < 0) {
    perror("pipe");
    exit(EXIT_FAILURE);
}

pid_t pid = fork();
if (pid < 0) { perror("fork"); exit(EXIT_FAILURE); }

if (pid == 0) {
    /* ---- Child: become nc ---- */
    dup2(pipe_to_nc[0],   STDIN_FILENO);   /* nc reads our pipe */
    dup2(pipe_from_nc[1], STDOUT_FILENO);  /* nc writes to our pipe */
    /* close all four originals — dup2 made copies */
    close(pipe_to_nc[0]);  close(pipe_to_nc[1]);
    close(pipe_from_nc[0]); close(pipe_from_nc[1]);
    execlp("nc", "nc", "-l", "8080", (char *)NULL);
    perror("execlp nc");   /* only reached on failure */
    exit(EXIT_FAILURE);
}

/* ---- Parent: close the child's ends ---- */
close(pipe_to_nc[0]);    /* parent does not read from this pipe */
close(pipe_from_nc[1]);  /* parent does not write to this pipe */
```
- **Speaker Note:** Walk the `dup2` calls carefully. `dup2(pipe_to_nc[0], STDIN_FILENO)` makes fd 0 (stdin) point at the read end of pipe_to_nc — so when nc does `read(0, ...)` it reads from our pipe. Then close the originals because nc's code never refers to the pipe FD numbers — only to 0 and 1. Closing unused pipe ends in the parent is critical: if the parent keeps `pipe_from_nc[1]` open, it holds the write end of that pipe, so `read(pipe_from_nc[0], ...)` in the parent will never see EOF even after nc exits.

---

## Slide 7: The Deadlock — Formal Analysis

- **Key Point:** A deadlock requires a circular wait: each party is blocked waiting for the other. With two pipes and two processes, the scenario is possible — but you must reason about whether it can actually occur.
- **Diagram:**
```
Deadlock requires ALL of these simultaneously:

1. Parent blocked: read(pipe_from_nc[0])  — waiting for nc to write
       AND
2. nc blocked:     write(pipe_from_nc[1]) — pipe buffer full
       AND
3. nc blocked:     read(pipe_to_nc[0])    — waiting for parent to write response
       AND
4. Parent blocked: waiting to write response — but hasn't finished reading request

For (2): nc can only be blocked writing if pipe_from_nc is FULL.
Linux pipe buffer = 65,536 bytes.
A typical HTTP GET request = < 2,000 bytes.

Therefore (2) cannot occur for normal GET requests.
The deadlock cannot happen in our use case.
```
- **Speaker Note:** Make students work through this. "What would have to be true for us to deadlock?" They should arrive at: the request would have to be larger than 64KB — which doesn't happen for GET requests with no body. The same analysis would fail for large POST bodies or chunked uploads. Understanding why it's safe is more valuable than just being told it's safe. Ask: "What if we were building an image upload endpoint?" Then we'd need `select()` — point to it as the robust solution without implementing it today.

---

## Slide 8: Why HTTP GET Is Safe — The Sequential Flow

- **Key Point:** For HTTP GET requests, the communication is inherently sequential: the client sends the complete request, then waits for the response. nc can write the entire request to the pipe before it needs to read from its stdin. No circular dependency exists.
- **Diagram:**
```
Timeline:

1. Browser sends complete GET request → nc receives it all
2. nc writes request to pipe_from_nc  (fits in 64KB buffer easily)
3. nc now blocks on read(stdin)       waiting for response
4. Parent reads full request from pipe_from_nc  ← no blocking here
5. Parent processes request, writes response to pipe_to_nc
6. nc reads response from pipe_to_nc, forwards to browser
7. Parent closes pipe_to_nc[1]        → nc sees EOF → closes connection
8. nc exits                           → parent waitpid() returns
9. Parent re-forks nc for next request

Sequential. No overlap. No circular wait.
```
- **Speaker Note:** This timeline is the key deliverable of the deadlock analysis. Post it — students should be able to reproduce it. Emphasize step 7: closing `pipe_to_nc[1]` after writing the response is not optional. nc will not forward the response to the browser and close the connection until it sees EOF on its stdin. If the parent never closes that FD, nc waits forever, the browser waits forever, and the student's server appears to hang. This is the most common bug in the assignment.

---

## Slide 9: Reading Until `\r\n\r\n` — The Real Implementation Problem

- **Key Point:** You cannot read until EOF — nc won't close its write end until the browser closes the connection, which won't happen until nc closes its read end, which won't happen until you write the response. You must detect the HTTP header delimiter: `\r\n\r\n` (blank line after headers).
- **Code Example:**
```c
#define HDR_END     "\r\n\r\n"
#define BUF_SIZE    4096

ssize_t read_http_request(int fd, char *buf, size_t bufsz) {
    size_t  total = 0;
    ssize_t n;

    memset(buf, 0, bufsz);

    while (total < bufsz - 1) {
        n = read(fd, buf + total, bufsz - total - 1);
        if (n < 0) { perror("read"); return -1; }
        if (n == 0) break;           /* nc closed the pipe */
        total += (size_t)n;
        buf[total] = '\0';
        if (strstr(buf, HDR_END) != NULL) break;  /* found end of headers */
    }
    return (ssize_t)total;
}
```
- **Speaker Note:** Walk the loop. `read()` may return any number of bytes — network data does not arrive all at once. We accumulate into `buf`, null-terminate after each read, then use `strstr()` to check for the double CRLF. When we find it, we stop — we have the complete headers and nothing more. The `bufsz - total - 1` guard prevents buffer overflow. Ask: "What's in the buffer after the loop?" Answer: the full HTTP request line and all headers, ending with `\r\n\r\n`. The `\0` at `buf[total]` makes it a valid C string for `strstr` and for the parser that calls this function.

---

## Slide 10: The Per-Connection Loop — nc Exits After Each Request

- **Key Point:** `nc -l` exits after serving exactly one connection. The server must loop: fork nc, handle one request, wait for nc to exit, repeat.
- **Code Example:**
```c
void server_loop(const char *port) {
    char request_buf[BUF_SIZE];

    while (1) {
        int to_nc[2], from_nc[2];
        if (pipe(to_nc) < 0 || pipe(from_nc) < 0) {
            perror("pipe"); exit(EXIT_FAILURE);
        }

        pid_t pid = fork();
        if (pid == 0) {
            /* child: exec nc */
            dup2(to_nc[0],   STDIN_FILENO);
            dup2(from_nc[1], STDOUT_FILENO);
            close(to_nc[0]);  close(to_nc[1]);
            close(from_nc[0]); close(from_nc[1]);
            execlp("nc", "nc", "-l", port, (char *)NULL);
            perror("execlp"); exit(EXIT_FAILURE);
        }

        /* parent: close unused ends */
        close(to_nc[0]);
        close(from_nc[1]);

        /* read request, send response */
        ssize_t n = read_http_request(from_nc[0], request_buf, BUF_SIZE);
        if (n > 0) {
            handle_request(to_nc[1], request_buf);  /* your v1 logic */
        }

        /* signal EOF to nc → nc closes connection */
        close(to_nc[1]);
        close(from_nc[0]);

        /* wait for nc to exit before re-listening */
        waitpid(pid, NULL, 0);

        fprintf(logfp, "connection handled, waiting for next\n");
    }
}
```
- **Speaker Note:** Emphasize the order: close `to_nc[1]` BEFORE `waitpid`. nc will not exit until it sees EOF on its stdin and has flushed its output to the browser. If you `waitpid` before closing, you deadlock — nc is waiting for EOF while the parent is waiting for nc to exit. The pattern is always: signal EOF by closing the write end, then wait. Also point out: each iteration of the loop creates new pipes — do not try to reuse the old FDs.

---

## Slide 11: Logging — From stderr to a File

- **Key Point:** httpd v2 adds a log directory specified on the command line. Replace `fprintf(stderr, ...)` calls with `fprintf(logfp, ...)` where `logfp` is a `FILE *` opened at startup. The format stays the same; only the destination changes.
- **Code Example:**
```c
#include <sys/stat.h>

FILE *open_log(const char *log_dir) {
    /* Create log directory if it doesn't exist */
    mkdir(log_dir, 0755);   /* ignore EEXIST */

    char path[MAX_PATH_LEN];
    snprintf(path, sizeof(path), "%s/httpd.log", log_dir);

    FILE *fp = fopen(path, "a");    /* append mode */
    if (fp == NULL) { perror("fopen log"); exit(EXIT_FAILURE); }
    fprintf(fp, "=== httpd v2 started, port %s ===\n", HTTP_PORT_STR);
    return fp;
}

/* Usage in main */
int main(int argc, char *argv[]) {
    const char *log_dir = (argc > 1) ? argv[1] : LOG_DIR;
    FILE *logfp = open_log(log_dir);
    /* pass logfp through to server_loop and handle_request */
    server_loop(logfp);
    fclose(logfp);
    return 0;
}
```
- **Speaker Note:** `mkdir` with `0755` — the octal permission mode. Connect to the bitwise lecture: `0755` is `rwxr-xr-x` packed into 9 bits. `fopen` with `"a"` (append) rather than `"w"` (write) means the log survives server restarts. The `logfp` needs to be passed through to every function that logs — this is a good opportunity to discuss global variables vs. parameter threading for context objects. For this project, threading it as a parameter is the right call.

---

## Slide 12: SIGPIPE — The Problem You Will Hit This Week

- **Key Point:** If the browser disconnects while the parent is writing the response to `pipe_to_nc[1]`, nc has already exited and the write generates `SIGPIPE`. The default action is to terminate your server. One line prevents it.
- **Code Example:**
```c
#include <signal.h>

/* At the top of main(), before anything else: */
signal(SIGPIPE, SIG_IGN);   /* ignore SIGPIPE — write() returns EPIPE instead */

/* Then check write() return values */
ssize_t written = write(to_nc[1], response, resp_len);
if (written < 0) {
    if (errno == EPIPE) {
        fprintf(logfp, "client disconnected before response sent\n");
    } else {
        perror("write response");
    }
}
```
- **Speaker Note:** This is a preview of next lecture's signal topic. `SIG_IGN` tells the kernel "do not terminate the process on this signal — just return an error from the syscall." Without it, a browser that hits reload or navigates away mid-response silently kills your server. With it, `write()` returns -1 with `errno == EPIPE`, which you can log and handle gracefully. Students will hit this in testing — save them the debugging time by putting this slide before the ICEX.

---

## Slide 13: Demo — The Full System Running

**[Switch to terminal]**

Live demo sequence:
1. Start httpd v2 in one terminal: `./httpd logs/ &`
2. In a second terminal: `curl -v http://localhost:8080/index.html`
3. Show the log file: `cat logs/httpd.log`
4. Hit the SIGPIPE case: start a request, kill it mid-flight, show the log entry
5. Show `nc` version check: `nc --version` (demonstrates GNU vs OpenBSD syntax difference)

**Speaker Note:** Keep this under 5 minutes — the ICEX is where students learn by doing. The demo proves the architecture works end-to-end and gives students a reference target. The key moment to show: the server stays up after a SIGPIPE event. That's the proof the `SIG_IGN` line works.

---

## Slide 14: Key Takeaways + What's Next

**Takeaways:**
- Two pipes, one per direction — `pipe_to_nc` and `pipe_from_nc`; after `fork`, close all ends you don't use
- Deadlock requires the request to overflow the pipe buffer (64KB) — HTTP GET requests are safe; POST with large bodies are not
- Never read until EOF — detect `\r\n\r\n` with `strstr()` to know when headers are complete
- Close `pipe_to_nc[1]` before `waitpid()` — nc won't exit until it sees EOF on its stdin
- `signal(SIGPIPE, SIG_IGN)` in `main()` — one line that prevents a class of silent server crashes
- `nc -l PORT` exits after each connection — the server loop re-forks for every request

**Next:** We need to handle SIGPIPE properly and manage child processes cleanly. Next lecture: function pointers — which are how you register signal handlers with the OS, and how `qsort()` lets you sort any data structure without rewriting the sort algorithm.

> *"The network is just a file descriptor. Pipes are just file descriptors. Everything is just file descriptors. Once you see it that way, none of this is complicated — it's just plumbing."*

---

> **In-class exercise:** See `icex18_httpd_v2.md`

**Duration:** 30 minutes
**Learning Goals:** Implement the two-pipe nc setup, the request-reading loop, and the per-connection server loop using the architecture from lecture.

---

## Background

You are evolving your httpd from v1 (stdin/stdout) to v2 (real network via nc). The scaffolded starter gives you the structure; you fill in the four core functions. By the end of the ICEX you should be able to `curl localhost:8080` and see a real HTTP response from your server.

---

## Starter Code

```bash
git pull upstream main
# starter: exercises/wk14/icex14b/httpd_v2.c
gcc -g -Wall -Wextra -std=c11 -o httpd_v2 httpd_v2.c
```

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <errno.h>

#define BUF_SIZE     4096
#define HDR_END      "\r\n\r\n"
#define DEFAULT_PORT "8080"
#define LOG_DIR      "logs"

/* ---- Task 1: create_pipes ----------------------------------------
   Create pipe_to_nc[2] and pipe_from_nc[2].
   Return 0 on success, -1 on failure. */
int create_pipes(int pipe_to_nc[2], int pipe_from_nc[2]);

/* ---- Task 2: spawn_nc --------------------------------------------
   Fork. In the child: dup2 pipe ends to stdin/stdout, close all
   four pipe FDs, exec nc on the given port.
   In the parent: close unused pipe ends.
   Return child pid. */
pid_t spawn_nc(const char *port, int pipe_to_nc[2], int pipe_from_nc[2]);

/* ---- Task 3: read_request ----------------------------------------
   Read from fd into buf (size bufsz) until HDR_END is detected
   or the buffer is full or the pipe closes.
   Return number of bytes read, -1 on error. */
ssize_t read_request(int fd, char *buf, size_t bufsz);

/* ---- Task 4: server_loop -----------------------------------------
   Loop: create pipes, spawn nc, read request, call handle_request,
   close pipe_to_nc[1] (signal EOF to nc), close pipe_from_nc[0],
   waitpid for nc, repeat. */
void server_loop(const char *port, FILE *logfp);

/* ---- Provided: handle_request ------------------------------------
   Minimal HTTP responder — replace with your v1 logic. */
void handle_request(int fd, const char *request, FILE *logfp) {
    const char *response =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html\r\n"
        "Connection: close\r\n"
        "\r\n"
        "<html><body><h1>httpd v2</h1></body></html>\r\n";
    write(fd, response, strlen(response));
    fprintf(logfp, "responded to: %.80s\n", request);
    fflush(logfp);
}

/* ---- Provided: open_log ----------------------------------------- */
FILE *open_log(const char *log_dir) {
    mkdir(log_dir, 0755);
    char path[256];
    snprintf(path, sizeof(path), "%s/httpd.log", log_dir);
    FILE *fp = fopen(path, "a");
    if (!fp) { perror("fopen log"); exit(EXIT_FAILURE); }
    fprintf(fp, "=== httpd v2 started ===\n");
    fflush(fp);
    return fp;
}

int main(int argc, char *argv[]) {
    const char *port    = (argc > 1) ? argv[1] : DEFAULT_PORT;
    const char *log_dir = (argc > 2) ? argv[2] : LOG_DIR;

    signal(SIGPIPE, SIG_IGN);   /* ignore broken pipe signals */

    FILE *logfp = open_log(log_dir);
    fprintf(stderr, "httpd v2 listening on port %s — log: %s/httpd.log\n",
            port, log_dir);

    server_loop(port, logfp);

    fclose(logfp);
    return 0;
}
```

---

## Tasks

**Task 1 — `create_pipes`**
Call `pipe()` for both `pipe_to_nc` and `pipe_from_nc`. Return -1 on failure.

**Task 2 — `spawn_nc`**
Fork. In the child: `dup2` the pipe ends to stdin and stdout, close all four original FDs, then `execlp("nc", "nc", "-l", port, (char *)NULL)`. In the parent: close the two ends the parent does not use (`pipe_to_nc[0]` and `pipe_from_nc[1]`). Return the child PID.

**Task 3 — `read_request`**
Accumulate bytes from `fd` into `buf`. After each `read()`, null-terminate and call `strstr(buf, HDR_END)`. Break when the delimiter is found, when `read()` returns 0, or when the buffer is full.

**Task 4 — `server_loop`**
Implement the per-connection loop:
1. `create_pipes()`
2. `spawn_nc()`
3. `read_request()` from `pipe_from_nc[0]`
4. If bytes read > 0, call `handle_request(pipe_to_nc[1], ...)`
5. `close(pipe_to_nc[1])` — signals EOF to nc
6. `close(pipe_from_nc[0])`
7. `waitpid(pid, NULL, 0)`
8. Go to 1

---

## Testing

```bash
# Terminal 1: start the server
./httpd_v2 8080 logs/

# Terminal 2: send a request
curl -v http://localhost:8080/

# Check the log
cat logs/httpd.log

# Multiple requests
for i in 1 2 3; do curl -s http://localhost:8080/ > /dev/null && echo "request $i ok"; done
```

---

## Submission Instructions

1. Branch: `git checkout -b icex14b-httpd-v2`
2. Files: `exercises/wk14/icex14b/httpd_v2.c`
3. Commit, push, open PR to `main`, request review.

---

## Rubric

| Task | Points | Criteria |
|------|--------|----------|
| Task 1 — `create_pipes` | 2 | Both pipes created; errors checked |
| Task 2 — `spawn_nc` | 2 | `dup2` correct; unused ends closed; exec called |
| Task 3 — `read_request` | 2 | Accumulates correctly; stops on `\r\n\r\n`; no overflow |
| Task 4 — `server_loop` | 2 | Correct order: close write end before `waitpid`; loop re-forks |
| `curl` demo passes; compiles clean with `-Wall -Wextra` | 2 | Server handles at least 3 sequential requests without crashing |
| **Total** | **10** | |
