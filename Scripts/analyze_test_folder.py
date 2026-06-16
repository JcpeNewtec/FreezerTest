#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 13:52:07 2026

@author: jcpe
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


from Config.analysis_config import (
    FILTER_ANALYSIS_CONFIG,
    SPATIAL_EDGE_ROIS,
    SPECTRAL_LINE_ROIS,
    SMOOTHING_ENABLED,
    SPECTRAL_SMOOTHING_WINDOW,
    SPATIAL_SMOOTHING_WINDOW,
    DEBUG_PROFILE_PLOTS,
    DEBUG_PROFILE_PLOT_MAX_SWEEPS,
    SPATIAL_LSF_GAUSSIAN_FIT_ENABLED,
    SPATIAL_LSF_FIT_HALF_WINDOW,
)

try:
    from scipy.optimize import curve_fit
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


GAUSSIAN_FWHM_FACTOR = 2.354820045



def load_image(path: Path) -> np.ndarray:
    return np.array(Image.open(path)).astype(float)


def crop_roi(image: np.ndarray, roi: dict) -> np.ndarray:
    return image[roi["y0"]:roi["y1"], roi["x0"]:roi["x1"]]


def fwhm_pixels(profile: np.ndarray) -> float:
    profile = profile.astype(float)

    baseline = np.percentile(profile, 10)
    y = profile - baseline
    y[y < 0] = 0

    peak_idx = int(np.argmax(y))
    peak = y[peak_idx]

    if peak <= 0:
        return np.nan

    half = peak / 2.0

    # Find left half-max crossing
    left = peak_idx
    while left > 0 and y[left] >= half:
        left -= 1

    if left == 0:
        return np.nan

    # Linear interpolation between left and left+1
    x0, x1 = left, left + 1
    y0, y1 = y[x0], y[x1]
    left_cross = x0 + (half - y0) / (y1 - y0)

    # Find right half-max crossing
    right = peak_idx
    while right < len(y) - 1 and y[right] >= half:
        right += 1

    if right == len(y) - 1:
        return np.nan

    # Linear interpolation between right-1 and right
    x0, x1 = right - 1, right
    y0, y1 = y[x0], y[x1]
    right_cross = x0 + (half - y0) / (y1 - y0)

    return float(right_cross - left_cross)

def smooth_profile(profile: np.ndarray, window: int = 3) -> np.ndarray:
    """
    Moving-average smoothing with edge padding that avoids artificial edge spikes.
    """
    profile = np.asarray(profile, dtype=float)

    if window is None or window <= 1:
        return profile.copy()

    if window % 2 == 0:
        raise ValueError("Smoothing window must be odd.")

    pad = window // 2
    padded = np.pad(profile, pad_width=pad, mode="edge")
    kernel = np.ones(window, dtype=float) / window

    return np.convolve(padded, kernel, mode="valid")

def baseline_correct(profile: np.ndarray, baseline_percentile: float = 10) -> np.ndarray:
    profile = np.asarray(profile, dtype=float)
    baseline = np.percentile(profile, baseline_percentile)
    y = profile - baseline
    y[y < 0] = 0
    return y

