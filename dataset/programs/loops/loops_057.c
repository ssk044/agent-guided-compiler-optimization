#include <stdio.h>
int compute(int x) { int sum = 0; int i = 0; while (i < 20) { int k = 8 * 8; sum += x + k + i; i++; } return sum; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
