"""Dataclasses, memoization, generators, async execution, and pattern matching."""
import asyncio
from dataclasses import dataclass
from functools import lru_cache

@dataclass(frozen=True)
class Result:
    index: int
    value: int

@lru_cache(maxsize=None)
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

async def calculate(count: int) -> list[Result]:
    await asyncio.sleep(0)
    return [Result(i, fibonacci(i)) for i in range(count)]

async def main() -> None:
    results = await calculate(10)
    for result in results:
        match result:
            case Result(index=i, value=value):
                print(f"fib({i}) = {value}")
    print("Total:", sum(result.value for result in results))

if __name__ == "__main__":
    asyncio.run(main())