def gaussian_with_offset(x, amplitude, center, sigma, offset):
    return offset + amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def fit_gaussian_peak(
    profile: np.ndarray,
    half_window: int = 5,
) -> dict:
    """
    Fit a Gaussian + constant offset around the dominant peak.

    Returns sub-pixel center and FWHM.
    """
    if not SCIPY_AVAILABLE:
        return {
            "fit_success": False,
            "error": "scipy_not_available",
            "center_px": np.nan,
            "fwhm_px": np.nan,
        }

    profile = np.asarray(profile, dtype=float)

    if len(profile) < 5:
        return {
            "fit_success": False,
            "error": "profile_too_short",
            "center_px": np.nan,
            "fwhm_px": np.nan,
        }

    peak_idx = int(np.argmax(profile))

    i0 = max(0, peak_idx - half_window)
    i1 = min(len(profile), peak_idx + half_window + 1)

    x = np.arange(i0, i1, dtype=float)
    y = profile[i0:i1].astype(float)

    if len(x) < 5:
        return {
            "fit_success": False,
            "error": "fit_window_too_short",
            "center_px": np.nan,
            "fwhm_px": np.nan,
        }

    offset0 = float(np.percentile(y, 10))
    amplitude0 = float(np.max(y) - offset0)

    if amplitude0 <= 0:
        return {
            "fit_success": False,
            "error": "non_positive_amplitude",
            "center_px": np.nan,
            "fwhm_px": np.nan,
        }

    sigma0 = max(1.0, half_window / 3)

    p0 = [
        amplitude0,
        float(peak_idx),
        sigma0,
        offset0,
    ]

    lower_bounds = [
        0.0,
        float(i0),
        0.2,
        -np.inf,
    ]

    upper_bounds = [
        np.inf,
        float(i1 - 1),
        float(max(half_window * 3, 1.0)),
        np.inf,
    ]

    try:
        popt, _ = curve_fit(
            gaussian_with_offset,
            x,
            y,
            p0=p0,
            bounds=(lower_bounds, upper_bounds),
            maxfev=10000,
        )
    except Exception as e:
        return {
            "fit_success": False,
            "error": str(e),
            "center_px": np.nan,
            "fwhm_px": np.nan,
        }

    amplitude, center, sigma, offset = popt
    fwhm = GAUSSIAN_FWHM_FACTOR * abs(sigma)

    return {
        "fit_success": True,
        "center_px": float(center),
        "fwhm_px": float(fwhm),
        "amplitude": float(amplitude),
        "sigma_px": float(abs(sigma)),
        "offset": float(offset),
        "fit_i0": int(i0),
        "fit_i1": int(i1),
    }


def windowed_centroid_pixels(
    profile: np.ndarray,
    threshold_fraction: float = 0.2,
) -> float:
    """
    Centroid calculated only around the main peak, not across the full profile.
    This avoids long tails pulling the centroid too far.
    """
    y = baseline_correct(profile)

    peak_idx = int(np.argmax(y))
    peak = y[peak_idx]

    if peak <= 0:
        return np.nan

    threshold = peak * threshold_fraction

    left = peak_idx
    while left > 0 and y[left] >= threshold:
        left -= 1

    right = peak_idx
    while right < len(y) - 1 and y[right] >= threshold:
        right += 1

    idx = np.arange(left + 1, right)

    if len(idx) < 1:
        return np.nan

    weights = y[idx]
    total = np.sum(weights)

    if total <= 0:
        return np.nan

    return float(np.sum(idx * weights) / total)


def quadratic_peak_pixels(
    profile: np.ndarray,
    half_window: int = 2,
) -> float:
    """
    Sub-pixel peak position from a quadratic fit around the local maximum.

    This is better than centroid for tracking line motion because it is local
    and less affected by asymmetric tails.
    """
    y = baseline_correct(profile)

    peak_idx = int(np.argmax(y))

    i0 = max(0, peak_idx - half_window)
    i1 = min(len(y), peak_idx + half_window + 1)

    if i1 - i0 < 3:
        return float(peak_idx)

    x = np.arange(i0, i1, dtype=float)
    yy = y[i0:i1]

    try:
        a, b, c = np.polyfit(x, yy, 2)
    except Exception:
        return float(peak_idx)

    # If parabola opens upward, fit is not useful.
    if a >= 0:
        return float(peak_idx)

    x_peak = -b / (2 * a)

    # Reject unreasonable extrapolations.
    if x_peak < i0 or x_peak > i1 - 1:
        return float(peak_idx)

    return float(x_peak)


def centroid_pixels(profile: np.ndarray) -> float:
    profile = profile.astype(float)

    baseline = np.percentile(profile, 10)
    y = profile - baseline
    y[y < 0] = 0

    total = np.sum(y)
    if total <= 0:
        return np.nan

    x = np.arange(len(y))
    return float(np.sum(x * y) / total)


