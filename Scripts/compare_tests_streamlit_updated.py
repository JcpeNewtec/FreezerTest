#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interactive comparison viewer for freezer-test analysis results.

Run from the repository root with:

    streamlit run Scripts/compare_tests_streamlit.py

The app has two stages:

1. Browse test_metadata.json and test_summary.json only. This is intentionally
   lightweight and does not load sweep_metrics.csv / sweep_diagnostics.csv.
2. Tick individual tests or complete repeat groups and click
   "Load checked data". Only then are the analysis CSV files loaded.

Expected input structure:

    <results_root>/
        <test_folder_1>/
            test_metadata.json
            test_summary.json
            analysis/
                sweep_metrics.csv
        <test_folder_2>/
            analysis/
                sweep_metrics.csv
"""

from pathlib import Path
import json
from datetime import date
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


DEFAULT_RESULTS_ROOT = "/home/jcpe/Documents/Projects /FreezerTestSetup/Test_Results"


METRIC_LABELS = {
    "sweep_index": "Sweep index",
    "repeat_index": "Repeat cycle index",
    "temp_probe_1_c": "Probe 1 temperature [C]",
    "temp_probe_2_c": "Probe 2 temperature [C]",
    "temp_probe_3_c": "Probe 3 temperature [C]",
    "temp_probe_4_c": "Probe 4 temperature [C]",
    "temp_probe_5_c": "Probe 5 temperature [C]",

    "bp_780_fwhm_px_mean": "780 nm spectral FWHM [px]",
    "bp_1064_fwhm_px_mean": "1064 nm spectral FWHM [px]",
    "bp_1550_fwhm_px_mean": "1550 nm spectral FWHM [px]",

    "bp_780_fwhm_px_mean_delta": "780 nm spectral FWHM change [px]",
    "bp_1064_fwhm_px_mean_delta": "1064 nm spectral FWHM change [px]",
    "bp_1550_fwhm_px_mean_delta": "1550 nm spectral FWHM change [px]",

    "bp_780_peak_fit_y_px_mean_delta": "780 nm spectral line shift [px]",
    "bp_1064_peak_fit_y_px_mean_delta": "1064 nm spectral line shift [px]",
    "bp_1550_peak_fit_y_px_mean_delta": "1550 nm spectral line shift [px]",
    "bp_780_peak_fit_y_px_mean_repeat_delta_px": "780 nm return error [px]",
    "bp_1064_peak_fit_y_px_mean_repeat_delta_px": "1064 nm return error [px]",
    "bp_1550_peak_fit_y_px_mean_repeat_delta_px": "1550 nm return error [px]",
    "no_filter_edge_gaussian_x_px_mean_repeat_delta_px": "Spatial edge return error [px]",

    "no_filter_lsf_gaussian_fwhm_px_mean": "Spatial FWHM [px]",
    "no_filter_edge_gaussian_x_px_mean_delta": "Spatial edge shift [px]",

    "no_filter_signal_signal_mean_mean": "No-filter signal mean [DN]",
    "no_filter_signal_signal_mean_mean_delta": "No-filter signal change [DN]",
    "no_filter_signal_signal_std_mean": "No-filter signal std [DN]",
    "dark_noise_dark_mean_mean": "Dark-region mean level [DN]",
    "dark_noise_noise_std_mean": "Dark-region noise std [DN]",
    "dark_noise_noise_std_std": "Dark-region noise std ROI variation [DN]",
}


X_AXIS_OPTIONS = [
    "sweep_index",
    "temp_probe_1_c",
    "temp_probe_2_c",
    "temp_probe_3_c",
    "temp_probe_4_c",
    "temp_probe_5_c",
]


PREFERRED_CUSTOM_METRICS = [
    "bp_780_fwhm_px_mean",
    "bp_1064_fwhm_px_mean",
    "bp_1550_fwhm_px_mean",
    "bp_780_fwhm_px_mean_delta",
    "bp_1064_fwhm_px_mean_delta",
    "bp_1550_fwhm_px_mean_delta",
    "bp_780_peak_fit_y_px_mean_delta",
    "bp_1064_peak_fit_y_px_mean_delta",
    "bp_1550_peak_fit_y_px_mean_delta",
    "no_filter_lsf_gaussian_fwhm_px_mean",
    "no_filter_edge_gaussian_x_px_mean_delta",
    "no_filter_signal_signal_mean_mean",
    "dark_noise_noise_std_mean",
    "dark_noise_dark_mean_mean",
]


REPEAT_POSITION_COLUMNS = [
    "bp_780_peak_fit_y_px_mean",
    "bp_1064_peak_fit_y_px_mean",
    "bp_1550_peak_fit_y_px_mean",
    "no_filter_edge_gaussian_x_px_mean",
]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def label_for_column(column: str) -> str:
    if column in METRIC_LABELS:
        return METRIC_LABELS[column]

    if column.startswith("camera_internal_") and column.endswith("_c"):
        label = column.removeprefix("camera_internal_").removesuffix("_c")
        label = label.replace("before_capture_", "Before capture: ")
        label = label.replace("after_capture_", "After capture: ")
        label = label.replace("_", " ")
        return f"Camera internal {label} [C]"

    return column


def safe_name(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    text = text.strip("_")
    return text or "unknown_camera"


def is_missing(value) -> bool:
    """Return True for None, empty strings, NaN, and pandas NA."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def infer_repeat_index_from_name(test_name: str) -> int:
    match = re.search(r"_repeat_(\d+)_", test_name)
    if match:
        return int(match.group(1))
    return 1


