"""Tách file jobshop1.txt của OR-Library thành một file cho mỗi instance."""
from __future__ import annotations
import argparse
import re
from pathlib import Path


def split_instances(text: str) -> dict[str, str]:
    chunks = re.split(r"(?m)^\s*instance\s+(\w+)\s*$", text)
    result = {}
    for name, block in zip(chunks[1::2], chunks[2::2]):
        lines = block.splitlines()
        for i, line in enumerate(lines):
            if re.fullmatch(r"\s*\d+\s+\d+\s*", line):
                nj, nm = map(int, line.split())
                rows = [s.strip() for s in lines[i + 1:i + 1 + nj]]
                if len(rows) != nj or any(len(r.split()) != 2 * nm for r in rows):
                    raise ValueError(f"Invalid instance {name}")
                result[name] = f"{nj} {nm}\n" + "\n".join(rows) + "\n"
                break
        else:
            raise ValueError(f"Missing dimensions: {name}")
    if not result:
        raise ValueError("No 'instance NAME' blocks found")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path, default=Path("data"))
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    items = split_instances(args.source.read_text(encoding="utf-8-sig"))
    for name, text in items.items():
        (args.output / f"{name}.txt").write_text(text, encoding="utf-8")
    print(f"Imported {len(items)} instances")


if __name__ == "__main__":
    main()
