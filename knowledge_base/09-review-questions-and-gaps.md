# Review questions and gaps

Status: remaining review questions · Updated: 27 October 2026

This register contains unanswered questions after the first owner-review batch. Confirmed component identities, normal 5 °C pre-cool, the shorter 12 °C trial, camera-family scope, wheel checks, and camera-change focusing are now in the relevant chapters. The abandoned camera-start workaround is closed, not a pending feature. See [owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026).

## A. Confirm the current system and sequence

| ID | Question / gap | Why it matters | Current evidence |
|---|---|---|---|
| A01 | Is the reviewed source the version currently deployed on the host and on each camera? | Local source does not prove deployed-file identity | [Software](03-software-and-configuration.md) |
| A02 | What is `probe_5` physically attached to? Supply a map for every probe | Both pre-cool and endpoint currently depend on this probe; a label alone cannot identify camera, air, or mount temperature | [Hardware](02-hardware-and-connections.md) |
| A03 | Is the intended run an unpowered pre-cool followed by uncontrolled warm-up, or should the rig perform controlled ramps/holds? | Current code has no closed-loop heating or equilibrium criterion | [Operations](04-running-the-test.md) |
| A04 | Confirm the actual camera/freezer relay wiring, power supplies, and interlocks | A calibration-script comment is not a circuit diagram; the Tic controller has its own supply limits | [Hardware](02-hardware-and-connections.md) |
| A05 | What compressor minimum-off time is required by the actual freezer? Is protection built into the appliance/contactor? | The configured 600-second value is not a general interlock in the long-test runner | [Operations](04-running-the-test.md) |
| A06 | What is the required camera shutdown procedure? Is relay power removal acceptable for its filesystem/firmware? | Current cleanup cuts power; it does not establish an orderly embedded Linux shutdown | [Software](03-software-and-configuration.md), [context](08-project-context.md) |
| A07 | What endpoint, repeat count, and sweep wait are standard, and which are chosen per experiment? | Normal cold threshold is resolved as 5 °C; the historical profile's other settings remain run-specific | [Configuration](03-software-and-configuration.md) |
| A08 | Which device path and driver/firmware versions are valid on the actual camera? | Current code fixes `/dev/video4`; historical device-discovery proposals are not present | [Context](08-project-context.md) |

## B. Describe and identify the hardware

| ID | Information to supply | Useful evidence |
|---|---|---|
| B01 | Per-unit serial/revision, detector/optical configuration, TEC settings, and firmware/software image | Qtec Hypervision family is confirmed; maintain a unit/revision inventory rather than nominate one fixed reference camera |
| B02 | Freezer manufacturer/model, fan behavior, thermostat settings, internal layout, and any modifications | Nameplate, photographs, annotated layout |
| B03 | MCC serial and terminal map; probe locations, junction attachment, extension lengths, and exact freezer-side connector model | MCC, Omega probe, and KX extension identities are supplied; the connector itself lacks a separate link/part number |
| B04 | Lamp/source type, model, spectrum, supply, driver, geometry, stability, and warm-up requirement | Part numbers, datasheet, photo of illumination path |
| B05 | Calibration target/chart/slit geometry and mounting; optical path through filter wheel and camera | Annotated photograph or drawing with dimensions |
| B06 | Individual-filter certificates if available, fitted orientation/loading, and per-run position verification/acceptance method | Thorlabs part numbers and selection rationale are resolved |
| B07 | Exact NEMA 17 motor model/current/step angle, controller supply voltage, SL353HT versus LT suffix/interface, mechanical coupling, and zero reference | Tic controller identity, Honeywell Hall family, and base/magnet arrangement are supplied; remaining values are not implied by those identifiers |
| B08 | Relay/contactor/supply part numbers, normally-open/closed contacts, active polarity, and complete power wiring | Electrical schematic and component labels |
| B09 | Camera mechanical revision: steel-cup grade, rod dimensions, PC grade/geometry, mirror/grating specifications, exact adhesives and cure | Drawing/BOM and build notes |
| B10 | Cable pass-through method, sealing, connector placement, strain relief, and rig orientation | Detailed photographs |
| B11 | Installed humidity/condensation prevention and monitoring, if any | Photos, operating notes, humidity logs if available |
| B12 | Identify the role of each of the six CAD files, source units, material/process, and assembly revision; clarify `PI04` versus `PI04-B` | [Labeled CAD reference](reference/filterwheel-cad/README.md) and an annotated assembly photo/drawing |
| B13 | Define how manual focus on the target plane is judged and recorded after camera changes | A focus criterion/image and setup note; the manual requirement itself is confirmed |

