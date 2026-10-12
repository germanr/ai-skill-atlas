"""Match PDFs that the owner saved in the _inbox folder to screening candidates.

Each PDF is matched by the share of a candidate's title words found on its first two pages.
A match needs a share of at least 0.8 and a clear lead over the runner-up. Matched files are
moved into the library under the standard name and converted to markdown; retrieval.json is
updated with source "owner". Unmatched files stay in the inbox and are listed.
"""
import io
import json
import re
import shutil

import pymupdf

import retrieve as R

INBOX = R.LIB / "_inbox"
cands = json.load(io.open(R.ROOT / "candidates.json", encoding="utf-8"))
log_path = R.ROOT / "retrieval.json"
log = json.load(io.open(log_path, encoding="utf-8"))
need = [c for c in cands if log.get(c["cid"], {}).get("status") != "ok" and not c.get("library")]

matched, unmatched = [], []
for pdf in sorted(INBOX.glob("*.pdf")):
    try:
        doc = pymupdf.open(pdf)
        text = " ".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
        pages = doc.page_count
        doc.close()
    except Exception as exc:
        unmatched.append((pdf.name, f"cannot open: {exc}"))
        continue
    have = set(re.findall(r"[a-z0-9]+", R.fold(text).lower()))
    scored = []
    for c in need:
        titles = [c["title"]] + list(c.get("title_variants") or [])
        best = 0.0
        for t in titles:
            words = R.title_words(t)
            if len(words) >= 3:
                best = max(best, sum(w in have for w in words) / len(words))
        scored.append((best, c))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] < 0.8 or (len(scored) > 1 and scored[0][0] - scored[1][0] < 0.12):
        top = [(round(s, 2), c["cid"], c["title"][:50]) for s, c in scored[:2]]
        unmatched.append((pdf.name, f"no clear match; best: {top}"))
        continue
    share, cand = scored[0]
    stem = R.file_stem(cand)
    target_pdf, target_md = R.LIB / f"{stem}.pdf", R.LIB / f"{stem}.md"
    if target_pdf.exists():
        unmatched.append((pdf.name, f"target already exists: {target_pdf.name}"))
        continue
    shutil.move(str(pdf), str(target_pdf))
    chars = R.convert(target_pdf, target_md)
    log[cand["cid"]] = {**log.get(cand["cid"], {}), "status": "ok", "source": "owner", "title": cand["title"], "pages": pages,
                        "title_word_share": round(share, 2), "md_chars": chars,
                        "pdf_path": str(target_pdf).replace("\\", "/"), "md_path": str(target_md).replace("\\", "/")}
    need = [c for c in need if c["cid"] != cand["cid"]]
    matched.append((cand["cid"], pdf.name, target_pdf.name))

with io.open(log_path, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(log, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
print("matched", len(matched))
for row in matched:
    print("  ", row)
print("unmatched", len(unmatched))
for row in unmatched:
    print("  ", row)
print(" ".join(m[0] for m in matched))
