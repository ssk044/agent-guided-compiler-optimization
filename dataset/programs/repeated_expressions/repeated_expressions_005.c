#include <stdio.h>
int compute(int x) { int a = x * 7; int b = x * 7; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
