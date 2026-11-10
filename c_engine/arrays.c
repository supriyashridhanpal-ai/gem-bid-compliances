#include <stdio.h>
#include "ds.h"

int compute_weighted_score(const int scores[], const int weights[], int size) {
    int total_weighted = 0;
    int total_weights = 0;
    for (int i = 0; i < size; i++) {
        total_weighted += (scores[i] * weights[i]);
        total_weights += weights[i];
    }
    return total_weights ? (total_weighted / total_weights) : 0;
}

void demo_array(void) {
    printf("\n--- Demonstration: Array (Weighted Compliance Calculation) ---\n");
    int scores[3] = {100, 70, 100};
    int weights[3] = {40, 30, 30};
    int total = compute_weighted_score(scores, weights, 3);
    printf("Clauses Evaluated: 3\nCalculated Composite Score: %d%%\n", total);
}