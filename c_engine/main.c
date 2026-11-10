#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ds.h"

// Safe delimiter parser avoiding nested strtok corruption
TenderNode* parse_tenders_to_linked_list(const char *raw_data) {
    if (!raw_data || strlen(raw_data) == 0) return NULL;

    TenderNode *head = NULL;
    char buffer[8192];
    strncpy(buffer, raw_data, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    char *pos = buffer;
    while (pos && *pos) {
        char *next_entry = strstr(pos, ";;");
        if (next_entry) {
            *next_entry = '\0';
        }

        char *pipe1 = strchr(pos, '|');
        if (pipe1) {
            *pipe1 = '\0';
            char *title_start = pipe1 + 1;
            char *pipe2 = strchr(title_start, '|');
            if (pipe2) {
                *pipe2 = '\0';
                char *req_start = pipe2 + 1;
                int id = atoi(pos);
                head = append_tender_node(head, id, title_start, req_start);
            }
        }

        if (next_entry) {
            pos = next_entry + 2;
        } else {
            break;
        }
    }
    return head;
}

void parse_submissions_to_queue(BidQueue *q, const char *raw_data) {
    if (!raw_data || strlen(raw_data) == 0) return;

    char buffer[8192];
    strncpy(buffer, raw_data, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    char *pos = buffer;
    while (pos && *pos) {
        char *next_entry = strstr(pos, ";;");
        if (next_entry) {
            *next_entry = '\0';
        }

        char *pipe1 = strchr(pos, '|');
        if (pipe1) {
            *pipe1 = '\0';
            char *comp_start = pipe1 + 1;
            char *pipe2 = strchr(comp_start, '|');
            if (pipe2) {
                *pipe2 = '\0';
                char *tender_start = pipe2 + 1;
                int sub_id = atoi(pos);
                enqueue_bid(q, sub_id, comp_start, tender_start);
            }
        }

        if (next_entry) {
            pos = next_entry + 2;
        } else {
            break;
        }
    }
}

TenderBSTNode* parse_tenders_to_bst(const char *raw_data) {
    if (!raw_data || strlen(raw_data) == 0) return NULL;

    TenderBSTNode *root = NULL;
    char buffer[8192];
    strncpy(buffer, raw_data, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    char *pos = buffer;
    while (pos && *pos) {
        char *next_entry = strstr(pos, ";;");
        if (next_entry) *next_entry = '\0';

        char *pipe1 = strchr(pos, '|');
        if (pipe1) {
            *pipe1 = '\0';
            char *title_start = pipe1 + 1;
            char *pipe2 = strchr(title_start, '|');
            if (pipe2) {
                *pipe2 = '\0';
                char *req_start = pipe2 + 1;
                char *pipe3 = strchr(req_start, '|');
                if (pipe3) {
                    *pipe3 = '\0';
                    int budget = atoi(pipe3 + 1);
                    int id = atoi(pos);
                    root = insert_tender_bst(root, id, title_start, req_start, budget);
                }
            }
        }

        if (next_entry) pos = next_entry + 2;
        else break;
    }
    return root;
}

void parse_submissions_to_heap(MaxHeap *h, const char *raw_data) {
    if (!raw_data || strlen(raw_data) == 0) return;

    char buffer[8192];
    strncpy(buffer, raw_data, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    char *pos = buffer;
    while (pos && *pos) {
        char *next_entry = strstr(pos, ";;");
        if (next_entry) *next_entry = '\0';

        char *pipe1 = strchr(pos, '|');
        if (pipe1) {
            *pipe1 = '\0';
            char *comp_start = pipe1 + 1;
            char *pipe2 = strchr(comp_start, '|');
            if (pipe2) {
                *pipe2 = '\0';
                char *tender_start = pipe2 + 1;
                char *pipe3 = strchr(tender_start, '|');
                if (pipe3) {
                    *pipe3 = '\0';
                    int score = atoi(pipe3 + 1);
                    int sub_id = atoi(pos);
                    heap_insert(h, sub_id, comp_start, tender_start, score);
                }
            }
        }

        if (next_entry) pos = next_entry + 2;
        else break;
    }
}

int main(int argc, char *argv[]) {
    // Mode 1: Delete tender via C Linked List
    if (argc >= 4 && strcmp(argv[1], "delete_tender") == 0) {
        int target_id = atoi(argv[2]);
        TenderNode *head = parse_tenders_to_linked_list(argv[3]);

        int deleted_flag = 0;
        head = delete_tender_node(head, target_id, &deleted_flag);

        char json_out[8192] = {0};
        tender_list_to_json(head, json_out, sizeof(json_out));
        printf("{\"status\": \"%s\", \"deleted_id\": %d, %s\n",
               deleted_flag ? "SUCCESS" : "NOT_FOUND",
               target_id,
               json_out + 1);

        free_tender_list(head);
        return 0;
    }

    // Mode 2: Process next bid in FIFO Queue
    if (argc >= 3 && strcmp(argv[1], "process_queue") == 0) {
        BidQueue bq;
        init_bid_queue(&bq);
        parse_submissions_to_queue(&bq, argv[2]);

        BidNode next_bid;
        if (dequeue_bid(&bq, &next_bid)) {
            printf("{\"status\": \"SUCCESS\", \"dequeued_id\": %d, \"company_name\": \"%s\", \"tender_title\": \"%s\", \"remaining_in_queue\": %d}\n",
                   next_bid.submission_id,
                   next_bid.company_name,
                   next_bid.tender_title,
                   bq.count);
        } else {
            printf("{\"status\": \"EMPTY\", \"remaining_in_queue\": 0}\n");
        }

        free_bid_queue(&bq);
        return 0;
    }

    // Mode 3: Feature 2 - BST Range Filter
    if (argc >= 5 && strcmp(argv[1], "filter_bst") == 0) {
        int min_budget = atoi(argv[2]);
        int max_budget = atoi(argv[3]);
        TenderBSTNode *bst_root = parse_tenders_to_bst(argv[4]);

        char json_items[8192] = {0};
        int first = 1;
        bst_range_search_json(bst_root, min_budget, max_budget, json_items, sizeof(json_items), &first);

        printf("{\"status\": \"SUCCESS\", \"min\": %d, \"max\": %d, \"tenders\": [%s]}\n",
               min_budget, max_budget, json_items);

        free_tender_bst(bst_root);
        return 0;
    }

    // Mode 4: Feature 4 - Binary Max-Heap Leaderboard (Extracts all bids ordered high to low)
    if (argc >= 3 && strcmp(argv[1], "leaderboard_heap") == 0) {
        MaxHeap h;
        heap_init(&h);
        parse_submissions_to_heap(&h, argv[2]);

        char json_items[8192] = {0};
        int offset = 0;
        int rank = 1;
        HeapBid top;

        while (heap_extract_max(&h, &top) && rank <= 50) {
            offset += snprintf(json_items + offset, sizeof(json_items) - offset,
                "%s{\"rank\": %d, \"submission_id\": %d, \"company_name\": \"%s\", \"tender_title\": \"%s\", \"score\": %d}",
                (rank == 1) ? "" : ", ",
                rank, top.submission_id, top.company_name, top.tender_title, top.score);
            rank++;
        }

        printf("{\"status\": \"SUCCESS\", \"leaderboard\": [%s]}\n", json_items);
        return 0;
    }

    // Mode 5: Compliance checking via C engine
    if (argc > 1) {
        char output[4096] = {0};
        if (process_tender(argv[1], output, sizeof(output)) == 0) {
            printf("%s\n", output);
            return 0;
        } else {
            fprintf(stderr, "Error processing tender\n");
            return 1;
        }
    }

    // Mode 6: Interactive CLI Demo for Viva
    int choice;
    do {
        printf("\n==================================================\n");
        printf("    GeM BID DATA STRUCTURES ENGINE (VIVA DEMO)    \n");
        printf("==================================================\n");
        printf("1. Array (Weighted Compliance Score)\n");
        printf("2. Stack (LIFO Audit Trail)\n");
        printf("3. Queue (FIFO Bid Processing & Clauses)\n");
        printf("4. Singly Linked List (Tender Nodes & Unlinking)\n");
        printf("5. Binary Search Tree (Budget Range Search)\n");
        printf("6. Priority Queue / Binary Max-Heap (Leaderboard)\n");
        printf("7. Hashing (Exemption Code Lookup)\n");
        printf("8. Graph (BFS & DFS Pipeline Traversal)\n");
        printf("0. Exit\n");
        printf("Enter your choice: ");

        if (scanf("%d", &choice) != 1) {
            printf("Invalid input.\n");
            return 0;
        }

        switch (choice) {
            case 1: demo_array(); break;
            case 2: demo_stack(); break;
            case 3: demo_queue(); break;
            case 4: demo_linked_lists(); break;
            case 5: demo_trees(); break;
            case 6: demo_heap(); break;
            case 7: demo_hashing(); break;
            case 8: demo_graph(); break;
            case 0: printf("Exiting engine. Goodbye!\n"); break;
            default: printf("Invalid choice.\n");
        }
    } while (choice != 0);

    return 0;
}