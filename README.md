# FreezerTest

The setup, software, operating sequence, and analysis documentation are in the [FreezerTest knowledge base](knowledge_base/README.md).

Start there for the knowledge base under owner review (v0.3.1, updated 29 October 2026), known gaps, source provenance, and local-AI import instructions. Individual test results are outside this documentation corpus.

Portable copies are generated in `knowledge_base/exports/`:

- [Single-file knowledge base](knowledge_base/exports/FreezerTest_Knowledge_Base.md)
- JSONL document and section exports in `knowledge_base/exports/`

Generate the ZIP package locally with `python3 knowledge_base/build_exports.py`. Generated ZIP archives are not tracked in Git.

For the test PC, follow [the one-time scripts-only checkout setup](TEST_PC_SETUP.md) **before pulling documentation changes**. Full checkouts for documentation editing or AI indexing need no sparse configuration.

This copied source folder was compared with public GitHub commit `df4ccebbbd0f41e32f5ae415e967728e5845d56b`. All 33 shared Python/shell files match; `Config/local_config.py` supplies additional local settings. See the knowledge base for implementation caveats and unresolved hardware details.
