#include <stdio.h>
int compute(int x) { int a = x * 10; int b = x * 10; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
