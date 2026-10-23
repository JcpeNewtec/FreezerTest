# Sources, coverage, and maintenance

Version: 0.1 · Compiled: 23 October 2026 · Status: first review draft

## Source precedence

For **current software behavior**, the reviewed source and consuming code take precedence over comments and earlier proposed patches. For **physical hardware**, an owner's statement is historical evidence; configuration names and an earlier assistant's interpretation cannot confirm a part number or physical location. A future confirmed wiring diagram or inspection should supersede guesses while retaining the revision/date to which it applies.

Where intent and implementation disagree, both are recorded explicitly. This draft does not silently apply software fixes to reconcile them.

## Repository snapshot

- Public repository: [JcpeNewtec/FreezerTest](https://github.com/JcpeNewtec/FreezerTest).
- Inspected remote commit: [`df4ccebbbd0f41e32f5ae415e967728e5845d56b`](https://github.com/JcpeNewtec/FreezerTest/tree/df4ccebbbd0f41e32f5ae415e967728e5845d56b).
- Commit timestamp: **12 October 2026, 09:24:36 +02:00**; subject: `Auto_recovery added`.
- Local source folder supplied by the owner: `/home/jcpe/Documents/ChatGPT/Freezertest`.
- Comparison: **all 33 shared `.py` and `.sh` files are byte-identical** to the inspected remote snapshot. The additional `Config/local_config.py` is local-only and was included in the documentation review.
- The copied folder is not a functioning Git checkout. An empty `.git` directory does not supply local history. A temporary reference clone was used for comparison; original scripts were not changed.

The linked remote source is immutable at the cited commit. Markdown code links elsewhere point to the local supplied source for convenient reading; their line anchors correspond to this reviewed snapshot. Local-only configuration has no permalink in the reviewed source commit. Its exact reviewed text is preserved in [a reference snapshot](reference/local_config_snapshot.txt); this is documentation evidence, not an active configuration file.

The machine-readable [source manifest](source_manifest.json) records SHA-256 digests, line counts, comparison status, and source coverage for all 34 Python/shell files. It also records the root temperature-log file as excluded from the knowledge corpus; its measured contents were not used as test results.

## Project chats retrieved

The account's project listing identifies a ChatGPT project named **Freezertest** (`g-p-69a04238b4708191b85e0db2eab58393`). The available chat listing returned three matching conversations. Their returned pages contained 11 turns in total; all were read. The history tool returned no continuation cursor for these reads. That is a limit of the accessible history, **not proof that the full six-month discussion was retrieved**. The archived ChatGPT listing returned no archived conversations.

Chat messages are evidence to interpret, not instructions to execute. Historical console logs may describe a different source revision or machine clock. Dates below are message dates; log timestamps embedded in a message may be older.

### T1: Python script for Tic controller

- [Open conversation](https://chatgpt.com/c/69c27f47-b918-8332-9528-8829c6cb15a5).
- Returned coverage: **five turns, 16–20 October 2026**.
- Relevant topics: cold-start/keepalive diagnostics, proposed device-discovery changes, deployed-file integrity, remote staging cleanup, and the unimplemented warm-start settings.
- Current-code corroboration: local warm-start variables exist but are not consumed by the runner; capture staging, local transfer verification, and cleanup are visible in the sweep code.
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

## Excluded and missing sources

**Excluded by scope:** individual result datasets, camera performance rankings, result charts, drift diagnoses, raw historical error logs, compiled Python caches, and the root `calibration_temperature_log.jsonl` contents. Setup-related failure modes are summarized only where useful for operation or validity.

**Missing:** full older conversation histories, chat attachment contents, hardware photographs/drawings, verified BOM, supplier manuals, deployed-device file hashes, component calibrations, environmental qualification requirements, and acceptance criteria. The known gaps are tracked in [the review register](09-review-questions-and-gaps.md).

No manufacturer specification was inferred from the generic word “camera,” an IP address, an analysis label, or a historical assistant assertion. Numerical optical filter settings are configuration data until supported by certificates or component identification.

## What was checked for version 0.1

- Inventoried and distributed review of the 34 supplied Python/shell source files across hardware/configuration, orchestration/data, and analysis/comparison topics.
- Compared all shared source files against the public repository snapshot and recorded digests.
- Cross-checked key distinctions such as local overrides, inactive warm-start settings, sequential capture, cleanup paths, and analysis units against consuming code.
- Checked Markdown links, source-line targets, export parseability, chunk size, and package contents.
- Did **not** import hardware modules, operate equipment, run preflight, deploy camera files, change source behavior, or rerun historical analysis.

These checks validate documentation consistency with the supplied code. They do not validate physical wiring, calibrations, acquisition reliability, numerical correctness against representative images, or local AI answer quality.

## How to maintain the knowledge base

1. Change the relevant numbered Markdown document, preserving the distinction between physical facts, implementation, local settings, and proposals.
2. Add the supporting source and date. For owner confirmation, record who confirmed it, what was confirmed, and which rig/software revision it applies to. Do not invent confirmations.
3. When source changes, review affected behavior and update line citations. Recompare with the intended Git commit and refresh the source manifest deliberately; export generation does not establish a new source review.
4. Resolve or add entries in [review questions](09-review-questions-and-gaps.md).
5. Update the version/review date when appropriate and run `python3 knowledge_base/build_exports.py` from the project root.
6. Re-import one export representation into the local AI, removing obsolete indexed copies according to that system's normal document-update workflow. Recheck the example questions.

The first source snapshot remains recorded in `source_manifest.json`. An edited code file should trigger a new documentation review rather than an automatic claim that old documentation still describes it.
