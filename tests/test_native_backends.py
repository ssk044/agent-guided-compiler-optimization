"""Advanced syntax must compile through production backends without IR rewriting."""
import tempfile
from pathlib import Path

from src.compiler import compile_python
from src.compiler.c_backend import compile_native_c, execute_ir_pair


ADVANCED_C = r'''
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
typedef struct { int key; double value; } Item;
static int compare(const void *a, const void *b) {
    const Item *x = a, *y = b;
    return (x->key > y->key) - (x->key < y->key);
}
static int factorial(int n) { return n < 2 ? 1 : n * factorial(n - 1); }
int main(void) {
    Item *items = malloc(3 * sizeof *items);
    if (!items) return 1;
    items[0] = (Item){3, 9.0}; items[1] = (Item){1, 4.0}; items[2] = (Item){2, 16.0};
    qsort(items, 3, sizeof *items, compare);
    double total = 0;
    for (int i = 0; i < 3; i++) total += sqrt(items[i].value);
    printf("%d %.1f %d\n", items[0].key, total, factorial(5));
    free(items);
    return 0;
}
'''


def test_native_c_advanced_constructs_preserve_output():
    result = compile_native_c(ADVANCED_C)
    assert not result['custom_optimizer']
    assert result['verification_passed'] is None
    assert result['initial_ir'] and result['code']
    outputs = execute_ir_pair(result['initial_ir'], result['code'])
    assert all(execution.returncode == 0 for execution in outputs.values())
    assert outputs['before'].stdout == outputs['after'].stdout == '1 9.0 120\n'


def test_native_c_standard_input():
    result = compile_native_c('#include <stdio.h>\nint main(void){int x;if(scanf("%d",&x)!=1)return 1;printf("%d\\n",x*x);return 0;}')
    outputs = execute_ir_pair(result['initial_ir'], result['code'], '7\n')
    assert outputs['before'].stdout == outputs['after'].stdout == '49\n'


def test_python_advanced_syntax_and_nonexecution():
    source = '''from dataclasses import dataclass
from functools import lru_cache
@dataclass
class Value:
    number: int
@lru_cache(None)
def fib(n):
    return n if n < 2 else fib(n-1) + fib(n-2)
async def values():
    return [Value(fib(i)) for i in range(10)]
match Value(3):
    case Value(number=n) if n > 0:
        result = {i: i*i for i in range(n)}
raise RuntimeError("Compilation must not execute this")
'''
    result = compile_python(source, 0)
    assert result.pyc_bytes and 'fib' in result.bytecode_listing


def test_python_levels_are_explicit():
    source = '"module docs"\nassert False, "keep this by default"\n'
    normal = compile_python(source, 0)
    optimized = compile_python(source, 2)
    assert 'module docs' in normal.code_object.co_consts
    assert 'module docs' not in optimized.code_object.co_consts
    assert 'keep this by default' in normal.code_object.co_consts
    assert 'keep this by default' not in optimized.code_object.co_consts
