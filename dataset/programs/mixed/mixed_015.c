#include <stdio.h>
int compute(int x) { int t = 17+7; int u = x*8; int v = x*8; int dead = t*4; if (x>2) return u+v+t; return x+t; }
int main(int argc, char **argv) { printf("%d\n", compute(argc)); return 0; }
