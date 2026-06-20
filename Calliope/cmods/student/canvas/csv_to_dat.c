/*
 * csv_to_dat.c
 *
 * Reads Client records from a CSV text file and writes them to a binary
 * data file (clients.dat) using fwrite().
 *
 * Usage: ./csv_to_dat <input_csv_file>
 * Example: ./csv_to_dat clients_sample.csv
 *
 * CSV format (one record per line, comma-separated):
 *   account,name,balance
 *   100,Jones,24.98
 */

#include <stdio.h>
#include <stdlib.h>

#define MAX_CLIENTS 100

typedef struct { int account; char name[30]; float balance; } Client;

int main(int argc, char *argv[]) {

    // check that exactly one command-line argument was provided (argc)
    // if not, print usage message and exit with EXIT_FAILURE

    // open the input CSV file for reading using argv[1]
    // if fopen returns NULL, print an error message and exit with EXIT_FAILURE

    Client clients[MAX_CLIENTS];
    int count = 0;

    // read Client records from the CSV file using fscanf
    //   format string: "%d,%29s,%f"
    //   store each record in clients[count] and increment count
    //   stop when fscanf does not return 3 or count reaches MAX_CLIENTS

    // close the input CSV file

    // open "clients.dat" for binary writing ("wb")
    // if fopen returns NULL, print an error message and exit with EXIT_FAILURE

    // write all count Client records to the binary file using fwrite
    //   write the entire clients array in a single fwrite call

    // close the binary output file

    printf("Wrote %d records to clients.dat\n", count);
    return 0;
}
