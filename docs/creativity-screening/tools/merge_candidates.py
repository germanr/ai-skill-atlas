"""Merge and de-duplicate the search-lane candidate files into candidates.json.

Reads every seed-*.json and lane-*.json under docs/creativity-screening/search,
validates the records, links versions of one work (shared DOI, arXiv id, listed
other versions, or near-identical title), and writes one merged record per work.
Prints a short report. Deterministic: same inputs give the same output and ids.
"""
import difflib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SEARCH = ROOT / "search"

DESIGNS = {
    "randomized_experiment_people", "experiment_assignment_unclear", "quasi_experiment_people",
    "ai_vs_human_output", "observational", "synthesis", "model_only", "other",
}
REQUIRED = ["title", "authors", "year", "design_guess", "lane"]


def norm_doi(value):
    if not value or not isinstance(value, str):
        return None
    v = value.strip().lower()
    v = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", v)
    v = re.sub(r"^doi:\s*", "", v)
    v = v.rstrip(".,;) ")
    # OSF and arXiv DOIs: drop version suffixes so versions of one preprint link up.
    v = re.sub(r"(10\.31234/osf\.io/[a-z0-9]+)_v\d+$", r"\1", v)
    v = re.sub(r"(10\.48550/arxiv\.\d{4}\.\d{4,5})v\d+$", r"\1", v)
    return v if v.startswith("10.") else None


def norm_arxiv(value):
    if not value or not isinstance(value, str):
        return None
    m = re.search(r"(\d{4}\.\d{4,5})", value)
    return m.group(1) if m else None


