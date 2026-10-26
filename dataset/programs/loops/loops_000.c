#include <stdio.h>
int compute(int x) { int sum = 0; for (int i=0; i<20; i++) { int k = 2 * 8; sum += x + k + i; } return sum; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
