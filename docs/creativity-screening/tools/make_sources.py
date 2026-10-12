"""Build code/creativity/papers/<paper_key>.json from the reconciled extraction of each paper.

Inputs per paper: extraction/<cid>.json (reconciled and, when flagged, fixed), extraction/status/<cid>.json,
forms/citations/<cid>.json, forms/citations-family.json, forms/<cid>.json (one-line finding, sample overlap), and
retrieval.json (the PDF read). A paper is "verified" when its chain ended with no open problem: the verifier found
nothing, or the second verifier found nothing in what the fixer changed or kept. Otherwise it is "draft", and the
builder validates it without emitting it.

Paper keys follow the learning section: family_year, family_and_family_year, family_etal_year, in ASCII. A key that
another creativity paper or a different learning paper already uses gets a letter (a, b, ...) in cid order.
Contractor and Reyes (2026) [c750] keeps the learning key contractor_reyes_2026 (Review 1 Decision 7).

Usage: python tools/make_sources.py [--only c006 ...]
"""
import argparse
import hashlib
import io
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

SCREEN = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
REPO = Path("C:/Dropbox/Admin/website/ai-skill-atlas")
OUT = REPO / "code" / "creativity" / "papers"
EXT = SCREEN / "extraction"
PARTICLES = {"van", "von", "de", "der", "den", "da", "del", "della", "di", "du", "la", "le", "dos", "das", "ten", "ter", "bin"}
OWN = {"c750": "contractor_reyes_2026"}
STATEMENT = ("Extracted and checked by Codex jobs (gpt-6-astra): two independent extractions, a reconciliation against the "
             "source PDF, a script that matched every number to its quote and every quote to the cited page, and a verifier; "
             "not yet verified by a human research assistant.")


