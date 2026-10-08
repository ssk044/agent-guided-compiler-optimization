#include <stdio.h>

int compute_constants(int n) {
    // Compile-time constants
    int a = 10 * 5;          // Constant folding: 50
    int b = a + 2;           // Constant propagation & folding: 52
    int dead_var = 123 * 45; // Dead code
    int unused = dead_var + 10;
    
    int sum = 0;
    for (int i = 0; i < n; i++) {
        int inv = 16 * 4;    // Loop invariant & constant: 64
        sum += i + inv + b;
    }
    return sum;
}

int main(int argc, char* argv[]) {
    int n = 100000;
    if (argc > 1) {
        // Read simple arg if provided
        int parsed = 0;
        char* p = argv[1];
        while (*p >= '0' && *p <= '9') {
            parsed = parsed * 10 + (*p - '0');
            p++;
        }
        if (parsed > 0) n = parsed;
    }
    int res = compute_constants(n);
    printf("Result: %d\n", res);
    return 0;
}
