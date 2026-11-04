"""Download freely licensed interior photographs for the demo.

Source: Wikimedia Commons, using the public MediaWiki API. Each file keeps its
author, licence and source page in photos.json so the report can credit it.

Run from the backend folder:

    .venv/Scripts/python.exe scripts/fetch_portfolio_photos.py
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "portfolio" / "photos"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "CSIT314-coursework/1.0 (student project; contact: glennangzx@gmail.com)"
TARGET = 16
MAX_PER_QUERY = 3

QUERIES = [
    ("living room interior", "Living Room", "living room"),
    ("bedroom interior design", "Bedroom", "bedroom"),
    ("kitchen interior design", "Kitchen", "kitchen"),
    ("dining room interior", "Dining Room", "dining room"),
    ("home office interior", "Home Office", "home office"),
    ("scandinavian interior", "Living Room", "interior"),
    ("minimalist interior", "Studio", "interior"),
    ("apartment living room", "Living Room", "living room"),
]

ALLOWED_SUFFIXES = (".jpg", ".jpeg", ".png")

# Commons search returns noise: fences, press photographs, museum paintings.
# A candidate is only kept when its file name names a room and avoids these.
NOISE_WORDS = (
    "fencing",
    "secretary",
    "minister",
    "podium",
    "portrait",
    "painting",
    "drawing",
    "stage design",
    "stage set",
    "design for a",
    "museum",
    "museu",
    "exhibition",
    "fair",
    "crowd",
    "construction",
    "demolish",
    "exterior",
    "street",
    "cathedral",
    "church",
    "castle",
    "cabin",
    "aircraft",
    "hostess",
    "car ",
    "train ",
)


def is_relevant(title: str, keyword: str) -> bool:
    """Return True when a Commons file name names the room and avoids noise."""
    lowered = title.lower()
    if keyword not in lowered:
        return False
    return not any(word in lowered for word in NOISE_WORDS)


def api_get(params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def search(term: str, limit: int = 15) -> list[dict]:
    payload = api_get(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{term} filetype:bitmap",
            "gsrnamespace": "6",
            "gsrlimit": str(limit),
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "iiurlwidth": "1000",
            "format": "json",
        }
    )
    return list((payload.get("query") or {}).get("pages", {}).values())


def licence_of(meta: dict) -> tuple[str, str, str]:
    """Return (author, licence name, licence url) from the Commons metadata."""
    def value(key: str) -> str:
        entry = meta.get(key) or {}
        return str(entry.get("value", "")).strip()

    author = value("Artist")
    if "<" in author:
        author = author.split("<")[0].strip() or "Unknown"
    name = value("LicenseShortName") or "See source page"
    url = value("LicenseUrl") or ""
    return author or "Unknown", name, url


def write_attribution(records: list[dict]) -> None:
    """Write ATTRIBUTION.md next to the photographs."""
    lines = [
        "# Photograph credits",
        "",
        "The images in this folder come from Wikimedia Commons. Each line names the",
        "author, the licence and the source page. The course report may cite this file.",
        "",
        "| File | Room | Author | Licence | Source |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            f"| {record['file']} | {record['title']} | {record['author']} "
            f"| {record['licence']} | {record['source']} |"
        )
    (OUTPUT.parent / "ATTRIBUTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    seen: set[str] = set()

    for term, room, keyword in QUERIES:
        if len(records) >= TARGET:
            break
        try:
            pages = search(term)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"search failed for {term!r}: {exc}")
            continue

        for page in pages:
            if len(records) >= TARGET:
                break
            taken_here = sum(1 for record in records if record["query"] == term)
            if taken_here >= MAX_PER_QUERY:
                break
            if not is_relevant(page.get("title", ""), keyword):
                continue
            info = (page.get("imageinfo") or [{}])[0]
            thumb = info.get("thumburl", "")
            width = int(info.get("width", 0))
            if not thumb or width < 900:
                continue
            if not thumb.lower().split("?")[0].endswith(ALLOWED_SUFFIXES):
                continue
            if thumb in seen:
                continue
            seen.add(thumb)

            name = f"photo-{len(records) + 1:02d}{Path(thumb.split('?')[0]).suffix.lower()}"
            author, licence, licence_url = licence_of(info.get("extmetadata") or {})
            try:
                request = urllib.request.Request(
                    thumb, headers={"User-Agent": USER_AGENT}
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    (OUTPUT / name).write_bytes(response.read())
            except Exception as exc:  # noqa: BLE001 - report and continue
                print(f"download failed for {name}: {exc}")
                continue

            records.append(
                {
                    "file": f"photos/{name}",
                    "title": room,
                    "query": term,
                    "source": info.get("descriptionurl", ""),
                    "author": author,
                    "licence": licence,
                    "licence_url": licence_url,
                }
            )
            print(f"{name} <- {page.get('title', '')[:70]}")

    (OUTPUT.parent / "photos.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )
    write_attribution(records)
    print(f"wrote {len(records)} photographs and photos.json")


if __name__ == "__main__":
    main()