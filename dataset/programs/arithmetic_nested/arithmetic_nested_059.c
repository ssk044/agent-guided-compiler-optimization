#include <stdio.h>
int compute(int x) { int a = (10 + 7) * (4 + 4); int b = a * 16; return b; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
