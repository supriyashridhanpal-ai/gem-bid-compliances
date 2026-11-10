#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ds.h"

// ----------------------------------------------------------------------------
// FEATURE 4: PRIORITY QUEUE / BINARY MAX-HEAP (L1/H1 BIDDER LEADERBOARD)
// ----------------------------------------------------------------------------

void heap_init(MaxHeap *h) {
    h->size = 0;
}

static void swap_nodes(HeapBid *a, HeapBid *b) {
    HeapBid temp = *a;
    *a = *b;
    *b = temp;
}

// Insert into Binary Max-Heap: O(log n) Heapify Up
void heap_insert(MaxHeap *h, int sub_id, const char *company, const char *tender, int score) {
    if (h->size >= MAX_HEAP_SIZE) return;

    int idx = h->size;
    h->items[idx].submission_id = sub_id;
    strncpy(h->items[idx].company_name, company, sizeof(h->items[idx].company_name) - 1);
    h->items[idx].company_name[sizeof(h->items[idx].company_name) - 1] = '\0';
    strncpy(h->items[idx].tender_title, tender, sizeof(h->items[idx].tender_title) - 1);
    h->items[idx].tender_title[sizeof(h->items[idx].tender_title) - 1] = '\0';
    h->items[idx].score = score;
    h->size++;

    // Heapify Up: bubble up if score is greater than parent
    while (idx > 0) {
        int parent = (idx - 1) / 2;
        if (h->items[idx].score > h->items[parent].score) {
            swap_nodes(&h->items[idx], &h->items[parent]);
            idx = parent;
        } else {
            break;
        }
    }
}

// Extract Max from Binary Max-Heap: O(log n) Heapify Down
int heap_extract_max(MaxHeap *h, HeapBid *out) {
    if (h->size <= 0) return 0;

    *out = h->items[0];
    h->items[0] = h->items[h->size - 1];
    h->size--;

    int idx = 0;
    // Heapify Down
    while (1) {
        int left = 2 * idx + 1;
        int right = 2 * idx + 2;
        int largest = idx;

        if (left < h->size && h->items[left].score > h->items[largest].score) {
            largest = left;
        }
        if (right < h->size && h->items[right].score > h->items[largest].score) {
            largest = right;
        }

        if (largest != idx) {
            swap_nodes(&h->items[idx], &h->items[largest]);
            idx = largest;
        } else {
            break;
        }
    }

    return 1;
}

// ----------------------------------------------------------------------------
// VIVA DEMO
// ----------------------------------------------------------------------------

void demo_heap(void) {
    printf("\n--- Demonstration: Priority Queue / Binary Max-Heap (Leaderboard) ---\n");
    MaxHeap h;
    heap_init(&h);

    printf("Inserting bid scores into Max-Heap...\n");
    heap_insert(&h, 101, "Alpha Tech", "Laptops Tender", 75);
    heap_insert(&h, 102, "Beta Global", "Laptops Tender", 95);
    heap_insert(&h, 103, "Gamma Networks", "Laptops Tender", 60);
    heap_insert(&h, 104, "Delta Solutions", "Laptops Tender", 100);
    heap_insert(&h, 105, "Epsilon Infotech", "Laptops Tender", 85);

    printf("Total Bids in Heap: %d\n", h.size);
    printf("Extracting Top Bidders in descending order via heap_extract_max():\n");

    HeapBid top;
    int rank = 1;
    while (heap_extract_max(&h, &top)) {
        printf(" -> Rank #%d: %s | Score: %d%% (Submission #%d)\n",
               rank++, top.company_name, top.score, top.submission_id);
    }
}