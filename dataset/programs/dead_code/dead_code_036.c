#include <stdio.h>
int compute(int x) { int unused = x * 4; int dead = unused + 6; return x + 2; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