def norm_title(value):
    v = (value or "").lower()
    v = v.replace("&amp;", "and").replace("&", "and")
    v = re.sub(r"[^a-z0-9]+", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def ids_from_text(text):
    """DOIs and arXiv ids mentioned in an other_versions string."""
    out = set()
    for m in re.finditer(r"10\.\d{4,9}/[^\s,;\"')\]]+", text or "", flags=re.I):
        d = norm_doi(m.group(0))
        if d:
            out.add(("doi", d))
    for m in re.finditer(r"arxiv[:\s]*?(\d{4}\.\d{4,5})", text or "", flags=re.I):
        out.add(("arxiv", m.group(1)))
    return out


def load():
    records, problems, lane_meta = [], [], {}
    for path in sorted(SEARCH.glob("*.json")):
        if path.name == "library.json":
            continue
        try:
            data = json.load(io.open(path, encoding="utf-8"))
        except Exception as exc:  # malformed file: report and skip
            problems.append(f"{path.name}: does not parse ({exc})")
            continue
        cands = data.get("candidates") if isinstance(data, dict) else data
        if not isinstance(cands, list):
            problems.append(f"{path.name}: no candidates list")
            continue
        lane_meta[path.stem] = {
            "n": len(cands),
            "queries": len(data.get("queries", [])) if isinstance(data, dict) else None,
            "coverage_limits": data.get("coverage_limits", "") if isinstance(data, dict) else "",
        }
        for i, rec in enumerate(cands):
            if not isinstance(rec, dict):
                problems.append(f"{path.name}[{i}]: not an object")
                continue
            missing = [k for k in REQUIRED if rec.get(k) in (None, "")]
            if "title" in missing:
                problems.append(f"{path.name}[{i}]: no title, skipped")
                continue
            if not (rec.get("url") or rec.get("doi") or rec.get("arxiv_id")):
                missing.append("url/doi/arxiv_id")
            if missing:
                problems.append(f"{path.name}[{i}] {rec.get('title', '')[:50]!r}: missing {missing}")
            if rec.get("design_guess") not in DESIGNS:
                problems.append(f"{path.name}[{i}]: design_guess {rec.get('design_guess')!r} not in list")
                rec["design_guess"] = "other"
            rec["_file"] = path.stem
            rec["_doi"] = norm_doi(rec.get("doi"))
            rec["_arxiv"] = norm_arxiv(rec.get("arxiv_id"))
            rec["_title"] = norm_title(rec.get("title"))
            records.append(rec)
    return records, problems, lane_meta


def cluster(records):
    parent = list(range(len(records)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    keys = defaultdict(list)
    for i, r in enumerate(records):
        if r["_doi"]:
            keys[("doi", r["_doi"])].append(i)
        if r["_arxiv"]:
            keys[("arxiv", r["_arxiv"])].append(i)
            keys[("doi", "10.48550/arxiv." + r["_arxiv"])].append(i)
        if len(r["_title"]) >= 25:
            keys[("title", r["_title"])].append(i)
        for other in r.get("other_versions") or []:
            for key in ids_from_text(other if isinstance(other, str) else json.dumps(other)):
                keys[key].append(i)
                if key[0] == "arxiv":
                    keys[("doi", "10.48550/arxiv." + key[1])].append(i)
    for members in keys.values():
        for m in members[1:]:
            union(members[0], m)

    # Near-identical titles (preprint and journal versions often differ by punctuation).
    fuzzy = []
    titles = [(i, r["_title"]) for i, r in enumerate(records) if len(r["_title"]) >= 25]
    for a in range(len(titles)):
        ia, ta = titles[a]
        for b in range(a + 1, len(titles)):
            ib, tb = titles[b]
            if find(ia) == find(ib):
                continue
            if abs(len(ta) - len(tb)) > 0.25 * max(len(ta), len(tb)):
                continue
            ratio = difflib.SequenceMatcher(None, ta, tb).ratio()
            if ratio >= 0.93:
                union(ia, ib)
                fuzzy.append((round(ratio, 3), records[ia]["title"], records[ib]["title"]))
    groups = defaultdict(list)
    for i in range(len(records)):
        groups[find(i)].append(i)
    return list(groups.values()), fuzzy


STATUS_RANK = {"journal": 0, "proceedings": 1, "working_paper": 2, "preprint": 3, "thesis": 4, "other": 5, None: 6}
CONFIRM_RANK = {"publisher_page": 0, "pdf": 0, "crossref_api": 1, "openalex_api": 1, "arxiv": 1, "ssrn": 1,
                "osf": 1, "nber": 1, "prior_report": 2, "search_snippet_only": 3}


def merge(group, records):
    recs = [records[i] for i in group]
    best = sorted(recs, key=lambda r: (STATUS_RANK.get(r.get("status"), 6),
                                       CONFIRM_RANK.get(r.get("confirmed_from"), 3),
                                       -(r.get("year") or 0), r["_file"]))[0]
    dois = sorted({r["_doi"] for r in recs if r["_doi"]})
    arxivs = sorted({r["_arxiv"] for r in recs if r["_arxiv"]})
    versions = sorted({v if isinstance(v, str) else json.dumps(v)
                       for r in recs for v in (r.get("other_versions") or [])})
    ns = sorted({r["n_participants"] for r in recs if isinstance(r.get("n_participants"), int)})
    posted = sorted({str(r["first_posted"]) for r in recs if r.get("first_posted")})
    return {
        "title": best.get("title"),
        "authors": best.get("authors"),
        "year": best.get("year"),
        "venue": best.get("venue"),
        "status": best.get("status"),
        "doi": best["_doi"] or (dois[0] if dois else None),
        "arxiv_id": best["_arxiv"] or (arxivs[0] if arxivs else None),
        "url": best.get("url") or ("https://doi.org/" + (best["_doi"] or dois[0]) if (best["_doi"] or dois) else None)
               or ("https://arxiv.org/abs/" + arxivs[0] if arxivs else None),
        "library": next(({"md_path": r["library_md_path"], "pdf_path": r["library_pdf_path"],
                          "paper_key": r.get("library_paper_key"), "library_title": r.get("title")}
                         for r in recs if r.get("library_md_path")), None),
        "all_dois": dois,
        "all_arxiv_ids": arxivs,
        "other_versions": versions,
        "first_posted": posted[0] if posted else None,
        "design_guesses": dict(Counter(r.get("design_guess") for r in recs)),
        "question_guesses": sorted({q for r in recs for q in (r.get("question_guess") or [])}),
        "n_participants_reported": ns,
        "task": best.get("task") or next((r.get("task") for r in recs if r.get("task")), ""),
        "evidence": [{"lane": r["_file"], "text": r.get("evidence", "")} for r in recs],
        "confirmed_from": sorted({r.get("confirmed_from") for r in recs if r.get("confirmed_from")}),
        "lanes": sorted({r["_file"] for r in recs}),
        "title_variants": sorted({r.get("title") for r in recs if r.get("title") != best.get("title")}),
        "year_variants": sorted({r.get("year") for r in recs if r.get("year") and r.get("year") != best.get("year")}),
    }


def match_library(merged):
    lib = json.load(io.open(SEARCH / "library.json", encoding="utf-8"))
    linked = {m["library"]["md_path"] for m in merged if m.get("library")}
    unmatched = [row["md_path"].split("/")[-1] for row in lib if row["md_path"] not in linked]
    return len(linked), unmatched


def seed_id_check():
    """Every DOI and arXiv id in a seed JSON must appear verbatim in its source report."""
    bad = []
    for path in sorted(SEARCH.glob("seed-*.json")):
        if not path.with_suffix(".md").exists():
            continue
        report = io.open(path.with_suffix(".md"), encoding="utf-8").read().lower()
        data = json.load(io.open(path, encoding="utf-8"))
        for rec in data.get("candidates", []):
            for field in ("doi", "arxiv_id"):
                val = rec.get(field)
                if val and str(val).lower() not in report:
                    bad.append(f"{path.name}: {field} {val!r} not found in the report ({rec.get('title', '')[:50]!r})")
    return bad


def main():
    records, problems, lane_meta = load()
    groups, fuzzy = cluster(records)
    merged = [merge(g, records) for g in groups]
    merged.sort(key=lambda m: (norm_title(m["authors"] or "zzz"), m["year"] or 0, norm_title(m["title"])))

    # Stable ids: a work keeps the cid it had in the previous candidates.json (matched on
    # DOI, arXiv id, or normalized title); new works get the next free numbers.
    prev_path = ROOT / "candidates.json"
    prev = json.load(io.open(prev_path, encoding="utf-8")) if prev_path.exists() else []
    prev_keys = {}
    for p in prev:
        for d in p.get("all_dois", []) + ([p["doi"]] if p.get("doi") else []):
            prev_keys.setdefault(("doi", d), p["cid"])
        for a in p.get("all_arxiv_ids", []) + ([p["arxiv_id"]] if p.get("arxiv_id") else []):
            prev_keys.setdefault(("arxiv", a), p["cid"])
        for t in [p.get("title")] + list(p.get("title_variants", [])):
            if t:
                prev_keys.setdefault(("title", norm_title(t)), p["cid"])
    used, retired = set(), []
    next_num = max([int(p["cid"][1:]) for p in prev], default=0) + 1
    for m in merged:
        keys = ([("doi", d) for d in m["all_dois"]] + [("arxiv", a) for a in m["all_arxiv_ids"]]
                + [("title", norm_title(t)) for t in [m["title"]] + m["title_variants"] if t])
        hits_prev = sorted({prev_keys[k] for k in keys if k in prev_keys} - used)
        if hits_prev:
            m["cid"] = hits_prev[0]
            retired += [(extra, hits_prev[0]) for extra in hits_prev[1:]]
            used.update(hits_prev)
        else:
            m["cid"] = None
    for m in merged:
        if m["cid"] is None:
            m["cid"] = f"c{next_num:03d}"
            next_num += 1
    dropped = sorted({p["cid"] for p in prev} - {m["cid"] for m in merged} - {r[0] for r in retired})
    merged.sort(key=lambda m: m["cid"])
    if prev:
        new_count = sum(1 for m in merged if m["cid"] not in used)
        print(f"previous ids kept: {len(used)}  new ids: {new_count}"
              f"  merged-away ids: {retired}  ids no longer present: {dropped}")
    hits, unmatched = match_library(merged)
    merged = [{"cid": m.pop("cid"), **m} for m in merged]
    with io.open(ROOT / "candidates.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(merged, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print(f"files: {len(lane_meta)}  records: {len(records)}  merged works: {len(merged)}")
    for name, meta in sorted(lane_meta.items()):
        print(f"  {name:32s} n={meta['n']:4d} queries={meta['queries']}")
    top = Counter()
    for m in merged:
        top[max(m["design_guesses"], key=m["design_guesses"].get)] += 1
    print("design (majority guess):", dict(top))
    print("found by one lane only:", sum(len(m["lanes"]) == 1 for m in merged),
          "| by 2+:", sum(len(m["lanes"]) >= 2 for m in merged))
    print("conflicting design guesses:", sum(len(m["design_guesses"]) > 1 for m in merged))
    print(f"library matches: {hits}; library files with no candidate: {unmatched}")
    print(f"fuzzy title merges: {len(fuzzy)}")
    for ratio, a, b in fuzzy[:40]:
        print(f"   {ratio}  {a[:70]!r}  ~  {b[:70]!r}")
    bad = seed_id_check()
    print(f"seed id check failures: {len(bad)}")
    for line in bad[:30]:
        print("  ", line)
    print(f"validation problems: {len(problems)}")
    for line in problems[:60]:
        print("  ", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
