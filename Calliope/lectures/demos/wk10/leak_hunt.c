/*
 * leak_hunt.c — Live demo: Hunting memory leaks with valgrind
 *
 * This program has TWO memory leaks:
 *   1. OBVIOUS:  only free(head) is called — the rest of the list is leaked
 *   2. SUBTLE:   even after fixing #1, each node's label string is still leaked
 *
 * Build:   gcc -g -Wall -Wextra -std=c11 -o leak_hunt leak_hunt.c
 * Run:     valgrind --leak-check=full ./leak_hunt
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- Data definition ---- */

typedef struct Node {
    int          id;
    char        *label;       /* heap-allocated string — separate malloc! */
    struct Node *next;
} Node;

/* ---- Create a new node (TWO allocations: node + label) ---- */

Node *create_node(int id, const char *label) {
    Node *n = malloc(sizeof(Node));
    if (n == NULL) {
        perror("malloc node");
        exit(EXIT_FAILURE);
    }

    n->id = id;

    /* Allocate space for the label string and copy it in */
    n->label = malloc(strlen(label) + 1);
    if (n->label == NULL) {
        perror("malloc label");
        free(n);
        exit(EXIT_FAILURE);
    }
    strcpy(n->label, label);

    n->next = NULL;
    return n;
}

/* ---- Print the list ---- */

void print_list(const Node *head) {
    printf("Roster:\n");
    for (const Node *cur = head; cur != NULL; cur = cur->next) {
        printf("  [%d] %s\n", cur->id, cur->label);
    }
}

/* ---- main ---- */

int main(void) {
    const char *names[] = {"alpha", "bravo", "charlie", "delta", "echo"};
    int count = 5;

    /* Build the list — 5 nodes, each with a heap-allocated label */
    Node *head = NULL;
    for (int i = 0; i < count; i++) {
        Node *n = create_node(i + 1, names[i]);
        n->next = head;        /* prepend */
        head = n;
    }

    print_list(head);

    /*
     * BUG #1 (obvious): We only free the head node.
     * The other 4 nodes — and ALL 5 label strings — are leaked.
     *
     * Total allocations: 10  (5 nodes + 5 labels)
     * Total frees:        1  (just head)
     * Leaked blocks:      9
     */
    free(head);

    /*
     * FIX #1: Replace the single free(head) above with a traversal:
     *
     *   Node *cur = head;
     *   while (cur != NULL) {
     *       Node *next = cur->next;
     *       free(cur);
     *       cur = next;
     *   }
     *
     * Re-run valgrind — leaked blocks drop from 9 to 5.
     * The 5 label strings are STILL leaked.
     */

    /*
     * FIX #2: Free each node's label BEFORE freeing the node:
     *
     *   Node *cur = head;
     *   while (cur != NULL) {
     *       Node *next = cur->next;
     *       free(cur->label);     // free inner allocation first
     *       free(cur);            // then free the node itself
     *       cur = next;
     *   }
     *
     * Re-run valgrind:
     *   HEAP SUMMARY: in use at exit: 0 bytes in 0 blocks
     *   ERROR SUMMARY: 0 errors from 0 contexts
     */

    return 0;
}
