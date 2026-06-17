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
    {"name": "edge_1", "x0": 720, "x1": 750, "y0": 460, "y1": 500},
]

SPECTRAL_LINE_ROIS = {
    "bp_780": [
        {"name": "roi_1", "x0": 620, "x1": 650, "y0": 260, "y1": 300},
    ],
    "bp_1064": [
        {"name": "roi_1", "x0": 620, "x1": 650, "y0": 460, "y1": 500},
    ],
    "bp_1550": [
        {"name": "roi_1", "x0": 620, "x1": 650, "y0": 815, "y1": 855},
    ],
}

# Smoothing
# For spectral lines the raw profiles are already clean, so smoothing should usually be off.
# A window of 1 means "no smoothing".
SMOOTHING_ENABLED = True
SPECTRAL_SMOOTHING_WINDOW = 1
SPATIAL_SMOOTHING_WINDOW = 1

DEBUG_PROFILE_PLOTS = False
DEBUG_PROFILE_PLOT_MAX_SWEEPS = 1

SPATIAL_LSF_GAUSSIAN_FIT_ENABLED = True
SPATIAL_LSF_FIT_HALF_WINDOW = 5