#include <stdio.h>
int compute(int x) { int unused = x * 6; int dead = unused + 3; return x + 7; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
