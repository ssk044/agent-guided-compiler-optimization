#include <stdio.h>
int compute(int x) { int unused = x * 17; int dead = unused + 7; return x + 2; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
