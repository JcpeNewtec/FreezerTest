# Project context and owner review

Status: historical chat context retrieved on 23 October 2026; updated by owner reviews on 27 and 29 October 2026.

This page retains useful historical context alongside the owner's later clarifications. The latest applicable owner confirmation takes precedence over an earlier suggestion or unknown. Current hardware and operating details live in their respective chapters; this page does not reproduce individual results or promote old proposals into installed features.

## Current scope and normal preparation

The owner confirms that the apparatus tests variants in the **Qtec Hypervision camera family**, with no single fixed reference camera. The test has two purposes: assess repeatability across units of the same type, and evaluate the effects of changes. The camera family is an owner-supplied identification; it is not evidence that the reviewed scripts use a manufacturer SDK. Current capture code uses V4L2 and GStreamer. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [capture pipeline](../Camera_scripts/camera_control.py#L114).

Normal pre-cool uses **`probe_5` at 5 °C**. The 12 °C value in the preserved local configuration was intentionally used for a shorter recent trial. Operators verify/calibrate filter positions before every run because the internal motor reference may drift, and manually focus on the target plane whenever the camera changes. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [operating preparation](04-running-the-test.md#operator-preparation).

An earlier camera warm-start workaround was abandoned after the owner traced the startup problem to faulty camera hardware, which was unacceptable. It is not part of the normal procedure or an outstanding implementation task; the reviewed runner has no warm-start feature. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [camera startup sequence](../Scripts/run_long_test.py#L559).

The owner confirms the thermal sequence: freezer cooling with camera off, then freezer off before camera startup. The camera and sweep-switched lamp warm the chamber toward its endpoint; camera/freezer operation does not overlap normally. Removing camera power directly is the accepted routine shutdown practice. The usual map is exterior-shell probes 1–3 and opposite tray-surface probes 4–5, with changes allowed per test. The PTFE/cage target, halogen reflector, photographed components, and DRTB-2 connector family are now described in [hardware](02-hardware-and-connections.md). The local AI's repository access via deploy SSH key is also owner-confirmed. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

## Camera construction reported by the owner

Source: **Freezer Camera Drift Analysis**, owner message dated **31 August 2026**; [T2 provenance](10-sources-and-maintenance.md#t2-freezer-camera-drift-analysis). These details describe the build discussed then and should not be assumed identical across every Hypervision variant or unit.

| Item | What the owner stated | Evidence boundary / review needed |
|---|---|---|
| Optical architecture | Camera is based on an Offner setup | Optical prescription and current revision not available |
| Slit support | Slit is in a steel cup | Steel grade and dimensions not established |
| Structural rods | Stainless steel 304 | Number, dimensions, attachment, and current material certificates unknown |
| Grating holder | Polycarbonate | Grade, manufacture, geometry, and current revision unknown |
| Holder design intent | Differential expansion relative to steel is intended to keep the light path length constant as temperature changes | A design rationale, not a validated compensation calculation; no optical/mechanical model recovered |
| Grating bond | Loctite superglue to the holder | Exact product, substrate, bond pattern, thickness, cure, and date unknown |
| Mirror bond | Casco SuperFix+ to the top plate | Exact product revision, mirror substrate, bond geometry, cure, and current assembly state unknown |

The owner attached four images in that chat, but their pixels were not returned by the history tool. Therefore, details the earlier assistant inferred visually—spring/adjuster layout, column count, plate material, adhesive thickness—are **not adopted as confirmed hardware facts** here.

Qtec's family documentation provides product context, but the detector, optics, and materials used in any particular prototype must be tied to that unit's revision record. Historical assistant assertions and a generic product specification do not establish an as-built configuration for every tested camera.

The local test notes contain `PC Grating Holder`. That is configured descriptive metadata, not proof that every past or future test uses the same construction. [Local configuration](reference/local_config_snapshot.txt#L69).

## Freezer and wiring context

Source: **Temperature Test Control**, owner messages dated **22 April and 22 June 2026**; [T3 provenance](10-sources-and-maintenance.md#t3-temperature-test-control).

- The owner described thermocouple wires and 24 V power wires crossing the chamber boundary. The connector family is now identified as Omega DRTB-2; the chamber photograph shows the terminal arrangement. The exact boundary seals, fitted terminal-block suffix, strain relief, and full wiring map remain unrecorded.
- The owner stated that the freezer has an internal fan used while cooling. Its independent control, duty cycle, direction, and operation when freezer power is switched off remain unknown.
- Condensation on bandpass filter surfaces was explicitly reported as a setup problem associated with reduced signal and blurred spatial information at lower temperatures. This establishes a measurement-validity concern, not a quantified camera performance result.
- The owner wanted automatic camera shutdown and overnight operation. Relay power removal is now confirmed as accepted routine operation; the repository describes how cleanup/repeats are implemented.

The chamber photograph shows dishes of granular material, but its identity and conditioning state are not confirmed. Earlier suggestions for purge, optical enclosures, local heating, humidity/dew-point logging, or improved seals are not treated as installed controls. The code has no humidity channel, dew-point calculation, purge control, or filter-heater loop. [Chamber photo](reference/component-photos/IMG_5292.jpg).

The earlier assistant mentioned a 0–40 °C range without establishing a permanent specification. The preserved local profile selects 12–40 °C probe thresholds for the shorter trial, while the owner confirms normal pre-cool at 5 °C on `probe_5`. Probe thresholds are not a qualification of the chamber's full operating range. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [historical local profile](reference/local_config_snapshot.txt#L5).

## Control-software development context

Source: **Python script for Tic controller**, available messages dated **16–20 October 2026**; [T1 provenance](10-sources-and-maintenance.md#t1-python-script-for-tic-controller).

### Device naming and deployed-file integrity

Earlier chat responses proposed camera-device discovery and readiness changes, including a `/dev/qtec/video0` path. The present source still configures `/dev/video4`. A diagnostic script named `test_camera_boot_keepalive.py` appears in pasted historical console text but is not among the supplied source files. Do not cite historical proposed helpers as available tools in this checkout.

A historical deployed-file corruption problem shows why local and remote sources should be compared when diagnosing import failures; its cause was not proven. It is not a reason in this knowledge base to replace the owner's accepted direct power-cut procedure. The deployment helper copies files and does not implement atomic deployment or remote integrity verification.

### Camera storage is a staging area

The chat's explanation that camera data is staged remotely, copied to the host, checked, and removed is consistent with the reviewed sweep code. Exceptions before cleanup can leave remote data behind. This behavior is documented as current source behavior, not solely as a historical assistant assertion. [Sweep transfer](../Scripts/run_single_sweep_remote.py#L390), [data reference](05-data-and-metadata.md).

## What was deliberately not imported

Individual camera outcomes, amounts/directions of image movement, comparative resolution trends, raw console logs, per-run folders, and proposed causes of camera drift are reserved for the future camera-development knowledge base. Earlier advice about materials or adhesives is not promoted into supplier specifications. Missing attachments and older conversation turns are listed as coverage gaps in [sources](10-sources-and-maintenance.md).
