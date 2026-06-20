# ICEX 18: httpd v2 — Two Pipes and a Live Server

**Duration:** 30 minutes
**Learning Goals:** Implement the two-pipe nc setup, the request-reading loop, and the per-connection server loop using the architecture from lecture.

---

## Background

You are evolving your httpd from v1 (stdin/stdout) to v2 (real network via nc). The scaffolded starter gives you the structure; you fill in the four core functions. By the end of the ICEX you should be able to `curl localhost:8080` and see a real HTTP response from your server.

---

## Starter Code

```bash
git pull upstream main
# starter: exercises/wk14/icex18/httpd_v2.c
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

# Multiple requests — server must survive all three
for i in 1 2 3; do curl -s http://localhost:8080/ > /dev/null && echo "request $i ok"; done
```

---

## Submission Instructions

1. Branch: `git checkout -b icex18-httpd-v2`
2. Files: `exercises/wk14/icex18/httpd_v2.c`
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
