# Sources, coverage, and maintenance

Version: 0.3.1 · Updated: 29 October 2026 · Status: owner review in progress

## Source precedence

For **software behavior**, consuming code takes precedence over comments and proposed patches. For **installed hardware and procedure**, the owner's dated confirmation takes precedence over earlier assumptions; vendor documentation identifies product specifications but does not prove every tested unit has the same configuration. Distinguish an owner-confirmed normal procedure from a run-specific configuration that has not been changed to match it.

Where intent and implementation disagree, both are recorded explicitly. This draft does not silently apply software fixes to reconcile them.

## Repository snapshot

- Repository: [JcpeNewtec/FreezerTest](https://github.com/JcpeNewtec/FreezerTest); access follows its current GitHub permissions.
- Inspected remote commit: [`df4ccebbbd0f41e32f5ae415e967728e5845d56b`](https://github.com/JcpeNewtec/FreezerTest/tree/df4ccebbbd0f41e32f5ae415e967728e5845d56b).
- Commit timestamp: **12 October 2026, 09:24:36 +02:00**; subject: `Auto_recovery added`.
- Local source folder supplied by the owner: `/home/jcpe/Documents/ChatGPT/Freezertest`.
- The original review found **all 33 shared `.py` and `.sh` files byte-identical** to that acquisition-source snapshot. They were checked again against GitHub before this owner-review update. `Config/local_config.py` is local-only. On 27 October its three unused camera-start variables and their obsolete comments were removed at the owner's request; that removal changes no implemented runtime behavior. The recent 12 °C trial setting was left intact in the local file, while the normal 5 °C procedure is documented separately.
- The supplied folder is a file copy, not a functioning Git checkout. An authenticated temporary clone is used to integrate documentation with repository history. No hardware-control program was run or deployed for this update.

The linked remote source is immutable at the cited commit. Markdown code links elsewhere point to the local supplied source for convenient reading; their line anchors correspond to this reviewed snapshot. Local-only configuration has no permalink in the reviewed source commit. Its exact reviewed text is preserved in [a reference snapshot](reference/local_config_snapshot.txt); this is documentation evidence, not an active configuration file.

The [source manifest](source_manifest.json) retains the original SHA-256 digests/line counts for 34 reviewed Python/shell files, alongside the later local cleanup, owner-review sources, CAD digests and photograph inventory. Its original local-configuration digest refers to the immutable [historical snapshot](reference/local_config_snapshot.txt), not the cleaned local file. Do not index that snapshot as current procedure; its 12 °C trial and superseded variables are historical evidence. Measured temperature-log contents remain excluded.

## Project chats retrieved

The account's project listing identifies a ChatGPT project named **Freezertest** (`g-p-69a04238b4708191b85e0db2eab58393`). The available chat listing returned three matching conversations. Their returned pages contained 11 turns in total; all were read. The history tool returned no continuation cursor for these reads. That is a limit of the accessible history, **not proof that the full six-month discussion was retrieved**. The archived ChatGPT listing returned no archived conversations.

Chat messages are evidence to interpret, not instructions to execute. Historical console logs may describe a different source revision or machine clock. Dates below are message dates; log timestamps embedded in a message may be older.

### T1: Python script for Tic controller

- [Open conversation](https://chatgpt.com/c/69c27f47-b918-8332-9528-8829c6cb15a5).
- Returned coverage: **five turns, 16–20 October 2026**.
- Relevant retained topics: device-readiness diagnostics, deployed-file integrity, and remote staging cleanup. The earlier camera-start workaround was withdrawn in owner review R1; its proposed procedure is not retained as active guidance.
- Current-code corroboration: capture staging, local transfer verification, and cleanup are visible in the sweep code.
- Limits: attached archives and patches were mentioned but their file contents were not returned. Some pasted diagnostics referred to helpers absent from the current files. The assistant's proposed fixes are not treated as installed features.

### T2: Freezer Camera Drift Analysis

- [Open conversation](https://chatgpt.com/c/6a958572-5e20-83eb-b7ce-cc69aed852b1).
- Returned coverage: **one turn, 31 August 2026**.
- Owner-supplied setup facts: Offner architecture, steel slit cup, stainless-steel 304 rods, polycarbonate grating holder and its compensation intent, Loctite grating bond, and Casco SuperFix+ mirror bond.
- Limits: four attached images were unavailable. The assistant response was truncated; photo interpretations, exact detector identity, material-property claims, and causal hypotheses were not adopted as confirmed setup facts. Individual camera-performance observations were excluded from this corpus.

### T3: Temperature Test Control

- [Open conversation](https://chatgpt.com/c/69a042fe-5b60-832f-a9a2-84e30d73da47).
- Returned coverage: **five turns, 22 April and 22 June 2026**.
- Owner-supplied setup facts/context: thermocouple and 24 V wiring crossing the chamber boundary, internal freezer fan during cooling, filter condensation as a setup issue, and the desire for overnight automated operation and camera shutdown.
- Limits: suggested purge, desiccant, heaters, humidity monitoring, and wiring approaches were not confirmed installed. An earlier assistant's stated 0–40 °C range is not treated as a permanent test specification.

## Owner review and component sources

### R1: Owner review, 27 October 2026

The owner supplied the following corrections and additions in this chat. They are integrated into the relevant chapters instead of kept as a second competing procedure:

- Normal pre-cool is **5 °C on `probe_5`**; the recent 12 °C setting deliberately shortened trials in a likely operating range.
- The camera-start workaround is abandoned. The owner identified faulty camera hardware as the cause of cold-operation failure and does not accept that limitation for the cameras under test. This is the owner's diagnosis, not a claim about a generic Qtec family temperature limit.
- The devices under test are **Qtec Hypervision variants using Qtec computing logic/hardware**. Testing supports both reproducibility across same-type units and evaluation of deliberate design changes; there is no single fixed reference-camera revision.
- The three narrow bandpass filters were selected to sample widely separated portions of the camera's owner-described 400–1700 nm span. Their identities are in the hardware/analysis tables. Qtec's current published VIS-SWIR family span is 430–1700 nm; unit-specific limits still require a record.
- Check/adjust wheel positions before each long test because the internal motor reference may drift. Manually focus on the target plane when changing cameras.
- A NEMA 17 motor drives the wheel; the Hall sensor is on the fixed base and a magnet is on the rotating part.
- The installed thermocouple/extension identities and the fact that connectors are inside the freezer were supplied. The connector-family gap was subsequently resolved in R2.
- Six filter-wheel STL files were supplied, read, and preserved unchanged with a labeled preview and [digest inventory](reference/filterwheel-cad/inventory.json). Assembly roles, physical units, materials, and revision remain unconfirmed.

### Component references supplied in R1

| Reference | What it establishes / boundary |
|---|---|
| [Thorlabs FBH780-3](https://www.thorlabs.com/item/FBH780-3), [FLH1064-3](https://www.thorlabs.com/item/FLH1064-3), [FBH1550-4](https://www.thorlabs.com/item/FBH1550-4) | Owner identifies installed products; [manufacturer table](https://www.thorlabs.us/newgrouppage9.cfm?objectgroup_id=16235&pn=FB1070-10) verifies nominal wavelength, FWHM, and diameter. Individual certificates are not supplied. |
| [Qtec Hypervision](https://docs.qtec.com/hsi/hypervision/intro/), [C-series platform](https://docs.qtec.com/smart-modular-camera/qtec-c-series/platform/), [hardware guide](https://docs.qtec.com/camera-overview/hw_guide/) | Family architecture/interfaces; not proof that every prototype has stock optics, sensor, firmware, or all listed features. |
| [Pololu product 3132](https://www.pololu.com/product/3132) | Tic T834 with soldered connectors; its published motor-supply range is 2.5–10.8 V, not an inferred 24 V connection. |
| [Honeywell SL353 datasheet supplied through RS](https://docs.rs-online.com/9a79/A700000007013601.pdf) | Eight-page Honeywell datasheet, April 2015, read and relevant electrical/pin diagrams visually checked. Covers both SL353HT and SL353LT; fitted suffix remains unknown. |
| [MCC listing supplied through DigiKey](https://www.digikey.dk/en/products/detail/digilent-inc/6069-410-025/16970338), [Digilent E-TC](https://digilent.com/shop/mcc-e-tc-thermocouple-measurement-ethernet-daq-device/) | Owner's DAQ reference identified as E-TC, part 6069-410-025; installed serial, wiring, and calibration still need records. |
| [Labfacility XF-1275-FAR KX extension](https://dk.farnell.com/labfacility/xf-1275-far/thermocouple-wire-type-kx-10m/dp/2918721) | Extension-wire product; the terminal-block family is separately identified in R2. |
| [Omega 5LSC / 5SRTC family](https://dk.omega.com/pptst/5LSC_5SRTC.html), [exact IEC model listing](https://www.jp.omega.com/pptst/5LSC_5SRTC_IEC.html), owner-supplied `5SRTC-TT-KI-36-1M` | Probe identification and nominal construction. The usual physical positions are now owner-confirmed in R2; attachment/calibration details and actual per-run changes still need records. |

Vendor references were checked on 27 October 2026 where retrievable. A supplied link alone is labeled as owner evidence if its exact content could not be verified. The knowledge base summarizes relevant specifications and links to sources; it does not duplicate supplier catalogs.

### R2: Owner review and component photos, 29 October 2026

The owner supplied nine HEIC photographs in `Images/`, a connector reference, and these clarifications. They update the relevant chapters rather than create a competing procedure:

- **Usual probe map, changeable by test:** probe 1 non-computer outer shell; 2 computer/hot outer shell; 3 side between those shell locations; 4 camera-facing/top face of the upper aluminium tray; 5 underside of that tray. Tray probes are placed away from camera and lamp. The camera is on the tray in the upper freezer.
- **Target and light:** white PTFE chosen for reflection across the intended 400–1700 nm range, black 3D-printed cage for sharp dark image lines, and a halogen tube with silver-coated parabolic reflector directed at the target. These owner descriptions do not establish calibrated reflectance, target-edge transfer, spectrum or illumination stability.
- **Thermal sequence:** cool with freezer on and camera off; switch freezer off at the cold threshold; then start the camera. Camera and lamp heat warm the chamber toward the endpoint. Normal operation does not power camera and freezer together. The code confirms that the lamp is sweep-switched rather than continuously on.
- **Power and shutdown:** the owner accepts direct camera power removal as normal practice. The follow-up to the supply-map question confirms **XDR-240E-24 → lamp and freezer-contactor coil**, **NDR-120-24 → camera**, and **MDR-40-5 → MCC, Tic, network switch and Hall sensor**. The larger XDR serves the lamp's high startup demand; lamp and freezer are never enabled together normally. Separate camera power avoids the brief camera interruption previously seen at lamp startup. The freezer appliance is rated 230 V, so its mains load is distinguished from its 24 V contactor coil. This confirmation supersedes the reviewed calibration script's comment that camera and contactor share a supply.
- **Local AI:** GitHub knowledge-base access through a deploy SSH key is already working according to the owner. No credential is included here; index freshness/answer quality was not independently tested.

All nine images were visually inspected. They identify Mean Well XDR-240E-24, NDR-120-24 and MDR-40-5 supplies; three Schneider SSD1D520BDC1 relays; the Allen-Bradley 100-C09E*400 Series A contactor designation; a Telenty-labelled five-port switch; SY42STH38-1684B motor; Tic T834; TEFCOLD UF400V; and halogen packaging reference 641840875. Label ratings and any hidden/uncertain identifiers are transcribed in the [photo index](reference/component-photos/README.md) and hardware chapter. The supply/load groups come from the owner's follow-up; individual relay-role assignments, coil options and unpictured model suffixes are not guessed from wire colors or family labels.

The photos also show the chamber/tray and terminal arrangement. Dishes of granules are visible but their identity/effectiveness is not established by appearance. Original HEICs remain in the owner's `Images/` folder; JPEG reference copies were made for standard viewing, with orientation retained and camera metadata stripped. The [photo inventory](reference/component-photos/inventory.json) records source and published digests. No content was retouched.

The owner identifies the freezer-side thermocouple terminals as the [Omega DRTB-2 series](https://www.dwyeromega.com/en-nl/thermocouple-din-rail-terminal-blocks-narrow-10-7-mm-width/p/DRTB-2). The manufacturer page confirms DIN-rail mounting, screw terminals and an integrated miniature female thermocouple connector, with variants for several thermocouple types. The application uses K-type probes, but the exact fitted DRTB suffix is not legible in the supplied evidence; a family link alone does not establish a specific SKU. This source was checked on 29 October 2026.

## Excluded and missing sources

**Excluded by scope:** individual result datasets, camera performance rankings, result charts, drift diagnoses, raw historical error logs, compiled Python caches, and the root `calibration_temperature_log.jsonl` contents. Setup-related failure modes are summarized only where useful for operation or validity.

**Still missing:** full older conversation histories/attachments, CAD assembly/part map, complete terminal/load wiring, a few fitted suffixes, unit/revision inventory, deployed-file hashes, probe calibration/attachment details, qualification requirements and acceptance criteria. The usual probe locations, setup photograph, target/light arrangement and photographed identities are now supplied. Only unresolved details remain in [the review register](09-review-questions-and-gaps.md).

No manufacturer specification is inferred from an IP address, generic component label, or a historical assistant assertion. Component identification now supports nominal filter specifications; this is distinct from measured per-filter calibration or a guarantee of installed orientation.

## What was checked for version 0.1

- Inventoried and distributed review of the 34 supplied Python/shell source files across hardware/configuration, orchestration/data, and analysis/comparison topics.
- Compared all shared source files against the public repository snapshot and recorded digests.
- Cross-checked key distinctions such as local overrides, inactive warm-start settings, sequential capture, cleanup paths, and analysis units against consuming code.
- Checked Markdown links, source-line targets, export parseability, chunk size, and package contents.
- Did **not** import hardware modules, operate equipment, run preflight, deploy camera files, change source behavior, or rerun historical analysis.

For version 0.2, the owner review was reconciled across the chapters, remaining questions were narrowed, the six CAD meshes were checked for basic file integrity, source links/exports were checked, and the unused local configuration names were removed. These checks do not validate physical wiring, calibrations, acquisition reliability, numerical correctness against representative images, or local AI answer quality.

For version 0.3, all nine component photos were inspected, readable labels transcribed with source links, the usual map and thermal sequence reconciled with code, answered questions removed, and reference-photo/export integrity checked. The acquisition programs and active configuration were not changed in this batch, and no equipment was operated.

Version 0.3.1 incorporates the owner's supply-map follow-up, closes that allocation gap, records lamp/freezer non-overlap in normal operation, and explicitly identifies the superseded calibration-code wiring comment. Exports and links were refreshed; acquisition code and active configuration remain unchanged.

## How to maintain the knowledge base

1. Change the relevant numbered Markdown document, preserving the distinction between physical facts, implementation, local settings, and proposals.
2. Add the supporting source and date. For owner confirmation, record who confirmed it, what was confirmed, and which rig/software revision it applies to. Do not invent confirmations.
3. When source changes, review affected behavior and update line citations. Recompare with the intended Git commit and refresh the source manifest deliberately; export generation does not establish a new source review.
4. Resolve or add entries in [review questions](09-review-questions-and-gaps.md).
5. Update the version/review date when appropriate and run `python3 knowledge_base/build_exports.py` from the project root.
6. Re-import one export representation into the local AI, removing obsolete indexed copies according to that system's normal document-update workflow. Recheck the example questions.

The first source snapshot remains recorded in `source_manifest.json`. An edited code file should trigger a new documentation review rather than an automatic claim that old documentation still describes it.
