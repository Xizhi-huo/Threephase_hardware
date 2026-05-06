from __future__ import annotations

import argparse
from pathlib import Path


EXCLUDED_DIRS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


def count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        yield path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report the largest Python source files in this repository."
    )
    parser.add_argument(
        "-n",
        "--top",
        type=int,
        default=5,
        help="Number of files to show. Default: 5.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    rows = []
    for path in iter_python_files(repo_root):
        rel_path = path.relative_to(repo_root)
        rows.append((count_lines(path), rel_path.as_posix()))

    rows.sort(key=lambda item: (-item[0], item[1]))

    print(f"Largest Python files under: {repo_root}")
    print(f"Top {args.top}")
    print("-" * 60)
    for idx, (line_count, rel_path) in enumerate(rows[: args.top], start=1):
        print(f"{idx:>2}. {line_count:>5}  {rel_path}")


if __name__ == "__main__":
    main()
