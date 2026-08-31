#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Repair repeat metadata and optionally rename completed repeat-test folders.

Example dry run:

    PYTHONPATH=. python3 Scripts/repair_and_rename_repeat_folders.py \
        "/path/to/FreezerTest_Results" --dry-run --rename-folders

Apply:

    PYTHONPATH=. python3 Scripts/repair_and_rename_repeat_folders.py \
        "/path/to/FreezerTest_Results" --rename-folders

What it does:
    - Finds completed test folders containing test_summary.json
    - Infers repeat groups from folder names like:
          freezer_test_repeat_001_20260813_085456
          freezer_test_repeat_002_20260813_214500
    - Uses camera_id + start date as repeat_group_id:
          EV-0-0-002-TEC_2026-08-13
    - Optionally renames folders:
          freezer_test_repeat_001_20260813_085456
      to:
          EV-0-0-002-TEC_repeat_001_20260813_085456
"""

import argparse
import json
import re
from pathlib import Path


REPEAT_FOLDER_RE = re.compile(
    r"^(?P<base>.+)_repeat_(?P<index>\d+)_(?P<timestamp>\d{8}_\d{6})$"
)

SINGLE_FOLDER_RE = re.compile(
    r"^(?P<base>.+)_(?P<timestamp>\d{8}_\d{6})$"
)


def safe_name(value: str) -> str:
    text = str(value).strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    text = text.strip("_")
    return text or "unknown_camera"


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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def is_test_folder(path: Path) -> bool:
    return (path / "test_summary.json").exists()


def find_test_folders(root: Path) -> list[Path]:
    root = root.expanduser().resolve()

    if is_test_folder(root):
        return [root]

    return sorted({
        summary_path.parent
        for summary_path in root.rglob("test_summary.json")
    })


def parse_repeat_folder(path: Path):
    match = REPEAT_FOLDER_RE.match(path.name)

    if not match:
        return None

    return {
        "folder": path,
        "base": match.group("base"),
        "repeat_index": int(match.group("index")),
        "timestamp": match.group("timestamp"),
    }


def date_from_timestamp(timestamp: str) -> str:
    return f"{timestamp[0:4]}-{timestamp[4:6]}-{timestamp[6:8]}"


def read_camera_id(folder: Path) -> str:
    metadata = load_json(folder / "test_metadata.json")
    summary = load_json(folder / "test_summary.json")

    camera_id = metadata.get("camera_id") or summary.get("camera_id") or ""

    if not camera_id or camera_id == "unknown_camera":
        # Last-resort fallback: keep old base if camera_id is missing.
        parsed = parse_repeat_folder(folder)
        if parsed:
            camera_id = parsed["base"]
        else:
            camera_id = folder.name

    return safe_name(camera_id)


def build_groups(folders: list[Path]) -> list[list[dict]]:
    parsed = []

    for folder in folders:
        item = parse_repeat_folder(folder)
        if item is not None:
            parsed.append(item)

    parsed.sort(key=lambda x: (x["base"], x["timestamp"], x["repeat_index"]))

    groups = []
    current = []
    last_base = None
    last_index = None

    for item in parsed:
        starts_new = (
            not current
            or item["base"] != last_base
            or item["repeat_index"] == 1
            or (last_index is not None and item["repeat_index"] != last_index + 1)
        )

        if starts_new:
            if current:
                groups.append(current)
            current = [item]
        else:
            current.append(item)

        last_base = item["base"]
        last_index = item["repeat_index"]

    if current:
        groups.append(current)

    return groups


def update_metadata(folder: Path, new_folder: Path, repeat_group_id: str, repeat_start_date: str, repeat_index: int, repeat_count: int, dry_run: bool):
    metadata_path = folder / "test_metadata.json"
    summary_path = folder / "test_summary.json"

    metadata = load_json(metadata_path)
    summary = load_json(summary_path)

    camera_id = read_camera_id(folder)

    metadata["camera_id"] = camera_id
    metadata["repeat_group_id"] = repeat_group_id
    metadata["repeat_group_start_date"] = repeat_start_date
    metadata["repeat_index"] = repeat_index
    metadata["repeat_count"] = repeat_count

    summary["camera_id"] = camera_id
    summary["test_name"] = camera_id
    summary["repeat_group_id"] = repeat_group_id
    summary["repeat_group_start_date"] = repeat_start_date
    summary["repeat_index"] = repeat_index
    summary["repeat_count"] = repeat_count
    summary["test_root_dir"] = str(new_folder)

    if not dry_run:
        write_json(metadata_path, metadata)
        write_json(summary_path, summary)


def repair_group(group: list[dict], rename_folders: bool, dry_run: bool):
    group = sorted(group, key=lambda x: x["repeat_index"])
    first = group[0]

    first_folder = first["folder"]
    camera_id = read_camera_id(first_folder)
    repeat_start_date = date_from_timestamp(first["timestamp"])
    repeat_group_id = f"{camera_id}_{repeat_start_date}"
    repeat_count = len(group)

    print()
    print(f"Group: {repeat_group_id}")
    print(f"Count: {repeat_count}")

    planned_renames = []

    for item in group:
        old_folder = item["folder"]
        repeat_index = item["repeat_index"]
        timestamp = item["timestamp"]

        new_name = f"{camera_id}_repeat_{repeat_index:03d}_{timestamp}"
        new_folder = old_folder.parent / new_name

        planned_renames.append((old_folder, new_folder, item))

        print(f"  {old_folder.name} -> {new_folder.name}")

    # Check for collisions before writing anything.
    if rename_folders:
        for old_folder, new_folder, _ in planned_renames:
            if new_folder != old_folder and new_folder.exists():
                raise RuntimeError(f"Target folder already exists: {new_folder}")

    # Update metadata first, then rename folder.
    for old_folder, new_folder, item in planned_renames:
        final_folder = new_folder if rename_folders else old_folder

        update_metadata(
            folder=old_folder,
            new_folder=final_folder,
            repeat_group_id=repeat_group_id,
            repeat_start_date=repeat_start_date,
            repeat_index=item["repeat_index"],
            repeat_count=repeat_count,
            dry_run=dry_run,
        )

    if rename_folders and not dry_run:
        for old_folder, new_folder, _ in planned_renames:
            if new_folder != old_folder:
                old_folder.rename(new_folder)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--rename-folders", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    folders = find_test_folders(args.results_root)
    groups = build_groups(folders)

    if not groups:
        raise RuntimeError("No repeat folders found.")

    print(f"Found {len(groups)} repeat group(s).")

    for group in groups:
        repair_group(
            group=group,
            rename_folders=args.rename_folders,
            dry_run=args.dry_run,
        )

    if args.dry_run:
        print("\nDry run only. Nothing was changed.")
    else:
        print("\nRepair complete.")
        if args.rename_folders:
            print("Folders were renamed. Re-run analysis so CSV test_folder/test_path fields are fresh.")


if __name__ == "__main__":
    main()