#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Analyze many repeated freezer-test cycles in one command.

Typical use:

    PYTHONPATH=. python3 Scripts/analyze_repeat_tests.py "/path/to/results_root"

This script:
    1. Finds test folders under the selected root.
    2. Runs Scripts/analyze_test_folder.py on each folder if needed.
    3. Loads each cycle's analysis/sweep_diagnostics.csv.
    4. Combines absolute spatial/spectral position data across cycles.
    5. Calculates position repeatability relative to the first repeat cycle
       at the same sweep index.

Output:

    <results_root>/repeat_analysis/
        combined_sweep_diagnostics.csv
        position_repeatability_by_sweep.csv
        cycle_start_position_repeatability.csv
        cycle_start_spectral_position_delta.png
        cycle_start_spatial_position_delta.png
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


POSITION_COLUMNS = [
    "bp_780_peak_fit_y_px_mean",
    "bp_1064_peak_fit_y_px_mean",
    "bp_1550_peak_fit_y_px_mean",
    "no_filter_edge_gaussian_x_px_mean",
]


POSITION_LABELS = {
    "bp_780_peak_fit_y_px_mean": "780 nm line position Y [px]",
    "bp_1064_peak_fit_y_px_mean": "1064 nm line position Y [px]",
    "bp_1550_peak_fit_y_px_mean": "1550 nm line position Y [px]",
    "no_filter_edge_gaussian_x_px_mean": "Spatial edge position X [px]",
}


def load_json_if_exists(path: Path) -> dict:
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


def is_test_folder(path: Path) -> bool:
    return (
        (path / "test_summary.json").exists()
        and any(path.glob("sweep_*"))
    )


def find_test_folders(root: Path) -> list[Path]:
    root = root.expanduser().resolve()

    if is_test_folder(root):
        return [root]

    test_folders = []

    for summary_path in root.rglob("test_summary.json"):
        folder = summary_path.parent

        if is_test_folder(folder):
            test_folders.append(folder)

    return sorted(set(test_folders))


def infer_repeat_index(test_dir: Path, metadata: dict, summary: dict) -> int:
    for source in (metadata, summary):
        value = source.get("repeat_index")
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass

    match = re.search(r"_repeat_(\d+)_", test_dir.name)
    if match:
        return int(match.group(1))

    return 1


