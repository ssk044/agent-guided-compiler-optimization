#include <stdio.h>
int compute(int x) { int a = x * 8; int b = x * 8; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
