#include <stdio.h>
#include "ds.h"

int run_bfs_workflow(int adj[GRAPH_NODES][GRAPH_NODES], int start_node) {
    int visited[GRAPH_NODES] = {0};
    int queue[GRAPH_NODES];
    int front = 0, rear = 0;
    int reached_count = 0;

    visited[start_node] = 1;
    queue[rear++] = start_node;

    while (front < rear) {
        int curr = queue[front++];
        reached_count++;

        for (int neighbor = 0; neighbor < GRAPH_NODES; neighbor++) {
            if (adj[curr][neighbor] && !visited[neighbor]) {
                visited[neighbor] = 1;
                queue[rear++] = neighbor;
            }
        }
    }
    return reached_count;
}

int run_dfs_check(int adj[GRAPH_NODES][GRAPH_NODES], int node, int target, int visited[]) {
    if (node == target) return 1;
    visited[node] = 1;

    for (int neighbor = 0; neighbor < GRAPH_NODES; neighbor++) {
        if (adj[node][neighbor] && !visited[neighbor]) {
            if (run_dfs_check(adj, neighbor, target, visited)) return 1;
        }
    }
    return 0;
}

void demo_graph(void) {
    printf("\n--- Demonstration: Directed Graph (BFS & DFS Traversal) ---\n");
    // Adjacency Matrix: 0 -> 1 -> 2 -> 3
    int adj[GRAPH_NODES][GRAPH_NODES] = {
        {0, 1, 0, 0},
        {0, 0, 1, 0},
        {0, 0, 0, 1},
        {0, 0, 0, 0}
    };

    int reached = run_bfs_workflow(adj, 0);
    printf("BFS Traversal: Reached %d of %d procurement stages.\n", reached, GRAPH_NODES);

    int visited[GRAPH_NODES] = {0};
    int path_cleared = run_dfs_check(adj, 0, 3, visited);
    printf("DFS Path Verification (Stage 0 to Stage 3): %s\n",
           path_cleared ? "Continuous Path Verified" : "Pipeline Broken");
}
