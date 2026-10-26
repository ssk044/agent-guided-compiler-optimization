#include <stdio.h>
int compute(int x) { int a = (16 + 6) * (1 + 4); int b = a * 16; return b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
