"""Tiny YAML subset loader (mappings + scalars). No external deps."""

from __future__ import annotations

from pathlib import Path


def _parse_scalar(raw: str) -> object:
    value = raw.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in ("null", "~", ""):
        return None
    try:
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            return int(value)
        return float(value)
    except ValueError:
        return value


def load_yaml(path: Path) -> dict:
    """Parse a constrained YAML file into a nested dict.

    Supports:
      - top-level and nested mappings (2-space indent)
      - string / int / float / bool / null scalars
    Does not support lists, anchors, or multi-line strings.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]

    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            raise ValueError(f"{path}:{lineno}: expected key: value, got {raw_line!r}")
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if rest == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(rest)

    return root
