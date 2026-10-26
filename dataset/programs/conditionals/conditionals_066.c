#include <stdio.h>
int compute(int x) { if (x > 17) { int y = x * 8; return y; } else { return x + 3; } }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
