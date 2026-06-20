# Assignment: HTTP Response Generator — `http_resp`

This assignment is the first step toward building a thin HTTP server over the next several assignments. You will write a program that reads a single HTTP GET request from stdin, maps the requested path into a filesystem directory, and writes a complete HTTP/1.1 response to stdout. Everything you need — `stat()`, `lstat()`, `opendir()`, `readdir()`, `closedir()`, `snprintf()`, `strftime()` — comes directly from this week's lecture.

Later assignments will wrap this logic in a socket listener and a `fork()`-per-connection model. The response generator you write here will survive those refactors largely unchanged.

---

# Background

## How a Web Server Responds to a GET Request

A minimal HTTP/1.1 exchange looks like this:

**Request (from client → server, arrives on stdin in this assignment):**
```
GET /index.html HTTP/1.1
Host: localhost
<blank line>
```

**Response (from server → client, written to stdout in this assignment):**
```
HTTP/1.1 200 OK\r\n
Content-Type: text/html\r\n
Content-Length: 142\r\n
\r\n
<html>...body...</html>
```

HTTP headers are terminated by `\r\n` (CRLF). The header block ends with a blank line (`\r\n\r\n`). The body follows immediately. **Content-Length** is the byte count of the body only, not the headers.

## DocumentRoot

Web servers map URL paths onto the local filesystem using a **DocumentRoot** directory. A request for `/images/logo.png` with `DocumentRoot=/var/www/html` maps to `/var/www/html/images/logo.png`. Your program accepts `DocumentRoot` as a command-line argument and prepends it to every requested path.

Review: [HTTP session overview — MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Session)

---

# Required Functions

The autograder verifies that each of the following is called at least once in your submitted source.

| Function | Header | Purpose in this program | Man page |
|---|---|---|---|
| `stat` or `lstat` | `<sys/stat.h>` | Check whether the requested path exists; get size and type | `man 2 stat` |
| `opendir` | `<dirent.h>` | Open a directory for listing | `man 3 opendir` |
| `readdir` | `<dirent.h>` | Iterate directory entries | `man 3 readdir` |
| `closedir` | `<dirent.h>` | Close the directory stream | `man 3 closedir` |
| `snprintf` | `<stdio.h>` | Build filesystem paths and HTML safely with size limits | `man 3 printf` |
| `strftime` | `<time.h>` | Format `st_mtime` as a human-readable date string | `man 3 strftime` |
| `sscanf` | `<stdio.h>` | Parse the method, path, and version from the request line | `man 3 scanf` |
| `fprintf(stderr,...)` | `<stdio.h>` | Write log output | `man 3 fprintf` |

<details>
<summary><strong>Building paths safely with snprintf — read before you start</strong></summary>

### Why snprintf, not strcat

`strcat` has no size limit — if the concatenated result exceeds your buffer, it silently overwrites adjacent memory. `snprintf` writes at most `n` bytes including the null terminator and always leaves your buffer in a valid state:

```c
char full_path[2048];
snprintf(full_path, sizeof(full_path), "%s/%s", doc_root, req_path);
```

The return value is the number of bytes that *would* have been written. If it is `>= sizeof(full_path)`, the path was truncated — log it and return a 404.

### Why snprintf for HTML too

For the directory listing body, write the entire HTML into a `char` buffer first, then measure it with `strlen` to get `Content-Length`:

```c
char body[8192];
int  pos = 0;
pos += snprintf(body + pos, sizeof(body) - pos, "<html><body><table>\n");
/* ... append rows ... */
pos += snprintf(body + pos, sizeof(body) - pos, "</table></body></html>\n");

/* Now you know the length before printing any headers */
printf("Content-Length: %d\r\n\r\n", pos);
printf("%s", body);
```

This is the pattern you will carry forward into every future version of the server.

</details>

<details>
<summary><strong>HTTP response format — exact requirements</strong></summary>

### Status line

```
HTTP/1.1 200 OK\r\n
```

The three status codes required for this assignment:

| Code | Reason | When |
|---|---|---|
| `200 OK` | Success | Path exists and was served |
| `404 Not Found` | No such file or directory | `stat()` fails with `ENOENT` |
| `501 Not Implemented` | Method not GET | First token of request line is not `GET` |

### Required headers (all responses)