def spectral_metrics_for_roi(
    image: np.ndarray,
    roi: dict,
    debug_dir: Path | None = None,
    debug_prefix: str = "",
    show_debug: bool = False,
) -> dict:
    cropped = crop_roi(image, roi)

    # Spectral dimension is Y, so average over X.
    raw_profile = cropped.mean(axis=1)

    if SMOOTHING_ENABLED:
        profile = smooth_profile(raw_profile, SPECTRAL_SMOOTHING_WINDOW)
    else:
        profile = raw_profile

    if debug_dir is not None:
        output_path = debug_dir / f"{debug_prefix}_{roi.get('name', 'roi')}_spectral_profile.png"
        plot_profile_debug(
            raw_profile=raw_profile,
            smooth_profile_data=profile,
            title=f"{debug_prefix} spectral ROI {roi.get('name', 'roi')}",
            output_path=output_path,
            show=show_debug,
        )

    peak_local_y = int(np.argmax(profile))
    peak_fit_local_y = quadratic_peak_pixels(profile)
    centroid_local_y = windowed_centroid_pixels(profile)
    fwhm_y = fwhm_pixels(profile)

    return {
        "roi_name": roi.get("name", "roi"),
        "peak_y_px": roi["y0"] + peak_local_y,
        "peak_fit_y_px": roi["y0"] + peak_fit_local_y,
        "centroid_y_px": roi["y0"] + centroid_local_y,
        "fwhm_px": fwhm_y,
        "peak_intensity": float(np.max(profile)),
        "mean_intensity": float(np.mean(cropped)),
        "smoothing_window": SPECTRAL_SMOOTHING_WINDOW if SMOOTHING_ENABLED else 1,
    }


def spatial_metrics_for_roi(
    image: np.ndarray,
    roi: dict,
    debug_dir: Path | None = None,
    debug_prefix: str = "",
    show_debug: bool = False,
) -> dict:
    cropped = crop_roi(image, roi)

    # Spatial dimension is X, so average over Y.
    raw_esf = cropped.mean(axis=0)

    # Raw LSF from raw edge spread function.
    # This is the profile we use for the actual Gaussian fit.
    raw_lsf = np.abs(np.gradient(raw_esf))

    # Optional smoothed versions are only for visual diagnostics.
    # Do not use smoothed LSF as the main resolution metric because it broadens the peak.
    if SMOOTHING_ENABLED and SPATIAL_SMOOTHING_WINDOW > 1:
        esf_for_plot = smooth_profile(raw_esf, SPATIAL_SMOOTHING_WINDOW)
        lsf_for_plot = smooth_profile(raw_lsf, SPATIAL_SMOOTHING_WINDOW)
    else:
        esf_for_plot = raw_esf
        lsf_for_plot = raw_lsf

    # Old / diagnostic metrics
    raw_lsf_fwhm_x = fwhm_pixels(raw_lsf)
    raw_edge_peak_fit_x = quadratic_peak_pixels(raw_lsf)
    raw_edge_centroid_x = windowed_centroid_pixels(raw_lsf)

    # New recommended Gaussian-fit metrics
    if SPATIAL_LSF_GAUSSIAN_FIT_ENABLED:
        gaussian_fit = fit_gaussian_peak(
            raw_lsf,
            half_window=SPATIAL_LSF_FIT_HALF_WINDOW,
        )
    else:
        gaussian_fit = {
            "fit_success": False,
            "error": "disabled",
            "center_px": np.nan,
            "fwhm_px": np.nan,
        }

    if gaussian_fit.get("fit_success", False):
        edge_gaussian_x = gaussian_fit["center_px"]
        lsf_gaussian_fwhm_x = gaussian_fit["fwhm_px"]
    else:
        edge_gaussian_x = np.nan
        lsf_gaussian_fwhm_x = np.nan

    if debug_dir is not None:
        output_path = debug_dir / f"{debug_prefix}_{roi.get('name', 'roi')}_spatial_esf.png"
        plot_profile_debug(
            raw_profile=raw_esf,
            smooth_profile_data=esf_for_plot,
            title=f"{debug_prefix} spatial ESF ROI {roi.get('name', 'roi')}",
            output_path=output_path,
            show=show_debug,
        )

        output_path = debug_dir / f"{debug_prefix}_{roi.get('name', 'roi')}_spatial_lsf.png"
        plot_profile_debug(
            raw_profile=raw_lsf,
            smooth_profile_data=lsf_for_plot,
            title=f"{debug_prefix} spatial LSF ROI {roi.get('name', 'roi')}",
            output_path=output_path,
            show=show_debug,
            gaussian_fit=gaussian_fit,
        )

    contrast = float(np.percentile(esf_for_plot, 95) - np.percentile(esf_for_plot, 5))

    return {
        "roi_name": roi.get("name", "roi"),

        # Main recommended spatial metrics
        "edge_gaussian_x_px": roi["x0"] + edge_gaussian_x,
        "lsf_gaussian_fwhm_px": lsf_gaussian_fwhm_x,
        "gaussian_fit_success": bool(gaussian_fit.get("fit_success", False)),

        # Diagnostic spatial metrics
        "edge_x_px": roi["x0"] + int(np.argmax(raw_lsf)),
        "edge_peak_fit_x_px": roi["x0"] + raw_edge_peak_fit_x,
        "edge_centroid_x_px": roi["x0"] + raw_edge_centroid_x,
        "lsf_fwhm_px": raw_lsf_fwhm_x,

        "edge_contrast": contrast,
        "mean_intensity": float(np.mean(cropped)),
        "smoothing_window": SPATIAL_SMOOTHING_WINDOW if SMOOTHING_ENABLED else 1,
    }


