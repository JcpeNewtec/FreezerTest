# Review questions and gaps

Status: remaining review questions · Updated: 29 October 2026

This register contains unanswered details after both owner-review batches. The usual probe map, target/illumination, thermal sequence, direct power-cut shutdown, photographed part identities, connector family, and AI's deploy-key access are now recorded in the relevant chapters. They are no longer open questions. Remaining entries below concern specific implementation, calibration, or per-run records. See [R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026) and [R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

## A. Confirm the current system and sequence

| ID | Question / gap | Why it matters | Current evidence |
|---|---|---|---|
| A01 | Is the reviewed source the version currently deployed on the host and on each camera? | Local source does not prove deployed-file identity | [Software](03-software-and-configuration.md) |
| A04 | Map each pictured relay to its load/terminals and identify the contactor's fitted coil option | Supply groups are resolved: XDR powers lamp/contactor coil, NDR powers camera, MDR powers small devices. Physical relay-role/terminal details remain open | [Hardware](02-hardware-and-connections.md), [photos](reference/component-photos/README.md) |
| A05 | What compressor minimum-off time is required by the actual freezer? Is protection built into the appliance/contactor? | The configured 600-second value is not a general interlock in the long-test runner | [Operations](04-running-the-test.md) |
| A07 | What endpoint, repeat count, and sweep wait are standard, and which are chosen per experiment? | Normal cold threshold is resolved as 5 °C; the historical profile's other settings remain run-specific | [Configuration](03-software-and-configuration.md) |
| A08 | Which device path and driver/firmware versions are valid on the actual camera? | Current code fixes `/dev/video4`; historical device-discovery proposals are not present | [Context](08-project-context.md) |

## B. Describe and identify the hardware

| ID | Information to supply | Useful evidence |
|---|---|---|
| B01 | Per-unit serial/revision, detector/optical configuration, TEC settings, and firmware/software image | Qtec Hypervision family is confirmed; maintain a unit/revision inventory rather than nominate one fixed reference camera |
| B02 | Freezer thermostat settings/modifications, fan behavior when freezer is off, and any internal compressor protection | TEFCOLD UF400V and nameplate ratings are resolved; these operating details are not |
| B03 | MCC serial/terminal wiring, probe attachment/calibration, actual extension lengths, fitted DRTB thermocouple-type suffix, and how per-run placement changes are recorded | Usual probe locations and Omega DRTB-2 series are resolved |
| B04 | Lamp brand if needed, actual operating voltage, reflector/target distances, and illumination stability over the capture window | Halogen tube packaging identity/ratings and silver-coated reflector arrangement are supplied |
| B05 | PTFE grade/thickness, black cage material/geometry, feature dimensions, mounting and optical distances | White PTFE plus black 3D-printed cage is confirmed; no calibrated target drawing is supplied |
| B06 | Individual-filter certificates if available, fitted orientation/loading, and per-run position verification/acceptance method | Thorlabs part numbers and selection rationale are resolved |
| B07 | Motor winding ratings/step angle, SL353HT versus LT suffix/interface, mechanical drive ratio and zero reference | Motor SY42STH38-1684B and 5 V controller supply are resolved; frame/label alone does not provide the remaining specifications |
| B08 | Complete power/terminal drawing, contactor coil option, switch exact model and physical relay-role assignment | Component model labels and normal control sequence are recorded; a photograph is not a full circuit diagram |
| B09 | Camera mechanical revision: steel-cup grade, rod dimensions, PC grade/geometry, mirror/grating specifications, exact adhesives and cure | Drawing/BOM and build notes |
| B10 | Exact cable pass-through and terminal-mounting details/dimensions, sealing, strain relief, and rig orientation | Inside-freezer connector location and the photographed terminal arrangement are established; add detailed mounting/pass-through views |
| B11 | Identify the granular material visible in the chamber dishes, conditioning/replacement practice, and any humidity monitoring | The material is visible in IMG_5292, but identity and effectiveness are not established by the photo |
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
| C09 | How should case/tray gradients and thermal lag be handled in comparisons? | Usual locations are known; transient measurements do not directly establish optical-core equilibrium |
| C10 | Should comparison interpolate on temperature/time, compare only matched conditions, or show native samples? | Existing comparison tools are exploratory; they do not create a validated matching methodology |
| C11 | How should repeat groups remain unique across multiple sequences on the same day? | Default group ID uses camera ID and date; folder repair tools can modify metadata |
| C12 | How should inter-unit reproducibility be quantified, and which comparisons control unit/revision/focus differences? | The test purpose is confirmed; current within-group delta plots do not themselves produce a population-level statistical study |

## D. Source coverage and local AI

| ID | Gap | Next review action |
|---|---|---|
| D01 | Only three matching chats and their returned turns were available, not all historical discussion | Add earlier chat exports or accessible links if they contain missing setup/method decisions |
| D02 | Older chat attachments are unavailable; the newly supplied CAD files have no assembly map | Supply only missing material relevant to unresolved setup questions |
| D03 | Component sources are now supplied, but the complete installed BOM and per-unit revisions are not | Add remaining part numbers and revision records without duplicating vendor catalogs |
| D04 | Which content representation and update/index-refresh process does the existing local AI use? | GitHub access through deploy SSH key is confirmed; imported version/retrieval behavior has not been checked here |
| D05 | No local AI retrieval evaluation has been run | Use the question set in [the local AI guide](11-local-ai-guide.md) after import |

## Review record

When a question is resolved, edit the relevant canonical page first, record the owner's confirmation or supporting file in [sources](10-sources-and-maintenance.md), and mark the entry resolved with date and evidence. Regenerate the exports afterward. Avoid treating a closed review question as proof that older tests used the newly confirmed setup.
