#ifndef DS_H
#define DS_H

#define MAX_DESC 128
#define HASH_SIZE 11
#define GRAPH_NODES 4
#define MAX_HEAP_SIZE 100

// ============================================================================
// 1. SINGLY LINKED LIST: TENDER DIRECTORY & DELETION
// ============================================================================

typedef struct TenderNode {
    int id;
    char title[128];
    char requirements[256];
    struct TenderNode *next;
} TenderNode;

TenderNode* append_tender_node(TenderNode *head, int id, const char *title, const char *req);
TenderNode* delete_tender_node(TenderNode *head, int id, int *deleted_flag);
void tender_list_to_json(TenderNode *head, char *out, int max_len);
void free_tender_list(TenderNode *head);
void demo_linked_lists(void);

typedef struct ViolationNode {
    char reason[MAX_DESC];
    struct ViolationNode *next;
} ViolationNode;

ViolationNode* add_violation(ViolationNode *head, const char *msg);
void free_violations(ViolationNode *head);

// ============================================================================
// 2. QUEUE: FIFO BID PROCESSING
// ============================================================================

typedef struct BidNode {
    int submission_id;
    char company_name[64];
    char tender_title[128];
    struct BidNode *next;
} BidNode;

typedef struct {
    BidNode *front;
    BidNode *rear;
    int count;
} BidQueue;

void init_bid_queue(BidQueue *q);
void enqueue_bid(BidQueue *q, int sub_id, const char *company, const char *tender);
int dequeue_bid(BidQueue *q, BidNode *out_bid);
void free_bid_queue(BidQueue *q);

typedef struct {
    char name[MAX_DESC];
    int required_val;
    int submitted_val;
    int weight;
} Clause;

typedef struct {
    Clause items[10];
    int front, rear, count;
} ClauseQueue;

void init_queue(ClauseQueue *q);
void enqueue(ClauseQueue *q, const char *name, int req, int sub, int weight);
int dequeue(ClauseQueue *q, Clause *out);
void demo_queue(void);

// ============================================================================
// 3. STACK & ARRAYS
// ============================================================================

typedef struct {
    char logs[10][MAX_DESC];
    int top;
} AuditStack;

void init_stack(AuditStack *s);
void push_audit(AuditStack *s, const char *msg);
void demo_stack(void);

int compute_weighted_score(const int scores[], const int weights[], int size);
void demo_array(void);

// ============================================================================
// 4. TREE DATA STRUCTURES: BINARY SEARCH TREE (BST RANGE FILTER)
// ============================================================================

typedef struct BSTNode {
    int turnover_threshold;
    char tier_label[32];
    struct BSTNode *left;
    struct BSTNode *right;
} BSTNode;

BSTNode* insert_bst(BSTNode *root, int threshold, const char *label);
BSTNode* find_best_tier(BSTNode *root, int turnover);
void free_bst(BSTNode *root);
void demo_trees(void);

// Tender BST for Range Search
typedef struct TenderBSTNode {
    int id;
    char title[128];
    char requirements[256];
    int budget;
    struct TenderBSTNode *left;
    struct TenderBSTNode *right;
} TenderBSTNode;

TenderBSTNode* insert_tender_bst(TenderBSTNode *root, int id, const char *title, const char *req, int budget);
int bst_range_search_json(TenderBSTNode *root, int min_val, int max_val, char *out, int max_len, int *first);
void free_tender_bst(TenderBSTNode *root);

// ============================================================================
// 5. PRIORITY QUEUE / BINARY MAX-HEAP (LEADERBOARD)
// ============================================================================

typedef struct {
    int submission_id;
    char company_name[64];
    char tender_title[128];
    int score;
} HeapBid;

typedef struct {
    HeapBid items[MAX_HEAP_SIZE];
    int size;
} MaxHeap;

void heap_init(MaxHeap *h);
void heap_insert(MaxHeap *h, int sub_id, const char *company, const char *tender, int score);
int heap_extract_max(MaxHeap *h, HeapBid *out);
void demo_heap(void);

// ============================================================================
// 6. HASHING & GRAPH
// ============================================================================

typedef struct HashEntry {
    char key[32];
    int is_valid;
    struct HashEntry *next;
} HashEntry;

typedef struct {
    HashEntry *buckets[HASH_SIZE];
} HashTable;

void hash_insert(HashTable *ht, const char *key, int is_valid);
int hash_lookup(HashTable *ht, const char *key);
void free_hash_table(HashTable *ht);
void demo_hashing(void);

int run_bfs_workflow(int adj[GRAPH_NODES][GRAPH_NODES], int start_node);
int run_dfs_check(int adj[GRAPH_NODES][GRAPH_NODES], int node, int target, int visited[]);
void demo_graph(void);

int process_tender(const char *input, char *output, int output_size);

#endif