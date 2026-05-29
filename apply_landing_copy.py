from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


KEY_RE = re.compile(r"^\[([A-Za-z0-9_.-]+)\]\s*$")


def read_copy(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            result[current_key] = "\n".join(current_lines).strip()
        current_key = None
        current_lines = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        match = KEY_RE.match(line)
        if match:
            flush()
            current_key = match.group(1)
            continue
        if current_key is None:
            continue
        current_lines.append(raw_line)

    flush()
    return result


def render_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    return escaped.replace("\n", "<br />\n")


def apply_copy(index_path: Path, copy: dict[str, str]) -> tuple[int, list[str]]:
    source = index_path.read_text(encoding="utf-8")
    warnings: list[str] = []
    changed = 0

    for key, value in copy.items():
        pattern = re.compile(
            r"(<(?P<tag>[A-Za-z][A-Za-z0-9-]*)(?=[^>]*\bdata-copy-key=\""
            + re.escape(key)
            + r"\")[^>]*>)(?P<body>.*?)(</(?P=tag)>)",
            re.DOTALL,
        )

        def replace(match: re.Match[str]) -> str:
            nonlocal changed
            changed += 1
            return f"{match.group(1)}{render_text(value)}{match.group(4)}"

        source, count = pattern.subn(replace, source)
        if count == 0:
            warnings.append(f"key from copy file was not found in HTML: {key}")

    html_keys = set(re.findall(r'data-copy-key="([^"]+)"', source))
    missing = sorted(html_keys - set(copy))
    for key in missing:
        warnings.append(f"HTML key has no text in copy file: {key}")

    index_path.write_text(source, encoding="utf-8")
    return changed, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply landing-copy.txt texts to index.html.")
    parser.add_argument("--copy", default="landing-copy.txt", help="Path to copy text file.")
    parser.add_argument("--html", default="index.html", help="Path to landing HTML file.")
    args = parser.parse_args()

    copy_path = Path(args.copy)
    index_path = Path(args.html)
    copy = read_copy(copy_path)
    changed, warnings = apply_copy(index_path, copy)

    print(f"Updated {changed} text nodes in {index_path}.")
    for warning in warnings:
        print(f"Warning: {warning}")
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