These can be filled in gradually. Existing photographs and rough notes are enough for an initial annotated inventory. Historical construction statements are already captured in [project context](08-project-context.md).

## C. Agree the analysis and interpretation

| ID | Question / gap | Current limit |
|---|---|---|
| C01 | What are the acceptance criteria for position, width, signal, and noise? | No pass/fail thresholds are implemented |
| C02 | What is the intended definition of spectral resolution, and is there a wavelength calibration? | Present FWHM is in pixels and includes the bandpass-filter line shape |
| C03 | Confirm image orientation, ROI locations, the chosen dark-bar edge, and acceptable movement before ROI retuning | ROIs are fixed image coordinates, not image registration |
| C04 | Confirm physical units of `exposure_time_absolute`, camera processing, gain, and effective output bit depth | Stored format is GRAY8; exposure normalization is not performed |
| C05 | Are background ROIs optically dark at all temperatures? Is temporal noise or true dark-current analysis required? | Current noise metric is spatial DN scatter in a filtered image |
| C06 | How should saturated, clipped, dim, condensed, partial, or misaligned images be excluded? | Existing computations do not establish a complete image-quality acceptance policy |
| C07 | Should filter bandwidth be deconvolved, or should results remain observed profile widths? | Code does not deconvolve filter bandwidth |
| C08 | What uncertainty should be reported: fit uncertainty, spatial ROI variation, temporal repeatability, or all three? | Current ROI standard deviations are not general measurement uncertainty |
| C09 | Which temperature best represents each optical component, and how should thermal lag be handled? | Probe location and equilibrium criteria are unknown |
| C10 | Should comparison interpolate on temperature/time, compare only matched conditions, or show native samples? | Existing comparison tools are exploratory; they do not create a validated matching methodology |
| C11 | How should repeat groups remain unique across multiple sequences on the same day? | Default group ID uses camera ID and date; folder repair tools can modify metadata |
| C12 | How should inter-unit reproducibility be quantified, and which comparisons control unit/revision/focus differences? | The test purpose is confirmed; current within-group delta plots do not themselves produce a population-level statistical study |

## D. Source coverage and local AI

| ID | Gap | Next review action |
|---|---|---|
| D01 | Only three matching chats and their returned turns were available, not all historical discussion | Add earlier chat exports or accessible links if they contain missing setup/method decisions |
| D02 | Older chat attachments are unavailable; the newly supplied CAD files have no assembly map | Supply only missing material relevant to unresolved setup questions |
| D03 | Component sources are now supplied, but the complete installed BOM and per-unit revisions are not | Add remaining part numbers and revision records without duplicating vendor catalogs |
| D04 | Local AI application, document importer, model, embedding method, and context limit are unknown | Select the import representation after identifying the local system |
| D05 | No local AI retrieval evaluation has been run | Use the question set in [the local AI guide](11-local-ai-guide.md) after import |

## Review record

When a question is resolved, edit the relevant canonical page first, record the owner's confirmation or supporting file in [sources](10-sources-and-maintenance.md), and mark the entry resolved with date and evidence. Regenerate the exports afterward. Avoid treating a closed review question as proof that older tests used the newly confirmed setup.
