"""Family names for report labels, from Crossref, for citation files that lack "authors_family".

Writes forms/citations-family.json: {cid: {"family": [...], "source": "crossref" | "citation_file"}}.
A Crossref list is accepted only when it has as many authors as the citation file's list and
each family name appears inside the corresponding full name. Otherwise the cid is left out and
the report falls back to a rule that keeps particles such as "van" and "de".
"""
import io
import json
import time
import unicodedata
import urllib.parse
import urllib.request

import retrieve as R

OUT = R.ROOT / "forms" / "citations-family.json"


def fold(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower().replace("-", " ").replace("’", "'")


def main():
    known = json.load(io.open(OUT, encoding="utf-8")) if OUT.exists() else {}
    added = skipped = 0
    for path in sorted((R.ROOT / "forms" / "citations").glob("c*.json")):
        cid = path.stem
        try:
            cite = json.load(io.open(path, encoding="utf-8"))
        except Exception:
            continue
        lv = cite.get("latest_version") or {}
        if lv.get("authors_family"):
            known[cid] = {"family": lv["authors_family"], "source": "citation_file"}
            continue
        if cid in known or not lv.get("doi") or not lv.get("authors"):
            continue
        url = "https://api.crossref.org/works/" + urllib.parse.quote(lv["doi"])
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "atlas-screening/0.1"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                msg = json.loads(resp.read().decode("utf-8"))["message"]
        except Exception:
            skipped += 1
            continue
        fams = [a.get("family") for a in msg.get("author", []) if a.get("family")]
        full = lv["authors"]
        if len(fams) == len(full) and all(fold(f) in fold(n) for f, n in zip(fams, full)):
            known[cid] = {"family": fams, "source": "crossref"}
            added += 1
        else:
            skipped += 1
        time.sleep(0.3)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(known, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("family-name lists:", len(known), "| added from Crossref:", added, "| not matched:", skipped)


if __name__ == "__main__":
    main()
