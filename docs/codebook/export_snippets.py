"""Write the snippet list that the renderer turns into pictures.

A snippet longer than 42 lines is cut into parts. One picture per part keeps the
text large enough to read after the document scales it to the page width.

    python docs/codebook/export_snippets.py
"""

from __future__ import annotations

import json
from pathlib import Path

from codebook_model import entries

HERE = Path(__file__).resolve().parent
OUT = HERE / "render" / "snippets.json"
MAX_LINES = 42


def main() -> int:
    rows = []
    for row in entries():
        code_lines = row["code"]
        head = code_lines[0] if code_lines else ""
        verbatim = not ("signatures only" in head or "first 20 lines" in head)
        base_offset = (row["start"] - 1) if verbatim else 0
        chunks = [
            code_lines[index : index + MAX_LINES]
            for index in range(0, max(len(code_lines), 1), MAX_LINES)
        ]
        for part, chunk in enumerate(chunks, start=1):
            key = row["key"] if len(chunks) == 1 else f"{row['key']}-p{part}"
            rows.append(
                {
                    "key": key,
                    "name": row["name"],
                    "file": row["file"],
                    "start": row["start"],
                    "end": row["end"],
                    "lang": row["lang"],
                    "code": "\n".join(chunk),
                    "part": part,
                    "parts": len(chunks),
                    "offset": base_offset + (part - 1) * MAX_LINES,
                }
            )

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    split = sum(1 for row in rows if row["parts"] > 1)
    print(f"wrote {OUT} · {len(rows)} pictures from {len(entries())} entries ({split} split)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
