#include <stdio.h>

int hoist_bench(int n) {
    int total = 0;
    int a = 15;
    int b = 35;

    for (int i = 0; i < n; i++) {
        // Invariant calculations repeated inside the loop:
        int inv1 = a * b;        // 15 * 35 = 525 (invariant)
        int inv2 = inv1 + 75;    // 600 (invariant)
        total += (i + inv2);
    }
    return total;
}

int main(int argc, char* argv[]) {
    int n = 80000;
    if (argc > 1) {
        int parsed = 0;
        char* p = argv[1];
        while (*p >= '0' && *p <= '9') {
            parsed = parsed * 10 + (*p - '0');
            p++;
        }
        if (parsed > 0) n = parsed;
    }
    int res = hoist_bench(n);
    printf("Hoist result: %d\n", res);
    return 0;
}
