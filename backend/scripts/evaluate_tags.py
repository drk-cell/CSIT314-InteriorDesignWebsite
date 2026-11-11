"""Measure the tag analyser against the COCO 2017 validation set.

Ground truth is the COCO instance annotation. An image counts as **interior**
when it carries at least one furniture class, and every emitted object tag that
COCO also labels is checked against that annotation. So precision, recall and
the false-positive rate on non-interior photos are measured, not assumed.

Data, fetched once into the folder you name:

    annotations/instances_val2017.json   from annotations_trainval2017.zip
    images/<id>.jpg                       from images.cocodataset.org

Usage, from the repository root:

    backend/.venv/Scripts/python.exe backend/scripts/evaluate_tags.py --limit 200

The script writes ``tag-evaluation.json`` next to the data folder and prints a
summary. Two honest limits: COCO does not annotate every object in a frame, so a
correct tag on an unlabelled chair counts against precision, and COCO has no
class for a desk, a wardrobe or a bookshelf, so those tags are skipped rather
than guessed.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from app.services.object_labels import read  # noqa: E402

IMAGE_URL = "http://images.cocodataset.org/val2017/{name}"

# Catalogue tag -> COCO class. Only the tags COCO can verify are measured.
TAG_TO_COCO: dict[str, str] = {
    "sofa": "couch",
    "dining table": "dining table",
    "bed": "bed",
    "chair": "chair",
    "toilet": "toilet",
    "microwave": "microwave",
    "refrigerator": "refrigerator",
    "stove": "oven",
    "vase": "vase",
    "plant pot": "potted plant",
    "clock": "clock",
    "bench": "bench",
}

# A photo with one of these is a room, a shop or a shelf: furniture is present.
FURNITURE: set[str] = {
    "bench",
    "chair",
    "couch",
    "dining table",
    "bed",
    "toilet",
    "tv",
    "microwave",
    "oven",
    "sink",
    "refrigerator",
    "clock",
    "vase",
    "potted plant",
    "book",
}

# What the reviewer will upload instead of a design: animals, people, vehicles.
FOREIGN: set[str] = {
    "person",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "bird",
    "car",
    "truck",
    "bus",
    "motorcycle",
    "bicycle",
    "airplane",
    "boat",
    "banana",
    "apple",
    "orange",
    "sandwich",
    "pizza",
    "cake",
    "sports ball",
}

GATES: tuple[float, ...] = (0.0, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30)


@dataclass
class Sample:
    """One evaluated photo."""

    image_id: str
    file_name: str
    group: str
    present: set[str]
    tags: list[str]
    top_label: str
    top_probability: float
    interior_probability: float
    subject: str
    ms: float


def load_ground_truth(path: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Return image id -> class names, and image id -> file name."""
    data = json.loads(path.read_text(encoding="utf-8"))
    categories = {entry["id"]: entry["name"] for entry in data["categories"]}
    images = {entry["id"]: entry["file_name"] for entry in data["images"]}
    found: dict[int, set[str]] = {}
    for annotation in data["annotations"]:
        found.setdefault(annotation["image_id"], set()).add(
            categories[annotation["category_id"]]
        )
    return {str(key): sorted(value) for key, value in found.items()}, {
        str(key): value for key, value in images.items()
    }


def choose(
    labels: dict[str, list[str]], files: dict[str, str], limit: int
) -> tuple[list[tuple[str, str, set[str]]], list[tuple[str, str, set[str]]]]:
    """Split the set into interior and non-interior samples, seeded."""
    interior: list[tuple[str, str, set[str]]] = []
    foreign: list[tuple[str, str, set[str]]] = []
    for image_id, names in labels.items():
        if image_id not in files:
            continue
        found = set(names)
        if found & FURNITURE:
            interior.append((image_id, files[image_id], found))
        elif found & FOREIGN:
            foreign.append((image_id, files[image_id], found))
    random.Random(7).shuffle(interior)
    random.Random(11).shuffle(foreign)
    return interior[:limit], foreign[:limit]


