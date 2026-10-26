#include <stdio.h>
int compute(int x) { if (x > 16) { int y = x * 8; return y; } else { return x + 7; } }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
