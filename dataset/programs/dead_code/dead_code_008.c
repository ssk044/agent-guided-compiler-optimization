#include <stdio.h>
int compute(int x) { int unused = x * 10; int dead = unused + 11; return x + 2; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