def safe_name(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    text = text.strip("_")
    return text or "unknown_camera"


def infer_repeat_group_id(test_dir: Path, metadata: dict, summary: dict) -> str:
    camera_id = safe_name(
        metadata.get("camera_id")
        or summary.get("camera_id")
        or "unknown_camera"
    )

    repeat_group_start_date = (
        metadata.get("repeat_group_start_date")
        or summary.get("repeat_group_start_date")
    )

    if repeat_group_start_date:
        return f"{camera_id}_{str(repeat_group_start_date)[:10]}"

    existing_group_id = (
        metadata.get("repeat_group_id")
        or summary.get("repeat_group_id")
    )

    if existing_group_id:
        existing_group_id = str(existing_group_id)

        match = re.search(r"(\d{4}-\d{2}-\d{2})", existing_group_id)
        if match:
            return f"{camera_id}_{match.group(1)}"

        match = re.search(r"(\d{8})(?:_\d{6})?", existing_group_id)
        if match:
            date_text = match.group(1)
            date_iso = f"{date_text[0:4]}-{date_text[4:6]}-{date_text[6:8]}"
            return f"{camera_id}_{date_iso}"

    match = re.search(r"_(?:repeat_\d+_)?(\d{8})_\d{6}$", test_dir.name)
    if match:
        date_text = match.group(1)
        date_iso = f"{date_text[0:4]}-{date_text[4:6]}-{date_text[6:8]}"
        return f"{camera_id}_{date_iso}"

    test_date = metadata.get("test_date") or summary.get("test_date")
    if test_date:
        return f"{camera_id}_{str(test_date)[:10]}"

    return f"{camera_id}_unknown_date"


def analyze_test_folder(test_dir: Path, force: bool = False):
    diagnostics_path = test_dir / "analysis" / "sweep_diagnostics.csv"

    if diagnostics_path.exists() and not force:
        print(f"Skipping existing analysis: {test_dir}")
        return

    print(f"Analyzing: {test_dir}")

    cmd = [
        sys.executable,
        "Scripts/analyze_test_folder.py",
        str(test_dir),
    ]

    subprocess.run(cmd, check=True)


def load_cycle_diagnostics(test_dir: Path) -> pd.DataFrame:
    diagnostics_path = test_dir / "analysis" / "sweep_diagnostics.csv"

    if not diagnostics_path.exists():
        raise FileNotFoundError(f"Missing diagnostics CSV: {diagnostics_path}")

    metadata = load_json_if_exists(test_dir / "test_metadata.json")
    summary = load_json_if_exists(test_dir / "test_summary.json")

    df = pd.read_csv(diagnostics_path)

    repeat_index = infer_repeat_index(test_dir, metadata, summary)
    repeat_group_id = infer_repeat_group_id(test_dir, metadata, summary)

    df["test_folder"] = test_dir.name
    df["test_path"] = str(test_dir)
    df["camera_id"] = metadata.get("camera_id", test_dir.name)
    df["test_date"] = metadata.get("test_date", "")
    df["repeat_index"] = repeat_index
    df["repeat_group_id"] = repeat_group_id

    return df


def add_repeatability_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each repeat group and each sweep_index, compare absolute position
    metrics to the first repeat cycle at that same sweep index.
    """
    df = df.copy()

    for col in POSITION_COLUMNS:
        if col not in df.columns:
            continue

        delta_col = f"{col}_repeat_delta_px"
        df[delta_col] = pd.NA

        group_cols = ["repeat_group_id", "sweep_index"]

        for _, group in df.groupby(group_cols, dropna=False):
            valid = group.dropna(subset=[col])

            if valid.empty:
                continue

            baseline_row = valid.sort_values(["repeat_index", "test_folder"]).iloc[0]
            baseline_value = baseline_row[col]

            df.loc[group.index, delta_col] = group[col] - baseline_value

    return df


def write_cycle_start_table(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    if "sweep_index" not in df.columns:
        return pd.DataFrame()

    first_sweep_index = int(df["sweep_index"].dropna().min())

    start_df = df[df["sweep_index"] == first_sweep_index].copy()
    start_df = start_df.sort_values(["repeat_group_id", "repeat_index", "test_folder"])

    output_path = output_dir / "cycle_start_position_repeatability.csv"
    start_df.to_csv(output_path, index=False)

    return start_df


def plot_cycle_start_repeatability(start_df: pd.DataFrame, output_dir: Path):
    if start_df.empty:
        return

    spectral_delta_cols = [
        "bp_780_peak_fit_y_px_mean_repeat_delta_px",
        "bp_1064_peak_fit_y_px_mean_repeat_delta_px",
        "bp_1550_peak_fit_y_px_mean_repeat_delta_px",
    ]

    spatial_delta_cols = [
        "no_filter_edge_gaussian_x_px_mean_repeat_delta_px",
    ]

    def plot_cols(cols, output_name, ylabel):
        available = [c for c in cols if c in start_df.columns]

        if not available:
            return

        plt.figure()

        for group_id, group_df in start_df.groupby("repeat_group_id"):
            group_df = group_df.sort_values("repeat_index")

            for col in available:
                plt.plot(
                    group_df["repeat_index"],
                    group_df[col],
                    marker="o",
                    label=f"{group_id}: {col}",
                )

        plt.axhline(0, linestyle="--", linewidth=1)
        plt.xlabel("Repeat cycle index")
        plt.ylabel(ylabel)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / output_name, dpi=200)
        plt.close()

    plot_cols(
        spectral_delta_cols,
        "cycle_start_spectral_position_delta.png",
        "Spectral line start-position delta vs cycle 1 [px]",
    )

    plot_cols(
        spatial_delta_cols,
        "cycle_start_spatial_position_delta.png",
        "Spatial edge start-position delta vs cycle 1 [px]",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "results_root",
        type=Path,
        help="Folder containing one or more freezer-test result folders.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run analyze_test_folder.py even if analysis exists.",
    )

    args = parser.parse_args()

    root = args.results_root.expanduser().resolve()
    test_folders = find_test_folders(root)

    if not test_folders:
        raise RuntimeError(f"No test folders found under: {root}")

    print(f"Found {len(test_folders)} test folders.")

    for test_dir in test_folders:
        analyze_test_folder(test_dir, force=args.force)

    frames = []

    for test_dir in test_folders:
        try:
            frames.append(load_cycle_diagnostics(test_dir))
        except Exception as e:
            print(f"Skipping {test_dir}: {e}")

    if not frames:
        raise RuntimeError("No diagnostics could be loaded.")

    combined = pd.concat(frames, ignore_index=True)
    combined = add_repeatability_deltas(combined)

    output_dir = root / "repeat_analysis"
    output_dir.mkdir(exist_ok=True)

    combined_path = output_dir / "combined_sweep_diagnostics.csv"
    repeatability_path = output_dir / "position_repeatability_by_sweep.csv"

    combined.to_csv(combined_path, index=False)
    combined.to_csv(repeatability_path, index=False)

    start_df = write_cycle_start_table(combined, output_dir)
    plot_cycle_start_repeatability(start_df, output_dir)

    print()
    print(f"Repeat analysis written to: {output_dir}")
    print(f"Combined diagnostics: {combined_path}")
    print(f"Position repeatability: {repeatability_path}")


if __name__ == "__main__":
    main()