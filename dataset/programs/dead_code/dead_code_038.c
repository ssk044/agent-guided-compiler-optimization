#include <stdio.h>
int compute(int x) { int unused = x * 6; int dead = unused + 8; return x + 4; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
