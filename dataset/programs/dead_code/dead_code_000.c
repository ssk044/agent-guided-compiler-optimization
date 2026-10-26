#include <stdio.h>
int compute(int x) { int unused = x * 2; int dead = unused + 3; return x + 1; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
