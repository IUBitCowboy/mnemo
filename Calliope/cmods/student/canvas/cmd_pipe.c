/*
 * cmd_pipe.c
 *
 * Forks a child process that runs "ls -1 <directory>", captures
 * its stdout through a pipe, and prints each line back in the
 * parent with a line number prefix.
 *
 * Usage: ./cmd_pipe <directory>
 * Example: ./cmd_pipe /tmp
 *
 * Expected output:
 *   [1] file_a.txt
 *   [2] file_b.c
 *   [3] subdir
 *   Child exited with status 0
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

/* ── Provided helper — do not modify ─────────────────────────────────────── */

/*
 * print_numbered() — reads all output from file descriptor 'fd' and
 * prints each chunk with a running line-number prefix.
 *
 * Limitations: splits on up to 255-byte chunks; a very long line may
 * be split across two reads (see README Q3).
 */
void print_numbered(int fd) {
    char buf[256];
    char line[256];
    int  line_num = 1;
    int  pos      = 0;
    ssize_t n;

    while ((n = read(fd, buf, sizeof(buf) - 1)) > 0) {
        buf[n] = '\0';
        for (int i = 0; i < n; i++) {
            if (buf[i] == '\n' || pos == (int)sizeof(line) - 2) {
                line[pos] = '\0';
                if (pos > 0)
                    printf("[%d] %s\n", line_num++, line);
                pos = 0;
            } else {
                line[pos++] = buf[i];
            }
        }
    }
    /* flush any partial line at EOF */
    if (pos > 0) {
        line[pos] = '\0';
        printf("[%d] %s\n", line_num, line);
    }
}

/* ── main ─────────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[]) {

    // check that exactly one argument was provided
    // if not, print: "usage: cmd_pipe <directory>\n" to stderr and exit

    int fd[2];

    // Task 1: create the pipe with pipe(fd)
    // check return value — perror("pipe") and exit on failure

    // Task 2: fork
    // check return value — perror("fork") and exit on -1

    // ── CHILD branch (pid == 0) ──────────────────────────────────────────

        // Task 3a: close the read end of the pipe — child does not read

        // Task 3b: dup2 the write end to STDOUT_FILENO
        //          after this, anything the child writes to stdout goes
        //          into the pipe

        // Task 3c: close the original write end — you have dup'd it,
        //          so fd[1] is now redundant

        // Task 3d: build the argument array for ls
        //   char *args[] = { "ls", "-1", argv[1], NULL };

        // Task 3e: execvp("ls", args)
        //          if execvp returns, it failed — perror("execvp") and exit

    // ── PARENT branch (pid > 0) ──────────────────────────────────────────

        // Task 4a: close the WRITE end of the pipe in the parent
        //          *** if you skip this, read() will block forever ***

        // Task 4b: call print_numbered(fd[0]) to read and print child output

        // Task 4c: close the read end now that you are done reading

        // Task 4d: waitpid for the child
        //   int status;
        //   waitpid(pid, &status, 0);

        // Task 4e: print the child's exit status
        //   printf("Child exited with status %d\n", WEXITSTATUS(status));

    return 0;
}