def infer_repeat_group_id(test_name: str, metadata: dict) -> str:
    """
    Return repeat group ID as CAMERA_ID_YYYY-MM-DD.

    Preferred source:
        metadata["repeat_group_start_date"]

    Fallbacks:
        - existing repeat_group_id containing a date
        - folder timestamp
        - test_date
    """
    camera_id = safe_name(metadata.get("camera_id") or "unknown_camera")

    repeat_group_start_date = metadata.get("repeat_group_start_date")
    if repeat_group_start_date:
        return f"{camera_id}_{str(repeat_group_start_date)[:10]}"

    existing_group_id = metadata.get("repeat_group_id")
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

    match = re.search(r"_(?:repeat_\d+_)?(\d{8})_\d{6}$", test_name)
    if match:
        date_text = match.group(1)
        date_iso = f"{date_text[0:4]}-{date_text[4:6]}-{date_text[6:8]}"
        return f"{camera_id}_{date_iso}"

    test_date = metadata.get("test_date")
    if test_date:
        return f"{camera_id}_{str(test_date)[:10]}"

    return f"{camera_id}_unknown_date"


# -----------------------------------------------------------------------------
# Lightweight catalog loading: JSON only, no analysis CSVs
# -----------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def find_metric_files(results_root: str) -> list[str]:
    root = Path(results_root).expanduser()

    if not root.exists():
        return []

    metric_files = sorted(root.glob("**/analysis/sweep_metrics.csv"))
    return [str(path) for path in metric_files]


def default_metadata(test_dir: Path) -> dict:
    return {
        "camera_id": test_dir.name,
        "test_date": "",
        "test_duration_hours": None,
        "operator": "",
        "notes": "",
    }


@st.cache_data(show_spinner=False)
def load_test_summary(test_dir_string: str) -> dict:
    test_dir = Path(test_dir_string)
    summary_path = test_dir / "test_summary.json"

    if not summary_path.exists():
        return {}

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        return {"summary_error": str(e)}


@st.cache_data(show_spinner=False)
def load_test_metadata(test_dir_string: str) -> dict:
    """
    Load user metadata and lightly backfill missing fields from test_summary.json.

    This function intentionally does not touch sweep_metrics.csv.
    """
    test_dir = Path(test_dir_string)
    metadata_path = test_dir / "test_metadata.json"
    summary = load_test_summary(str(test_dir))

    metadata = default_metadata(test_dir)
    user_metadata = {}

    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                user_metadata = loaded
                metadata.update(user_metadata)
        except Exception as e:
            metadata["metadata_error"] = str(e)

    # Backfill useful fields from summary only when the metadata file did not
    # explicitly provide them.
    if not user_metadata.get("camera_id") and summary.get("camera_id"):
        metadata["camera_id"] = summary.get("camera_id")

    if not user_metadata.get("test_date"):
        for key in ("start_time", "measurement_start_time", "folder_created_at"):
            if summary.get(key):
                metadata["test_date"] = str(summary[key]).split("T")[0]
                break

    if user_metadata.get("test_duration_hours") is None:
        metadata["test_duration_hours"] = summary.get(
            "test_duration_hours",
            metadata.get("test_duration_hours"),
        )

    for key in (
        "repeat_index",
        "repeat_count",
        "repeat_group_id",
        "repeat_group_start_date",
    ):
        if user_metadata.get(key) in (None, "") and summary.get(key) not in (None, ""):
            metadata[key] = summary.get(key)

    return metadata


def build_catalog_row(test_name: str, metric_path: str) -> dict:
    """Build one browser row using only metadata/summary JSON and folder info."""
    test_dir = Path(metric_path).parent.parent
    summary = load_test_summary(str(test_dir))
    metadata = load_test_metadata(str(test_dir))

    repeat_index = metadata.get("repeat_index")
    if repeat_index is None:
        repeat_index = summary.get("repeat_index")
    if repeat_index is None:
        repeat_index = infer_repeat_index_from_name(test_name)

    repeat_count = metadata.get("repeat_count")
    if repeat_count is None:
        repeat_count = summary.get("repeat_count")

    completed_sweeps = summary.get("completed_sweeps")
    if completed_sweeps is None:
        # Cheap filesystem fallback for older tests whose summary did not store
        # a completed sweep count. No images/CSVs are opened.
        try:
            completed_sweeps = sum(1 for p in test_dir.glob("sweep_*") if p.is_dir())
        except Exception:
            completed_sweeps = 0

    failed_sweeps = summary.get("failed_sweeps", 0)

    return {
        "test": test_name,
        "metric_path": metric_path,
        "test_path": str(test_dir),
        "camera_id": metadata.get("camera_id") or test_name,
        "test_date": metadata.get("test_date") or "",
        "repeat_group_id": infer_repeat_group_id(test_name, metadata),
        "repeat_group_start_date": metadata.get("repeat_group_start_date") or "",
        "repeat_index": repeat_index,
        "repeat_count": repeat_count,
        "status": summary.get("status", ""),
        "completed_sweeps": completed_sweeps,
        "failed_sweeps": failed_sweeps,
        "test_duration_hours": metadata.get("test_duration_hours"),
        "measurement_start": summary.get(
            "measurement_start_time",
            summary.get("start_time", metadata.get("folder_created_at", "")),
        ),
        "end_time": summary.get("end_time", ""),
        "operator": metadata.get("operator") or "",
        "notes": metadata.get("notes") or "",
    }


