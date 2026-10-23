# Glossary

Status: terminology for version 0.1

| Term | Meaning here |
|---|---|
| Bandpass filter | Optical filter passing a limited wavelength band; configured at 780, 1064, and 1550 nm. Nominal bandwidth is not the measured instrument width |
| Capture | One camera image and its sidecar metadata at one filter position |
| Centroid | Intensity-weighted profile coordinate; distinct from the raw peak location or a fitted center |
| DAQ | Data-acquisition device; the network MCC unit reads thermocouples and handles digital input/output |
| DIO | Digital input/output; individual bits control lamp, camera power, and freezer, and read the Hall sensor |
| DN | Digital number, an image's numerical intensity value; not automatically photons, electrons, radiance, or normalized signal |
| Edge position | Coordinate of the selected spatial transition; selection depends on ROI and edge-search mode |
| ESF | Edge-spread function, a profile across an image edge |
| Filter position | Wheel slot number mapped to a configured motor coordinate; not necessarily degrees or full motor steps |
| FWHM | Full width at half maximum. Spectral and spatial widths in the present pipeline are image-pixel widths |
| GRAY8 | Configured 8-bit grayscale capture format; not evidence of the detector's native ADC precision |
| Hall sensor | Magnetic reference input used to home the filter wheel; configured active-low |
| Homing | Searching for a Hall edge, approaching it slowly, and setting the motor coordinate reference |
| Keepalive stream | Continuous discarded-frame camera stream between sweeps; paused for still capture when configured |
| Local override | A setting imported from `Config/local_config.py` into system configuration, with effect only where code consumes it |
| LSF | Line-spread function; spatial analysis derives an edge-gradient profile and fits a Gaussian locally for its main width metric |
| MCC / uldaq | Measurement Computing device ecosystem and the Python-facing Universal Library interface used in this project |
| Offner | The optical architecture named by the owner; the detailed prescription is not supplied |
| PNG sidecar | JSON metadata file accompanying a captured PNG image |
| Pre-cool | Freezer-on stage before measurement; reaching the configured probe threshold completes it, while timeout aborts the test |
| Probe | Named external temperature channel such as `probe_5`; physical attachment points remain to be confirmed |
| Repeat | One complete test within an automated sequence, normally with its own test directory |
| Repeat group | Identifier used to associate repeat tests; current default is camera ID plus date |
| ROI | Region of interest; configured rectangular image crop, using x for columns/spatial direction and y for rows/spectral direction |
| SCP / SSH | File-transfer and remote-command tools linking host and camera |
| Spatial noise | Within-image variation of pixel DN in an ROI; differs from variation over repeated frames at the same pixel |
| Sweep | Sequential captures at all configured filter positions, plus metadata and transfer |
| TEC | Thermoelectric cooler; references to it do not establish a particular mode, setpoint, or control implementation in this repository |
| Tic / ticcmd | Stepper controller and command-line interface used to move the filter wheel |
| V4L2 | Linux video/control interface used by the camera scripts |

Metric-specific definitions and formulas are in [analysis methodology](06-analysis-methodology.md); filenames and field definitions are in [data and metadata](05-data-and-metadata.md).
