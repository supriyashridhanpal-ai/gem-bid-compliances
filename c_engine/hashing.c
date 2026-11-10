#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ds.h"

static unsigned int hash_code(const char *key) {
    unsigned int h = 0;
    while (*key) h = (h * 31) + *key++;
    return h % HASH_SIZE;
}

void hash_insert(HashTable *ht, const char *key, int is_valid) {
    unsigned int idx = hash_code(key);
    HashEntry *entry = (HashEntry*)malloc(sizeof(HashEntry));
    strncpy(entry->key, key, 31);
    entry->is_valid = is_valid;
    entry->next = ht->buckets[idx];
    ht->buckets[idx] = entry;
}

int hash_lookup(HashTable *ht, const char *key) {
    unsigned int idx = hash_code(key);
    HashEntry *curr = ht->buckets[idx];
    while (curr) {
        if (strcmp(curr->key, key) == 0) return curr->is_valid;
        curr = curr->next;
    }
    return 0;
}

void free_hash_table(HashTable *ht) {
    for (int i = 0; i < HASH_SIZE; i++) {
        HashEntry *curr = ht->buckets[i];
        while (curr) {
            HashEntry *temp = curr;
            curr = curr->next;
            free(temp);
        }
        ht->buckets[i] = NULL;
    }
}

void demo_hashing(void) {
    printf("\n--- Demonstration: Hashing with Separate Chaining ---\n");
    HashTable ht = {0};
    hash_insert(&ht, "PAN_ACTIVE", 1);
    hash_insert(&ht, "GST_VERIFIED", 1);
    hash_insert(&ht, "MSME_EXEMPTION", 1);

    printf("Lookup 'GST_VERIFIED': %s (O(1) time)\n",
           hash_lookup(&ht, "GST_VERIFIED") ? "Found [VALID]" : "Not Found");
    printf("Lookup 'STARTUP_DIPP': %s (O(1) time)\n",
           hash_lookup(&ht, "STARTUP_DIPP") ? "Found [VALID]" : "Not Found");
    free_hash_table(&ht);
}