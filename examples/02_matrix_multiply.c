#include <stdio.h>

int matrix_trace_sim(int n) {
    int scale = 4 * 8; // Invariant constant scale factor: 32
    int bias = 100 - 50; // Constant: 50
    int total = 0;

    for (int i = 0; i < n; i++) {
        int row_weight = scale * 2; // Loop invariant: 64
        for (int j = 0; j < 100; j++) {
            int cell_calc = (i * 8) + (j * 4) + row_weight + bias;
            total += cell_calc;
        }
    }
    return total;
}

int main(int argc, char* argv[]) {
    int n = 2000;
    if (argc > 1) {
        int parsed = 0;
        char* p = argv[1];
        while (*p >= '0' && *p <= '9') {
            parsed = parsed * 10 + (*p - '0');
            p++;
        }
        if (parsed > 0) n = parsed;
    }
    int res = matrix_trace_sim(n);
    printf("Matrix trace: %d\n", res);
    return 0;
}