```
Content-Type: text/html\r\n
Content-Length: <byte count of body>\r\n
\r\n
```

For 404 and 501 responses, the body is a minimal HTML error page. Its byte count still goes in `Content-Length`.

</details>

---

# Requirements

## Command-Line Interface

```
./http_resp <documentRoot>
```

`<documentRoot>` is the absolute path to the directory that serves as the root of the URL namespace. Your program must log the configured DocumentRoot to stderr on startup.

```bash
./http_resp /home/user/www < request.txt > response.txt
```

## Reading the Request

Read one line from stdin. That line is the HTTP request line:

```
GET /path/to/resource HTTP/1.1
```

Parse it with `sscanf` into three fields: method, path, and HTTP version. Log all three to stderr.

You do not need to parse or process subsequent header lines for this assignment. Read and discard them (loop until you see a blank line or EOF) so your program cleanly consumes the full request.

## Building the Filesystem Path

Prepend `documentRoot` to the request path using `snprintf`:

```c
char full_path[2048];
snprintf(full_path, sizeof(full_path), "%s%s", doc_root, req_path);
```

Note: if `req_path` already starts with `/`, the result is `documentRoot/path` — correct. Log the full filesystem path you resolved to stderr.

Call `lstat(full_path, &sb)` to determine whether the path exists and what type it is.

## Error Responses

**501 Not Implemented** — if the method parsed from the request line is anything other than `GET`, emit a 501 response and exit.

**404 Not Found** — if `lstat()` fails (path does not exist), emit a 404 response and exit.

Both error responses must include `Content-Type: text/html` and `Content-Length` headers with a small HTML body:

```html
<html><body><h1>404 Not Found</h1></body></html>
```

## File Response

If `lstat()` reports the path is a regular file (`S_ISREG`):

1. Open the file for reading with `fopen`
2. Emit the HTTP 200 status line and headers. Use `sb.st_size` for `Content-Length`
3. Read the file contents and write them to stdout
4. Close the file

## Directory Response

If `lstat()` reports the path is a directory (`S_ISDIR`):

1. Build the HTML body into a buffer using `snprintf` (see snprintf notes above)
2. The body must contain an HTML table. Each row represents one directory entry
3. Skip `.` and `..`
4. For each entry, the table row must contain:

| Column | Content | Notes |
|---|---|---|
| Name | `<a href="/req_path/entry_name">entry_name</a>` | href is path relative to documentRoot, not filesystem |
| Size | `sb.st_size` in bytes | from `lstat()` on the full path |
| Type | `file` or `dir` | from `S_ISREG` / `S_ISDIR` on `sb.st_mode` |
| Modified | date string from `strftime` | use `"%b %d %Y %H:%M"` on `sb.st_mtime` |

5. Use the `strlen` of the completed body buffer as `Content-Length`
6. Emit the status line, headers, blank line, then the body

## Logging Requirements

All log output goes to **stderr**. stdout is reserved for the HTTP response. Log:

- On startup: the configured DocumentRoot
- Per request: parsed method, path, and HTTP version
- Per request: the full filesystem path resolved for the response
- Per request: the response status code and reason being sent
- Per directory response: each entry name and size on one line

---

# Programming Constraints

- No global variables except constants. All working state is locally scoped or passed as parameters
- Use `#define` or `const` for all constants (buffer sizes, HTTP status strings, format strings). No magic numbers
- `main()` must follow a driver architecture — delegate to separate functions for: parsing the request, building the response headers, serving a file, serving a directory
- Use `snprintf` (never `strcat` or `strcpy`) for all path and string construction that writes into fixed-size buffers
- Build the directory listing HTML body into a buffer before emitting any headers, so `Content-Length` is known before output begins

---

# Output Format

## File response example

Request:
```
GET /index.html HTTP/1.1
```

With `DocumentRoot=/var/www/html` and `/var/www/html/index.html` being a 98-byte file:

```
HTTP/1.1 200 OK\r\n
Content-Type: text/html\r\n
Content-Length: 98\r\n
\r\n
<contents of index.html>
```

## Directory response example

Request:
```
GET / HTTP/1.1
```

<details>
<summary>Expected stdout (directory listing)</summary>