def build_repeat_group_catalog(metadata_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    if metadata_df.empty:
        return pd.DataFrame()

    for group_id, group_df in metadata_df.groupby("repeat_group_id", sort=False):
        group_df = group_df.copy()
        group_df["repeat_index_numeric"] = pd.to_numeric(
            group_df["repeat_index"], errors="coerce"
        )
        group_df = group_df.sort_values(
            ["repeat_index_numeric", "test_date", "test"], na_position="last"
        )

        repeat_count_values = pd.to_numeric(
            group_df["repeat_count"], errors="coerce"
        ).dropna()
        planned_repeats = (
            int(repeat_count_values.max())
            if not repeat_count_values.empty
            else len(group_df)
        )

        completed_sweeps = pd.to_numeric(
            group_df["completed_sweeps"], errors="coerce"
        ).fillna(0).sum()
        failed_sweeps = pd.to_numeric(
            group_df["failed_sweeps"], errors="coerce"
        ).fillna(0).sum()

        notes = [
            str(v).strip()
            for v in group_df["notes"].dropna()
            if str(v).strip()
        ]
        operators = [
            str(v).strip()
            for v in group_df["operator"].dropna()
            if str(v).strip()
        ]
        statuses = sorted({
            str(v).strip()
            for v in group_df["status"].dropna()
            if str(v).strip()
        })

        explicit_start_dates = [
            str(v)[:10]
            for v in group_df["repeat_group_start_date"].dropna()
            if str(v).strip()
        ]
        if explicit_start_dates:
            started = min(explicit_start_dates)
        else:
            test_dates = [
                str(v)[:10]
                for v in group_df["test_date"].dropna()
                if str(v).strip()
            ]
            started = min(test_dates) if test_dates else ""

        rows.append({
            "repeat_group_id": group_id,
            "camera_id": group_df["camera_id"].iloc[0],
            "started": started,
            "cycles_available": len(group_df),
            "cycles_planned": planned_repeats,
            "completed_sweeps": int(completed_sweeps),
            "failed_sweeps": int(failed_sweeps),
            "status": ", ".join(statuses),
            "operator": " | ".join(dict.fromkeys(operators)),
            "notes": " | ".join(dict.fromkeys(notes)),
        })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(
            ["started", "camera_id", "repeat_group_id"],
            ascending=[False, True, True],
        )
    return result


def render_individual_test_details(catalog_df: pd.DataFrame):
    if catalog_df.empty:
        return

    labels = {}
    for _, row in catalog_df.iterrows():
        cycle = row.get("repeat_index", "")
        count = row.get("repeat_count", "")
        cycle_text = f"cycle {cycle}/{count}" if not is_missing(count) else f"cycle {cycle}"
        note = str(row.get("notes") or "").strip()
        note_suffix = f" | {note[:60]}" if note else ""
        labels[row["test"]] = (
            f"{row.get('camera_id', '')} | {row.get('test_date', '')} | "
            f"{cycle_text} | {row.get('completed_sweeps', 0)} sweeps{note_suffix}"
        )

    selected = st.selectbox(
        "Inspect test details without loading analysis data",
        options=catalog_df["test"].tolist(),
        format_func=lambda name: labels.get(name, name),
        key="browser_individual_detail_test",
    )

    row = catalog_df[catalog_df["test"] == selected].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Camera", str(row.get("camera_id", "")))
    c2.metric("Status", str(row.get("status", "") or "unknown"))
    c3.metric("Completed sweeps", int(row.get("completed_sweeps", 0) or 0))
    cycle_value = row.get("repeat_index", "")
    repeat_count = row.get("repeat_count", "")
    c4.metric(
        "Repeat",
        f"{cycle_value}/{repeat_count}" if not is_missing(repeat_count) else str(cycle_value),
    )

    st.write(f"**Repeat group:** {row.get('repeat_group_id', '')}")
    st.write(f"**Test date:** {row.get('test_date', '')}")
    st.write(f"**Planned duration:** {row.get('test_duration_hours', '')} h")
    st.write(f"**Operator:** {row.get('operator', '')}")
    st.write(f"**Notes:** {row.get('notes', '') or '—'}")
    st.caption(str(row.get("test_path", "")))


def render_repeat_group_details(group_df: pd.DataFrame, metadata_df: pd.DataFrame):
    if group_df.empty:
        return

    labels = {}
    for _, row in group_df.iterrows():
        note = str(row.get("notes") or "").strip()
        note_suffix = f" | {note[:60]}" if note else ""
        labels[row["repeat_group_id"]] = (
            f"{row.get('repeat_group_id', '')} | "
            f"{row.get('cycles_available', 0)}/{row.get('cycles_planned', 0)} cycles | "
            f"{row.get('completed_sweeps', 0)} sweeps{note_suffix}"
        )

    selected_group = st.selectbox(
        "Inspect repeat group without loading analysis data",
        options=group_df["repeat_group_id"].tolist(),
        format_func=lambda group: labels.get(group, group),
        key="browser_group_detail",
    )

    row = group_df[group_df["repeat_group_id"] == selected_group].iloc[0]
    cycle_rows = metadata_df[
        metadata_df["repeat_group_id"] == selected_group
    ].copy()
    cycle_rows["repeat_index_numeric"] = pd.to_numeric(
        cycle_rows["repeat_index"], errors="coerce"
    )
    cycle_rows = cycle_rows.sort_values(
        ["repeat_index_numeric", "test_date", "test"], na_position="last"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Camera", str(row.get("camera_id", "")))
    c2.metric("Cycles", f"{row.get('cycles_available', 0)}/{row.get('cycles_planned', 0)}")
    c3.metric("Total sweeps", int(row.get("completed_sweeps", 0) or 0))
    c4.metric("Failed sweeps", int(row.get("failed_sweeps", 0) or 0))

    st.write(f"**Started:** {row.get('started', '')}")
    st.write(f"**Status:** {row.get('status', '') or 'unknown'}")
    st.write(f"**Operator:** {row.get('operator', '')}")
    st.write(f"**Notes:** {row.get('notes', '') or '—'}")

    cycle_preview_cols = [
        "repeat_index",
        "test_date",
        "status",
        "completed_sweeps",
        "failed_sweeps",
        "test_duration_hours",
        "notes",
        "test",
    ]
    cycle_preview_cols = [c for c in cycle_preview_cols if c in cycle_rows.columns]
    st.dataframe(cycle_rows[cycle_preview_cols], width="stretch", hide_index=True)


# -----------------------------------------------------------------------------
# Heavy analysis loading: called only after user presses Load checked data
# -----------------------------------------------------------------------------


def merge_diagnostics_columns(metric_file: str, metrics_df: pd.DataFrame) -> pd.DataFrame:
    diagnostics_path = Path(metric_file).parent / "sweep_diagnostics.csv"

    if not diagnostics_path.exists():
        return metrics_df

    diagnostics_df = pd.read_csv(diagnostics_path)

    desired_cols = [
        "sweep_name",
        "sweep_index",
        "bp_780_peak_fit_y_px_mean",
        "bp_1064_peak_fit_y_px_mean",
        "bp_1550_peak_fit_y_px_mean",
        "no_filter_edge_gaussian_x_px_mean",
    ]

    available_cols = [c for c in desired_cols if c in diagnostics_df.columns]

    if "sweep_name" in metrics_df.columns and "sweep_name" in available_cols:
        merge_key = "sweep_name"
    else:
        merge_key = "sweep_index"

    available_cols = [
        c for c in available_cols
        if c == merge_key or c not in metrics_df.columns
    ]

    if len(available_cols) <= 1:
        return metrics_df

    return metrics_df.merge(
        diagnostics_df[available_cols],
        on=merge_key,
        how="left",
    )


@st.cache_data(show_spinner=False)
def load_metrics(metric_file: str) -> pd.DataFrame:
    path = Path(metric_file)
    df = pd.read_csv(path)
    df = merge_diagnostics_columns(metric_file, df)

    test_dir = path.parent.parent
    metadata = load_test_metadata(str(test_dir))
    repeat_index = metadata.get("repeat_index")
    if repeat_index is None:
        repeat_index = infer_repeat_index_from_name(test_dir.name)

    repeat_group_id = infer_repeat_group_id(test_dir.name, metadata)

    camera_id = metadata.get("camera_id") or test_dir.name
    test_date = metadata.get("test_date") or ""
    test_duration_hours = metadata.get("test_duration_hours")
    operator = metadata.get("operator") or ""
    notes = metadata.get("notes") or ""

    df["test_folder"] = test_dir.name
    df["test_path"] = str(test_dir)

    df["camera_id"] = camera_id
    df["test_date"] = test_date
    df["test_duration_hours"] = test_duration_hours
    df["repeat_index"] = int(repeat_index)
    df["repeat_count"] = metadata.get("repeat_count")
    df["repeat_group_id"] = repeat_group_id
    df["operator"] = operator
    df["notes"] = notes

    if test_date:
        df["plot_label"] = f"{camera_id} / {test_date} / {test_dir.name}"
    else:
        df["plot_label"] = f"{camera_id} / {test_dir.name}"

    return df


def add_repeatability_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "repeat_group_id" not in df.columns or "sweep_index" not in df.columns:
        return df

    for col in REPEAT_POSITION_COLUMNS:
        if col not in df.columns:
            continue

        delta_col = f"{col}_repeat_delta_px"
        df[delta_col] = pd.NA

        for _, group_df in df.groupby(
            ["repeat_group_id", "sweep_index"], dropna=False
        ):
            valid = group_df.dropna(subset=[col])

            if valid.empty:
                continue

            baseline_row = valid.sort_values(
                ["repeat_index", "test_folder"]
            ).iloc[0]
            baseline = baseline_row[col]
            df.loc[group_df.index, delta_col] = group_df[col] - baseline

    return df


def available_numeric_columns(df: pd.DataFrame) -> list[str]:
    excluded = {
        "test_folder",
        "test_path",
        "camera_id",
        "plot_label",
        "sweep_name",
        "sweep_started_at",
    }

    columns = []
    for col in df.columns:
        if col in excluded:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            columns.append(col)
    return columns


def sort_metrics(columns: list[str]) -> list[str]:
    preferred = [col for col in PREFERRED_CUSTOM_METRICS if col in columns]
    remaining = sorted([col for col in columns if col not in preferred])
    return preferred + remaining


def camera_internal_temperature_columns(df: pd.DataFrame) -> list[str]:
    return sorted([
        col for col in df.columns
        if col.startswith("camera_internal_") and col.endswith("_c")
    ])


def make_plot_df(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
) -> pd.DataFrame:
    plot_columns = [
        x_col,
        y_col,
        "plot_label",
        "test_folder",
        "sweep_index",
    ]

    plot_columns = list(dict.fromkeys(plot_columns))
    available_columns = [col for col in plot_columns if col in df.columns]
    plot_df = df[available_columns].dropna()

    sort_cols = [
        col for col in ["plot_label", x_col, "sweep_index"]
        if col in plot_df.columns
    ]
    if sort_cols:
        plot_df = plot_df.sort_values(sort_cols)

    return plot_df


def plot_overlay(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str | None = None,
    show_markers: bool = True,
    chart_key: str | None = None,
):
    if x_col not in df.columns:
        st.warning(f"Missing x-axis column: {x_col}")
        return

    if y_col not in df.columns:
        st.warning(f"Missing metric column: {y_col}")
        return

    plot_df = make_plot_df(df, x_col, y_col)
    if plot_df.empty:
        st.info(f"No valid data for {label_for_column(y_col)}.")
        return

    fig = go.Figure()
    mode = "lines+markers" if show_markers else "lines"

    for plot_label, group_df in plot_df.groupby("plot_label", sort=False):
        group_df = group_df.sort_values(x_col)
        fig.add_trace(
            go.Scatter(
                x=group_df[x_col],
                y=group_df[y_col],
                mode=mode,
                name=str(plot_label),
                line=dict(width=2),
                marker=dict(size=5),
                connectgaps=False,
                customdata=group_df[
                    [
                        col
                        for col in ["test_folder", "sweep_index"]
                        if col in group_df.columns
                    ]
                ].to_numpy(),
                hovertemplate=(
                    "Test=%{fullData.name}<br>"
                    f"{label_for_column(x_col)}=%{{x}}<br>"
                    f"{label_for_column(y_col)}=%{{y}}<br>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=title or f"{label_for_column(y_col)} vs {label_for_column(x_col)}",
        xaxis_title=label_for_column(x_col),
        yaxis_title=label_for_column(y_col),
        legend_title_text="Test",
        hovermode="closest",
        template="plotly_dark",
        height=520,
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font=dict(color="#F5F5F5"),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.15)",
            zerolinecolor="rgba(255,255,255,0.25)",
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.15)",
            zerolinecolor="rgba(255,255,255,0.25)",
        ),
    )

    if chart_key is None:
        chart_key = f"plot_{x_col}_{y_col}_{abs(hash(title or ''))}"

    st.plotly_chart(
        fig,
        width="stretch",
        key=chart_key,
        theme=None,
        config={"responsive": True, "displaylogo": False},
    )


def selected_test_overview(
    selected_test_names: list[str],
    test_options: dict[str, str],
) -> pd.DataFrame:
    rows = []

    for test_name in selected_test_names:
        metric_path = Path(test_options[test_name])
        test_path = metric_path.parent.parent

        df = load_metrics(test_options[test_name])
        metadata = load_test_metadata(str(test_path))

        row = {
            "test": test_name,
            "camera_id": metadata.get("camera_id", ""),
            "test_date": metadata.get("test_date", ""),
            "duration_h": metadata.get("test_duration_hours", ""),
            "operator": metadata.get("operator", ""),
            "notes": metadata.get("notes", ""),
            "sweeps": (
                int(df["sweep_index"].count())
                if "sweep_index" in df.columns
                else len(df)
            ),
            "path": str(test_path),
        }

        if "sweep_index" in df.columns:
            row["first_sweep"] = df["sweep_index"].min()
            row["last_sweep"] = df["sweep_index"].max()

        for probe_col in [
            "temp_probe_1_c",
            "temp_probe_2_c",
            "temp_probe_3_c",
            "temp_probe_4_c",
            "temp_probe_5_c",
        ]:
            if probe_col in df.columns:
                row[f"{probe_col}_min"] = df[probe_col].min()
                row[f"{probe_col}_max"] = df[probe_col].max()

        rows.append(row)

    return pd.DataFrame(rows)


def plot_metric_group(
    df: pd.DataFrame,
    x_col: str,
    metrics: list[tuple[str, str]],
    show_markers: bool,
    key_prefix: str = "metric_group",
):
    for idx, (metric_col, title) in enumerate(metrics):
        plot_overlay(
            df=df,
            x_col=x_col,
            y_col=metric_col,
            title=title,
            show_markers=show_markers,
            chart_key=f"{key_prefix}_{idx}_{x_col}_{metric_col}",
        )


# -----------------------------------------------------------------------------
# Metadata editing
# -----------------------------------------------------------------------------


def save_test_metadata(test_dir: Path, metadata: dict):
    metadata_path = test_dir / "test_metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    # Clear caches so edits are reflected immediately.
    load_test_metadata.clear()
    load_test_summary.clear()
    load_metrics.clear()
    find_metric_files.clear()


def load_raw_user_metadata(test_dir: Path) -> dict:
    """Load only test_metadata.json so editing never removes repeat fields."""
    metadata_path = test_dir / "test_metadata.json"
    if not metadata_path.exists():
        return {}

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def metadata_editor(test_options: dict[str, str]):
    st.subheader("Edit test metadata")

    selected_test_name = st.selectbox(
        "Test to edit",
        options=list(test_options.keys()),
        key="metadata_editor_selected_test",
    )

    metric_path = Path(test_options[selected_test_name])
    test_dir = metric_path.parent.parent
    metadata = load_test_metadata(str(test_dir))

    key_prefix = "metadata_" + selected_test_name.replace("/", "_").replace(" ", "_")

    camera_id = st.text_input(
        "Camera ID",
        value=str(metadata.get("camera_id") or ""),
        key=f"{key_prefix}_camera_id",
    )

    current_date_text = str(metadata.get("test_date") or "")
    try:
        current_date = date.fromisoformat(current_date_text)
    except ValueError:
        current_date = date.today()

    test_date = st.date_input(
        "Test date",
        value=current_date,
        key=f"{key_prefix}_test_date",
    )

    duration_value = metadata.get("test_duration_hours")
    try:
        duration_value = float(duration_value)
    except (TypeError, ValueError):
        duration_value = 0.0

    test_duration_hours = st.number_input(
        "Test duration [hours]",
        min_value=0.0,
        value=duration_value,
        step=0.5,
        key=f"{key_prefix}_duration",
    )

    operator = st.text_input(
        "Operator",
        value=str(metadata.get("operator") or ""),
        key=f"{key_prefix}_operator",
    )

    notes = st.text_area(
        "Notes",
        value=str(metadata.get("notes") or ""),
        height=120,
        key=f"{key_prefix}_notes",
    )

    if st.button("Save metadata", key=f"{key_prefix}_save"):
        # Preserve repeat_group_id, repeat_group_start_date, repeat_index,
        # repeat_count, and any future metadata fields already present.
        new_metadata = load_raw_user_metadata(test_dir)
        new_metadata.update({
            "camera_id": camera_id,
            "test_date": test_date.isoformat(),
            "test_duration_hours": test_duration_hours,
            "operator": operator,
            "notes": notes,
        })

        save_test_metadata(test_dir, new_metadata)
        st.success(f"Saved metadata to {test_dir / 'test_metadata.json'}")
        st.rerun()


# -----------------------------------------------------------------------------
# Browser / selection UI
# -----------------------------------------------------------------------------


def render_test_browser(
    selection_mode: str,
    filtered_metadata_df: pd.DataFrame,
) -> list[str]:
    """
    Render lightweight checkbox browser and return the currently checked tests.

    No analysis CSV is loaded in this function.
    """
    st.subheader("Test browser")
    st.caption(
        "This browser reads only test_metadata.json and test_summary.json. "
        "Tick what you want, inspect the notes/sweep counts, then click "
        "'Load checked data'."
    )

    loaded_names = set(st.session_state.get("loaded_test_names", []))
    browser_version = st.session_state.get("browser_version", 0)

    if selection_mode == "Repeat groups":
        group_catalog = build_repeat_group_catalog(filtered_metadata_df)

        if group_catalog.empty:
            st.info("No repeat groups match the current filters.")
            return []

        fully_loaded_groups = set()
        for group_id, group_tests in filtered_metadata_df.groupby("repeat_group_id"):
            names = set(group_tests["test"].tolist())
            if names and names.issubset(loaded_names):
                fully_loaded_groups.add(group_id)

        browser_df = group_catalog.copy()
        browser_df.insert(
            0,
            "load",
            browser_df["repeat_group_id"].isin(fully_loaded_groups),
        )

        edited_df = st.data_editor(
            browser_df,
            width="stretch",
            hide_index=True,
            disabled=[col for col in browser_df.columns if col != "load"],
            column_config={
                "load": st.column_config.CheckboxColumn(
                    "Load",
                    help="Load every available cycle in this repeat group.",
                ),
                "repeat_group_id": "Repeat group",
                "camera_id": "Camera",
                "started": "Started",
                "cycles_available": "Cycles available",
                "cycles_planned": "Cycles planned",
                "completed_sweeps": "Total sweeps",
                "failed_sweeps": "Failed sweeps",
                "status": "Status",
                "operator": "Operator",
                "notes": "Notes",
            },
            key=f"repeat_group_browser_{browser_version}",
        )

        selected_groups = edited_df.loc[
            edited_df["load"], "repeat_group_id"
        ].tolist()

        requested_test_names = filtered_metadata_df.loc[
            filtered_metadata_df["repeat_group_id"].isin(selected_groups),
            "test",
        ].tolist()

        with st.expander("Inspect repeat group details", expanded=True):
            render_repeat_group_details(group_catalog, filtered_metadata_df)

        return requested_test_names

    # Individual tests
    browser_df = filtered_metadata_df[
        [
            "test",
            "camera_id",
            "test_date",
            "repeat_group_id",
            "repeat_index",
            "repeat_count",
            "status",
            "completed_sweeps",
            "failed_sweeps",
            "test_duration_hours",
            "operator",
            "notes",
        ]
    ].copy()

    # Recent tests first while keeping repeat cycles in logical order.
    browser_df["repeat_index_numeric"] = pd.to_numeric(
        browser_df["repeat_index"], errors="coerce"
    )
    browser_df = browser_df.sort_values(
        ["test_date", "camera_id", "repeat_group_id", "repeat_index_numeric"],
        ascending=[False, True, True, True],
        na_position="last",
    ).drop(columns=["repeat_index_numeric"])

    browser_df.insert(0, "load", browser_df["test"].isin(loaded_names))

    edited_df = st.data_editor(
        browser_df,
        width="stretch",
        hide_index=True,
        disabled=[col for col in browser_df.columns if col != "load"],
        column_config={
            "load": st.column_config.CheckboxColumn(
                "Load",
                help="Load this test's analysis CSVs.",
            ),
            "test": "Test folder",
            "camera_id": "Camera",
            "test_date": "Date",
            "repeat_group_id": "Repeat group",
            "repeat_index": "Cycle",
            "repeat_count": "Cycles planned",
            "status": "Status",
            "completed_sweeps": "Sweeps",
            "failed_sweeps": "Failed",
            "test_duration_hours": "Duration [h]",
            "operator": "Operator",
            "notes": "Notes",
        },
        key=f"individual_test_browser_{browser_version}",
    )

    requested_test_names = edited_df.loc[edited_df["load"], "test"].tolist()

    detail_catalog = filtered_metadata_df[
        filtered_metadata_df["test"].isin(browser_df["test"])
    ].copy()
    detail_catalog = detail_catalog.set_index("test").loc[
        browser_df["test"]
    ].reset_index()

    with st.expander("Inspect individual test details", expanded=True):
        render_individual_test_details(detail_catalog)

    return requested_test_names


# -----------------------------------------------------------------------------
# Main app
# -----------------------------------------------------------------------------


def main():
    st.set_page_config(
        page_title="Freezer test comparison",
        layout="wide",
    )

    st.title("Freezer test comparison")
    st.markdown(
        "Browse completed tests quickly from metadata, then explicitly load only "
        "the tests you want to analyse."
    )

    st.session_state.setdefault("loaded_test_names", [])
    st.session_state.setdefault("browser_version", 0)

    with st.sidebar:
        st.header("Data source")

        results_root = st.text_input(
            "Results root folder",
            value=DEFAULT_RESULTS_ROOT,
            help=(
                "Folder containing test result folders. The app searches "
                "recursively for analysis/sweep_metrics.csv."
            ),
        )

        metric_files = find_metric_files(results_root)

        if not metric_files:
            st.warning("No analysis/sweep_metrics.csv files found.")
            st.stop()

        test_options_all = {
            Path(path).parent.parent.name: path
            for path in metric_files
        }

        # IMPORTANT: this catalog is JSON-only. No sweep CSV is loaded here.
        metadata_rows = [
            build_catalog_row(test_name, metric_path)
            for test_name, metric_path in test_options_all.items()
        ]
        metadata_df = pd.DataFrame(metadata_rows)

        st.header("Filters")

        camera_options = sorted([
            str(camera_id)
            for camera_id in metadata_df["camera_id"].dropna().unique()
        ])

        selected_cameras = st.multiselect(
            "Camera ID",
            options=camera_options,
            default=camera_options,
        )

        search_text = st.text_input(
            "Search camera/group/folder/notes",
            value="",
        )

        selection_mode = st.radio(
            "Browser mode",
            options=["Individual tests", "Repeat groups"],
            index=0,
        )

    filtered_metadata_df = metadata_df.copy()

    if selected_cameras:
        filtered_metadata_df = filtered_metadata_df[
            filtered_metadata_df["camera_id"].isin(selected_cameras)
        ]

    if search_text.strip():
        search = search_text.strip().lower()
        search_mask = (
            filtered_metadata_df["test"].astype(str).str.lower().str.contains(search, na=False)
            | filtered_metadata_df["camera_id"].astype(str).str.lower().str.contains(search, na=False)
            | filtered_metadata_df["repeat_group_id"].astype(str).str.lower().str.contains(search, na=False)
            | filtered_metadata_df["notes"].astype(str).str.lower().str.contains(search, na=False)
            | filtered_metadata_df["operator"].astype(str).str.lower().str.contains(search, na=False)
            | filtered_metadata_df["test_path"].astype(str).str.lower().str.contains(search, na=False)
        )
        filtered_metadata_df = filtered_metadata_df[search_mask]

    if filtered_metadata_df.empty:
        st.warning("No tests match the current filters.")
        return

    requested_test_names = render_test_browser(
        selection_mode=selection_mode,
        filtered_metadata_df=filtered_metadata_df,
    )

    # Load/unload controls. The expensive CSV read happens only after this.
    b1, b2, b3 = st.columns([1.3, 1.0, 4.0])

    with b1:
        load_clicked = st.button(
            "Load checked data",
            type="primary",
            disabled=not requested_test_names,
        )

    with b2:
        clear_clicked = st.button(
            "Clear loaded data",
            disabled=not st.session_state.get("loaded_test_names"),
        )

    if load_clicked:
        st.session_state["loaded_test_names"] = list(dict.fromkeys(requested_test_names))
        st.session_state["browser_version"] += 1
        st.rerun()

    if clear_clicked:
        st.session_state["loaded_test_names"] = []
        st.session_state["browser_version"] += 1
        st.rerun()

    loaded_test_names = [
        name
        for name in st.session_state.get("loaded_test_names", [])
        if name in test_options_all
    ]

    st.caption(
        f"Checked in browser: {len(requested_test_names)} test cycle(s). "
        f"Currently loaded for analysis: {len(loaded_test_names)} test cycle(s)."
    )

    if not loaded_test_names:
        st.info(
            "No analysis data is loaded yet. Inspect the metadata above, tick the "
            "tests or repeat groups you want, then click 'Load checked data'."
        )
        return

    loaded_metadata_df = metadata_df[
        metadata_df["test"].isin(loaded_test_names)
    ]
    loaded_group_count = loaded_metadata_df["repeat_group_id"].nunique()
    st.success(
        f"Loaded selection: {len(loaded_test_names)} test cycle(s) from "
        f"{loaded_group_count} repeat group(s)."
    )

    # ------------------------------------------------------------------
    # Heavy loading starts here and nowhere above this point.
    # ------------------------------------------------------------------
    with st.spinner(f"Loading analysis data for {len(loaded_test_names)} test cycle(s)..."):
        dfs = [
            load_metrics(test_options_all[test_name])
            for test_name in loaded_test_names
        ]

    combined = pd.concat(dfs, ignore_index=True)
    combined = add_repeatability_columns(combined)
    csv_data = combined.to_csv(index=False).encode("utf-8")

    selected_test_names = loaded_test_names
    test_options = test_options_all

    with st.sidebar:
        st.divider()
        st.header("Loaded analysis")
        st.write(f"{len(loaded_test_names)} test cycle(s)")
        st.write(f"{loaded_group_count} repeat group(s)")

        st.download_button(
            label="Download loaded data CSV",
            data=csv_data,
            file_name="selected_freezer_test_data.csv",
            mime="text/csv",
        )

    numeric_cols = available_numeric_columns(combined)
    available_x_axes = [
        col for col in X_AXIS_OPTIONS
        if col in numeric_cols
    ]

    if not available_x_axes:
        st.error("No usable x-axis columns found.")
        return

    with st.sidebar:
        st.header("Global plot settings")

        x_col = st.selectbox(
            "X-axis",
            options=available_x_axes,
            format_func=label_for_column,
            index=0,
        )

        show_markers = st.checkbox("Show markers", value=False)

    tabs = st.tabs([
        "Overview",
        "Spectral resolution",
        "Spectral shift",
        "Spatial performance",
        "Signal stability",
        "Camera internal temperatures",
        "Cycle repeatability",
        "Custom plot",
    ])

    with tabs[0]:
        st.header("Overview")

        st.subheader("Loaded tests")
        overview_df = selected_test_overview(selected_test_names, test_options)
        st.dataframe(overview_df, width="stretch")

        with st.expander("Edit metadata"):
            metadata_editor({
                name: test_options[name]
                for name in selected_test_names
            })

        st.subheader("Temperature profile")

        available_temp_cols = [
            col for col in [
                "temp_probe_1_c",
                "temp_probe_2_c",
                "temp_probe_3_c",
                "temp_probe_4_c",
                "temp_probe_5_c",
            ]
            if col in combined.columns
        ]

        if available_temp_cols:
            show_all_temperature_probes = st.checkbox(
                "Show all temperature probes",
                value=False,
                key="overview_show_all_temperature_probes",
            )

            if show_all_temperature_probes:
                for temp_col in available_temp_cols:
                    plot_overlay(
                        df=combined,
                        x_col="sweep_index",
                        y_col=temp_col,
                        title=f"{label_for_column(temp_col)} vs sweep index",
                        show_markers=show_markers,
                        chart_key=f"overview_temperature_{temp_col}",
                    )
            else:
                overview_temp_col = st.selectbox(
                    "Temperature probe to show",
                    options=available_temp_cols,
                    format_func=label_for_column,
                    index=0,
                    key="overview_temperature_probe",
                )

                plot_overlay(
                    df=combined,
                    x_col="sweep_index",
                    y_col=overview_temp_col,
                    title=f"{label_for_column(overview_temp_col)} vs sweep index",
                    show_markers=show_markers,
                    chart_key=f"overview_temperature_{overview_temp_col}",
                )
        else:
            st.info("No temperature probe columns found.")

    with tabs[1]:
        st.header("Spectral resolution")

        st.markdown(
            "Absolute spectral FWHM. Use this to compare spectral resolution "
            "between cameras or repeated tests."
        )

        plot_metric_group(
            df=combined,
            x_col=x_col,
            show_markers=show_markers,
            key_prefix="spectral_resolution_abs",
            metrics=[
                ("bp_780_fwhm_px_mean", "780 nm spectral FWHM"),
                ("bp_1064_fwhm_px_mean", "1064 nm spectral FWHM"),
                ("bp_1550_fwhm_px_mean", "1550 nm spectral FWHM"),
            ],
        )

        st.subheader("Spectral FWHM change from first sweep")

        plot_metric_group(
            df=combined,
            x_col=x_col,
            show_markers=show_markers,
            key_prefix="spectral_resolution_delta",
            metrics=[
                ("bp_780_fwhm_px_mean_delta", "780 nm spectral FWHM change"),
                ("bp_1064_fwhm_px_mean_delta", "1064 nm spectral FWHM change"),
                ("bp_1550_fwhm_px_mean_delta", "1550 nm spectral FWHM change"),
            ],
        )

    with tabs[2]:
        st.header("Spectral shift")

        st.markdown(
            "Spectral line shift relative to the first valid sweep. "
            "This is useful for checking whether spectral features move on the sensor."
        )

        plot_metric_group(
            df=combined,
            x_col=x_col,
            show_markers=show_markers,
            key_prefix="spectral_shift",
            metrics=[
                ("bp_780_peak_fit_y_px_mean_delta", "780 nm spectral line shift"),
                ("bp_1064_peak_fit_y_px_mean_delta", "1064 nm spectral line shift"),
                ("bp_1550_peak_fit_y_px_mean_delta", "1550 nm spectral line shift"),
            ],
        )

    with tabs[3]:
        st.header("Spatial performance")

        st.markdown(
            "Spatial FWHM tracks edge sharpness. Spatial edge shift tracks image movement."
        )

        plot_metric_group(
            df=combined,
            x_col=x_col,
            show_markers=show_markers,
            key_prefix="spatial_performance",
            metrics=[
                ("no_filter_lsf_gaussian_fwhm_px_mean", "Spatial absolute FWHM"),
                ("no_filter_edge_gaussian_x_px_mean_delta", "Spatial edge shift"),
            ],
        )

    with tabs[4]:
        st.header("Signal stability")

        st.markdown(
            "No-filter signal is useful for detecting illumination instability, "
            "camera response drift, or remaining warm-up effects."
        )

        plot_metric_group(
            df=combined,
            x_col=x_col,
            show_markers=show_markers,
            metrics=[
                ("no_filter_signal_signal_mean_mean", "No-filter signal mean"),
                ("no_filter_signal_signal_mean_mean_delta", "No-filter signal change"),
                ("dark_noise_noise_std_mean", "Dark-region noise level"),
                ("dark_noise_dark_mean_mean", "Dark-region mean level"),
            ],
        )

    with tabs[5]:
        st.header("Camera internal temperatures")

        st.markdown(
            "Internal camera/module temperatures read from the camera computer. "
            "These values are stored once before image capture and once after "
            "image capture for each sweep."
        )

        internal_temp_cols = camera_internal_temperature_columns(combined)

        if not internal_temp_cols:
            st.info(
                "No camera-internal temperature columns found. Re-run analysis "
                "on tests acquired after the camera temperature integration was added."
            )
        else:
            selected_internal_temp_cols = st.multiselect(
                "Camera-internal temperature sensors to plot",
                options=internal_temp_cols,
                default=internal_temp_cols[: min(6, len(internal_temp_cols))],
                format_func=label_for_column,
                key="camera_internal_temperature_columns",
            )

            plot_metric_group(
                df=combined,
                x_col=x_col,
                show_markers=show_markers,
                key_prefix="camera_internal_temperatures",
                metrics=[
                    (col, label_for_column(col))
                    for col in selected_internal_temp_cols
                ],
            )

    with tabs[6]:
        st.header("Cycle repeatability")

        st.markdown(
            "This checks whether the spectral lines and spatial edge return to the "
            "same absolute sensor position at the same sweep index in repeated cycles. "
            "The plotted value is relative to the first repeat cycle in each repeat group."
        )

        if "repeat_index" not in combined.columns:
            st.info("No repeat_index column found.")
        else:
            available_sweeps = sorted([
                int(v) for v in combined["sweep_index"].dropna().unique()
            ])

            if not available_sweeps:
                st.info("No sweep indices available.")
            else:
                selected_repeatability_sweep = st.selectbox(
                    "Sweep index to compare across cycles",
                    options=available_sweeps,
                    index=0,
                    key="repeatability_sweep_index",
                )

                repeatability_df = combined[
                    combined["sweep_index"] == selected_repeatability_sweep
                ].copy()

                repeatability_metrics = [
                    (
                        "bp_780_peak_fit_y_px_mean_repeat_delta_px",
                        "780 nm line return error",
                    ),
                    (
                        "bp_1064_peak_fit_y_px_mean_repeat_delta_px",
                        "1064 nm line return error",
                    ),
                    (
                        "bp_1550_peak_fit_y_px_mean_repeat_delta_px",
                        "1550 nm line return error",
                    ),
                    (
                        "no_filter_edge_gaussian_x_px_mean_repeat_delta_px",
                        "Spatial edge return error",
                    ),
                ]

                plot_metric_group(
                    df=repeatability_df,
                    x_col="repeat_index",
                    show_markers=True,
                    key_prefix="cycle_repeatability",
                    metrics=repeatability_metrics,
                )

                with st.expander("Show repeatability data"):
                    cols = [
                        "repeat_group_id",
                        "repeat_index",
                        "test_folder",
                        "sweep_index",
                        "bp_780_peak_fit_y_px_mean_repeat_delta_px",
                        "bp_1064_peak_fit_y_px_mean_repeat_delta_px",
                        "bp_1550_peak_fit_y_px_mean_repeat_delta_px",
                        "no_filter_edge_gaussian_x_px_mean_repeat_delta_px",
                    ]

                    cols = [c for c in cols if c in repeatability_df.columns]
                    st.dataframe(
                        repeatability_df[cols].sort_values(
                            ["repeat_group_id", "repeat_index", "test_folder"]
                        ),
                        width="stretch",
                    )

    with tabs[7]:
        st.header("Custom plot")

        custom_metric_options = sort_metrics([
            col for col in numeric_cols
            if col not in available_x_axes
        ])

        if not custom_metric_options:
            st.warning("No custom metrics available.")
            return

        custom_y_col = st.selectbox(
            "Y metric",
            options=custom_metric_options,
            format_func=label_for_column,
            index=0,
        )

        plot_overlay(
            df=combined,
            x_col=x_col,
            y_col=custom_y_col,
            title=f"{label_for_column(custom_y_col)} vs {label_for_column(x_col)}",
            show_markers=show_markers,
            chart_key=f"custom_plot_{x_col}_{custom_y_col}",
        )

        with st.expander("Show plotted data"):
            plot_df = make_plot_df(combined, x_col, custom_y_col)
            st.dataframe(plot_df, width="stretch")


if __name__ == "__main__":
    main()
