#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ds.h"

// ----------------------------------------------------------------------------
// ENTERPRISE TIER CLASSIFICATION BST
// ----------------------------------------------------------------------------

BSTNode* insert_bst(BSTNode *root, int threshold, const char *label) {
    if (!root) {
        BSTNode *node = (BSTNode*)malloc(sizeof(BSTNode));
        node->turnover_threshold = threshold;
        strncpy(node->tier_label, label, 31);
        node->left = node->right = NULL;
        return node;
    }
    if (threshold < root->turnover_threshold)
        root->left = insert_bst(root->left, threshold, label);
    else if (threshold > root->turnover_threshold)
        root->right = insert_bst(root->right, threshold, label);
    return root;
}

BSTNode* find_best_tier(BSTNode *root, int turnover) {
    BSTNode *curr = root;
    BSTNode *best = NULL;
    while (curr) {
        if (turnover >= curr->turnover_threshold) {
            best = curr;
            curr = curr->right;
        } else {
            curr = curr->left;
        }
    }
    return best;
}

void free_bst(BSTNode *root) {
    if (!root) return;
    free_bst(root->left);
    free_bst(root->right);
    free(root);
}

// ----------------------------------------------------------------------------
// FEATURE 2: TENDER BUDGET BST & RANGE SEARCH TRAVERSAL
// ----------------------------------------------------------------------------

TenderBSTNode* insert_tender_bst(TenderBSTNode *root, int id, const char *title, const char *req, int budget) {
    if (!root) {
        TenderBSTNode *node = (TenderBSTNode*)malloc(sizeof(TenderBSTNode));
        if (!node) return NULL;
        node->id = id;
        strncpy(node->title, title, sizeof(node->title) - 1);
        node->title[sizeof(node->title) - 1] = '\0';
        strncpy(node->requirements, req, sizeof(node->requirements) - 1);
        node->requirements[sizeof(node->requirements) - 1] = '\0';
        node->budget = budget;
        node->left = node->right = NULL;
        return node;
    }

    if (budget < root->budget) {
        root->left = insert_tender_bst(root->left, id, title, req, budget);
    } else {
        root->right = insert_tender_bst(root->right, id, title, req, budget);
    }
    return root;
}

// In-Order Traversal with Range Pruning: O(log n + k)
int bst_range_search_json(TenderBSTNode *root, int min_val, int max_val, char *out, int max_len, int *first) {
    if (!root) return 0;
    int written = 0;

    // Prune left subtree if current budget is already <= min_val
    if (root->budget > min_val) {
        written += bst_range_search_json(root->left, min_val, max_val, out + written, max_len - written, first);
    }

    // Process current node if within range
    if (root->budget >= min_val && root->budget <= max_val) {
        char item[512];
        snprintf(item, sizeof(item), "%s{\"id\": %d, \"title\": \"%s\", \"requirements\": \"%s\", \"budget\": %d}",
                 (*first) ? "" : ", ", root->id, root->title, root->requirements, root->budget);
        *first = 0;

        int len = (int)strlen(item);
        if (written + len < max_len - 50) {
            strcat(out + written, item);
            written += len;
        }
    }

    // Prune right subtree if current budget is already >= max_val
    if (root->budget < max_val) {
        written += bst_range_search_json(root->right, min_val, max_val, out + written, max_len - written, first);
    }

    return written;
}

void free_tender_bst(TenderBSTNode *root) {
    if (!root) return;
    free_tender_bst(root->left);
    free_tender_bst(root->right);
    free(root);
}

// ----------------------------------------------------------------------------
// VIVA DEMO
// ----------------------------------------------------------------------------

void demo_trees(void) {
    printf("\n--- Demonstration: BST Range Search (Tender Budgets) ---\n");
    TenderBSTNode *root = NULL;
    root = insert_tender_bst(root, 1, "Supply of Laptops", "Turnover > 30L", 30);
    root = insert_tender_bst(root, 2, "Solar Panel Grid", "Turnover > 75L", 75);
    root = insert_tender_bst(root, 3, "School Food Grains", "Turnover > 50L", 50);
    root = insert_tender_bst(root, 4, "Highways Surveillance", "Turnover > 90L", 90);
    root = insert_tender_bst(root, 5, "Classroom Tablets", "Turnover > 20L", 20);

    printf("Built BST ordered by Tender Budget (Lakhs).\n");
    printf("Executing Range Search [40L to 80L] via In-Order Traversal...\n");

    char buffer[1024] = {0};
    int first = 1;
    bst_range_search_json(root, 40, 80, buffer, sizeof(buffer), &first);
    printf("Matched Tenders within range:\n[%s]\n", buffer);

    free_tender_bst(root);
}