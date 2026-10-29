# FreezerTest knowledge base

Version: **0.3 — owner review and component photographs** · Updated: **29 October 2026**

This knowledge base explains the FreezerTest apparatus, control software, test sequence, data, and analysis methodology. It is intended for operators, colleagues, and a local AI answering questions about the test. It describes a particular source snapshot, not a certified operating procedure or a validated hardware inventory.

The original code review covered **33 shared Python/shell files**, identical to GitHub commit `df4ccebbbd0f41e32f5ae415e967728e5845d56b` (12 October 2026), plus the local configuration. Three project chats supplied historical context. Owner reviews on **27 and 29 October** add component identities, nine component photographs, six filter-wheel CAD files, the usual probe map, target/illumination details, and operating corrections. Those confirmations supersede conflicting historical assumptions. Unanswered questions remain in one [review register](09-review-questions-and-gaps.md). See [sources and maintenance](10-sources-and-maintenance.md) for provenance.

## Find information

| Document | Use it for |
|---|---|
| [01 — Purpose and system overview](01-purpose-and-system-overview.md) | What is measured, system diagram, vocabulary, and scope |
| [02 — Hardware and connections](02-hardware-and-connections.md) | Components, digital I/O, temperature probes, filter wheel, and camera interfaces |
| [03 — Software and configuration](03-software-and-configuration.md) | Modules, dependencies, deployment, defaults, and local overrides |
| [04 — Running the test](04-running-the-test.md) | Pre-cool, measurement, sweeps, repeats, stopping, and recovery |
| [05 — Data and metadata](05-data-and-metadata.md) | Folder structure, files, metadata, timestamps, and transfer |
| [06 — Analysis methodology](06-analysis-methodology.md) | Spectral and spatial metrics, signal/noise, ROIs, units, and limitations |
| [07 — Analysis tools and troubleshooting](07-analysis-tools-and-troubleshooting.md) | Analysis commands, comparisons, preview tools, and common problems |
| [08 — Project context and owner review](08-project-context.md) | Camera-family scope, confirmed context, and relevant historical distinctions |
| [09 — Review questions and gaps](09-review-questions-and-gaps.md) | Prioritized questions for our review, including missing hardware details |
| [10 — Sources and maintenance](10-sources-and-maintenance.md) | Evidence, exact source version, history coverage, and update procedure |
| [11 — Using this with a local AI](11-local-ai-guide.md) | Import options, answer rules, and retrieval checks |
| [12 — Glossary](12-glossary.md) | Terminology used in the code and documentation |

## Evidence labels

- **Implemented / source-derived:** visible behavior in the reviewed code. This does not prove the deployed camera has the same files.
- **Configured:** a value in the reviewed configuration. Local overrides take precedence where the consuming module uses the value. A setting's presence alone does not implement a feature.
- **Owner-confirmed:** a dated description of installed hardware or procedure. Usual arrangements may change by test; use that test's recorded setup when it differs.
- **Photographed:** a visible part/label in the supplied images. A nameplate rating is not a measured load, and visible wiring is not a complete circuit drawing.
- **Proposed / unverified:** an earlier suggestion, an interpretation, or a feature not established by the reviewed sources.
- **Unknown:** evidence is missing. These gaps are deliberately left open.

## Read these distinctions first

1. **Normal pre-cool ends at `probe_5 <= 5 °C`.** Probe 5 is usually attached to the underside of the upper aluminium tray. The historical 12 °C setting was for a shorter trial. Probe placement can change and must be recorded per test; neither threshold establishes thermal equilibrium of the whole camera.
2. The test covers **Qtec Hypervision variants**, both to establish reproducibility across units and to investigate design changes. There is no single fixed reference-camera revision. Record the unit, revision, focus/setup, and run settings for meaningful comparisons.
3. **Freezer on/camera off for cooling → freezer off → camera on for measurement.** Camera heat and intermittent lamp heat warm the chamber toward the endpoint. Normal operation never powers camera and freezer together. There is no controlled heater ramp or stability hold.
4. Analysis widths and shifts are in **pixels**. Signal and image-noise metrics are in **digital numbers (DN)**. The code does not establish calibrated spectral resolution in nm, temporal read noise, or acceptance limits.
5. Preflight and diagnostic scripts can switch real outputs. They are not all read-only checks. Do not run them alongside an acquisition.

## Scope and delivery

Individual runs, images, measured performance, camera rankings, and causal conclusions about camera development are excluded. Setup-related failure modes and measurement validity concerns are retained. The root `calibration_temperature_log.jsonl` and compiled `__pycache__` files are not part of the knowledge corpus.

The numbered Markdown files are the editable source of truth. `exports/FreezerTest_Knowledge_Base.md` is a single-file copy for import. `exports/documents.jsonl` provides one record per document, and `exports/chunks.jsonl` provides section-level records. Import **one representation only**, so the local AI does not retrieve duplicate copies. [The local AI guide](11-local-ai-guide.md) explains the details.

The [component photographs](reference/component-photos/README.md), [CAD reference](reference/filterwheel-cad/README.md), and AI exports are all under `knowledge_base/`, outside the scripts-only test-PC checkout. The owner confirms that the local AI already accesses GitHub through a deploy SSH key; the guide describes content/version checks, not a missing connection. No acquisition code or deployed camera files were changed in this update.
