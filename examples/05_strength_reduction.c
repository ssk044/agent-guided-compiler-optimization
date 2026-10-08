#include <stdio.h>

int signal_filter(int n) {
    int filtered = 0;
    for (int i = 0; i < n; i++) {
        // Multiplications by powers of two & identities
        int val1 = i * 8;   // Can be lowered to i << 3
        int val2 = i * 32;  // Can be lowered to i << 5
        int val3 = i * 64;  // Can be lowered to i << 6
        int ident = val1 * 1; // Identity
        filtered += (val1 + val2 + val3 + ident);
    }
    return filtered;
}

int main(int argc, char* argv[]) {
    int n = 100000;
    if (argc > 1) {
        int parsed = 0;
        char* p = argv[1];
        while (*p >= '0' && *p <= '9') {
            parsed = parsed * 10 + (*p - '0');
            p++;
        }
        if (parsed > 0) n = parsed;
    }
    int res = signal_filter(n);
    printf("Filter output: %d\n", res);
    return 0;
}