def load(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return default


def ascii_hyphens(s):
    """Unicode hyphens (U+2010, U+2011) as the ASCII hyphen; some citation records use them inside family names."""
    return str(s).replace("\u2010", "-").replace("\u2011", "-")


def ascii_word(s):
    s = unicodedata.normalize("NFKD", ascii_hyphens(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def family(full):
    parts = str(full or "").replace(",", " ").split()
    if not parts:
        return ""
    out = [parts[-1]]
    for token in reversed(parts[:-1]):
        if token.lower() in PARTICLES:
            out.insert(0, token)
        else:
            break
    return " ".join(out)


def families(cid, cite, fam_override):
    lv = (cite or {}).get("latest_version") or {}
    fams = lv.get("authors_family")
    if fams and all(isinstance(x, str) and x.strip() for x in fams):
        names = fams
    else:
        names = (fam_override.get(cid) or {}).get("family") or [family(a) for a in lv.get("authors") or []]
    return [ascii_hyphens(x.title() if x.isalpha() and x.isupper() and len(x) > 1 else x) for x in names]


HEDGED = re.compile(r"\b(possibly|probably|presumably|likely|not stated|unclear|unknown|uncertain)\b", re.I)


def arms_named(arm_names, text):
    """The study's arm names that a text names, in study order. Longest names first, each match removed from the text,
    so that "T&AI" is not also read as the arm "T"."""
    rest, found = str(text), []
    for n in sorted((n for n in arm_names if n), key=len, reverse=True):
        if n in rest:
            found.append(n)
            rest = rest.replace(n, "\x00")
    return [n for n in arm_names if n in found]


def label(names):
    if not names:
        return None
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    if len(names) == 3:
        return f"{names[0]}, {names[1]}, and {names[2]}"
    return f"{names[0]} et al."


def base_key(names, year):
    if len(names) == 1:
        return f"{ascii_word(names[0])}_{year}"
    if len(names) == 2:
        return f"{ascii_word(names[0])}_and_{ascii_word(names[1])}_{year}"
    return f"{ascii_word(names[0])}_etal_{year}"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def chain_verified(status, cid=None, ext=None):
    """Verified when the last verification of the chain found nothing, or when every problem it left is closed by a written
    review resolution in the extraction file (key review_resolutions: slug, field, check, resolution, by, date)."""
    if not status:
        return False, "the extraction chain has not finished"
    def open_after(last):
        n = status.get(f"{last}_problems", 0) if last.startswith("sup") else status.get(f"{last}_problems", 1)
        if n == 0:
            return []
        problems = (load(EXT / "checks" / f"{cid}.{last}.json", {}) or {}).get("problems") or []
        resolved = {(r.get("slug"), r.get("field")) for r in ((ext or {}).get("review_resolutions") or []) if r.get("check") == last and r.get("resolution")}
        return [p for p in problems if (p.get("slug"), p.get("field")) not in resolved]

    last = "verify" if status.get("fixes") is None and status.get("kept") is None else "reverify"
    open_main = open_after(last)
    if status.get("round2") and open_main:
        # After a second fix round, the open problems are the third verifier's, plus any second-verifier problem the second
        # fixer neither fixed nor kept (nothing disappears unaddressed).
        touched = {(f.get("slug"), (f.get("field") or "").replace("stats.", "")) for f in ((ext or {}).get("fixes2") or []) + ((ext or {}).get("kept2") or [])}
        touched_slugs = {s for s, _ in touched}
        unaddressed = [p for p in open_main if p.get("slug") not in touched_slugs]
        status = {**status, "reverify2_problems": status["round2"].get("reverify2_problems", 1)}
        open_main = unaddressed + open_after("reverify2")
        last = "reverify2"
    # A supplement pass adds its own last check: supverify, or supreverify after a fix round.
    sup = status.get("supplement") or {}
    open_sup = []
    if sup:
        sup_last = "supverify" if sup.get("fixes") is None and sup.get("kept") is None else "supreverify"
        status = {**status, f"{sup_last}_problems": sup.get(f"{sup_last}_problems", 1)}
        open_sup = open_after(sup_last)
    if not open_main and not open_sup:
        return True, None
    parts = [f"{len(open_main)} {last} problems open"] if open_main else []
    parts += [f"{len(open_sup)} supplement-pass problems open"] if open_sup else []
    return False, "; ".join(parts) + " (no review resolution)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    retrieval = load(SCREEN / "retrieval.json", {})
    fam_override = load(SCREEN / "forms" / "citations-family.json", {})
    learning_keys = {p["paper_key"] for p in load(REPO / "src" / "papers.json", [])}
    cids = sorted(p.stem for p in EXT.glob("c*.json"))
    # Keys are assigned over every paper in the extraction scope, extracted or not, so that a later run cannot change an
    # earlier paper's key.
    st = load(SCREEN / "report-data.json", {}).get("status_by_cid", {})
    scope = sorted(set(cids) | {c for c, v in st.items() if v == "core" and c not in {"c044", "c276", "c818"}})
    bases = {}
    meta = {}
    for cid in scope:
        cite = load(SCREEN / "forms" / "citations" / f"{cid}.json", {})
        names = families(cid, cite, fam_override)
        year = ((cite.get("latest_version") or {}).get("year"))
        meta[cid] = (cite, names, year)
        bases[cid] = OWN.get(cid) or base_key(names, year)
    groups = defaultdict(list)
    for cid in scope:
        groups[bases[cid]].append(cid)
    keys = {}
    for base, members in groups.items():
        if base in OWN.values():
            for c in members:
                keys[c] = base
        elif len(members) == 1 and base not in learning_keys:
            keys[members[0]] = base
        else:
            for i, c in enumerate(sorted(members)):
                keys[c] = base + "abcdefghijklmnopqrstuvwxyz"[i]
    assert len(set(keys.values())) == len(keys), "duplicate paper keys"
    overrides = (load(REPO / "code" / "creativity" / "primary-overrides.json", {}) or {}).get("papers", {})
    aliases = (load(REPO / "code" / "creativity" / "arm-aliases.json", {}) or {}).get("papers", {})
    shared = {}
    for link in (load(REPO / "code" / "creativity" / "shared-samples.json", {}) or {}).get("links", []):
        for c, sid in link["members"]:
            shared[(c, sid)] = link["sample_id"]
    today = date.today().isoformat()
    n = {"verified": 0, "draft": 0}
    for cid in cids:
        if a.only and cid not in a.only:
            continue
        ext = load(EXT / f"{cid}.json")
        if not ext:
            continue
        status = load(EXT / "status" / f"{cid}.json")
        ok, why = chain_verified(status, cid, ext)
        cite, names, year = meta[cid]
        lv = cite.get("latest_version") or {}
        form = load(SCREEN / "forms" / f"{cid}.json", {})
        pdf = (ext.get("source") or {}).get("pdf_file") or (retrieval.get(cid) or {}).get("pdf_path")
        pdf_name = Path(pdf).name if pdf else None
        digest = sha256(pdf) if pdf and Path(pdf).exists() else None
        key = keys[cid]
        studies = []
        for s in ext.get("studies", []):
            s = dict(s)
            # Participants shared with another paper keep one sample_id (code/creativity/shared-samples.json).
            s["sample_id"] = shared.get((cid, s.get("study_id"))) or f"{key}__{str(s.get('study_id')).lower()}"
            studies.append(s)
        estimates = [dict(e) for e in ext.get("estimates", [])]
        by_slug = {e.get("slug"): e for e in estimates}
        # Arm names: an exact arm name stays; a text naming two or more of the study's arms becomes "A and B (combined)"; an
        # explicit alias (code/creativity/arm-aliases.json) settles the rest. The original wording is kept in <field>_text.
        arms_of = {s.get("study_id"): [a.get("name") for a in s.get("arms") or []] for s in ext.get("studies", [])}
        for e in estimates:
            arm_names = arms_of.get(e.get("study_id")) or []
            for field in ("treatment_arm", "control_arm"):
                text = e.get(field)
                if text in arm_names:
                    continue
                alias = (aliases.get(key) or {}).get(text)
                if not alias and HEDGED.search(str(text)):
                    continue  # the extraction is unsure which arms it means: no combined-arm claim is made for it
                hits = arms_named(arm_names, text)
                prefix = sorted([n for n in arm_names if n and str(text).startswith(n + " (")], key=len, reverse=True)
                if alias:
                    e[field + "_text"], e[field] = text, alias
                elif len(hits) >= 2 and not str(text).endswith("(combined)"):
                    e[field + "_text"], e[field] = text, " and ".join(hits) + " (combined)"
                elif prefix:  # "AI-assisted (Task 1, Group B)": the arm name with a qualifier
                    e[field + "_text"], e[field] = text, prefix[0]
        # The screening form's outcome code says which outcome the preregistration or the paper names as primary.
        form_primary = {o.get("outcome_id"): o.get("primary") for s in form.get("studies", []) for o in s.get("outcomes", [])}
        for e in estimates:
            code = form_primary.get(e.get("form_outcome_id"))
            e["named_primary"] = {"preregistered_primary": "preregistered", "paper_primary": "paper"}.get(code)
        # Statistics from posted data that two analysts computed and agreed on (analysis/<cid>/compare.json).
        cmp = load(SCREEN / "analysis" / cid / "compare.json", {}) or {}
        deposits = "; ".join((load("D:/projects/ai-skill-atlas/creativity-data/manifest.json", {}) or {}).get("papers", {}).get(cid, [])) or "posted data"
        for acc in cmp.get("accepted", []):
            comp = acc.get("computed") or {}
            ds = {"round": acc.get("round"), "n_treatment": comp.get("n_treatment"), "n_control": comp.get("n_control"),
                  "treatment_mean": comp.get("treatment_mean"), "treatment_sd": comp.get("treatment_sd"),
                  "control_mean": comp.get("control_mean"), "control_sd": comp.get("control_sd"),
                  "difference": comp.get("difference"), "difference_se": comp.get("difference_se"),
                  "se_type": comp.get("se_type"), "n_clusters": comp.get("n_clusters"),
                  "scripts": [f"docs/creativity-screening/analysis/{cid}/A.py", f"docs/creativity-screening/analysis/{cid}/B.py"],
                  "deposit": deposits, "compare_file": f"docs/creativity-screening/analysis/{cid}/compare.json"}
            base = by_slug.get(acc.get("slug"))
            if base is None:
                print(f"{cid}: accepted analysis result for unknown slug {acc.get('slug')}; skipped")
                continue
            # Only complete participant-level statistics feed the builder (positive counts, SDs, and SE, and a known SE type).
            complete = (all(isinstance(ds.get(k), (int, float)) and ds[k] > 0 for k in ("n_treatment", "n_control", "control_sd", "difference_se"))
                        and isinstance(ds.get("difference"), (int, float)) and ds.get("se_type") in ("HC2", "cluster", "paired"))
            if not complete:
                base.setdefault("data_notes", []).append({"round": acc.get("round"), "computed": comp, "compare_file": ds["compare_file"],
                                                          "why_not_used": "incomplete for an effect: a count, SD, SE, or SE type is missing or zero"})
                continue
            if acc.get("round") == "all":
                base["data_stats"] = ds
                continue
            twin = next((e for e in estimates if e.get("within_person") == "first_round" and e.get("study_id") == base.get("study_id")
                         and e.get("form_outcome_id") == base.get("form_outcome_id") and e.get("treatment_arm") == base.get("treatment_arm")
                         and e.get("control_arm") == base.get("control_arm")), None)
            if twin is not None:
                twin["data_stats"] = ds
                continue
            slug = base["slug"][:-len("_paired")] + "_first_round" if base["slug"].endswith("_paired") else base["slug"] + "_first_round"
            derived = {k: v for k, v in base.items() if k not in ("data_stats", "primary_override", "primary_override_reason")}
            derived.update({"slug": slug, "within_person": "first_round", "n_treatment": None, "n_control": None, "n_total": None,
                            "stats": {k: (None if k != "difference_is" else "treatment minus control") for k in base["stats"]},
                            "se_basis": "participant", "sources": [], "data_stats": ds,
                            "notes": "First round only (each person's first condition), computed from the authors' posted data; the paper prints no first-round results."})
            estimates.append(derived)
            by_slug[slug] = derived
        for o in overrides.get(key, []):
            e = by_slug.get(o["slug"])
            if e is None:
                raise SystemExit(f"{key}: primary-overrides.json names slug {o['slug']}, which the extraction does not have")
            e["primary_override"] = bool(o["primary_override"])
            e["primary_override_reason"] = o["reason"]
        src = {
            "schema": 1,
            "paper_key": key,
            "cid": cid,
            "status": "verified" if ok else "draft",
            "status_reason": why,
            "paper": {
                "authors_short": label(names),
                "authors_full": ascii_hyphens(", ".join(lv.get("authors") or [])),
                "year": year,
                "title": lv.get("title"),
                "venue": lv.get("venue"),
                "doi": lv.get("doi"),
                "url": lv.get("url") or (f"https://doi.org/{lv['doi']}" if lv.get("doi") else None),
                "pdf_filename": pdf_name,
                "version_read": (ext.get("source") or {}).get("version"),
                "is_own_paper": cid in OWN,
                "one_line_finding": form.get("one_line_finding"),
                "shared_samples": (form.get("sample_overlap") or {}).get("shares_participants_with") or None,
            },
            "provenance": {
                "source_document": pdf_name,
                "source_url": lv.get("url") or (f"https://doi.org/{lv['doi']}" if lv.get("doi") else None),
                "source_version": ((ext.get("source") or {}).get("version") or "") + (f"; PDF SHA-256 {digest}" if digest else ""),
                "extraction_date": (status or {}).get("finished_at", today)[:10],
                "review_date": (status or {}).get("finished_at", today)[:10],
                "review_basis": "primary_source",
                "checked_by": "two Codex extractors, a reconciler, a mechanical check, a verifier, and, where flagged, a fixer and a second verifier",
                "statement": STATEMENT,
            },
            "studies": studies,
            "estimates": estimates,
            "not_extracted": ext.get("not_extracted", []),
            "open_items": ext.get("open_items", []),
            "chain": {k: v for k, v in (status or {}).items() if k != "cid"},
            "review_corrections": ext.get("review_corrections", []),
            "review_resolutions": ext.get("review_resolutions", []),
        }
        with io.open(OUT / f"{key}.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(src, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        n[src["status"]] += 1
        print(f"{cid} -> {key}.json ({src['status']}{': ' + why if why else ''}; {len(src['estimates'])} estimates)")
    print(n)


if __name__ == "__main__":
    main()
