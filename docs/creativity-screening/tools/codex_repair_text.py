"""Repair characters that Codex jobs lost to the console encoding (written as "?") in screening forms
and citation files. One Codex job per file restores each lost character from the source document or
from typographic context and writes a corrected copy; this script accepts the copy only if every
string differs from the original solely where the original had "?", and each "?" became one character.

Usage: python codex_repair_text.py [--list] [--workers 8]
"""
import argparse
import io
import json
import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_pipeline as cp  # noqa: E402

ROOT = cp.ROOT
R = cp.R
URL = re.compile(r"https?://\S+")
LITERAL_OK = {("c074", "??"), ("c082", "??")}  # the PDFs themselves print "??" (a header placeholder and a broken figure reference)
PATS = [re.compile(r"\d\?\d"), re.compile(r"(?<=[\s(,;\[])\?{1,2}[\d.]"), re.compile(r"\?\?"), re.compile("�"),
        re.compile(r"[A-Za-z]\?[A-Za-z]")]


def strings(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def suspicious(cid, text):
    t = URL.sub(" ", text)
    hits = []
    for pat in PATS:
        for m in pat.finditer(t):
            if (cid, "??") in LITERAL_OK and m.group(0) == "??":
                continue
            hits.append(t[max(0, m.start() - 30): m.end() + 20])
    return hits


def targets():
    out = []
    for p in sorted((ROOT / "forms").glob("c*.json")) + sorted((ROOT / "forms" / "citations").glob("c*.json")):
        if not p.stem[1:].isdigit():
            continue
        d = cp.load(p)
        n = sum(len(suspicious(p.stem, s)) for _, s in strings(d))
        if n:
            out.append((p, n))
    return out


def same_but_restored(old, new):
    """True if new equals old except that each '?' in old became exactly one character (non-ASCII, or a real '?')."""
    if isinstance(old, dict):
        return isinstance(new, dict) and old.keys() == new.keys() and all(same_but_restored(old[k], new[k]) for k in old)
    if isinstance(old, list):
        return isinstance(new, list) and len(old) == len(new) and all(same_but_restored(a, b) for a, b in zip(old, new))
    if isinstance(old, str):
        if not isinstance(new, str) or len(old) != len(new):
            return False
        return all(a == b or (a == "?" and (ord(b) > 127 or b == "?")) for a, b in zip(old, new))
    return old == new


def brief(path, out):
    kind = "citation file" if path.parent.name == "citations" else "screening form"
    cid = path.stem
    return "\n".join([
        f"You repair one {kind} of a literature screening for the AI and Human Skill Atlas. An earlier job wrote it through a console "
        "that could not carry non-ASCII characters, so some characters became a question mark: en dashes in page ranges (\"pp. 6?7\"), "
        "minus signs (\"?0.21\"), section signs (\"?5.2\"), Greek letters (\"?? = .096\" for eta squared), curly apostrophes "
        "(\"paper?s\"), multiplication signs (\"5?5 network\"), arrows, and accented letters in names (\"M?ller\").",
        "",
        f"The file: {str(path).replace(chr(92), '/')}. Its paper's sources: key \"{cid}\" in {R}/retrieval.json (pdf_path, md_path) and the "
        f"object with \"cid\": \"{cid}\" in {R}/candidates.json. For names and titles, the citation APIs (Crossref) may help.",
        "",
        "Task: find every question mark that stands for a lost character and restore that character. Decide from the source document "
        "where the text quotes or cites it (open the PDF page with pymupdf), and from typographic context otherwise (a number range takes "
        "an en dash, a negative number a minus sign). Leave real question marks (in questions and URL query strings) as they are. "
        "Change nothing else: not a word, a space, or a field. Each lost character is replaced by exactly one character.",
        "",
        "Rules: write every non-ASCII character in your python source as a \\u escape (for example \\u2013, \\u2212, \\u00a7, \\u03b7, "
        "\\u00b2, \\u2019, \\u00d7, \\u2192, \\u00fc), because the console loses it otherwise. Read the original with json.load, edit the "
        "strings in python, and write the corrected object with json.dump(obj, fh, ensure_ascii=False, indent=1) to "
        f"{out} (encoding utf-8). Do not modify the original file. Write no other file. Confirm with python that the output parses.",
        "",
        'Final message: a JSON list of the changes, each {"field": "<json path>", "context": "<a few words around>", "restored": "<character>", "basis": "<source page or typographic rule>"}.',
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    t = targets()
    print(f"files with lost characters: {len(t)} | hits: {sum(n for _, n in t)}")
    for p, n in t:
        print(f"  {n:4d}  {p.relative_to(ROOT)}")
    if a.list:
        return
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    base = ROOT / "codex-jobs" / f"repair-{stamp}"
    base.mkdir(parents=True, exist_ok=True)
    cp.JOBS = base
    cp.SLOTS = threading.Semaphore(a.workers)
    results = []

    def one(item):
        p, _ = item
        name = ("cite-" if p.parent.name == "citations" else "form-") + p.stem
        out = base / name / "fixed.json"
        (base / name).mkdir(exist_ok=True)
        cp.run_job(name, brief(p, str(out).replace("\\", "/")), network=p.parent.name == "citations")
        new = cp.load(out)
        old = cp.load(p)
        if new is None:
            return (str(p), "no output")
        if not same_but_restored(old, new):
            return (str(p), "rejected: changes beyond lost characters")
        left = sum(len(suspicious(p.stem, s)) for _, s in strings(new))
        bak = base / name / "original.json"
        shutil.copy2(p, bak)
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(new, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        return (str(p), f"accepted; suspicious left: {left}")

    with ThreadPoolExecutor(a.workers) as pool:
        results = list(pool.map(one, t))
    for r in results:
        print("  ", r)
    json.dump(results, io.open(base / "results.json", "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
