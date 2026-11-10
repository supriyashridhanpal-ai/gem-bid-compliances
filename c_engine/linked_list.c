#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ds.h"

// ----------------------------------------------------------------------------
// TENDER SINGLY LINKED LIST (CORE FEATURE)
// ----------------------------------------------------------------------------

TenderNode* append_tender_node(TenderNode *head, int id, const char *title, const char *req) {
    TenderNode *newNode = (TenderNode*)malloc(sizeof(TenderNode));
    if (!newNode) return head;

    newNode->id = id;
    strncpy(newNode->title, title, sizeof(newNode->title) - 1);
    newNode->title[sizeof(newNode->title) - 1] = '\0';
    strncpy(newNode->requirements, req, sizeof(newNode->requirements) - 1);
    newNode->requirements[sizeof(newNode->requirements) - 1] = '\0';
    newNode->next = NULL;

    if (!head) return newNode;

    TenderNode *curr = head;
    while (curr->next) {
        curr = curr->next;
    }
    curr->next = newNode;
    return head;
}

TenderNode* delete_tender_node(TenderNode *head, int id, int *deleted_flag) {
    *deleted_flag = 0;
    if (!head) return NULL;

    // Case 1: Target is the Head node
    if (head->id == id) {
        TenderNode *temp = head;
        head = head->next;
        free(temp);
        *deleted_flag = 1;
        return head;
    }

    // Case 2: Target is in the middle or at the tail
    TenderNode *prev = head;
    TenderNode *curr = head->next;

    while (curr) {
        if (curr->id == id) {
            prev->next = curr->next; // Unlink node by updating pointer
            free(curr);              // Free memory
            *deleted_flag = 1;
            return head;
        }
        prev = curr;
        curr = curr->next;
    }

    return head; // Not found
}

void tender_list_to_json(TenderNode *head, char *out, int max_len) {
    int offset = snprintf(out, max_len, "{\"tenders\": [");
    TenderNode *curr = head;

    while (curr && offset < max_len - 150) {
        offset += snprintf(out + offset, max_len - offset,
            "{\"id\": %d, \"title\": \"%s\", \"requirements\": \"%s\"}%s",
            curr->id, curr->title, curr->requirements, curr->next ? ", " : "");
        curr = curr->next;
    }
    snprintf(out + offset, max_len - offset, "]}");
}

void free_tender_list(TenderNode *head) {
    while (head) {
        TenderNode *temp = head;
        head = head->next;
        free(temp);
    }
}

// ----------------------------------------------------------------------------
// VIOLATION LIST (FOR COMPLIANCE ENGINE)
// ----------------------------------------------------------------------------

ViolationNode* add_violation(ViolationNode *head, const char *msg) {
    ViolationNode *newNode = (ViolationNode*)malloc(sizeof(ViolationNode));
    if (!newNode) return head;
    strncpy(newNode->reason, msg, MAX_DESC - 1);
    newNode->next = NULL;

    if (!head) return newNode;
    ViolationNode *curr = head;
    while (curr->next) curr = curr->next;
    curr->next = newNode;
    return head;
}

void free_violations(ViolationNode *head) {
    while (head) {
        ViolationNode *temp = head;
        head = head->next;
        free(temp);
    }
}

// ----------------------------------------------------------------------------
// VIVA DEMO
// ----------------------------------------------------------------------------

void demo_linked_lists(void) {
    printf("\n--- Demonstration: Singly Linked List (Tender Nodes & Unlinking) ---\n");
    TenderNode *list = NULL;
    list = append_tender_node(list, 101, "Supply of Laptops", "Turnover > 50L, Exp > 3 Yrs");
    list = append_tender_node(list, 102, "Cloud Hosting Service", "Turnover > 100L, ISO 27001");
    list = append_tender_node(list, 103, "CCTV Surveillance Installation", "Make in India, EMD Paid");

    printf("Initial Linked List:\n");
    TenderNode *curr = list;
    while (curr) {
        printf(" -> [Node #%d: %s]\n", curr->id, curr->title);
        curr = curr->next;
    }

    printf("\nDeleting Tender #102 via pointer manipulation (prev->next = curr->next)...\n");
    int deleted = 0;
    list = delete_tender_node(list, 102, &deleted);

    printf("Updated Linked List:\n");
    curr = list;
    while (curr) {
        printf(" -> [Node #%d: %s]\n", curr->id, curr->title);
        curr = curr->next;
    }
    free_tender_list(list);
}