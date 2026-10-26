#include <stdio.h>
int compute(int x) { int unused = x * 4; int dead = unused + 12; return x + 5; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
