# Project context and owner review

Status: historical chat context retrieved on 23 October 2026; updated by owner review on 27 October 2026.

This page combines setup facts recovered from three accessible project chats with the owner's subsequent clarifications. The 27 October review takes precedence where it corrects historical discussion. It does not reproduce individual result logs or camera-performance conclusions. A prior assistant suggestion is not evidence that a component was installed or a patch applied.

## Current scope and normal preparation

The owner confirms that the apparatus tests variants in the **Qtec Hypervision camera family**, with no single fixed reference camera. The test has two purposes: assess repeatability across units of the same type, and evaluate the effects of changes. The camera family is an owner-supplied identification; it is not evidence that the reviewed scripts use a manufacturer SDK. Current capture code uses V4L2 and GStreamer. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [capture pipeline](../Camera_scripts/camera_control.py#L114).

Normal pre-cool uses **`probe_5` at 5 °C**. The 12 °C value in the preserved local configuration was intentionally used for a shorter recent trial. Operators verify/calibrate filter positions before every run because the internal motor reference may drift, and manually focus on the target plane whenever the camera changes. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [operating preparation](04-running-the-test.md#operator-preparation).

An earlier camera warm-start workaround was abandoned after the owner traced the startup problem to faulty camera hardware, which was unacceptable. It is not part of the normal procedure or an outstanding implementation task; the reviewed runner has no warm-start feature. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [camera startup sequence](../Scripts/run_long_test.py#L559).

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

- The owner described thermocouple wires and 24 V power wires passing between the freezer interior and exterior. The actual pass-through route, seals, connector types, strain relief, and wiring diagram were not confirmed.
- The owner stated that the freezer has an internal fan used while cooling. Its independent control, duty cycle, direction, and operation when freezer power is switched off remain unknown.
- Condensation on bandpass filter surfaces was explicitly reported as a setup problem associated with reduced signal and blurred spatial information at lower temperatures. This establishes a measurement-validity concern, not a quantified camera performance result.
- The owner wanted automatic camera shutdown and overnight operation. Current relay control and repeat orchestration address parts of that intent, but the repository is the authority for what is implemented.

Earlier suggestions included desiccant, dry-air or nitrogen purge, an optical enclosure, local heating, humidity/dew-point logging, and improved cable sealing. **None of those is confirmed as installed.** The reviewed software has no humidity channel, dew-point calculation, purge control, or filter-heater loop. Their existence or absence physically must be checked with the owner.

The earlier assistant mentioned a 0–40 °C range without establishing a permanent specification. The preserved local profile selects 12–40 °C probe thresholds for the shorter trial, while the owner confirms normal pre-cool at 5 °C on `probe_5`. Probe thresholds are not a qualification of the chamber's full operating range. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [historical local profile](reference/local_config_snapshot.txt#L5).

## Control-software development context

Source: **Python script for Tic controller**, available messages dated **16–20 October 2026**; [T1 provenance](10-sources-and-maintenance.md#t1-python-script-for-tic-controller).

### Device naming and deployed-file integrity

Earlier chat responses proposed camera-device discovery and readiness changes, including a `/dev/qtec/video0` path. The present source still configures `/dev/video4`. A diagnostic script named `test_camera_boot_keepalive.py` appears in pasted historical console text but is not among the supplied source files. Do not cite historical proposed helpers as available tools in this checkout.

The chat also discusses a deployed camera Python file containing NUL bytes. That is useful deployment context: the host source and remote copy may differ. The cause was not proven. Hard power removal was suggested as one possible explanation; it is not established here as the cause of file corruption. The current deployment script copies files; the knowledge base does not claim it implements atomic deployment or remote integrity verification.

### Camera storage is a staging area

The chat's explanation that camera data is staged remotely, copied to the host, checked, and removed is consistent with the reviewed sweep code. Exceptions before cleanup can leave remote data behind. This behavior is documented as current source behavior, not solely as a historical assistant assertion. [Sweep transfer](../Scripts/run_single_sweep_remote.py#L390), [data reference](05-data-and-metadata.md).

## What was deliberately not imported

Individual camera outcomes, amounts/directions of image movement, comparative resolution trends, raw console logs, per-run folders, and proposed causes of camera drift are reserved for the future camera-development knowledge base. Earlier advice about materials or adhesives is not promoted into supplier specifications. Missing attachments and older conversation turns are listed as coverage gaps in [sources](10-sources-and-maintenance.md).
