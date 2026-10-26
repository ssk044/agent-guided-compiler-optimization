#include <stdio.h>
int compute(int x) { int unused = x * 17; int dead = unused + 8; return x + 1; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
