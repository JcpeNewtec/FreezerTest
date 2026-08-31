#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interactive comparison viewer for freezer-test analysis results.

Run from the repository root with:

    streamlit run Scripts/compare_tests_streamlit.py

Expected input structure:

    <results_root>/
        <test_folder_1>/
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


@st.cache_data(show_spinner=False)
def find_metric_files(results_root: str) -> list[str]:
    root = Path(results_root).expanduser()

    if not root.exists():
        return []

    metric_files = sorted(root.glob("**/analysis/sweep_metrics.csv"))
    return [str(path) for path in metric_files]


@st.cache_data(show_spinner=False)
def load_metrics(metric_file: str) -> pd.DataFrame:
    path = Path(metric_file)
    df = pd.read_csv(path)
    df = merge_diagnostics_columns(metric_file, df)

    test_dir = path.parent.parent
    metadata = load_test_metadata(test_dir)
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

    # Remove duplicates while preserving order.
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
                    [col for col in ["test_folder", "sweep_index"] if col in group_df.columns]
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
        config={
            "responsive": True,
            "displaylogo": False,
        },
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
        metadata = load_test_metadata(test_path)

        row = {
            "test": test_name,
            "camera_id": metadata.get("camera_id", ""),
            "test_date": metadata.get("test_date", ""),
            "duration_h": metadata.get("test_duration_hours", ""),
            "operator": metadata.get("operator", ""),
            "notes": metadata.get("notes", ""),
            "sweeps": int(df["sweep_index"].count()) if "sweep_index" in df.columns else len(df),
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
        
def default_metadata(test_dir: Path) -> dict:
    return {
        "camera_id": test_dir.name,
        "test_date": "",
        "test_duration_hours": None,
        "operator": "",
        "notes": "",
    }


def safe_name(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    text = text.strip("_")
    return text or "unknown_camera"

def load_test_metadata(test_dir: Path) -> dict:
    metadata_path = test_dir / "test_metadata.json"
    summary_path = test_dir / "test_summary.json"

    metadata = default_metadata(test_dir)

    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                user_metadata = json.load(f)

            if isinstance(user_metadata, dict):
                metadata.update(user_metadata)

        except Exception as e:
            metadata["metadata_error"] = str(e)

    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)

            if not metadata.get("test_date") and summary.get("start_time"):
                metadata["test_date"] = str(summary["start_time"]).split("T")[0]

            if metadata.get("test_duration_hours") is None:
                metadata["test_duration_hours"] = summary.get("test_duration_hours")

        except Exception as e:
            metadata["summary_error"] = str(e)

    return metadata

def infer_repeat_index_from_name(test_name: str) -> int:
    import re

    match = re.search(r"_repeat_(\d+)_", test_name)

    if match:
        return int(match.group(1))

    return 1


def infer_repeat_group_id(test_name: str, metadata: dict) -> str:
    """
    Return repeat group ID as:

        CAMERA_ID_YYYY-MM-DD

    Preferred source:
        metadata["repeat_group_start_date"]

    Fallbacks:
        - existing repeat_group_id containing a date
        - folder timestamp
        - test_date
    """

    camera_id = safe_name(metadata.get("camera_id") or "unknown_camera")

    # Best source: explicitly repaired/written metadata.
    repeat_group_start_date = metadata.get("repeat_group_start_date")
    if repeat_group_start_date:
        return f"{camera_id}_{str(repeat_group_start_date)[:10]}"

    # If old metadata already has a repeat_group_id, extract the date from it.
    existing_group_id = metadata.get("repeat_group_id")
    if existing_group_id:
        existing_group_id = str(existing_group_id)

        # Handles EV-0-0-002-TEC_2026-08-13
        match = re.search(r"(\d{4}-\d{2}-\d{2})", existing_group_id)
        if match:
            return f"{camera_id}_{match.group(1)}"

        # Handles freezer_test_20260813_085456
        match = re.search(r"(\d{8})(?:_\d{6})?", existing_group_id)
        if match:
            date_text = match.group(1)
            date_iso = f"{date_text[0:4]}-{date_text[4:6]}-{date_text[6:8]}"
            return f"{camera_id}_{date_iso}"

    # Folder-name fallback:
    # EV-0-0-002-TEC_repeat_001_20260813_085456
    # freezer_test_repeat_002_20260814_010000
    match = re.search(r"_(?:repeat_\d+_)?(\d{8})_\d{6}$", test_name)
    if match:
        date_text = match.group(1)
        date_iso = f"{date_text[0:4]}-{date_text[4:6]}-{date_text[6:8]}"
        return f"{camera_id}_{date_iso}"

    # Last fallback. This may split a multi-day repeat sequence,
    # so repaired metadata is preferred.
    test_date = metadata.get("test_date")
    if test_date:
        return f"{camera_id}_{str(test_date)[:10]}"

    return f"{camera_id}_unknown_date"

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

    available_cols = [c for c in available_cols if c == merge_key or c not in metrics_df.columns]

    if len(available_cols) <= 1:
        return metrics_df

    return metrics_df.merge(
        diagnostics_df[available_cols],
        on=merge_key,
        how="left",
    )

REPEAT_POSITION_COLUMNS = [
    "bp_780_peak_fit_y_px_mean",
    "bp_1064_peak_fit_y_px_mean",
    "bp_1550_peak_fit_y_px_mean",
    "no_filter_edge_gaussian_x_px_mean",
]

def add_repeatability_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "repeat_group_id" not in df.columns or "sweep_index" not in df.columns:
        return df

    for col in REPEAT_POSITION_COLUMNS:
        if col not in df.columns:
            continue

        delta_col = f"{col}_repeat_delta_px"
        df[delta_col] = pd.NA

        for _, group_df in df.groupby(["repeat_group_id", "sweep_index"], dropna=False):
            valid = group_df.dropna(subset=[col])

            if valid.empty:
                continue

            baseline_row = valid.sort_values(["repeat_index", "test_folder"]).iloc[0]
            baseline = baseline_row[col]

            df.loc[group_df.index, delta_col] = group_df[col] - baseline

    return df

def save_test_metadata(test_dir: Path, metadata: dict):
    metadata_path = test_dir / "test_metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    # Clear Streamlit cache so the updated metadata is reloaded.
    load_metrics.clear()
    find_metric_files.clear()
def metadata_editor(test_options: dict[str, str]):
    st.subheader("Edit test metadata")

    selected_test_name = st.selectbox(
        "Test to edit",
        options=list(test_options.keys()),
        key="metadata_editor_selected_test",
    )

    metric_path = Path(test_options[selected_test_name])
    test_dir = metric_path.parent.parent
    metadata = load_test_metadata(test_dir)

    # Make widget keys unique for each selected test.
    # This makes Streamlit load/show the correct values when switching tests.
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
        new_metadata = {
            "camera_id": camera_id,
            "test_date": test_date.isoformat(),
            "test_duration_hours": test_duration_hours,
            "operator": operator,
            "notes": notes,
        }

        save_test_metadata(test_dir, new_metadata)

        st.success(f"Saved metadata to {test_dir / 'test_metadata.json'}")
        st.rerun()

def main():
    st.set_page_config(
        page_title="Freezer test comparison",
        layout="wide",
    )

    st.title("Freezer test comparison")

    st.markdown(
        "Compare completed freezer-test runs by loading their "
        "`analysis/sweep_metrics.csv` files."
    )

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
        
        metadata_rows = []
        
        for test_name, metric_path in test_options_all.items():
            test_dir = Path(metric_path).parent.parent
            metadata = load_test_metadata(test_dir)
        
            metadata_rows.append({
                "test": test_name,
                "metric_path": metric_path,
                "test_path": str(test_dir),
                "camera_id": metadata.get("camera_id", test_name),
                "test_date": metadata.get("test_date", ""),
                "test_duration_hours": metadata.get("test_duration_hours", None),
                "repeat_index": metadata.get("repeat_index", infer_repeat_index_from_name(test_name)),
                "repeat_group_id": infer_repeat_group_id(test_name, metadata),
                "operator": metadata.get("operator", ""),
                "notes": metadata.get("notes", ""),
            })
        
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
            "Search test/folder/notes",
            value="",
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
                | filtered_metadata_df["notes"].astype(str).str.lower().str.contains(search, na=False)
                | filtered_metadata_df["test_path"].astype(str).str.lower().str.contains(search, na=False)
            )
        
            filtered_metadata_df = filtered_metadata_df[search_mask]
        
        filtered_test_options = {
            row["test"]: row["metric_path"]
            for _, row in filtered_metadata_df.iterrows()
        }
        
        if not filtered_test_options:
            st.warning("No tests match the current filters.")
            st.stop()
        
        selection_mode = st.radio(
            "Selection mode",
            options=["Individual tests", "Repeat groups"],
            index=0,
        )
        
        if selection_mode == "Repeat groups":
            repeat_group_options = sorted(filtered_metadata_df["repeat_group_id"].dropna().unique())
        
            selected_repeat_groups = st.multiselect(
                "Select repeat groups",
                options=repeat_group_options,
                default=repeat_group_options[: min(2, len(repeat_group_options))],
            )
        
            filtered_metadata_df = filtered_metadata_df[
                filtered_metadata_df["repeat_group_id"].isin(selected_repeat_groups)
            ]
        
            selected_test_names = filtered_metadata_df["test"].tolist()
        
            if not selected_test_names:
                st.warning("Select at least one repeat group.")
                st.stop()
        
        else:
            selected_test_names = st.multiselect(
                "Select tests to compare",
                options=list(filtered_test_options.keys()),
                default=list(filtered_test_options.keys())[: min(3, len(filtered_test_options))],
            )
        
            if not selected_test_names:
                st.warning("Select at least one test.")
                st.stop()
        
        test_options = filtered_test_options

    dfs = []

    for test_name in selected_test_names:
        dfs.append(load_metrics(test_options[test_name]))

    combined = pd.concat(dfs, ignore_index=True)
    combined = add_repeatability_columns(combined)
    csv_data = combined.to_csv(index=False).encode("utf-8")

    with st.sidebar:
        st.download_button(
            label="Download selected data CSV",
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
        st.stop()

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

        st.subheader("Selected tests")
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
            "These values are stored once before image capture and once after image capture for each sweep."
        )

        internal_temp_cols = camera_internal_temperature_columns(combined)

        if not internal_temp_cols:
            st.info("No camera-internal temperature columns found. Re-run analysis on tests acquired after the camera temperature integration was added.")
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
            st.stop()

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