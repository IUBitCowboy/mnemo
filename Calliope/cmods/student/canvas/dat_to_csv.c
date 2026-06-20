/*
 * dat_to_csv.c
 *
 * Reads Client records from a binary data file and writes them to a
 * CSV text file (clients.csv) using fprintf().
 *
 * Usage: ./dat_to_csv <input_dat_file>
 * Example: ./dat_to_csv clients.dat
 *
 * Output file: clients.csv
 * CSV format (one record per line, comma-separated):
 *   account,name,balance
 */

#include <stdio.h>
#include <stdlib.h>

typedef struct { int account; char name[30]; float balance; } Client;

int main(int argc, char *argv[]) {

    // check that exactly one command-line argument was provided (argc)
    // if not, print usage message and exit with EXIT_FAILURE

    // open the input binary file for binary reading ("rb") using argv[1]
    // if fopen returns NULL, print an error message and exit with EXIT_FAILURE

    // open "clients.csv" for text writing ("w")
    // if fopen returns NULL, print an error message and exit with EXIT_FAILURE

    Client c;
    int count = 0;

    // read Client records one at a time using fread
    //   read a single Client record per call: fread(&c, sizeof(Client), 1, ...)
    //   fread returns the number of items read; loop until it returns 0 (EOF)
    //   for each record read, write one CSV line to clients.csv using fprintf
    //   format string: "%d,%s,%.2f\n"
    //   increment count for each record written

    // close both files

    printf("Wrote %d records to clients.csv\n", count);
    return 0;
}
