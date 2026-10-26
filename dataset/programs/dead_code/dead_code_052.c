#include <stdio.h>
int compute(int x) { int unused = x * 3; int dead = unused + 11; return x + 4; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