def average_metric_dicts(metric_dicts: list[dict], prefix: str) -> dict:
    output = {}

    if not metric_dicts:
        return output

    keys = [
        key for key in metric_dicts[0].keys()
        if key != "roi_name"
    ]

    for key in keys:
        values = np.array(
            [m[key] for m in metric_dicts if key in m],
            dtype=float,
        )

        output[f"{prefix}_{key}_mean"] = float(np.nanmean(values))
        output[f"{prefix}_{key}_std"] = float(np.nanstd(values))
        output[f"{prefix}_{key}_n"] = int(np.sum(~np.isnan(values)))

    return output


def get_temperature(summary: dict) -> dict:
    temp = summary.get("temperature_before_sweep") or {}
    return temp.get("temperatures_c", {})


def analyze_sweep(
    sweep_dir: Path,
    debug_dir: Path | None = None,
    show_debug: bool = False,
) -> dict:
    summary_path = sweep_dir / "sweep_summary.json"

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    result = {
        "sweep_name": sweep_dir.name,
        "sweep_index": summary.get("sweep_index"),
        "sweep_started_at": summary.get("sweep_started_at"),
        "sweep_duration_s": summary.get("sweep_duration_s"),
        "transfer_duration_s": summary.get("transfer_duration_s"),
    }

    temps = get_temperature(summary)
    for name, value in temps.items():
        result[f"temp_{name}_c"] = value

    for filt in summary.get("filters", []):
        filter_number = filt["filter_number"]
        cfg = FILTER_ANALYSIS_CONFIG.get(filter_number)

        if cfg is None:
            continue

        image_path = sweep_dir / Path(filt["remote_image_path"]).name

        if not image_path.exists():
            result[f"filter_{filter_number}_missing"] = True
            continue

        image = load_image(image_path)
        name = cfg["name"]

        result[f"{name}_exposure_time_absolute"] = filt.get("exposure_time_absolute")

        if cfg["type"] == "spectral":
            rois = SPECTRAL_LINE_ROIS[name]
            roi_metrics = [
                spectral_metrics_for_roi(
                    image,
                    roi,
                    debug_dir=debug_dir,
                    debug_prefix=f"{sweep_dir.name}_{name}",
                    show_debug=show_debug,
                )
                for roi in rois
            ]

            result.update(average_metric_dicts(roi_metrics, name))

            result[f"{name}_wavelength_nm"] = cfg["wavelength_nm"]
            result[f"{name}_filter_fwhm_nm"] = cfg["filter_fwhm_nm"]

        elif cfg["type"] == "spatial":
            roi_metrics = [
                spatial_metrics_for_roi(
                    image,
                    roi,
                    debug_dir=debug_dir,
                    debug_prefix=f"{sweep_dir.name}_{name}",
                    show_debug=show_debug,
                )
                for roi in SPATIAL_EDGE_ROIS
            ]

            result.update(average_metric_dicts(roi_metrics, name))

    return result


