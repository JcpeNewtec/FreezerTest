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

        rect = Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            fill=False,
            edgecolor ="red",
            linewidth=2,
        )
        ax.add_patch(rect)

        ax.text(
            x0,
            y0,
            roi.get("name", "roi"),
            color="red",
            fontsize=9,
            bbox={
                "facecolor": "white",
                "alpha": 0.8,
                "edgecolor": "red",
            },
        )

    ax.set_xlabel("X / spatial axis [px]")
    ax.set_ylabel("Y / spectral axis [px]")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    all_figures.append(fig)


def get_rois_for_filter(cfg):
    rois = []

    if cfg["type"] == "spatial":
        rois.extend(SPATIAL_EDGE_ROIS)

        for roi in NO_FILTER_SIGNAL_ROIS:
            roi_copy = dict(roi)
            roi_copy["name"] = f"signal_{roi_copy.get('name', 'roi')}"
            rois.append(roi_copy)

    elif cfg["type"] == "spectral":
        rois.extend(SPECTRAL_LINE_ROIS[cfg["name"]])

    return rois


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
            title=f"Filter {filter_number}: {cfg['name']}",
            output_path=output_path,
        )

        print(f"Saved: {output_path}")

    print(f"\nROI previews saved to: {output_dir}")
    
    plt.show()


if __name__ == "__main__":
    main()