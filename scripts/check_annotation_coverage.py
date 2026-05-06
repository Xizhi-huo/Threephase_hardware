"""统计 services/ 目录的返回类型标注覆盖率。

口径：
- 排除 __init__ / __post_init__
- 排除 dunder 方法（__xxx__）
- 把 @property / @staticmethod / @classmethod 计入分母
- 私有方法（单下划线开头）计入分母

阈值：本轮目标 >= 90%
"""

from __future__ import annotations

import ast
import pathlib
import sys


def main(target: str = "services") -> int:
    total = 0
    with_ann = 0
    missing_locs: list[tuple[str, int, str]] = []

    for path in sorted(pathlib.Path(target).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name in ("__init__", "__post_init__"):
                continue
            if node.name.startswith("__") and node.name.endswith("__"):
                continue
            total += 1
            if node.returns is not None:
                with_ann += 1
            else:
                missing_locs.append((str(path), node.lineno, node.name))

    pct = 100 * with_ann / total if total else 0
    print(f"{target}/: {with_ann}/{total} = {pct:.1f}%")
    if pct < 90.0:
        print("Missing locations:")
        for path, lineno, name in missing_locs[:50]:
            print(f"  {path}:{lineno} :: {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
