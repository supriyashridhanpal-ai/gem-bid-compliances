#include <stdio.h>
#include <string.h>
#include "ds.h"

void init_stack(AuditStack *s) {
    s->top = -1;
}

void push_audit(AuditStack *s, const char *msg) {
    if (s->top < 9) {
        strncpy(s->logs[++s->top], msg, MAX_DESC - 1);
    }
}

void demo_stack(void) {
    printf("\n--- Demonstration: Stack (LIFO Audit History) ---\n");
    AuditStack s;
    init_stack(&s);
    push_audit(&s, "Stage 1: Document Upload Verified");
    push_audit(&s, "Stage 2: GST & PAN Passed");
    push_audit(&s, "Stage 3: Turnover Threshold Met");

    printf("Audit Trail (Unwinding in Reverse Chronological Order):\n");
    while (s.top >= 0) {
        printf(" -> %s\n", s.logs[s.top--]);
    }
}