def plot_metric(df: pd.DataFrame, x_col: str, y_cols: list[str], output_path: Path, ylabel: str):
    plt.figure()

    for y_col in y_cols:
        if y_col in df.columns:
            plt.plot(df[x_col], df[y_col], marker="o", label=y_col)

    plt.xlabel(x_col)
    plt.ylabel(ylabel)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def make_plots(df: pd.DataFrame, analysis_dir: Path):
    if "sweep_index" not in df.columns:
        return

    spectral_fwhm_cols = [
        "bp_780_fwhm_px_mean",
        "bp_1064_fwhm_px_mean",
        "bp_1550_fwhm_px_mean",
    ]

    spectral_position_cols = [
        "bp_780_peak_fit_y_px_mean",
        "bp_1064_peak_fit_y_px_mean",
        "bp_1550_peak_fit_y_px_mean",
    ]

    spatial_fwhm_cols = [
        "no_filter_lsf_gaussian_fwhm_px_mean",
    ]

    spatial_position_cols = [
        "no_filter_edge_gaussian_x_px_mean",
    ]

    temp_cols = [
        col for col in df.columns
        if col.startswith("temp_") and col.endswith("_c")
    ]

    plot_metric(
        df,
        "sweep_index",
        spectral_fwhm_cols,
        analysis_dir / "spectral_fwhm_vs_sweep.png",
        "Spectral FWHM [px]",
    )

    plot_metric(
        df,
        "sweep_index",
        spectral_position_cols,
        analysis_dir / "spectral_position_vs_sweep.png",
        "Spectral centroid Y [px]",
    )

    plot_metric(
        df,
        "sweep_index",
        spatial_fwhm_cols,
        analysis_dir / "spatial_resolution_vs_sweep.png",
        "Spatial LSF FWHM [px]",
    )

    plot_metric(
        df,
        "sweep_index",
        spatial_position_cols,
        analysis_dir / "spatial_edge_position_vs_sweep.png",
        "Spatial edge X [px]",
    )

    if temp_cols:
        plot_metric(
            df,
            "sweep_index",
            temp_cols,
            analysis_dir / "temperature_vs_sweep.png",
            "Temperature [C]",
        )

        # Plot core metrics vs first temperature probe.
        x_temp = temp_cols[0]

        plot_metric(
            df,
            x_temp,
            spectral_fwhm_cols,
            analysis_dir / "spectral_fwhm_vs_temperature.png",
            "Spectral FWHM [px]",
        )

        plot_metric(
            df,
            x_temp,
            spatial_fwhm_cols,
            analysis_dir / "spatial_resolution_vs_temperature.png",
            "Spatial LSF FWHM [px]",
        )

