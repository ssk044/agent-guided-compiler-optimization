#include <stdio.h>
int compute(int x) { int a = x * 5; int b = x * 5; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
