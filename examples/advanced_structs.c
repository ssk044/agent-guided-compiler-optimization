#include <stdio.h>
#include <stdlib.h>
#include <math.h>
typedef struct { int key; double value; } Item;
static int compare(const void *a, const void *b) {
    const Item *x = a, *y = b;
    return (x->key > y->key) - (x->key < y->key);
}
static int factorial(int n) { return n < 2 ? 1 : n * factorial(n - 1); }
int main(void) {
    Item *items = malloc(3 * sizeof *items);
    if (!items) return 1;
    items[0] = (Item){3, 9.0}; items[1] = (Item){1, 4.0}; items[2] = (Item){2, 16.0};
    qsort(items, 3, sizeof *items, compare);
    double total = 0;
    for (int i = 0; i < 3; i++) total += sqrt(items[i].value);
    printf("%d %.1f %d\n", items[0].key, total, factorial(5));
    free(items);
    return 0;
}
