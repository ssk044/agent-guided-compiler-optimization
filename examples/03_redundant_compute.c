#include <stdio.h>

int redundant_expressions(int n) {
    int sum = 0;
    int k = 128 / 4; // Constant: 32

    for (int i = 0; i < n; i++) {
        // Common subexpressions: (i * 16) calculated multiple times
        int t1 = i * 16;
        int t2 = i * 16;
        int t3 = t1 + t2;
        // Strength reduction: mul by 2, mul by 0, add 0
        int s1 = t3 * 2;
        int s2 = s1 * 1;
        int s3 = s2 + 0;
        sum += s3 + k;
    }
    return sum;
}

int main(int argc, char* argv[]) {
    int n = 50000;
    if (argc > 1) {
        int parsed = 0;
        char* p = argv[1];
        while (*p >= '0' && *p <= '9') {
            parsed = parsed * 10 + (*p - '0');
            p++;
        }
        if (parsed > 0) n = parsed;
    }
    int res = redundant_expressions(n);
    printf("Redundant compute sum: %d\n", res);
    return 0;
}
