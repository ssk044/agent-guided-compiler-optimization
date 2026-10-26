#include <stdio.h>
int compute(int x) { int a = x * 17; int b = x * 17; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
