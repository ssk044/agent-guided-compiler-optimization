#include <stdio.h>
int compute(int x) { int a = x * 11; int b = x * 11; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
