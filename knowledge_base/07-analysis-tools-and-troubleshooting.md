# Analysis tools and troubleshooting

Status: source-derived tool reference with owner clarifications through 2026-10-29. Source inspection date: 2026-10-23. Commands below describe how the tools are intended to be used; creating this knowledge base did not execute acquisition, hardware-control, repair, or analysis scripts.

## Working directory and dependencies

Run the examples from the repository root. Replace `/path/to/test_folder`, `/path/to/sweep_folder`, and `/path/to/results_root` with actual data locations. `PYTHONPATH=.` allows script imports such as `Config.analysis_config` to resolve from the repository root.

The offline analyzer needs NumPy, pandas, Pillow, and Matplotlib; SciPy is needed for the primary spatial Gaussian fit. Without SciPy the import is handled gracefully, but spatial Gaussian width and position become missing values. The comparison viewers need pandas, Plotly, and Streamlit. The supplied files do not pin library versions; environment reproduction remains a documentation gap. [Analyzer imports](../Scripts/analyze_test_folder.py#L4), [optional SciPy handling](../Scripts/analyze_test_folder.py#L223), [viewer imports](../Scripts/compare_tests_streamlit_updated.py#L31).

## Recommended analysis workflow

1. Retain a record of the operator's wheel-position verification before every long test and manual focus adjustment when changing cameras. These are owner-confirmed setup practices; the analysis tools do not enforce them. [Owner review](10-sources-and-maintenance.md#r1-owner-review-27-october-2026).
2. Inspect the region overlays on an early and late sweep, after a camera change, and on any substantially shifted image. Confirm that the spatial ROI crosses the intended black cage line against the white PTFE and that signal, spectral, and background ROIs remain appropriate. Check that `Config/analysis_config.py` matches the current framing and metric settings. [Target description](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).
3. Analyze an individual test and inspect `sweep_diagnostics.csv` for errors, missing filters, ROI counts, and fit success.
4. When comparing repeat cycles, regenerate stale analyses with the same settings, check unit/revision, probe-placement and repeat-group metadata, then run repeat analysis or load the desired cycles in the updated viewer. Keep within-unit cycle repeatability distinct from comparisons between units or development revisions.

Keep the acquisition images and metadata alongside their derived analysis. Record the code revision and configuration used for reporting; the analyzer does not save a configuration snapshot or version stamp into its output itself. See [Analysis methodology](06-analysis-methodology.md) for definitions and interpretation limits.

## Preview the configured regions

```bash
PYTHONPATH=. python3 Scripts/preview_analysis_rois.py "/path/to/sweep_folder"
```

Input is one sweep folder containing `sweep_summary.json` and the image files named by the basenames of its `remote_image_path` entries. The tool draws the configured regions and saves:

```text
<sweep_folder>/analysis_roi_preview/
    filter_1_no_filter_roi_preview.png
    filter_2_bp_780_roi_preview.png
    filter_3_bp_1064_roi_preview.png
    filter_4_bp_1550_roi_preview.png
```

Only configured, present images are processed. Missing images are printed and skipped. Overlay colors are red for spatial edges, lime for no-filter signal, cyan for spectral lines, and yellow for background/noise regions. [Region assembly](../Scripts/preview_analysis_rois.py#L79), [color mapping](../Scripts/preview_analysis_rois.py#L247), [input and output handling](../Scripts/preview_analysis_rois.py#L261).

Spatial guide lines show configured expected targets and search ranges. In `dark_line_auto` mode the drawn edge-search band is positioned relative to the expected dark-line target; it is an approximate setup guide and does not show the edge actually selected from the image. The tool displays Matplotlib windows after saving. [Guide implementation](../Scripts/preview_analysis_rois.py#L110), [display call](../Scripts/preview_analysis_rois.py#L304).

## Analyze one test folder

```bash
PYTHONPATH=. python3 Scripts/analyze_test_folder.py "/path/to/test_folder"
```

The analyzer scans sorted `sweep_*` paths, reads each sweep summary, and processes the images named there. It identifies a local image as `<sweep_folder>/<basename of remote_image_path>`; the remote directory itself is not required. An unknown filter number is skipped. A missing configured image records `filter_<number>_missing = True`. An exception during a sweep records a row with `sweep_name` and `analysis_error`; the script can still print “Analysis complete” after individual sweep failures. [Sweep input parsing](../Scripts/analyze_test_folder.py#L752), [error handling](../Scripts/analyze_test_folder.py#L1311).

Outputs:

| File or folder | Contents |
| --- | --- |
| `analysis/sweep_metrics.csv` | Selected primary metrics and available camera-internal temperature columns |
| `analysis/sweep_diagnostics.csv` | All aggregated numeric metrics, positions, ROI spreads/counts, exposure values, temperatures, derived differences, missing-filter flags, and sweep errors |
| `analysis/plots/` | Available metric plots listed below |
| `analysis/profile_debug/` | Profile plots when `DEBUG_PROFILE_PLOTS = True` |

The command overwrites both CSV files and removes the existing `analysis/plots` directory before rebuilding plots. A successful exit confirms that processing reached the end; inspect diagnostics to determine which measurements succeeded. [Output writing and plot replacement](../Scripts/analyze_test_folder.py#L1335).

Current plot filenames, when their required columns are present:

```text
01_temperature_vs_sweep.png
02_signal_vs_sweep.png
03_spatial_fwhm_vs_sweep.png
04_spectral_fwhm_vs_sweep.png
05_spectral_fwhm_change_vs_sweep.png
06_spatial_edge_shift_vs_sweep.png
07_spectral_line_shift_vs_sweep.png
08_dark_noise_vs_sweep.png
09_dark_level_vs_sweep.png
```

Source: [plot generation](../Scripts/analyze_test_folder.py#L1087). The supplied default disables debug profile plots. If enabled, debug profiles are saved for all processed sweeps; `DEBUG_PROFILE_PLOT_MAX_SWEEPS` limits interactive display to the first configured number of sweeps, rather than limiting which sweep profiles are saved. [Debug configuration](../Config/analysis_config.py#L121), [debug call selection](../Scripts/analyze_test_folder.py#L1304), [profile plot saving](../Scripts/analyze_test_folder.py#L1283).

## Analyze repeat cycles

```bash
PYTHONPATH=. python3 Scripts/analyze_repeat_tests.py "/path/to/results_root"
```

The root can be an individual test or a parent tree. Test discovery requires `test_summary.json` and at least one `sweep_*` path. It recursively discovers test summaries unless the root already qualifies as one test. Existing `analysis/sweep_diagnostics.csv` files are reused; it runs the single-test analyzer only when that file is absent. Use `--force` when settings or source code changed and existing analyses need regeneration:

```bash
PYTHONPATH=. python3 Scripts/analyze_repeat_tests.py "/path/to/results_root" --force
```

The child analyzer is addressed relative to the current directory, so run this command from the repository root. `--force` invokes the single-test analyzer and therefore overwrites its derived CSV/plot outputs. If a child analyzer exits unsuccessfully, its `check=True` subprocess call stops the batch before the later per-table loading error handler can skip it. [Discovery](../Scripts/analyze_repeat_tests.py#L73), [reuse and subprocess](../Scripts/analyze_repeat_tests.py#L166), [main processing loop](../Scripts/analyze_repeat_tests.py#L307).

Output is written under `<results_root>/repeat_analysis/`:

```text
combined_sweep_diagnostics.csv
position_repeatability_by_sweep.csv
cycle_start_position_repeatability.csv
cycle_start_spectral_position_delta.png
cycle_start_spatial_position_delta.png
```

The first two CSV files currently contain the same combined table. The cycle-start table and plots are based on the global minimum sweep index, which can exclude cycles missing that index. These tools compare absolute sensor positions at matching sweep indices; consult the methodology page before calling the result thermal return accuracy. [Cycle-start table](../Scripts/analyze_repeat_tests.py#L238), [plot outputs](../Scripts/analyze_repeat_tests.py#L253), [CSV outputs](../Scripts/analyze_repeat_tests.py#L344).

## Interactive comparison: two supplied versions

Both viewers read existing `analysis/sweep_metrics.csv` files, optionally merge absolute position columns from adjacent `sweep_diagnostics.csv`, add test metadata, calculate repeat deltas, and provide Plotly overlays and a selected-data CSV download. They do not analyze images or regenerate missing measurements. They offer overview, spectral resolution, spectral shift, spatial performance, signal stability, camera internal temperatures, cycle repeatability, and custom plot tabs. [Original loading](../Scripts/compare_tests_streamlit.py#L125), [updated loading](../Scripts/compare_tests_streamlit_updated.py#L543), [updated tabs](../Scripts/compare_tests_streamlit_updated.py#L1329).

The rig tests variants of the qtec Hypervision camera family, so use `camera_id` to identify the individual unit rather than putting only the common family name in that field. Record the hardware/design revision and relevant setup differences in `notes` or accompanying run metadata. Include the focus adjustment after a camera change, wheel-position check, exposure/gain, ROI settings, actual probe-placement map, and thermal protocol when comparing tests. The usual probe map is documented in [analysis methodology](06-analysis-methodology.md#temperatures); it can change between tests. The metadata editor exposes camera ID, date, duration, operator, and notes; it does not provide structured fields or automatic comparability checks for all these details. The updated editor preserves additional fields already present. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026), [updated metadata editor](../Scripts/compare_tests_streamlit_updated.py#L893).

For statistical repeatability between units, select physically comparable units and revisions under comparable conditions. When evaluating a deliberate development change, label that revision difference and avoid treating it as unexplained unit variation. Do not combine different units into one repeat group to make the within-group return-error calculation act as an inter-unit statistic: the viewers provide overlays and within-group reference differences, not a population-level repeatability model. The experimental comparison plan must define that statistical treatment. Individual performance outcomes belong in the separate camera-development knowledge base.

| Aspect | `compare_tests_streamlit.py` | `compare_tests_streamlit_updated.py` |
| --- | --- | --- |
| Browsing | Builds a JSON metadata catalog, then automatically loads selected tests' CSVs | Browses JSON metadata first; CSVs load after **Load checked data** |
| Selection | Individual-test or repeat-group multiselect | Checkable individual-test or repeat-group browser, explicit load/clear controls |
| Summary backfill | Limited date/duration fallback | Also backfills camera ID, repeat fields, and additional date sources |
| Metadata save | Replaces the file with five editor fields, dropping other fields | Preserves existing fields, including repeat identity, then updates editor fields |
| Cache refresh after edit | Clears metrics and file-discovery caches | Also clears summary and metadata caches |

Source: [original initial catalog](../Scripts/compare_tests_streamlit.py#L678), [original editor](../Scripts/compare_tests_streamlit.py#L633), [updated metadata fallback](../Scripts/compare_tests_streamlit_updated.py#L249), [updated editor](../Scripts/compare_tests_streamlit_updated.py#L953), [explicit loading](../Scripts/compare_tests_streamlit_updated.py#L1225).

For first-version documentation, use the updated viewer because it preserves repeat metadata and supports loading selected data explicitly. This is a recommendation based on the inspected code; the preferred long-term filename has not been confirmed with the owner.

```bash
PYTHONPATH=. streamlit run Scripts/compare_tests_streamlit_updated.py
```

Enter the actual results root in the sidebar, inspect or filter the catalog, check tests or repeat groups, then click **Load checked data**. Changing checkboxes does not replace already loaded data until that button is clicked. **Download loaded data CSV** exports the combined loaded table as `selected_freezer_test_data.csv`. [Load controls](../Scripts/compare_tests_streamlit_updated.py#L1225), [download](../Scripts/compare_tests_streamlit_updated.py#L1294).

The updated file's opening comment still gives the original filename in its example launch command. To run the original viewer explicitly:

```bash
PYTHONPATH=. streamlit run Scripts/compare_tests_streamlit.py
```

Both files contain a machine-specific default results path, including a space in `Projects `. It is an example of the author's environment, not the required location for data. Both cache file discovery and data loading by their arguments; refreshing the app alone may reuse cached data after files change externally. Restart the viewer or clear its cache when regenerating analyses. [Updated default path](../Scripts/compare_tests_streamlit_updated.py#L41), [cached discovery](../Scripts/compare_tests_streamlit_updated.py#L212), [cached metrics](../Scripts/compare_tests_streamlit_updated.py#L582).

### Reading viewer plots correctly

The viewer drops rows missing any selected plotting fields and sorts lines by the chosen X variable. A temperature X axis therefore sorts by temperature rather than acquisition order; a heating/cooling loop may be drawn in a misleading order. Missing points are removed before plotting, so `connectgaps=False` does not by itself preserve every gap in the original measurement sequence. No interpolation, image registration, or fitted temperature-response model is applied. [Updated plot preparation](../Scripts/compare_tests_streamlit_updated.py#L684), [line plotting](../Scripts/compare_tests_streamlit_updated.py#L711).

Choose a temperature axis using the map recorded for that test. In the usual arrangement, probes 1–3 are camera-case surface readings and probes 4–5 are opposite surfaces of an aluminium tray away from the camera/lamp; probe 5 is not a free-air or camera-core temperature. The measurement stage is a transient warm-up with the freezer off, camera on, and lamp switched during sweeps. Keep the native sweep order and temperature histories available when interpreting gradients or lag; the viewer does not compensate for them or establish thermal equilibrium. [Temperature interpretation](06-analysis-methodology.md#temperatures), [owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

Repeat references are recalculated from the loaded selection. To compare with cycle 1, include its valid data and verify group identity. Both viewers index discovered tests by folder basename, so duplicate folder names under different parent directories can overwrite each other in the selection dictionary. [Updated test dictionary](../Scripts/compare_tests_streamlit_updated.py#L1161), [repeat calculation](../Scripts/compare_tests_streamlit_updated.py#L622).

## Metadata repair tools

These tools change existing result metadata and can optionally rename folders. They infer groups from folder names; they do not recover the original experimental intent from measurements. Inspect a dry run and back up the affected metadata before applying a repair. No repair was performed while building this knowledge base.

```bash
PYTHONPATH=. python3 Scripts/repair_repeat_group_metadata.py "/path/to/results_root" --dry-run
PYTHONPATH=. python3 Scripts/repair_and_rename_repeat_folders.py "/path/to/results_root" --dry-run
PYTHONPATH=. python3 Scripts/repair_and_rename_repeat_folders.py "/path/to/results_root" --dry-run --rename-folders
```

`repair_repeat_group_metadata.py` groups names matching `<base>_repeat_<index>_<YYYYMMDD_HHMMSS>`, sorting by base and timestamp. It starts a new group at index 1, a base-name change, or a gap/nonconsecutive repeat index. It writes a timestamp-anchored `<base>_<timestamp>` group ID, index, count of discovered members, and base to both `test_metadata.json` and `test_summary.json`. It does not write `repeat_group_start_date`. [Grouping](../Scripts/repair_repeat_group_metadata.py#L89), [written fields](../Scripts/repair_repeat_group_metadata.py#L137).

`repair_and_rename_repeat_folders.py` uses the same general grouping rule but sets camera/date-based identity, `repeat_group_start_date`, camera ID, repeat index/count, and summary root path. With `--rename-folders`, it renames to `<camera_id>_repeat_<index padded to 3 digits>_<timestamp>`. It checks destination collisions within each group, writes metadata first, then renames. Removing `--dry-run` applies the requested changes. Re-run analysis after renaming to refresh recorded paths. [Grouping](../Scripts/repair_and_rename_repeat_folders.py#L125), [metadata fields](../Scripts/repair_and_rename_repeat_folders.py#L164), [rename handling](../Scripts/repair_and_rename_repeat_folders.py#L192).

Both repair scripts treat malformed or unreadable JSON as an empty dictionary. An applying run can consequently replace unreadable original metadata with only reconstructed fields. Count is the number of discovered group members, not necessarily the originally planned repeat count. Camera/date-based IDs can collide for separate same-camera sequences starting the same day. These are reasons to review the dry-run grouping against the acquisition records before applying it. [First JSON loader](../Scripts/repair_repeat_group_metadata.py#L34), [second JSON loader](../Scripts/repair_and_rename_repeat_folders.py#L52).

## Troubleshooting reference

| Symptom | What to inspect |
| --- | --- |
| No tests appear in the viewer | Correct results root; presence of `analysis/sweep_metrics.csv`; cached discovery; duplicate folder basenames |
| A sweep is absent from plots | `analysis_error` in diagnostics; missing images; nonfinite metric; missing chosen X/Y values |
| Spatial Gaussian width or shift is missing | SciPy availability; fit enabled; ROI alignment; valid edge and enough fit samples |
| Spatial position suddenly jumps | Wrong dark-line minimum/edge; fallback to another gradient peak; changed framing; inspect debug profiles and selection diagnostics |
| Width or position differs after changing cameras | Check recorded unit/revision, manual focus adjustment, alignment, ROI placement, and wheel-position verification before attributing the difference to unit behavior |
| Raw spatial position differs from Gaussian position | Raw diagnostics can follow the strongest edge in the whole ROI while the Gaussian uses the selected target edge |
| Spectral FWHM is missing | Peak/crossings too close to an ROI boundary; feature clipped; weak/flat profile; wrong ROI |
| Spectral widths change after smoothing edits | Spectral smoothing changes the measurement input; compare analyses using identical settings |
| Spatial metrics do not change after smoothing edits | Spatial smoothing is used for debug display only |
| Signal changes between filters/runs | Check exposure, illumination, background, ROI placement, camera settings, and temperature; no exposure correction is applied |
| Signal changes when the target or lamp setup changes | Check PTFE/cage framing, halogen/reflector alignment, focus, and saturation; the analysis does not perform calibrated white-reference normalization |
| Signal loss or blurring at lower temperature | Inspect bandpass filters for condensation, an owner-reported setup concern; separate optical-path effects from camera behavior |
| “Noise” seems high or disagrees with another tool | This metric is spatial population scatter in the 1550 nm image, rather than temporal/read noise |
| Repeat cycles split over several days | Inspect `repeat_group_start_date` and group inference; folder-date fallback can split a sequence |
| Separate sequences merge | Camera/date identity may collide; verify grouping before interpreting repeat deltas |
| Repeat baseline changes after selection | The viewer recomputes the reference from loaded tests; include the intended baseline cycle |
| Metrics differ at the same displayed probe temperature | Confirm the actual probe map, warming history, camera-case/tray differences, lamp timing, and thermal lag; matching the usual tray-mounted probe 5 does not establish equal optical/core temperatures |
| Values remain unchanged after reanalysis | Cached viewer tables or repeat analyzer's reuse of existing diagnostics; clear/restart viewer and use `--force` when appropriate |

### Plot error-bar limitation in the current analyzer

The general error-bar helper chooses an error column by replacing **every** `_mean` substring with `_std`. For ordinary FWHM names this selects the intended ROI spread. For `no_filter_signal_signal_mean_mean`, it selects `no_filter_signal_signal_std_std`: the spread between within-ROI standard deviations, rather than `no_filter_signal_signal_mean_std`, the spread between mean signals. For `dark_noise_dark_mean_mean`, it asks for `dark_noise_dark_std_std`, which is not generated, so the dark-level plot falls back to a line without error bars. [Error-column selection](../Scripts/analyze_test_folder.py#L1004), [available signal metrics](../Scripts/analyze_test_folder.py#L517), [available dark metrics](../Scripts/analyze_test_folder.py#L642).

Use the explicit CSV definitions for interpretation until this plotting behavior is reviewed. ROI spread is not a confidence interval or a validated uncertainty budget, and the single configured spatial ROI produces zero aggregation spread by construction.
