#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 13:57:23 2026

@author: jcpe
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

FILTER_ANALYSIS_CONFIG = {
    1: {
        "type": "spatial",
        "name": "no_filter",
    },
    2: {
        "type": "spectral",
        "name": "bp_780",
        "wavelength_nm": 780,
        "filter_fwhm_nm": 3,
    },
    3: {
        "type": "spectral",
        "name": "bp_1064",
        "wavelength_nm": 1064,
        "filter_fwhm_nm": 3,
    },
    4: {
        "type": "spectral",
        "name": "bp_1550",
        "wavelength_nm": 1550,
        "filter_fwhm_nm": 4,
    },
}

# Coordinates are Python image coordinates:
# x = spatial axis, y = spectral axis
# ROI format: x0, x1, y0, y1

SPATIAL_EDGE_ROIS = [
    {
        "name": "central_dark_line_auto_right_edge",

        # Large enough to contain the central dark line even when the image shifts.
        "x0": 450,
        "x1": 640,
        "y0": 460,
        "y1": 500,

        # New mode: first find the dark vertical line, then find the edge.
        "edge_search_mode": "dark_line_auto",

        # Which edge of the dark line to measure.
        # right = dark-to-bright edge on the right side of the dark bar
        # left  = bright-to-dark edge on the left side of the dark bar
        "dark_line_edge_side": "right",

        # Initial expected position of the dark line center in full-image coordinates.
        # This is only used to avoid selecting the wrong dark line if multiple lines are in the ROI.
        "dark_line_target_x": 560,

        # Search range around dark_line_target_x for finding the dark line center.
        # Make this wide enough to handle test-to-test variation.
        "dark_line_search_half_width": 80,

        # Once the dark line center is found, search for the edge within this distance.
        # Should be wide enough to reach the side edge, but not so wide that it reaches the next bar.
        "edge_from_dark_line_min_px": 4,
        "edge_from_dark_line_max_px": 35,

        # Keep signed polarity to avoid jumping to the opposite edge.
        # right edge should normally be positive: dark-to-bright.
        "edge_polarity": "positive",
    },
]


SPECTRAL_LINE_ROIS = {
    "bp_780": [
        {"name": "roi_1", "x0": 620, "x1": 650, "y0": 245, "y1": 300},
        {"name": "roi_2", "x0": 450, "x1": 480, "y0": 245, "y1": 300},
        {"name": "roi_3", "x0": 760, "x1": 790, "y0": 245, "y1": 300},
    ],
    "bp_1064": [
        {"name": "roi_1", "x0": 620, "x1": 650, "y0": 450, "y1": 500},
        {"name": "roi_2", "x0": 450, "x1": 480, "y0": 450, "y1": 500},
        {"name": "roi_3", "x0": 760, "x1": 790, "y0": 450, "y1": 500},
    ],
    "bp_1550": [
        {"name": "roi_1", "x0": 620, "x1": 650, "y0": 790, "y1": 855},
        {"name": "roi_2", "x0": 450, "x1": 480, "y0": 790, "y1": 855},
        {"name": "roi_3", "x0": 760, "x1": 790, "y0": 790, "y1": 855},
    ],
}


NO_FILTER_SIGNAL_ROIS = [
        {"name": "signal_1", "x0": 600, "x1": 670, "y0": 460, "y1": 540},
        {"name": "signal_2", "x0": 600, "x1": 670, "y0": 540, "y1": 620},
    ]

NOISE_ANALYSIS_FILTER = "bp_1550"

NOISE_ROIS = [
        {"name": "noise_1", "x0": 200, "x1": 680, "y0": 460, "y1": 540},
        {"name": "noise_2", "x0": 200, "x1": 680, "y0": 540, "y1": 620},
    ]

# Smoothing
# For spectral lines the raw profiles are already clean, so smoothing should usually be off.
# A window of 1 means "no smoothing".
SMOOTHING_ENABLED = True
SPECTRAL_SMOOTHING_WINDOW = 1
SPATIAL_SMOOTHING_WINDOW = 1

# Spatial LSF Gaussian fitting
SPATIAL_LSF_GAUSSIAN_FIT_ENABLED = True
SPATIAL_LSF_FIT_HALF_WINDOW = 5

# Debug profile plots
# Turn this on while tuning ROIs/metrics.
DEBUG_PROFILE_PLOTS = True
DEBUG_PROFILE_PLOT_MAX_SWEEPS = 1