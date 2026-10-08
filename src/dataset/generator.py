"""Reproducible C benchmark generator (500 programs across seven categories)."""
from __future__ import annotations
import os
from pathlib import Path

CATEGORY_COUNTS = {
    "arithmetic_simple": 60, "arithmetic_nested": 60, "repeated_expressions": 60,
    "dead_code": 60, "loops": 80, "conditionals": 80, "mixed": 100,
}


class DatasetGenerator:
    def __init__(self, output_dir: str = "dataset/programs"):
        self.output_dir = Path(output_dir)

    def generate(self) -> list[str]:
        paths = []
        for category, count in CATEGORY_COUNTS.items():
            category_dir = self.output_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            for index in range(count):
                path = category_dir / f"{category}_{index:03d}.c"
                path.write_text(self._program(category, index), encoding="utf-8")
                paths.append(str(path))
        return paths

    def _program(self, category: str, n: int) -> str:
        a, b, c = n % 17 + 2, n % 11 + 3, n % 7 + 1
        body = {
            "arithmetic_simple": f"int value = {a} + {b}; int y = value * 8; return y;",
            "arithmetic_nested": f"int a = ({a} + {b}) * ({c} + 4); int b = a * 16; return b;",
            "repeated_expressions": f"int a = x * {a}; int b = x * {a}; return a + b;",
            "dead_code": f"int unused = x * {a}; int dead = unused + {b}; return x + {c};",
            "loops": (
                f"int sum = 0; for (int i=0; i<20; i++) {{ int k = {a} * 8; sum += x + k + i; }} return sum;"
                if n % 2 == 0 else
                f"int sum = 0; int i = 0; while (i < 20) {{ int k = {a} * 8; sum += x + k + i; i++; }} return sum;"
            ),
            "conditionals": f"if (x > {a}) {{ int y = x * 8; return y; }} else {{ return x + {b}; }}",
            "mixed": f"int t = {a}+{b}; int u = x*8; int v = x*8; int dead = t*4; if (x>{c}) return u+v+t; return x+t;",
        }[category]
        return f"#include <stdio.h>\nint compute(int x) {{ {body} }}\nint main(int argc, char **argv) {{ printf(\"%d\\n\", compute(argc)); return 0; }}\n"
