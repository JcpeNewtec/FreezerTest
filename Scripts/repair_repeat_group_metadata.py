#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Repair repeat_group_id metadata for already completed repeated freezer tests.

Typical use:

    PYTHONPATH=. python3 Scripts/repair_repeat_group_metadata.py "/path/to/results/root"

This script:
    - Finds test folders containing test_summary.json
    - Infers repeat_index and base repeat name from folder names like:
          TESTNAME_repeat_001_20260828_120000
    - Groups consecutive repeat folders by base name
    - Uses repeat_001 timestamp as the repeat_group_id anchor
    - Writes repeat_group_id, repeat_index, and repeat_count into test_metadata.json
      and test_summary.json

Use --dry-run first.
"""

import argparse
import json
import re
from pathlib import Path


REPEAT_FOLDER_RE = re.compile(
    r"^(?P<base>.+)_repeat_(?P<index>\d+)_(?P<timestamp>\d{8}_\d{6})$"
)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def is_test_folder(path: Path) -> bool:
    return (path / "test_summary.json").exists()


def parse_repeat_folder_name(path: Path):
    match = REPEAT_FOLDER_RE.match(path.name)

    if not match:
        return None

    return {
        "base": match.group("base"),
        "repeat_index": int(match.group("index")),
        "timestamp": match.group("timestamp"),
    }


def find_test_folders(root: Path) -> list[Path]:
    root = root.expanduser().resolve()

    if is_test_folder(root):
        return [root]

    folders = []

    for summary_path in root.rglob("test_summary.json"):
        folders.append(summary_path.parent)

    return sorted(set(folders))


def build_repeat_groups(test_folders: list[Path]):
    parsed = []

    for folder in test_folders:
        info = parse_repeat_folder_name(folder)

        if info is None:
            continue

        info["folder"] = folder
        parsed.append(info)

    parsed.sort(key=lambda x: (x["base"], x["timestamp"], x["repeat_index"]))

    groups = []
    current_group = []

    last_base = None
    last_index = None

    for item in parsed:
        base = item["base"]
        index = item["repeat_index"]

        starts_new_group = (
            not current_group
            or base != last_base
            or index == 1
            or (last_index is not None and index != last_index + 1)
        )

        if starts_new_group:
            if current_group:
                groups.append(current_group)

            current_group = [item]
        else:
            current_group.append(item)

        last_base = base
        last_index = index

    if current_group:
        groups.append(current_group)

    return groups


def repair_group(group: list[dict], dry_run: bool):
    first = sorted(group, key=lambda x: x["repeat_index"])[0]
    base = first["base"]
    anchor_timestamp = first["timestamp"]

    repeat_group_id = f"{base}_{anchor_timestamp}"
    repeat_count = len(group)

    print()
    print(f"Repeat group: {repeat_group_id}")
    print(f"Repeat count: {repeat_count}")

    for item in sorted(group, key=lambda x: x["repeat_index"]):
        folder = item["folder"]
        repeat_index = item["repeat_index"]

        print(f"  repeat {repeat_index:03d}: {folder}")

        metadata_path = folder / "test_metadata.json"
        summary_path = folder / "test_summary.json"

        metadata = load_json(metadata_path)
        summary = load_json(summary_path)

        metadata["repeat_group_id"] = repeat_group_id
        metadata["repeat_index"] = repeat_index
        metadata["repeat_count"] = repeat_count
        metadata["repeat_group_base"] = base

        summary["repeat_group_id"] = repeat_group_id
        summary["repeat_index"] = repeat_index
        summary["repeat_count"] = repeat_count
        summary["repeat_group_base"] = base

        if not dry_run:
            write_json(metadata_path, metadata)
            write_json(summary_path, summary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "results_root",
        type=Path,
        help="Root folder containing completed freezer-test folders.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed, but do not write files.",
    )

    args = parser.parse_args()

    test_folders = find_test_folders(args.results_root)
    groups = build_repeat_groups(test_folders)

    if not groups:
        raise RuntimeError("No repeat folders found.")

    print(f"Found {len(groups)} inferred repeat group(s).")

    for group in groups:
        repair_group(group, dry_run=args.dry_run)

    if args.dry_run:
        print()
        print("Dry run only. No files were changed.")
    else:
        print()
        print("Metadata repair complete.")


if __name__ == "__main__":
    main()