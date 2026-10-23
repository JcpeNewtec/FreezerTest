# Keep the test PC focused on acquisition scripts

The knowledge base lives in `knowledge_base/` in this same repository. Full checkouts and AI indexers can read it normally. The test PC can retain only `Camera_scripts`, `Config`, `Control`, and `Scripts`, plus small root-level files.

These settings are **local to each checkout**. Pushing documentation cannot set them on another PC. They do not change the camera scripts, deployed camera files, or the ignored `Config/local_config.py`.

## Existing test-PC checkout — run once, before the next pull

Stop any test first. Open a terminal in the existing FreezerTest repository and inspect `git status`. If there are modified tracked files, preserve/reconcile them first; do not reset or discard them. The ignored `Config/local_config.py` should remain in `Config/`.

```bash
git config --local remote.origin.promisor true
git config --local remote.origin.partialclonefilter blob:none
git config --local merge.stat false
git sparse-checkout set --cone Camera_scripts Config Control Scripts
git pull --ff-only
```

The sparse checkout keeps `knowledge_base/` out of the working folder. The `blob:none` filter requests future fetches without file contents, which Git retrieves when needed for included files. Git still receives commit/tree metadata; this is not a path-filtered history or a bandwidth guarantee for every Git command. Already downloaded objects are not removed. `merge.stat=false` suppresses the pull/merge change-summary table, which would otherwise fetch excluded blobs to calculate line counts even on a fast-forward update. Commands that explicitly inspect excluded documentation, such as some history/diff operations, may retrieve it on demand. GitHub supports filtered fetches; if Git warns that filtering is unsupported, stop and inspect rather than assuming contents were skipped.

The whitelist keeps `Config/`, so local settings remain in their normal place. Cone mode also keeps root files such as this guide, `.gitignore`, and `README.md`. New top-level software directories will need to be added to the whitelist when introduced. Use a Git version supporting `git sparse-checkout set --cone` and partial clone; Git 2.34 or newer is a practical baseline for this guide. If Git rejects a command, stop before pulling and update Git or request assistance.

After this one-time setup, update as usual:

```bash
git pull --ff-only
```

`--ff-only` stops on diverged local history rather than silently creating a merge. Resolve that situation deliberately; it does not require deleting local changes.

### Check the settings

```bash
git sparse-checkout list
git config --local --get remote.origin.promisor
git config --local --get remote.origin.partialclonefilter
git config --local --get merge.stat
git status --short
```

Expect the four selected directories, `true`, `blob:none`, and `false`. The `knowledge_base/` directory should be absent unless it contains local/untracked files that Git preserved. Do not delete such files blindly. Existing downloaded objects may still be in `.git`; these commands do not measure transfer savings.

## New scripts-only checkout

Use a **new destination** and transfer/create the test PC's own `Config/local_config.py` before running hardware scripts. The repository does not contain that active machine-specific file.

```bash
git clone --filter=blob:none --sparse https://github.com/JcpeNewtec/FreezerTest.git FreezerTest-scripts
cd FreezerTest-scripts
git sparse-checkout set --cone Camera_scripts Config Control Scripts
git config --local merge.stat false
```

No subsequent pull command needs a special filter flag. Sparse checkout and the remote's partial-clone filter persist locally.

## Documentation workstation / AI indexing

A normal full clone includes the knowledge base. Start at [knowledge_base/README.md](knowledge_base/README.md). An AI importer should select either the canonical Markdown pages, the combined Markdown export, or one JSONL representation, not all duplicates.

To restore all files in a sparse checkout:

```bash
git sparse-checkout disable
```

Git may download missing contents to populate the restored files. This does not automatically clear the fetch filter; keeping it is compatible with a full working folder because Git retrieves required file contents on demand.

Reference: [Git sparse checkout](https://git-scm.com/docs/git-sparse-checkout), [partial clone](https://git-scm.com/docs/partial-clone), and [`remote.<name>.partialclonefilter`](https://git-scm.com/docs/git-config#Documentation/git-config.txt-remoteltnamegtpartialclonefilter).