```
HTTP/1.1 200 OK\r\n
Content-Type: text/html\r\n
Content-Length: 312\r\n
\r\n
<html>
<body>
<h2>Index of /</h2>
<table>
<tr><th>Name</th><th>Size</th><th>Type</th><th>Modified</th></tr>
<tr><td><a href="/index.html">index.html</a></td><td>98</td><td>file</td><td>Apr 09 2026 14:22</td></tr>
<tr><td><a href="/images">images</a></td><td>128</td><td>dir</td><td>Mar 28 2026 09:05</td></tr>
</table>
</body>
</html>
```

</details>

<details>
<summary>Expected stderr (log output)</summary>

```
DocumentRoot: /var/www/html
REQUEST: method=GET path=/ version=HTTP/1.1
RESOLVED: /var/www/html
RESPONSE: 200 OK
DIR ENTRY: index.html 98
DIR ENTRY: images 128
```

</details>

---

# Comments and Style

Your source file must include:

- Header comment block: your name, a brief program description, and the assignment number
- No magic numbers — use `#define` or `const` for all buffer sizes, status codes, and format strings
- Short comment block above each function: description, parameters, return value
- Semantically meaningful variable names
- A `README.md` in your submission directory containing your pseudocode and a brief test plan (one line per rubric test describing how you will verify it)

---

# Testing & Rubric

| Test | Condition | Points |
|:---|:---|---:|
| test1 | Compiles without warnings (`-Wall`) | 5 |
| test2 | Returns HTTP 501 for a non-GET method (e.g. `POST / HTTP/1.1`) | 5 |
| test3 | Returns HTTP 404 when requested path does not exist | 5 |
| test4 | Accepts `documentRoot` as command-line argument and logs it to stderr | 5 |
| test5 | Parses and logs method, path, and version from the request line | 5 |
| test6 | Logs the full filesystem path resolved for the response | 5 |
| test7 | File response: correct `HTTP/1.1 200 OK` status line | 5 |
| test8 | File response: `Content-Length` header matches `st_size` of file | 10 |
| test9 | File response: `Content-Type: text/html` header present | 5 |
| test10 | File response: body matches file contents | 10 |
| test11 | Directory response: `HTTP/1.1 200 OK` + `Content-Type: text/html` | 5 |
| test12 | Directory response: HTML table present in body | 5 |
| test13 | Directory response: entry names are HTML anchor links with correct href | 5 |
| test14 | Directory response: table rows include size, type (`file`/`dir`), and date | 5 |
| test15 | Directory response: `.` and `..` excluded from listing | 5 |
| Handgrading | Comments, function decomposition, `#define` constants, README test plan | 5 |
| Handgrading | stderr logging completeness; no response output on stderr | 5 |
| **Total** | | **100** |
| ECtest1 | HEAD method: returns correct headers (no body), not 501 | 5 |
| ECtest2 | Path traversal safety: requests containing `..` that escape documentRoot return 403 | 5 |

---

# Suggestions

## Implementation order

Work through the features in this sequence — each step gives you something testable before moving on:

1. **argc check + DocumentRoot logging** — get test4 immediately
2. **Request line parsing** — get test5; you can now always log what came in
3. **Path building with snprintf + lstat** — get test6; the path is resolved even if response is wrong
4. **501 and 404 error responses** — get test2 and test3; forces you to think about the response format early
5. **File response** — get test7–10; the full response pipeline works for the simple case
6. **Directory response** — get test11–15; builds on everything above

## Test resources

Create a `testroot/` directory in your repo containing:
- A small `index.html` file (known size)
- A subdirectory with a few files
- A file whose name you will use in 404 testing (do not create it)

Create a `requests/` directory with one text file per rubric test, each containing a single HTTP request line followed by a blank line. Feed them to your program with `< requests/test_get_file.txt`.

## Commit milestones

Commit after each item in the implementation order above. If a later feature breaks an earlier one, `git diff` and `git log` will show you exactly where things diverged.

---

# Submission

Submit your source file named **`http_resp.c`** to the [Autograder](https://autograder.luddy.indiana.edu/web/project/XXXX).

Your submission directory must be `exercises/A##/` and must contain:
- `http_resp.c` — your implementation
- `README.md` — pseudocode and test plan
- `testroot/` — your test document root (the autograder uses its own, but having yours in the repo is required)

Commit everything and submit your commit hash URL to the [Canvas assignment](https://iu.instructure.com/courses/XXXXXXX/assignments/XXXXXXXX).
