#include <stdio.h>
int compute(int x) { int unused = x * 5; int dead = unused + 13; return x + 6; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
