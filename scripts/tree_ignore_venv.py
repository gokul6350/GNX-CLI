from pathlib import Path
import sys

def walk(path: Path, prefix: str = "", depth: int = 0, max_depth: int = 3):
    if depth > max_depth:
        return
    entries = sorted([p for p in path.iterdir() if p.name != ".venv"], key=lambda e: e.name.lower())
    for idx, entry in enumerate(entries):
        connector = "└──" if idx == len(entries) - 1 else "├──"
        print(f"{prefix}{connector} {entry.name}")
        if entry.is_dir():
            extension = "    " if idx == len(entries) - 1 else "│   "
            walk(entry, prefix + extension, depth + 1, max_depth)

root = Path(".")
print(root.name or '.')
walk(root)
