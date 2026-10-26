#include <stdio.h>
int compute(int x) { int a = x * 15; int b = x * 15; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
