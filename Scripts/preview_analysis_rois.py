#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 14:29:38 2026

@author: jcpe
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.patches import Rectangle

from Config.analysis_config import (
    FILTER_ANALYSIS_CONFIG,
    SPATIAL_EDGE_ROIS,
    SPECTRAL_LINE_ROIS,
    NO_FILTER_SIGNAL_ROIS,
    NOISE_ANALYSIS_FILTER,
    NOISE_ROIS,
)

all_figures = []

def load_image(path: Path) -> np.ndarray:
    return np.array(Image.open(path))


def draw_rois(image, rois, title, output_path):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(image, cmap="gray")
    ax.set_title(title)

    for roi in rois:
        x0, x1 = roi["x0"], roi["x1"]
        y0, y1 = roi["y0"], roi["y1"]

        color = roi_color(roi)
        group = roi.get("preview_group", "roi")
        name = roi.get("name", "roi")

        rect = Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            fill=False,
            edgecolor=color,
            linewidth=2,
        )
        ax.add_patch(rect)

        ax.text(
            x0,
            y0,
            f"{group}: {name}",
            color=color,
            fontsize=9,
            bbox={
                "facecolor": "black",
                "alpha": 0.65,
                "edgecolor": color,
            },
        )

        if group == "spatial_edge":
            draw_spatial_target_lines(ax, roi)

    ax.set_xlabel("X / spatial axis [px]")
    ax.set_ylabel("Y / spectral axis [px]")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    all_figures.append(fig)


def get_rois_for_filter(cfg: dict) -> list[dict]:
    rois = []
    filter_name = cfg["name"]

    if cfg["type"] == "spatial":
        for roi in SPATIAL_EDGE_ROIS:
            roi_copy = dict(roi)
            roi_copy["preview_group"] = "spatial_edge"
            rois.append(roi_copy)

        for roi in NO_FILTER_SIGNAL_ROIS:
            roi_copy = dict(roi)
            roi_copy["name"] = f"signal_{roi_copy.get('name', 'roi')}"
            roi_copy["preview_group"] = "no_filter_signal"
            rois.append(roi_copy)

    elif cfg["type"] == "spectral":
        for roi in SPECTRAL_LINE_ROIS.get(filter_name, []):
            roi_copy = dict(roi)
            roi_copy["preview_group"] = "spectral_line"
            rois.append(roi_copy)

        if filter_name == NOISE_ANALYSIS_FILTER:
            for roi in NOISE_ROIS:
                roi_copy = dict(roi)
                roi_copy["name"] = f"noise_{roi_copy.get('name', 'roi')}"
                roi_copy["preview_group"] = "dark_noise"
                rois.append(roi_copy)

    return rois

def draw_spatial_target_lines(ax, roi: dict):
    """
    Draw extra guides for spatial edge-search ROIs.

    Supports:
    - fixed_target mode:
        target_x +/- search_half_width

    - dark_line_auto mode:
        dark_line_target_x +/- dark_line_search_half_width
        and an approximate edge-search region relative to the expected dark-line target.
    """
    mode = roi.get("edge_search_mode", "fixed_target")

    y0 = roi["y0"]
    y1 = roi["y1"]

    if mode == "dark_line_auto":
        target_x = roi.get("dark_line_target_x", roi.get("target_x"))

        if target_x is None:
            return

        dark_line_search_half_width = roi.get(
            "dark_line_search_half_width",
            roi.get("search_half_width"),
        )

        ax.axvline(
            target_x,
            linestyle="--",
            linewidth=1.5,
            color="yellow",
            label=f"{roi.get('name', 'roi')} dark-line target",
        )

        ax.text(
            target_x,
            y0 - 8,
            "dark-line target",
            color="yellow",
            fontsize=8,
            rotation=90,
            verticalalignment="bottom",
        )

        if dark_line_search_half_width is not None:
            search_x0 = target_x - dark_line_search_half_width
            search_x1 = target_x + dark_line_search_half_width

            ax.axvline(search_x0, linestyle=":", linewidth=1.0, color="yellow")
            ax.axvline(search_x1, linestyle=":", linewidth=1.0, color="yellow")

            ax.fill_betweenx(
                [y0, y1],
                search_x0,
                search_x1,
                color="yellow",
                alpha=0.12,
            )

        side = roi.get("dark_line_edge_side", "right")
        min_px = roi.get("edge_from_dark_line_min_px", 4)
        max_px = roi.get("edge_from_dark_line_max_px", 35)

        if side == "right":
            edge_x0 = target_x + min_px
            edge_x1 = target_x + max_px
        elif side == "left":
            edge_x0 = target_x - max_px
            edge_x1 = target_x - min_px
        else:
            return

        ax.fill_betweenx(
            [y0, y1],
            edge_x0,
            edge_x1,
            color="magenta",
            alpha=0.18,
        )

        ax.axvline(edge_x0, linestyle="-.", linewidth=1.0, color="magenta")
        ax.axvline(edge_x1, linestyle="-.", linewidth=1.0, color="magenta")

        ax.text(
            (edge_x0 + edge_x1) / 2,
            y1 + 8,
            f"{side} edge search",
            color="magenta",
            fontsize=8,
            horizontalalignment="center",
        )

        return

    # Default/fallback: fixed target mode
    target_x = roi.get("target_x")

    if target_x is None:
        return

    ax.axvline(
        target_x,
        linestyle="--",
        linewidth=1.5,
        color="yellow",
        label=f"{roi.get('name', 'roi')} target_x",
    )

    ax.text(
        target_x,
        y0 - 8,
        "target_x",
        color="yellow",
        fontsize=8,
        rotation=90,
        verticalalignment="bottom",
    )

    search_half_width = roi.get("search_half_width")

    if search_half_width is not None:
        search_x0 = target_x - search_half_width
        search_x1 = target_x + search_half_width

        ax.axvline(search_x0, linestyle=":", linewidth=1.0, color="yellow")
        ax.axvline(search_x1, linestyle=":", linewidth=1.0, color="yellow")

        ax.fill_betweenx(
            [y0, y1],
            search_x0,
            search_x1,
            color="yellow",
            alpha=0.12,
        )
        
def roi_color(roi: dict) -> str:
    group = roi.get("preview_group", "roi")

    if group == "spatial_edge":
        return "red"
    if group == "no_filter_signal":
        return "lime"
    if group == "spectral_line":
        return "cyan"
    if group == "dark_noise":
        return "yellow"

    return "red"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sweep_folder", type=Path)
    args = parser.parse_args()

    sweep_folder = args.sweep_folder
    summary_path = sweep_folder / "sweep_summary.json"

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    output_dir = sweep_folder / "analysis_roi_preview"
    output_dir.mkdir(exist_ok=True)

    for filt in summary["filters"]:
        filter_number = filt["filter_number"]
        cfg = FILTER_ANALYSIS_CONFIG.get(filter_number)

        if cfg is None:
            continue

        image_path = sweep_folder / Path(filt["remote_image_path"]).name

        if not image_path.exists():
            print(f"Missing image: {image_path}")
            continue

        image = load_image(image_path)
        rois = get_rois_for_filter(cfg)

        output_path = output_dir / f"filter_{filter_number}_{cfg['name']}_roi_preview.png"

        draw_rois(
            image=image,
            rois=rois,
            title=f"Filter {filter_number}: {cfg['name']} ROI preview",
            output_path=output_path,
        )

        print(f"Saved: {output_path}")

    print(f"\nROI previews saved to: {output_dir}")
    
    plt.show()


if __name__ == "__main__":
    main()