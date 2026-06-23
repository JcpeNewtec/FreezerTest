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

import pandas as pd
import plotly.express as px
import streamlit as st
import json
from datetime import datetime


DEFAULT_RESULTS_ROOT = "."


METRIC_LABELS = {
    "sweep_index": "Sweep index",

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

    "no_filter_lsf_gaussian_fwhm_px_mean": "Spatial FWHM [px]",
    "no_filter_edge_gaussian_x_px_mean_delta": "Spatial edge shift [px]",

    "no_filter_signal_signal_mean_mean": "No-filter signal mean [DN]",
    "no_filter_signal_signal_mean_mean_delta": "No-filter signal change [DN]",
    "no_filter_signal_signal_std_mean": "No-filter signal std [DN]",
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
]


def label_for_column(column: str) -> str:
    return METRIC_LABELS.get(column, column)


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

    test_dir = path.parent.parent
    metadata = load_test_metadata(test_dir)

    camera_id = metadata.get("camera_id") or test_dir.name
    test_date = metadata.get("test_date") or ""
    notes = metadata.get("notes") or ""

    df["test_folder"] = test_dir.name
    df["test_path"] = str(test_dir)

    df["camera_id"] = camera_id
    df["test_date"] = test_date
    df["test_duration_hours"] = metadata.get("test_duration_hours")
    df["operator"] = metadata.get("operator", "")
    df["notes"] = notes

    if test_date:
        df["plot_label"] = f"{camera_id} / {test_date}"
    else:
        df["plot_label"] = camera_id

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

    return plot_df


def plot_overlay(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str | None = None,
    show_markers: bool = True,
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

    fig = px.line(
        plot_df,
        x=x_col,
        y=y_col,
        color="plot_label",
        markers=show_markers,
        hover_data=[
            col for col in ["test_folder", "sweep_index"]
            if col in plot_df.columns
        ],
        labels={
            x_col: label_for_column(x_col),
            y_col: label_for_column(y_col),
            "plot_label": "Test",
        },
        title=title or f"{label_for_column(y_col)} vs {label_for_column(x_col)}",
    )

    fig.update_layout(
        legend_title_text="Test",
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True)


def selected_test_overview(selected_test_names: list[str], test_options: dict[str, str]) -> pd.DataFrame:
    rows = []

    for test_name in selected_test_names:
        df = load_metrics(test_options[test_name])
        test_path = Path(test_options[test_name]).parent.parent

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
):
    for metric_col, title in metrics:
        plot_overlay(
            df=df,
            x_col=x_col,
            y_col=metric_col,
            title=title,
            show_markers=show_markers,
        )

def load_test_metadata(test_dir: Path) -> dict:
    metadata_path = test_dir / "test_metadata.json"
    summary_path = test_dir / "test_summary.json"

    metadata = {
        "camera_id": test_dir.name,
        "test_date": "",
        "test_duration_hours": None,
        "notes": "",
        "operator": "",
    }

    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                user_metadata = json.load(f)

            metadata.update(user_metadata)
        except Exception as e:
            metadata["metadata_error"] = str(e)

    # Fall back to test_summary.json where useful
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)

            if not metadata.get("test_date") and summary.get("start_time"):
                metadata["test_date"] = summary["start_time"].split("T")[0]

            if metadata.get("test_duration_hours") is None:
                metadata["test_duration_hours"] = summary.get("test_duration_hours")

        except Exception as e:
            metadata["summary_error"] = str(e)

    return metadata


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

        test_options = {
            Path(path).parent.parent.name: path
            for path in metric_files
        }

        selected_test_names = st.multiselect(
            "Select tests to compare",
            options=list(test_options.keys()),
            default=list(test_options.keys())[: min(3, len(test_options))],
        )

        if not selected_test_names:
            st.warning("Select at least one test.")
            st.stop()

    dfs = []

    for test_name in selected_test_names:
        dfs.append(load_metrics(test_options[test_name]))

    combined = pd.concat(dfs, ignore_index=True)

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

        show_markers = st.checkbox("Show markers", value=True)

    tabs = st.tabs([
        "Overview",
        "Spectral resolution",
        "Spectral shift",
        "Spatial performance",
        "Signal stability",
        "Custom plot",
    ])

    with tabs[0]:
        st.header("Overview")

        st.subheader("Selected tests")
        overview_df = selected_test_overview(selected_test_names, test_options)
        st.dataframe(overview_df, use_container_width=True)

        st.subheader("Temperature profile")
        for temp_col in [
            "temp_probe_1_c",
            "temp_probe_2_c",
            "temp_probe_3_c",
            "temp_probe_4_c",
            "temp_probe_5_c",
        ]:
            if temp_col in combined.columns:
                plot_overlay(
                    df=combined,
                    x_col="sweep_index",
                    y_col=temp_col,
                    title=f"{label_for_column(temp_col)} vs sweep index",
                    show_markers=show_markers,
                )

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
            ],
        )

    with tabs[5]:
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
        )

        with st.expander("Show plotted data"):
            plot_df = make_plot_df(combined, x_col, custom_y_col)
            st.dataframe(plot_df, use_container_width=True)


if __name__ == "__main__":
    main()