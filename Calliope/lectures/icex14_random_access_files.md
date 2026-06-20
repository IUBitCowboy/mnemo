# ICEX: Binary Client Records — CSV to DAT and Back

**Duration:** 30 minutes  
**Learning Goals:** Open files in binary mode, write a struct array with `fwrite`, read it back with `fread`, use command-line arguments to supply filenames.

---

## Background

Text files store data as human-readable characters. Binary files store data as raw memory — exactly what the program sees at runtime. A `Client` struct written with `fwrite` occupies the same bytes in the file as it does in RAM, which makes binary I/O fast and exact — but the file is not printable.

In this exercise you write two programs:

| Program | Input | Output |
|---------|-------|--------|
| `csv_to_dat` | CSV text file (command-line arg) | `clients.dat` (binary) |
| `dat_to_csv` | `.dat` binary file (command-line arg) | `clients.csv` (text) |

The struct used throughout:

```c
typedef struct { int account; char name[30]; float balance; } Client;
```

---

## Starter Files

Both skeleton files are provided in the class repo under `exercises/wk11/icex14/`.

```bash
git pull upstream main
cd exercises/wk11/icex14/
gcc -g -Wall -o csv_to_dat csv_to_dat.c
gcc -g -Wall -o dat_to_csv dat_to_csv.c
```

A sample input file `clients_sample.csv` is also provided:

```
100,Jones,24.98
200,Doe,345.67
300,White,0.00
400,Stone,-42.16
500,Rich,224.62
```

---

## Part 1 — `csv_to_dat.c` (required)

Open `csv_to_dat.c` and implement the steps marked by comments. The program takes one command-line argument — the path to a CSV file — and writes `clients.dat` in binary mode.

Key functions: `fopen`, `fscanf`, `fwrite`, `fclose`  
`fscanf` format string for a comma-separated record: `"%d,%29s,%f"`

**Expected run:**
```
$ ./csv_to_dat clients_sample.csv
Wrote 5 records to clients.dat
```

After running, try `cat clients.dat` — you will see garbage characters because the file is binary. That is expected.

---

## Part 2 — `dat_to_csv.c` *(Extra Credit — 3 pts)*

Open `dat_to_csv.c` and implement the steps marked by comments. The program takes one command-line argument — the path to a `.dat` file — and writes `clients.csv`.

Key functions: `fopen`, `fread`, `fprintf`, `fclose`  
`fread` returns the number of items successfully read. Loop until it returns `0`.

**Expected run:**
```
$ ./dat_to_csv clients.dat
Wrote 5 records to clients.csv
```

Verify round-trip correctness:
```bash
diff clients_sample.csv clients.csv
```
If `diff` produces no output, the data survived the round trip perfectly.

---

## Tasks

**Task 1 — Implement `csv_to_dat.c`** *(7 pts)*  
Fill in all comment-marked sections. Compile and run against `clients_sample.csv`. Confirm `clients.dat` is created and non-empty (`ls -l clients.dat`).

**Task 2 — Written answers in README.md** *(3 pts)*  
Answer Q1–Q3 in `exercises/wk11/icex14/README.md`.

**Task 3 — Implement `dat_to_csv.c`** *(Extra Credit — 3 pts)*  
Fill in all comment-marked sections. Run against `clients.dat`. Use `diff` to verify the round trip. Answer Q4 in README.md.

---

## Submission

```bash
git checkout -b icex14-binary-files
git add exercises/wk11/icex14/
git commit -m "icex14: binary client records"
git push -u origin icex14-binary-files
```

Open a PR on `github.iu.edu` and request a review from your TA or instructor.

---

## README.md Questions

**Q1.** What does the `"wb"` mode flag mean when passed to `fopen`? How does it differ from `"w"`?

**Q2.** After you run `csv_to_dat`, what is the size of `clients.dat` in bytes (use `ls -l`)? Show your calculation: what formula predicts that number from the struct definition?

**Q3.** Run `cat clients.dat`. Describe what you see and explain why the output looks the way it does.

**Q4.** *(Part 2 only)* Did `diff` show any differences? If it did, what might cause a mismatch even when the logic is correct?

---

## Rubric

| Task | Points | Criteria |
|------|--------|----------|
| Task 1 — `csv_to_dat.c` compiles without warnings | 1 | Compiles clean with `-Wall` |
| Task 1 — argc check and fopen error handling | 1 | Exits with message if no argument or file not found |
| Task 1 — fscanf loop reads all records | 2 | All 5 records read; loop terminates correctly |
| Task 1 — fwrite writes binary file | 2 | `clients.dat` created; size matches `5 * sizeof(Client)` |
| Task 1 — correct record count printed | 1 | Output matches number of records in input |
| Task 2 — written answers Q1–Q3 | 3 | All three questions answered correctly in README.md |
| **Total** | **10** | |
| | | |
| **Extra Credit** | | |
| Task 3 — `dat_to_csv.c` compiles and runs | 1 | Correct `fopen`/`fread` loop, `fprintf` output, `fclose` |
| Task 3 — round-trip verified | 1 | `diff clients_sample.csv clients.csv` produces no output |
| Task 3 — written answer Q4 | 1 | Correct explanation of potential float formatting mismatch |
| **Extra Credit Total** | **+3** | |