def fetch(client: httpx.Client, folder: Path, file_name: str) -> Path | None:
    """Download one image once, and return the cached path."""
    target = folder / file_name
    if target.is_file() and target.stat().st_size > 0:
        return target
    try:
        response = client.get(IMAGE_URL.format(name=file_name), timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    target.write_bytes(response.content)
    return target


def measure(
    samples: list[tuple[str, str, set[str]]], group: str, folder: Path, client: httpx.Client
) -> list[Sample]:
    """Analyse the samples that have an image on disk."""
    results: list[Sample] = []
    for image_id, file_name, present in samples:
        path = fetch(client, folder, file_name)
        if path is None:
            continue
        data = path.read_bytes()
        start = time.perf_counter()
        reading = read(data)
        elapsed = (time.perf_counter() - start) * 1000
        if reading is None:
            continue
        results.append(
            Sample(
                image_id=image_id,
                file_name=file_name,
                group=group,
                present=present,
                tags=reading.tags,
                top_label=reading.top_label,
                top_probability=reading.top_probability,
                interior_probability=reading.interior_probability,
                subject=reading.subject,
                ms=elapsed,
            )
        )
    return results


def report(interior: list[Sample], foreign: list[Sample]) -> dict:
    """Build the numbers the decision needs."""
    measured = set(TAG_TO_COCO)
    per_tag: dict[str, dict[str, int]] = {
        tag: {"emitted": 0, "correct": 0, "present": 0, "found": 0} for tag in measured
    }

    for sample in interior + foreign:
        for tag in sample.tags:
            if tag not in measured:
                continue
            per_tag[tag]["emitted"] += 1
            if TAG_TO_COCO[tag] in sample.present:
                per_tag[tag]["correct"] += 1
    for sample in interior:
        for tag, coco in TAG_TO_COCO.items():
            if coco in sample.present:
                per_tag[tag]["present"] += 1
                if tag in sample.tags:
                    per_tag[tag]["found"] += 1

    covered = sum(1 for sample in interior if sample.tags)
    false_tags = sum(1 for sample in foreign if sample.tags)
    any_emitted = sum(per_tag[tag]["emitted"] for tag in measured)
    any_correct = sum(per_tag[tag]["correct"] for tag in measured)

    refused = sum(1 for sample in foreign if sample.subject == "other")
    wrongly_refused = sum(1 for sample in interior if sample.subject == "other")

    gates = []
    for gate in GATES:
        kept_interior = sum(
            1 for sample in interior if sample.interior_probability >= gate
        )
        kept_foreign = sum(
            1 for sample in foreign if sample.interior_probability >= gate
        )
        gates.append(
            {
                "gate": gate,
                "interior_kept": kept_interior,
                "interior_rate": round(kept_interior / max(1, len(interior)), 3),
                "foreign_kept": kept_foreign,
                "foreign_rate": round(kept_foreign / max(1, len(foreign)), 3),
            }
        )

    return {
        "interior_images": len(interior),
        "foreign_images": len(foreign),
        "coverage": round(covered / max(1, len(interior)), 3),
        "false_positive_rate": round(false_tags / max(1, len(foreign)), 3),
        "tag_precision": round(any_correct / max(1, any_emitted), 3),
        "refused_as_not_room": round(refused / max(1, len(foreign)), 3),
        "rooms_wrongly_refused": round(wrongly_refused / max(1, len(interior)), 3),
        "mean_ms": round(
            sum(sample.ms for sample in interior + foreign)
            / max(1, len(interior) + len(foreign)),
            1,
        ),
        "per_tag": {
            tag: {
                "precision": round(row["correct"] / max(1, row["emitted"]), 3),
                "recall": round(row["found"] / max(1, row["present"]), 3),
                "emitted": row["emitted"],
                "present": row["present"],
            }
            for tag, row in per_tag.items()
        },
        "gates": gates,
        "top_labels_interior": Counter(
            sample.top_label for sample in interior
        ).most_common(8),
        "top_labels_foreign": Counter(
            sample.top_label for sample in foreign
        ).most_common(8),
        "foreign_examples": [
            {
                "file": sample.file_name,
                "present": sorted(sample.present),
                "top": f"{sample.top_label} {sample.top_probability:.2f}",
                "tags": sample.tags,
                "interior": round(sample.interior_probability, 3),
            }
            for sample in foreign
            if sample.tags
        ][:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure tag generation on COCO val")
    parser.add_argument(
        "--data",
        default=os.environ.get(
            "COCO_EVAL", str(Path(os.environ.get("TEMP", ".")) / "coco-eval")
        ),
        help="folder holding annotations/ and images/",
    )
    parser.add_argument("--limit", type=int, default=150, help="images per group")
    parser.add_argument("--report", default=None, help="where to write the JSON")
    args = parser.parse_args()

    folder = Path(args.data)
    annotation_file = folder / "annotations" / "instances_val2017.json"
    if not annotation_file.is_file():
        print(f"Cannot find {annotation_file}")
        print("Download annotations_trainval2017.zip and unzip it here first.")
        return 1
    images_folder = folder / "images"
    images_folder.mkdir(parents=True, exist_ok=True)

    labels, files = load_ground_truth(annotation_file)
    interior_rows, foreign_rows = choose(labels, files, args.limit)
    print(
        f"interior {len(interior_rows)} of {sum(1 for v in labels.values() if set(v) & FURNITURE)}, "
        f"non-interior {len(foreign_rows)} of {sum(1 for v in labels.values() if set(v) & FOREIGN)}"
    )

    with httpx.Client(follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(
                pool.map(
                    lambda row: fetch(client, images_folder, row[1]),
                    interior_rows + foreign_rows,
                )
            )
        interior = measure(interior_rows, "interior", images_folder, client)
        foreign = measure(foreign_rows, "foreign", images_folder, client)

    summary = report(interior, foreign)
    text = json.dumps(summary, indent=1)
    target = Path(args.report) if args.report else folder / "tag-evaluation.json"
    target.write_text(text, encoding="utf-8")
    rows = [
        {
            "file": sample.file_name,
            "group": sample.group,
            "subject": sample.subject,
            "top_label": sample.top_label,
            "top_probability": round(sample.top_probability, 4),
            "interior_probability": round(sample.interior_probability, 4),
            "tags": sample.tags,
        }
        for sample in interior + foreign
    ]
    (folder / "tag-evaluation-rows.json").write_text(
        json.dumps(rows, indent=0), encoding="utf-8"
    )

    print()
    print(f"interior images analysed : {summary['interior_images']}")
    print(f"non-interior analysed    : {summary['foreign_images']}")
    print(f"coverage on rooms        : {summary['coverage']:.1%} get an object tag")
    print(f"tag precision (COCO)     : {summary['tag_precision']:.1%}")
    print(f"object tag on a non-room : {summary['false_positive_rate']:.1%} of photos")
    print(f"non-room refused         : {summary['refused_as_not_room']:.1%}")
    print(f"rooms wrongly refused    : {summary['rooms_wrongly_refused']:.1%}")
    print(f"mean analysis time       : {summary['mean_ms']} ms")
    print()
    print(f"{'tag':<14}{'prec':>7}{'recall':>8}{'emitted':>9}{'present':>9}")
    for tag, row in summary["per_tag"].items():
        if row["emitted"] or row["present"]:
            print(
                f"{tag:<14}{row['precision']:>7.2f}{row['recall']:>8.2f}"
                f"{row['emitted']:>9}{row['present']:>9}"
            )
    print()
    print(f"{'gate':>6}{'rooms kept':>13}{'non-rooms kept':>16}")
    for row in summary["gates"]:
        print(
            f"{row['gate']:>6.2f}{row['interior_rate']:>12.1%}"
            f"{row['foreign_rate']:>16.1%}"
        )
    print()
    print("top labels, rooms  :", summary["top_labels_interior"])
    print("top labels, others :", summary["top_labels_foreign"])
    print(f"\nreport: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
