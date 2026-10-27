#!/usr/bin/env python3
"""Build portable documentation exports without importing acquisition code."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

KB = Path(__file__).resolve().parent
VERSION = "0.2"
DATE = "2026-10-27"
REVIEW_STATUS = "owner_review_in_progress"
COMMIT = "df4ccebbbd0f41e32f5ae415e967728e5845d56b"
REPO = "https://github.com/JcpeNewtec/FreezerTest"
MAX_CHUNK_CHARS = 4500


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower().replace("`", ""))
    return re.sub(r"[\s]+", "-", text.strip())


def sections(text: str):
    """Split at Markdown headings outside fenced code blocks."""
    heading = "Introduction"
    lines: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and re.match(r"^#{1,6} ", line):
            if lines and any(x.strip() for x in lines):
                yield heading, "\n".join(lines).strip()
            heading = re.sub(r"^#{1,6} ", "", line)
            lines = [line]
        else:
            lines.append(line)
    if lines and any(x.strip() for x in lines):
        yield heading, "\n".join(lines).strip()


def bounded_parts(body: str, budget: int):
    """Prefer paragraph boundaries; split long paragraphs at lines or spaces."""
    current = ""
    for paragraph in re.split(r"\n\s*\n", body):
        if len(current) + len(paragraph) + 2 <= budget:
            current += ("\n\n" if current else "") + paragraph
            continue
        if current:
            yield current
            current = ""
        while len(paragraph) > budget:
            cut = paragraph.rfind("\n", 0, budget)
            if cut < budget // 2:
                cut = paragraph.rfind(" ", 0, budget)
            if cut < 1:
                cut = budget
            yield paragraph[:cut].strip()
            paragraph = paragraph[cut:].strip()
        current = paragraph
    if current:
        yield current


def build():
    paths = [KB / "README.md"] + sorted(KB.glob("[0-9][0-9]-*.md"))
    if len(paths) != 13:
        raise SystemExit(f"Expected index plus 12 chapters, found {len(paths)}")
    exports = KB / "exports"
    exports.mkdir(exist_ok=True)
    doc_ids = {p.name: "doc-" + p.stem for p in paths}
    documents = []
    chunks = []
    combined = ["# FreezerTest knowledge base — portable edition\n",
                f"Version {VERSION} · Owner review in progress · {DATE}\n",
                "Generated from the canonical Markdown pages. Import this file OR another export, not both.\n"]

    for path in paths:
        content = path.read_text(encoding="utf-8")
        title = content.splitlines()[0].removeprefix("# ")
        document_id = doc_ids[path.name]
        base = {"document_id": document_id, "title": title,
                "source_path": "knowledge_base/" + path.name,
                "kb_version": VERSION, "compiled_date": DATE,
                "review_status": REVIEW_STATUS, "repository_commit": COMMIT}
        documents.append({**base, "id": document_id, "sha256": digest(content), "text": content})

        for section_index, (heading, body) in enumerate(sections(content), 1):
            prefix = f"Document: {title}\nSection: {heading}\nSource: knowledge_base/{path.name}\nStatus: owner review in progress; version {VERSION}; compiled {DATE}\n\n"
            for part_index, part in enumerate(bounded_parts(body, MAX_CHUNK_CHARS - len(prefix)), 1):
                text = prefix + part
                chunks.append({**base, "id": f"{document_id}-s{section_index:03d}-p{part_index:03d}",
                               "section": heading, "section_index": section_index,
                               "part_index": part_index, "sha256": digest(text), "text": text})

        # Make document/section navigation usable in the standalone edition.
        def rewrite_link(match):
            label, target = match.groups()
            filename, _, fragment = target.partition("#")
            if filename in doc_ids:
                anchor = doc_ids[filename] + ("-" + fragment if fragment else "")
                return f"[{label}](#{anchor})"
            if target.startswith("../"):
                repo_path = filename[3:]
                if repo_path != "Config/local_config.py":
                    return f"[{label}]({REPO}/blob/{COMMIT}/{repo_path}" + ("#" + fragment if fragment else "") + ")"
                return f"{label} (`{repo_path}" + ("#" + fragment if fragment else "") + "`; local-only source)"
            if filename.startswith(("reference/", "assets/")):
                return f"[{label}](../{target})"
            if filename == "source_manifest.json":
                return f"[{label}](../source_manifest.json)"
            return match.group(0)

        rewritten = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", rewrite_link, content)
        combined += [f'\n<a id="{document_id}"></a>\n']
        fenced = False
        seen = {}
        for line in rewritten.splitlines():
            if line.startswith("```"):
                fenced = not fenced
            if not fenced and re.match(r"^#{1,6} ", line):
                heading_slug = slug(re.sub(r"^#{1,6} ", "", line))
                n = seen.get(heading_slug, 0)
                seen[heading_slug] = n + 1
                suffix = f"-{n}" if n else ""
                combined.append(f'<a id="{document_id}-{heading_slug}{suffix}"></a>')
            combined.append(line)
        combined.append("\n---\n")

    (exports / "FreezerTest_Knowledge_Base.md").write_text("\n".join(combined), encoding="utf-8")
    for name, rows in [("documents.jsonl", documents), ("chunks.jsonl", chunks)]:
        (exports / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    inventory = {"kb_version": VERSION, "compiled_date": DATE,
                 "documents": len(documents), "chunks": len(chunks), "max_chunk_characters": MAX_CHUNK_CHARS,
                 "inputs": [{"path": r["source_path"], "sha256": r["sha256"]} for r in documents]}
    (exports / "export_manifest.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    package = exports / f"FreezerTest_Knowledge_Base_v{VERSION}.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
        evidence = [p for folder in ("reference", "assets") for p in sorted((KB / folder).rglob("*")) if p.is_file()]
        for path in paths + [KB / "source_manifest.json", KB / "build_exports.py"] + evidence:
            z.write(path, "knowledge_base/" + path.relative_to(KB).as_posix())
        for name in ["FreezerTest_Knowledge_Base.md", "documents.jsonl", "chunks.jsonl", "export_manifest.json"]:
            z.write(exports / name, "knowledge_base/exports/" + name)
    print(json.dumps({"documents": len(documents), "chunks": len(chunks), "package": str(package)}, indent=2))


if __name__ == "__main__":
    build()
