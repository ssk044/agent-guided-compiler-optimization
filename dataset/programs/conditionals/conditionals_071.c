#include <stdio.h>
int compute(int x) { if (x > 5) { int y = x * 8; return y; } else { return x + 8; } }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
