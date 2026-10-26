#include <stdio.h>
int compute(int x) { int a = x * 13; int b = x * 13; return a + b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
