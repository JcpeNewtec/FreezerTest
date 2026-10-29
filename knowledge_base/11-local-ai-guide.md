# Using the knowledge base with a local AI

Status: existing GitHub connection, content/version guide · Version: 0.3

The owner confirms that the **local AI accesses this knowledge base through GitHub using a deploy SSH key**. Its application/importer/model details and the version it has indexed have not been inspected here. No new connection or key is needed for this documentation update. After a repository update, let the existing sync/index process refresh and check that answers reflect the new version. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

## Choose one import route

| Your system supports | Import | Notes |
|---|---|---|
| A folder of Markdown documents | `README.md` and the numbered `01-` through `12-` files in `knowledge_base/` | Preferred for preserving document titles and section structure; do not also index `exports/` |
| A single text/Markdown document | `exports/FreezerTest_Knowledge_Base.md` | Self-contained prose with source paths retained; the application may split it into smaller passages |
| A JSONL document loader | `exports/documents.jsonl` | One record per canonical document; read `text` as content and preserve metadata |
| A pre-chunked JSONL pipeline | `exports/chunks.jsonl` | Each record has `id`, `document_id`, `source_path`, `section`, `text`, `kb_version`, and content digest |

The pre-chunked export splits at section boundaries and limits chunk size; a long section may be split into continuation chunks with its document/section heading repeated. Chunking is a starting point, not a tuned retrieval configuration. The downstream system must still embed/index these records and retrieve them at answer time. Table and code-block continuations may need neighboring chunks.

Keep the source manifest and `reference/` files available as evidence, but do not index the historical configuration snapshot, CAD meshes, build scripts, ZIP files, caches, raw temperature log, or duplicate export formats as current operating instructions. Canonical chapters summarize accepted hardware/CAD facts. If you index source code separately, label it with the reviewed revision and distinguish it from the human documentation.

## Recommended answer instruction

The following instruction can be adapted to the local AI's knowledge or retrieval settings:

> Answer FreezerTest questions from the retrieved knowledge-base passages and cite their document/section. Version 0.3 includes owner reviews through 29 October 2026; the older acquisition-source snapshot does not prove deployed-file identity. Distinguish usual setup, actual per-run settings, code behavior, photographed labels, and unknowns. Normal pre-cool is 5 °C on probe_5, usually on the tray underside; the old 12 °C profile was a shorter trial. Usual probes 1–3 measure the exterior case and 4–5 opposite tray surfaces; placements may change by test. The freezer cools with camera off, then switches off before camera startup; camera and intermittent lamp heat warm the chamber. Direct camera power removal is the owner's accepted normal shutdown. The target is white PTFE with a black printed cage, illuminated by a reflected halogen tube; it is not established as a calibrated reflectance standard. Cameras are Hypervision variants, not one fixed reference build. Do not invent missing facts, individual results, or permissions to operate equipment.

For an AI with equipment-control tools, answering an operational question does not itself authorize executing the command. This corpus includes hardware-active command examples, especially preflight, calibration, diagnostics, and the runner. Indexing documentation should not trigger them.

## Retrieval checks after import

Use these as manual checks. The expected answers summarize the reviewed snapshot and must change if that snapshot is superseded.

| Question | Expected answer / evidence |
|---|---|
| What happens during one complete repeat? | Freezer on/camera-lamp off for pre-cool, freezer off and settle, camera boot/keepalive, sweeps while camera and intermittent lamp heat warm the chamber, endpoint or limits, power-cut cleanup; document 04 |
| What is the normal pre-cool threshold, and why does the old configuration say 12 °C? | Normally probe_5 ≤5 °C; 12 °C was a deliberate shorter trial; documents 01, 03, 04 |
| What is the reference camera model? | Qtec Hypervision variants are tested; record the unit/revision rather than assume a single fixed reference build; documents 01, 02, 08 |
| Do the repeat plots establish statistical reproducibility across camera units? | That is a test purpose, but existing plots calculate within-group deltas/overlays; a defined inter-unit statistical model and controlled revision/setup records are still needed; documents 06, 09 |
| What must be checked when preparing a run or switching cameras? | Verify wheel positions before every long test; manually set focus to the target plane after a camera change; document 04 |
| What does `probe_5` measure physically? | Usually the underside of the upper aluminium tray, away from camera/lamp; not free air or camera core. Check the actual test's map; documents 02, 05 |
| Where are the other usual probes? | 1 non-computer outer shell, 2 computer/hot outer shell, 3 side between them, 4 top/camera-facing tray surface; placements may change; document 02 |
| Are camera and freezer on together, and is the lamp continuously on? | No overlap in normal operation. The lamp is on for sweep captures and off between sweeps; documents 03, 04 |
| What forms the image target? | White PTFE plus a black 3D-printed cage, illuminated by a halogen tube and silver-coated parabolic reflector; no calibrated reflectance/target-transfer function is supplied; documents 02, 06 |
| How is the camera normally shut down? | By removing power, accepted by the owner as routine practice; documents 03, 04 |
| Is 120 seconds the exact image-to-image cadence? | No; configured wait is scheduled after a sweep, so capture and transfer take additional time; document 04 |
| Which filters and exposure settings are configured? | No filter, Thorlabs FBH780-3, FLH1064-3, FBH1550-4; historical exposure control values 3000, 15000, 8000, 15000; confirm per run; documents 01–03 |
| What units are the spectral width and shift in? | Pixels; no wavelength calibration or filter deconvolution is implemented; document 06 |
| Is the reported noise the camera's read noise? | No; spatial DN scatter from configured ROIs in a bp_1550 image; document 06 |
| Where do captures live before and after transfer? | Camera staging under `/root/scripts/data`; permanent host path from local configuration; failed sweeps may remain remotely; document 05 |
| Is preflight safe to run during acquisition? | No; it can operate real outputs through controller connection/disconnection; documents 04, 07 |
| Does the generic product documentation establish every tested unit's detector/optics/revision? | No; family documentation is context, while unit-specific configuration requires its own record; documents 02, 08, 09 |
| Is a dry-air purge installed? | Not confirmed; it was suggested historically; document 08 |
| Which camera performed best? | Individual results are excluded; this corpus cannot answer; README and document 01 |

An adequate first import should retrieve the relevant passage, preserve the implementation/intent distinction, and admit unknowns. A fluent answer without source support is not a successful check.

## Updating and sharing

Use the Markdown pages as the editable master and regenerate exports after review. Replace outdated indexed versions rather than accumulating contradictory drafts. The portable ZIP includes canonical documents, exports, source manifest, reference evidence, CAD files, component photographs and previews; it excludes acquisition results and acquisition source code. Human-readable labels/meanings are transcribed into the chapters so the AI can retrieve them without reading the photos. The historical configuration snapshot is not imported by the scripts. Keep the source repository alongside the knowledge base for clickable code references.

The existing deploy key is a credential of the AI's connection, not knowledge-base content. No private key or token is included in the corpus. Repository access follows the repository's permissions. A successful fetch and correct answers using the latest version are separate checks; the access is owner-confirmed, while current retrieval/index freshness still needs to be checked in that AI.
