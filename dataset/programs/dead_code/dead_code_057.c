#include <stdio.h>
int compute(int x) { int unused = x * 8; int dead = unused + 5; return x + 2; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
