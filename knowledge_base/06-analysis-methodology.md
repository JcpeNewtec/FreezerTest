# Freezer test analysis methodology

Status: source-derived methodology with owner clarifications through 2026-10-29; remaining validation questions are listed below. Source inspection date: 2026-10-23. This page describes methods and limitations, without reporting individual test results.

## What the analysis measures

The analysis follows features in camera images while recording the temperatures associated with each acquisition sweep. A sweep contains images from the configured filter positions. The current filter-to-analysis mapping is:

| Filter position | Analysis name | Filter identity | Processing | Nominal wavelength | Configured optical filter FWHM |
| --- | --- | --- | --- | --- | --- |
| 1 | `no_filter` | Open position | Spatial edge and signal statistics | Not applicable | Not applicable |
| 2 | `bp_780` | Thorlabs [FBH780-3](https://www.thorlabs.com/item/FBH780-3) | Spectral line profile | 780 nm | 3 nm |
| 3 | `bp_1064` | Thorlabs [FLH1064-3](https://www.thorlabs.com/item/FLH1064-3) | Spectral line profile | 1064 nm | 3 nm |
| 4 | `bp_1550` | Thorlabs [FBH1550-4](https://www.thorlabs.com/item/FBH1550-4) | Spectral line profile and background-region statistics | 1550 nm | 4 nm |

The owner confirmed the filter part identities on 27 October 2026, including **FLH1064-3** for the 1064 nm position. The narrow bands were chosen as discrete samples across much of the owner-described 400–1700 nm camera range. They do not provide continuous coverage or verify performance between the sampled wavelengths. The test is used with variants of the **qtec Hypervision** camera family rather than one fixed reference camera. [Owner review](10-sources-and-maintenance.md#r1-owner-review-27-october-2026).

The wavelength and FWHM numbers above are the analysis configuration's nominal values; no measured transmission curve is used by the code. Filter bandwidth in nm is metadata; the implemented measured widths and movements are in image pixels. The analysis does not convert pixel widths to wavelength resolution, remove the finite optical filter bandwidth, or establish a physical distance per pixel. For component descriptions and supplier specifications, see [hardware and connections](02-hardware-and-connections.md#filterwheel-filters-and-position-calibration). [Filter mapping](../Config/analysis_config.py#L12), [analysis dispatch and metadata](../Scripts/analyze_test_folder.py#L776).

The primary quantities are spectral FWHM, spectral line position, spatial line spread function (LSF) Gaussian FWHM, spatial edge position, no-filter signal level, and dark-region level and spatial variation. Width describes the observed feature's sharpness; position tracks its movement. A change in these observables does not by itself identify which mechanical, optical, illumination, or sensor effect caused it.

The target is white **PTFE**, selected by the owner for its reflectance over the approximately 400–1700 nm range. A black 3D-printed cage over the PTFE produces the sharp dark lines used as spatial features. A halogen tube and silver-coated parabolic reflector focus illumination onto the target. These are owner-confirmed construction and selection details; no measured reflectance curve, calibrated Lambertian response, or quantified target-edge quality has been supplied. The analysis does not divide by a calibrated white reference or remove the target's edge response from the measured spatial width. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

## Image coordinates and current regions of interest

Images are loaded through Pillow into floating-point arrays. The analysis expects a two-dimensional intensity image and crops with `image[y0:y1, x0:x1]`. Coordinates are zero based; `x1` and `y1` are excluded. X is treated as the spatial direction and Y as the spectral direction. Intensity is reported as digital numbers (DN), meaning the stored image values; the scripts do not establish their conversion to electrons or radiometric units. [Image load and crop](../Scripts/analyze_test_folder.py#L43), [coordinate convention](../Config/analysis_config.py#L37), [DN plot labels](../Scripts/analyze_test_folder.py#L1136).

| Region | X interval | Y interval | Purpose |
| --- | --- | --- | --- |
| `central_dark_line_auto_right_edge` | `[450, 640)` | `[460, 500)` | Spatial edge profile in the no-filter image |
| `bp_780 / roi_1` | `[620, 650)` | `[245, 440)` | Spectral line at central spatial sample |
| `bp_780 / roi_2` | `[450, 480)` | `[245, 440)` | Spectral line at another spatial sample |
| `bp_780 / roi_3` | `[760, 790)` | `[245, 440)` | Spectral line at another spatial sample |
| `bp_1064 / roi_1` | `[620, 650)` | `[450, 640)` | Spectral line |
| `bp_1064 / roi_2` | `[450, 480)` | `[450, 640)` | Spectral line |
| `bp_1064 / roi_3` | `[760, 790)` | `[450, 640)` | Spectral line |
| `bp_1550 / roi_1` | `[620, 650)` | `[790, 995)` | Spectral line |
| `bp_1550 / roi_2` | `[450, 480)` | `[790, 995)` | Spectral line |
| `bp_1550 / roi_3` | `[760, 790)` | `[790, 995)` | Spectral line |
| `signal_1` | `[600, 670)` | `[460, 540)` | Signal statistics in the no-filter image |
| `signal_2` | `[600, 670)` | `[540, 620)` | Signal statistics in the no-filter image |
| `noise_1` | `[200, 680)` | `[460, 540)` | Background statistics in the 1550 nm filtered image |
| `noise_2` | `[200, 680)` | `[540, 620)` | Background statistics in the 1550 nm filtered image |

Source: [spatial region](../Config/analysis_config.py#L41), [spectral regions](../Config/analysis_config.py#L79), [signal and noise regions](../Config/analysis_config.py#L98). These coordinates describe the supplied configuration, not a permanent alignment standard. Verify them on images after changes to camera framing, optical alignment, or sensor format. The crop helper does not validate boundaries; NumPy may silently truncate an out-of-bounds crop.

Check that the fixed spatial ROI crosses the intended cage-produced dark line against the white PTFE in the current framing. Also check that the signal regions sample the intended illuminated target areas and that the spectral and background regions remain suitable. Knowing the target construction does not establish that these fixed pixel coordinates select the intended features on every camera or after a focus/alignment change. [Target description and usual setup](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

The owner verifies the wheel positions before every long test and adjusts manual focus when the camera is changed. Record those setup checks with the run and inspect the analysis regions after a camera change. Focus or framing changes can affect width and position comparisons even when the analysis code is unchanged. The offline analyzer does not verify that these manual checks occurred. [Owner review](10-sources-and-maintenance.md#r1-owner-review-27-october-2026).

## Processing before measurement

The loaded images are used directly. There is no dark-frame subtraction, flat-field correction, exposure normalization, image registration, saturation rejection, bad-pixel mask, or calibrated wavelength transformation in `analyze_sweep`. Background-region statistics are measured separately and are not subtracted from the spectral or signal images. [Per-filter processing](../Scripts/analyze_test_folder.py#L783).

For profile-based FWHM, centroid, and quadratic peak estimation, the common baseline correction is:

```text
b = 10th percentile of the one-dimensional profile p
q[i] = max(p[i] - b, 0)
```

The baseline is a percentile within that profile, rather than an independently acquired background. The spatial Gaussian fit instead fits its own constant offset to a local window of the raw absolute LSF. [Baseline correction](../Scripts/analyze_test_folder.py#L71), [Gaussian initialization](../Scripts/analyze_test_folder.py#L268).

The smoothing helper is a moving average with edge-value padding. Windows greater than one must be odd. The supplied configuration enables smoothing but sets both windows to `1`, which means no smoothing. Spectral smoothing, when increased, changes the profile used for spectral metrics. Spatial smoothing changes debug plot profiles only: the primary spatial Gaussian fit and raw diagnostics continue to use the unsmoothed gradient. [Smoothing helper](../Scripts/analyze_test_folder.py#L51), [spectral use](../Scripts/analyze_test_folder.py#L479), [spatial use](../Scripts/analyze_test_folder.py#L540), [current settings](../Config/analysis_config.py#L110).

## Spectral profile, width, and position

For each spectral ROI, the script averages over X to obtain an intensity profile along Y:

```text
p[y] = mean of I[y, x] over the ROI's X pixels
```

Each filter has three independent profiles at different X locations. Each profile is measured before the resulting metrics are averaged across ROIs. The script does not average all three image strips into one common profile. [Spectral profile and measurements](../Scripts/analyze_test_folder.py#L470), [ROI aggregation](../Scripts/analyze_test_folder.py#L794).

### Spectral FWHM

After the profile's percentile baseline correction, the largest sample defines the main peak. The algorithm walks left and right from this peak until it passes below half the peak height. At each side it linearly interpolates the crossing:

```text
h = max(q) / 2
crossing = i0 + (h - q[i0]) / (q[i1] - q[i0])
FWHM = right_crossing - left_crossing       [px]
```

It measures the connected peak near the maximum, rather than the distance between arbitrary above-half-maximum points across the entire ROI. It returns `NaN` for a nonpositive corrected peak, equal-valued crossing samples, or when the crossing search reaches either endpoint. In particular, reaching the first or last sample is rejected even if those two endpoint-adjacent samples could otherwise bracket a crossing. [FWHM implementation](../Scripts/analyze_test_folder.py#L83).

The output is `bp_780_fwhm_px_mean`, `bp_1064_fwhm_px_mean`, or `bp_1550_fwhm_px_mean` after ROI aggregation. The bandwidth labels 3, 3, and 4 nm do not mean the measured pixel FWHM has been corrected for filter width.

### Spectral line position

The primary position is a local quadratic peak estimate. The algorithm baseline-corrects the profile, finds its maximum, and fits `a*x^2 + b*x + c` to at most five samples centered on the maximum. The peak estimate is `-b/(2*a)`. It falls back to the integer maximum if there are fewer than three samples, fitting fails, the parabola does not open downward, or its vertex lies outside the fit interval. The ROI's `y0` is added to obtain a full-image Y coordinate. [Quadratic estimator](../Scripts/analyze_test_folder.py#L169), [full-image outputs](../Scripts/analyze_test_folder.py#L497).

`peak_fit_y_px` therefore means a quadratic peak fit, not a Gaussian spectral fit. Positive Y shift means movement toward larger image row numbers. The code also records the integer peak, profile maximum intensity, ROI mean intensity, and a windowed centroid as diagnostics.

The quadratic estimator has no minimum signal-amplitude or contrast acceptance threshold. A weak or flat profile can still yield a finite integer fallback position even when its width is missing. Position validity therefore needs a profile/signal check, rather than a finite-number check alone.

The centroid is calculated from the baseline-corrected profile around the main peak, with a 20% peak threshold:

```text
centroid = sum(i * q[i]) / sum(q[i])        [px]
```

The summation uses indices strictly between the left and right search boundaries. This is a windowed main-peak centroid, rather than a full-ROI center of mass; endpoint handling can also exclude an endpoint sample. [Centroid implementation](../Scripts/analyze_test_folder.py#L132).

## Spatial edge width and position

The no-filter spatial ROI crosses a dark vertical line. Averaging the ROI over Y gives an edge spread profile across X. The code computes a numerical gradient and its magnitude:

```text
ESF[x] = mean of I[y, x] over the ROI's Y pixels
signed_LSF = numpy.gradient(ESF)
LSF = abs(signed_LSF)
```

The differentiation sample spacing is one pixel. The implementation is a direct profile gradient; it does not perform slanted-edge oversampling or calculate an MTF curve. [Spatial profile construction](../Scripts/analyze_test_folder.py#L538).

### Selecting the intended edge

Current `dark_line_auto` settings first find the ESF minimum inside the ROI near full-image `x = 560`, with search half-width 80 pixels. The code then searches 4–35 pixels to the right of that minimum for the largest positive gradient: the intended dark-to-bright edge on the bar's right side. The search bounds are clipped to the available ROI. These settings reduce the chance of switching to another bar or the opposite edge, but the detected minimum is simply the minimum ESF sample, not a fitted bar center. [Current edge settings](../Config/analysis_config.py#L41), [dark-line search](../Scripts/analyze_test_folder.py#L354).

The alternative `fixed_target` mode searches around `target_x` and `search_half_width`; left-edge and negative-polarity searches are also supported. If the requested polarity has no positive candidate, the algorithm tries the absolute gradient. If the search is still empty or zero, it falls back to the strongest absolute gradient across the entire profile. A returned fit is therefore not proof that the intended physical edge was selected. [Alternate mode and fallbacks](../Scripts/analyze_test_folder.py#L404).

### Gaussian LSF fit

The primary spatial measurement fits a Gaussian plus constant offset to the raw absolute LSF around the selected edge:

```text
g(x) = offset + amplitude * exp(-0.5 * ((x - center) / sigma)^2)
spatial_FWHM = 2.354820045 * abs(sigma)       [px]
edge_position = ROI.x0 + center             [px]
```

The supplied fit half-window is 5, giving at most 11 samples. The fit requires SciPy and at least five samples. Its initial offset is the local 10th percentile, amplitude is the local maximum minus that offset, initial center is the selected gradient maximum, and initial sigma is `max(1, half_window/3)`. Bounds constrain amplitude to nonnegative values, center to the fit interval, and sigma between 0.2 and `max(3*half_window, 1)` pixels. Offset is unbounded. [Fit model and checks](../Scripts/analyze_test_folder.py#L207), [initialization and bounds](../Scripts/analyze_test_folder.py#L268), [current fit settings](../Config/analysis_config.py#L117).

The fit returns `NaN` width and position if disabled, SciPy is unavailable, the profile/window is too short, amplitude is nonpositive, or fitting raises an error. The primary CSV fields are `no_filter_lsf_gaussian_fwhm_px_mean` and the derived spatial position shift. `gaussian_fit_success` records successful numerical fitting; it does not include a residual test, confidence interval, goodness-of-fit threshold, or physical edge validation. The fit covariance returned by SciPy is discarded. [Fit return values](../Scripts/analyze_test_folder.py#L302), [spatial metrics and diagnostics](../Scripts/analyze_test_folder.py#L594).

Additional spatial diagnostics include the raw absolute LSF FWHM, raw quadratic peak, windowed centroid, mean image intensity, selected edge position, search bounds, detected dark-line position, and `edge_contrast = percentile95(ESF) - percentile5(ESF)` in DN. The raw FWHM, quadratic peak, and centroid search the strongest peak in the whole absolute LSF. They can describe a different edge from the selected edge used for the Gaussian fit; disagreement is not automatically a fit error. [Diagnostic calculations](../Scripts/analyze_test_folder.py#L594).

## Signal and background-region measurements

The no-filter signal ROIs each produce mean, median, population standard deviation, 5th/95th percentiles, minimum, and maximum of all their pixels. The primary signal field, `no_filter_signal_signal_mean_mean`, is the unweighted mean of the two ROI means. It retains background offsets and is not exposure normalized. The field `no_filter_signal_signal_std_mean` is the mean of the within-ROI pixel standard deviations; it is not the uncertainty of the mean signal. [Signal statistics](../Scripts/analyze_test_folder.py#L517), [aggregation](../Scripts/analyze_test_folder.py#L839).

The two noise ROIs are measured in the `bp_1550` image, away from the configured 1550 nm line location. For each cropped ROI with N pixels and mean mu:

```text
dark_mean = mean(I)                                      [DN]
noise_std = sqrt(sum((I - mu)^2) / N)                    [DN]
noise_rms = sqrt(mean((I - mean(I))^2))                  [DN]
```

`noise_std` and `noise_rms` are mathematically equivalent here: both are mean-subtracted population scatter across pixels. The script also records median, percentiles, minimum, and maximum. Primary outputs include `dark_noise_dark_mean_mean`, `dark_noise_noise_std_mean`, and `dark_noise_noise_std_std`. [Background calculation](../Scripts/analyze_test_folder.py#L642), [filter selection](../Scripts/analyze_test_folder.py#L812).

These measurements can contain fixed-pattern variation, gradients, hot pixels, stray light, and other spatial structure. They are not temporal noise from a stack of repeated frames, independently measured read noise, dark-current rate, an SNR calculation, or confirmation that the shutter/light source was off. Whether the regions are physically dark under the intended setup remains an experimental validation item.

The owner previously reported condensation on bandpass filters together with reduced signal and blurred spatial information. Treat filter condition as a measurement-validity check when interpreting signal and width changes; these effects cannot automatically be attributed to the camera under test. This is an owner-reported setup concern, not an individual-result conclusion. Humidity sensing, purge, and filter heating have not been confirmed as installed. [Recovered freezer and wiring context](08-project-context.md#freezer-and-wiring-context).

## Aggregation, deltas, and temperature association

### Meaning of output suffixes

`average_metric_dicts` treats each ROI as one equally weighted measurement. For each numeric metric it writes:

| Suffix | Meaning |
| --- | --- |
| `_mean` | `numpy.nanmean` across ROI metric values |
| `_std` | `numpy.nanstd` across ROI metric values, population convention (`ddof=0`) |
| `_n` | Number of non-NaN ROI metric values |

Missing values are omitted from these summaries. Text diagnostics are skipped; booleans become 0 or 1, so a mean fit-success field is a fraction of ROIs whose fit succeeded. The CSV holds aggregated diagnostics rather than a full table of separate per-ROI metric records. [Aggregation implementation](../Scripts/analyze_test_folder.py#L663).

The spectral standard deviation describes differences across the three X sample locations; it is not fit uncertainty or repeated-measurement uncertainty. There is currently one spatial edge ROI, so its aggregation standard deviation is zero whenever its metric is finite. Zero spread from one ROI does not establish zero measurement uncertainty.

### Within-test change

For each configured delta metric:

```text
metric_delta[sweep] = metric[sweep] - first_valid_metric_in_this_test
```

The baseline is selected independently for each column, so columns can use different baseline sweeps after missing measurements. The script processes lexically sorted `sweep_*` paths and does not explicitly sort the final rows by timestamp or numeric sweep index. The generated acquisition folder names must preserve chronological order for “first” to mean first in time. [Delta implementation](../Scripts/analyze_test_folder.py#L943), [sweep ordering](../Scripts/analyze_test_folder.py#L1311).

Configured deltas cover spectral FWHM, spectral quadratic peak position, spatial Gaussian edge position, and no-filter mean signal. Spatial Gaussian FWHM has an absolute output but is not included in the current `DELTA_COLUMNS`. [Metric lists](../Scripts/analyze_test_folder.py#L858).

### Temperatures

`temp_<probe-name>_c` fields come from `sweep_summary.json / temperature_before_sweep / temperatures_c`. They represent the summary's pre-sweep reading; the analyzer does not average continuously logged temperatures over exposure time. It also calculates `temp_probe_2_minus_probe_1_c` and its absolute value when both columns exist. Those derived differences are in the diagnostic table, but are not in the explicit primary-field list. [Temperature parsing](../Scripts/analyze_test_folder.py#L702), [difference columns](../Scripts/analyze_test_folder.py#L929), [primary columns](../Scripts/analyze_test_folder.py#L888).

The owner's usual probe placement is:

| Field | Usual measured location | Interpretation |
| --- | --- | --- |
| `temp_probe_1_c` | Camera outer case on the side without the computer | Local exterior case temperature |
| `temp_probe_2_c` | Camera outer case on the computer side, described as the hotter side | Local exterior case temperature near the computer side |
| `temp_probe_3_c` | Camera side between the probe 1 and probe 2 locations | Another local exterior case temperature |
| `temp_probe_4_c` | Camera-facing upper surface of an aluminium tray in the upper freezer, away from the camera and lamp | Tray surface temperature |
| `temp_probe_5_c` | Underside of the same tray, away from heat sources | Tray underside temperature; usual pre-cool/endpoint control channel |

This is the owner-confirmed **usual map**, not an immutable channel assignment; record the placement used for each test. Under this map, `temp_probe_2_minus_probe_1_c` means computer-side exterior case temperature minus the opposite exterior case temperature. A positive value means the computer-side measurement is warmer. Its absolute-value field discards that direction. This is a difference between two surface readings, not a measured core-to-case gradient or a spatial gradient per unit distance. Probes 4 and 5 measure the tray surfaces; neither is a free-air probe or an internal camera/optics measurement. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

The test first cools with the freezer on and camera off, then measures with the freezer off and camera on. The owner describes the camera and intermittently operated lamp as heat sources during the subsequent warm-up to the endpoint. In the reviewed runner the lamp is switched on for sweep capture and off afterward, rather than held on throughout measurement. Treat the data as a transient warming history: local case, tray, and internal temperatures can differ and lag each other. Matching two samples by probe 5 alone does not prove equal camera-core or optical temperatures. The code does not impose a steady-temperature hold, a controlled heating ramp, or a correction for thermal lag. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026), [pre-cool sequencing](../Scripts/run_long_test.py#L330), [camera startup](../Scripts/run_long_test.py#L559), [sweep lamp control](../Scripts/run_single_sweep_remote.py#L301).

Camera-internal readings, if recorded in the sweep summary, are flattened as `camera_internal_<reading-label>_<sensor-name>_c`. Status and error fields are retained in diagnostics. All available camera-internal temperature columns ending `_c` are added to the primary table. Missing camera temperatures are not reconstructed from another source. [Internal-temperature parsing](../Scripts/analyze_test_folder.py#L725), [primary table inclusion](../Scripts/analyze_test_folder.py#L960).

## Repeat-cycle comparison

The owner's purposes include statistical repeatability comparisons between camera units and comparisons during camera development. Within-unit repeated thermal cycles and differences between units or revisions are separate comparison questions. Identify the actual camera unit and revision for every test; the family name qtec Hypervision alone is insufficient. For repeatability estimates, compare physically comparable units and setup conditions. For an intentional development comparison, record the changed design and keep other conditions comparable. Individual outcomes remain outside this setup knowledge base. [Owner review](10-sources-and-maintenance.md#r1-owner-review-27-october-2026).

`analyze_repeat_tests.py` compares absolute positions, not within-test deltas. For each `repeat_group_id`, `sweep_index`, and available position metric, it chooses the first nonmissing row sorted by `repeat_index` and then `test_folder`, and subtracts that value from each cycle:

```text
repeat_delta_px[cycle, sweep] = absolute_position[cycle, sweep]
                             - earliest_valid_cycle_position[sweep]
```

The four quantities are the three spectral quadratic peak positions and spatial Gaussian edge position. If cycle 1 is missing or invalid for a metric, a later valid cycle becomes that metric's reference. Both comparison viewers apply this calculation to the tests currently loaded, so excluding the original reference cycle changes the plotted baseline. [Batch repeat calculation](../Scripts/analyze_repeat_tests.py#L208), [original viewer calculation](../Scripts/compare_tests_streamlit.py#L536), [updated viewer calculation](../Scripts/compare_tests_streamlit_updated.py#L622).

This aligns cycles by sweep index only. It does not interpolate onto equal temperature, elapsed time, heating/cooling branch, or thermal-equilibrium conditions; it does not register the images. Comparison at the same sweep index is therefore only a matched-condition comparison if the actual acquisition protocols and temperature histories support that interpretation.

The current repeat script produces within-group position differences, and the viewers can overlay different units' metrics. They do not automatically pool units into a statistical population, separate variation within units from variation between units, correct camera-to-camera focus/alignment differences, or calculate a validated inter-unit repeatability statistic. The population definition, comparable setup conditions, and statistical treatment still need to be specified for that use. Record unit identity, hardware/design revision, manual focus adjustment, wheel verification, exposure/gain, ROI configuration, actual probe-placement map, and the thermal protocol when preparing such a comparison.

Current repeat-group inference normalizes group identity to `camera_id + YYYY-MM-DD`, preferring `repeat_group_start_date`, then a date extracted from an existing group ID, then a folder timestamp, then test date. Two genuinely separate sequences from the same camera on the same date can consequently be merged. Missing an explicit shared start date can split a multi-day sequence into daily groups. [Batch group inference](../Scripts/analyze_repeat_tests.py#L120), [updated viewer group inference](../Scripts/compare_tests_streamlit_updated.py#L162).

The batch “cycle start” table selects the minimum sweep index across the entire combined dataset, then keeps rows at that index. It does not select the first available row separately for every cycle. Both combined CSV filenames currently receive the same combined table; `position_repeatability_by_sweep.csv` is not a separate statistical summary. [Cycle start selection](../Scripts/analyze_repeat_tests.py#L238), [CSV writing](../Scripts/analyze_repeat_tests.py#L344).

## Review items before treating the method as validated

1. Verify that each ROI selects the intended PTFE/cage feature or spectral/background region in the current framing and remains valid through the expected image movement.
2. Confirm the rationale and validation for the spatial sample locations and percentile/fit settings; filter identities and the narrow-band sampling rationale are owner-confirmed above.
3. Establish whether the noise ROIs are free of relevant signal and whether spatial scatter is the intended noise observable.
4. Define the exposure policy and whether signal comparisons require normalization.
5. Specify wavelength/spatial calibration, uncertainty estimation, saturation checks, fit-quality criteria, and acceptance limits if those are required for reporting.
6. Define matched thermal states and treatment of case/tray/optics temperature differences and lag, the unit/revision population and statistical treatment for between-unit comparisons, and how independently started same-day sequences should be identified.

These are gaps in documented experimental validation, not proposed changes already implemented in the scripts. Operational commands, output names, and known viewer issues are documented in [Analysis tools and troubleshooting](07-analysis-tools-and-troubleshooting.md).
