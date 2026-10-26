#include <stdio.h>
int compute(int x) { int unused = x * 15; int dead = unused + 5; return x + 7; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
