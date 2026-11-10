#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ds.h"

// ----------------------------------------------------------------------------
// 1. LINKED QUEUE (FIFO) FOR VENDOR BID SUBMISSIONS
// ----------------------------------------------------------------------------

void init_bid_queue(BidQueue *q) {
    q->front = NULL;
    q->rear = NULL;
    q->count = 0;
}

void enqueue_bid(BidQueue *q, int sub_id, const char *company, const char *tender) {
    BidNode *newNode = (BidNode*)malloc(sizeof(BidNode));
    if (!newNode) return;

    newNode->submission_id = sub_id;
    strncpy(newNode->company_name, company, sizeof(newNode->company_name) - 1);
    newNode->company_name[sizeof(newNode->company_name) - 1] = '\0';
    strncpy(newNode->tender_title, tender, sizeof(newNode->tender_title) - 1);
    newNode->tender_title[sizeof(newNode->tender_title) - 1] = '\0';
    newNode->next = NULL;

    if (q->rear == NULL) {
        q->front = q->rear = newNode;
    } else {
        q->rear->next = newNode;
        q->rear = newNode;
    }
    q->count++;
}

int dequeue_bid(BidQueue *q, BidNode *out_bid) {
    if (q->front == NULL) {
        return 0; // Queue empty
    }

    BidNode *temp = q->front;
    *out_bid = *temp; // Copy data to output parameter

    q->front = q->front->next;
    if (q->front == NULL) {
        q->rear = NULL;
    }

    free(temp);
    q->count--;
    return 1;
}

void free_bid_queue(BidQueue *q) {
    BidNode *curr = q->front;
    while (curr) {
        BidNode *temp = curr;
        curr = curr->next;
        free(temp);
    }
    q->front = q->rear = NULL;
    q->count = 0;
}

// ----------------------------------------------------------------------------
// 2. CIRCULAR ARRAY QUEUE FOR TENDER CLAUSE EVALUATION PIPELINE
// ----------------------------------------------------------------------------

void init_queue(ClauseQueue *q) {
    q->front = 0;
    q->rear = -1;
    q->count = 0;
}

void enqueue(ClauseQueue *q, const char *name, int req, int sub, int weight) {
    if (q->count < 10) {
        q->rear = (q->rear + 1) % 10;
        strncpy(q->items[q->rear].name, name, MAX_DESC - 1);
        q->items[q->rear].name[MAX_DESC - 1] = '\0';
        q->items[q->rear].required_val = req;
        q->items[q->rear].submitted_val = sub;
        q->items[q->rear].weight = weight;
        q->count++;
    }
}

int dequeue(ClauseQueue *q, Clause *out) {
    if (q->count == 0) return 0;
    *out = q->items[q->front];
    q->front = (q->front + 1) % 10;
    q->count--;
    return 1;
}

// ----------------------------------------------------------------------------
// 3. VIVA DEMONSTRATION
// ----------------------------------------------------------------------------

void demo_queue(void) {
    printf("\n--- Demonstration: Queue (FIFO Vendor Bid Submissions) ---\n");
    BidQueue bq;
    init_bid_queue(&bq);

    printf("Enqueuing bids in order of arrival...\n");
    enqueue_bid(&bq, 1, "Apex Infotech", "Supply of Laptops");
    enqueue_bid(&bq, 2, "Zenith Systems", "Solar Panel Installation");
    enqueue_bid(&bq, 3, "Bharat Solvers", "Food Grain Supply");

    printf("Total Bids in Queue: %d\n", bq.count);
    printf("Dequeuing bids in FIFO order (First-In, First-Out):\n");

    BidNode current;
    while (dequeue_bid(&bq, &current)) {
        printf(" -> Processed Submission #%d | Company: %s | Tender: %s\n",
               current.submission_id, current.company_name, current.tender_title);
    }
    free_bid_queue(&bq);
}