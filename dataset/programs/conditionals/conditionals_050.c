#include <stdio.h>
int compute(int x) { if (x > 18) { int y = x * 8; return y; } else { return x + 9; } }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
