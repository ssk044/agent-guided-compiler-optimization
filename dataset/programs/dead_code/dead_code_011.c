#include <stdio.h>
int compute(int x) { int unused = x * 13; int dead = unused + 3; return x + 5; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
