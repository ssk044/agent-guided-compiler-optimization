#include <stdio.h>
int compute(int x) { int unused = x * 10; int dead = unused + 7; return x + 4; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
