/*
 * mini_ls.c
 *
 * A stripped-down ls: prints type, modification date, and name for
 * a single file argument or every entry in a directory argument.
 *
 * Usage:  ./mini_ls <file-or-directory>
 *
 * Output columns (provided — do not modify print_entry):
 *   file_type   mod_date             file_name
 *   reg         Apr 09 14:22         clients.dat
 *   dir         Mar 28 09:05         docs
 *   lnk         Apr 01 11:30         latest
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <dirent.h>
#include <sys/stat.h>

/* ── Struct you will populate ─────────────────────────────────────────────── */

typedef struct {
    char file_name[256];   /* entry name only — no leading path */
    char mod_date[32];     /* formatted modification time       */
    char file_type[8];     /* "reg", "dir", or "lnk"            */
} FileInfo;

/* ── Provided helpers — do not modify ────────────────────────────────────── */

/*
 * format_date() — converts a time_t to a human-readable string.
 * Call it like: format_date(sb.st_mtime, fi.mod_date, sizeof(fi.mod_date));
 */
void format_date(time_t t, char *buf, size_t len) {
    struct tm *tm_info = localtime(&t);
    strftime(buf, len, "%b %d %H:%M", tm_info);
}

/*
 * print_entry() — prints one line of output from a populated FileInfo.
 * Do not change this function; the grading harness depends on its format.
 */
void print_entry(const FileInfo *fi) {
    printf("%-8s  %-20s  %s\n", fi->file_type, fi->mod_date, fi->file_name);
}

/* ── Functions you implement ──────────────────────────────────────────────── */

/*
 * fill_info() — populate a FileInfo from a struct stat and a filename.
 *
 * Parameters:
 *   sb    — a struct stat already filled by lstat()
 *   name  — the filename string (entry name only, not the full path)
 *   fi    — pointer to the FileInfo you must fill in
 *
 * Steps:
 *   1. Copy name into fi->file_name
 *   2. Call format_date() with sb.st_mtime to fill fi->mod_date
 *   3. Set fi->file_type to "reg", "dir", or "lnk" based on sb.st_mode
 *      using the S_IS*() macros
 */
void fill_info(const struct stat *sb, const char *name, FileInfo *fi) {

    // copy name into fi->file_name

    // call format_date() to fill fi->mod_date

    // set fi->file_type: "reg" for regular, "dir" for directory, "lnk" for symlink

}

/* ── main ─────────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[]) {

    // check that exactly one argument was provided; print usage and exit if not

    struct stat sb;

    // call lstat() on argv[1]; print an error with perror() and exit if it fails

    // --- Single file or symlink case ---
    // if argv[1] is a regular file or a symlink (not a directory):
    //   declare a FileInfo, call fill_info(), call print_entry(), return 0

    // --- Directory case ---
    // open the directory with opendir(); print an error and exit if it fails

    struct dirent *ep;
    char path[1024];
    FileInfo fi;

    // loop with readdir() until it returns NULL:
    //   skip entries whose name starts with '.'
    //   build the full path: snprintf(path, sizeof(path), "%s/%s", argv[1], ep->d_name)
    //   call lstat() on path (not ep->d_name) — print error with perror() and continue on failure
    //   call fill_info() and print_entry()

    // close the directory with closedir()

    return 0;
}
