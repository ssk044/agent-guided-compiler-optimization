#include <stdio.h>
int compute(int x) { int value = 9 + 10; int y = value * 8; return y; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
