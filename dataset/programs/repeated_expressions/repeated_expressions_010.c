#include <stdio.h>
int compute(int x) { int a = x * 12; int b = x * 12; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
