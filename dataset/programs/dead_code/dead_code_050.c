#include <stdio.h>
int compute(int x) { int unused = x * 18; int dead = unused + 9; return x + 2; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
