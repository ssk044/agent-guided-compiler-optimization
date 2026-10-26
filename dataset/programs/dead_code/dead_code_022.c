#include <stdio.h>
int compute(int x) { int unused = x * 7; int dead = unused + 3; return x + 2; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
