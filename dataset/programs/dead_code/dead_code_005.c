#include <stdio.h>
int compute(int x) { int unused = x * 7; int dead = unused + 8; return x + 6; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