def plot_profile_debug(
    raw_profile: np.ndarray,
    smooth_profile_data: np.ndarray,
    title: str,
    output_path: Path,
    show: bool = False,
    gaussian_fit: dict | None = None,
):
    plt.figure()

    x = np.arange(len(raw_profile))

    plt.plot(x, raw_profile, label="Raw profile", alpha=0.7)
    plt.plot(x, smooth_profile_data, label="Smoothed profile", linewidth=2)

    raw_fwhm = fwhm_pixels(raw_profile)
    smooth_fwhm = fwhm_pixels(smooth_profile_data)

    raw_peak_fit = quadratic_peak_pixels(raw_profile)
    smooth_peak_fit = quadratic_peak_pixels(smooth_profile_data)

    raw_centroid = windowed_centroid_pixels(raw_profile)
    smooth_centroid = windowed_centroid_pixels(smooth_profile_data)

    plt.axvline(
        raw_peak_fit,
        linestyle="--",
        label=f"Raw peak-fit: {raw_peak_fit:.2f}",
    )

    plt.axvline(
        smooth_peak_fit,
        linestyle="--",
        label=f"Smooth peak-fit: {smooth_peak_fit:.2f}",
    )

    plt.axvline(
        raw_centroid,
        linestyle=":",
        label=f"Raw centroid: {raw_centroid:.2f}",
    )

    plt.axvline(
        smooth_centroid,
        linestyle=":",
        label=f"Smooth centroid: {smooth_centroid:.2f}",
    )

    title_extra = (
        f"Raw FWHM={raw_fwhm:.3f}px, Smooth FWHM={smooth_fwhm:.3f}px"
    )

    if gaussian_fit is not None and gaussian_fit.get("fit_success"):
        x_fit = np.arange(
            gaussian_fit["fit_i0"],
            gaussian_fit["fit_i1"],
            dtype=float,
        )

        y_fit = gaussian_with_offset(
            x_fit,
            gaussian_fit["amplitude"],
            gaussian_fit["center_px"],
            gaussian_fit["sigma_px"],
            gaussian_fit["offset"],
        )

        plt.plot(
            x_fit,
            y_fit,
            linestyle="-.",
            linewidth=2,
            label=(
                f"Gaussian fit: center={gaussian_fit['center_px']:.2f}, "
                f"FWHM={gaussian_fit['fwhm_px']:.2f}"
            ),
        )

        title_extra += (
            f"\nGaussian FWHM={gaussian_fit['fwhm_px']:.3f}px, "
            f"center={gaussian_fit['center_px']:.3f}px"
        )

    elif gaussian_fit is not None:
        title_extra += f"\nGaussian fit failed: {gaussian_fit.get('error', 'unknown')}"

    plt.title(f"{title}\n{title_extra}")
    plt.xlabel("Profile pixel index within ROI")
    plt.ylabel("Intensity")
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_path, dpi=200)

    if show:
        plt.show(block=True)

    plt.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("test_folder", type=Path)
    args = parser.parse_args()

    test_folder = args.test_folder
    analysis_dir = test_folder / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    debug_dir = analysis_dir / "profile_debug"
    if DEBUG_PROFILE_PLOTS:
        debug_dir.mkdir(exist_ok=True)
    else:
        debug_dir = None

    sweep_dirs = sorted(test_folder.glob("sweep_*"))

    rows = []
    for idx, sweep_dir in enumerate(sweep_dirs):
        try:
            show_debug = DEBUG_PROFILE_PLOTS and idx < DEBUG_PROFILE_PLOT_MAX_SWEEPS
    
            rows.append(
                analyze_sweep(
                    sweep_dir,
                    debug_dir=debug_dir,
                    show_debug=show_debug,
                )
            )
        except Exception as e:
            rows.append({
                "sweep_name": sweep_dir.name,
                "analysis_error": str(e),
            })

    df = pd.DataFrame(rows)

    csv_path = analysis_dir / "sweep_metrics.csv"
    df.to_csv(csv_path, index=False)

    make_plots(df, analysis_dir)

    print(f"Analysis complete: {analysis_dir}")
    print(f"CSV written to: {csv_path}")


if __name__ == "__main__":
    main()