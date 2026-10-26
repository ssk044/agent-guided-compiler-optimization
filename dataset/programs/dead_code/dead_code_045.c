#include <stdio.h>
int compute(int x) { int unused = x * 13; int dead = unused + 4; return x + 4; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
