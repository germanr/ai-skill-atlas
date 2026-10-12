"""Build the generated parts of the creativity screening report from the files on disk.

Reads candidates.json, triage/decisions.json, retrieval.json, forms/, forms/challenges/,
forms/checks/, forms/citations/, search/*.json, and link-overrides.json. Writes report-data.json
(every count the prose uses) and report-generated.md (tables and per-paper notes). Nothing is
typed by hand: each cell comes from a form field, so the audit can trace it. Form text is printed
in full; only titles and venues are shortened.
"""
import io
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
PARTICLES = {"de", "del", "della", "der", "den", "di", "da", "dos", "du", "la", "le", "van", "von", "ten", "ter", "el", "al", "bin"}
QUESTIONS = ("with_ai", "across_people", "after_ai")
SETTLED_BY_SOURCE = ("supplement", "posted_data", "authors", "journal_version")


def load(path, default=None):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return default


def family(full):
    """Family name from a full name, keeping lower-case particles (van, de, ...)."""
    parts = (full or "").replace(",", " ").split()
    if not parts:
        return full or ""
    out = [parts[-1]]
    for token in reversed(parts[:-1]):
        if token.lower() in PARTICLES:
            out.insert(0, token)
        else:
            break
    return " ".join(out)


FAMILY = {}
LINKS = {}  # cid -> {"url": str or None, "why": str}, from link-overrides.json


def join_names(names):
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    if len(names) == 3:
        return f"{names[0]}, {names[1]}, and {names[2]}"
    return f"{names[0]} et al."


def short_cite(cand, cite):
    """(label, verified). A checked citation file gives family names; when the checker could not confirm
    the family-name split, the full names are used instead of a guessed split."""
    lv = (cite or {}).get("latest_version") or {}
    year = lv.get("year") or cand.get("year")
    fams = lv.get("authors_family")
    full = [a for a in (lv.get("authors") or []) if isinstance(a, str) and a.strip()]
    if fams and not all(isinstance(x, str) and x.strip() for x in fams):
        fams = None
        names = full or None
    else:
        known = (FAMILY.get(cand.get("cid")) or {}).get("family")
        names = fams or known or ([family(a) for a in full] if full else None)
    if names:
        # Crossref gives some family names in capitals ('ZHANG'); a single all-capital word is printed in title case.
        names = [x.title() if isinstance(x, str) and x.isalpha() and x.isupper() and len(x) > 1 else x for x in names]
        who = join_names(names).replace("\u2010", "-").replace("\u2011", "-")
        return f"{who} ({year})", True
    raw = str(cand.get("authors") or "Unknown")
    etal = bool(re.search(r"et al", raw, flags=re.I))
    parts = [x.strip() for x in re.split(r",|;| and | & ", re.sub(r"et al\.?", "", raw, flags=re.I)) if x.strip()]
    if not parts:
        who = raw
    elif etal and len(parts) < 4:
        who = f"{parts[0]} et al."
    else:
        who = join_names(parts)
    return f"{who} ({year})", False


def cell(text, limit=None, table=True):
    """One line of text. In a table, pipes are escaped; elsewhere they are kept."""
    text = re.sub(r"\s+", " ", str(text if text is not None else "")).strip()
    if limit and len(text) > limit:
        cut = text[: limit - 1]
        text = (cut.rsplit(" ", 1)[0] if " " in cut[-25:] else cut).rstrip(" ,;:") + "…"
    if table:
        text = text.replace("|", "\\|")
    return text


def rct_studies(form):
    """Studies that randomize people to AI: a randomized design class, or random assignment recorded in the assignment
    block of a study with a generative-AI arm (a survey that randomizes only the order of its items does not count)."""
    return [s for s in form.get("studies", []) if str(s.get("design_class", "")).endswith("_rct")
            or ((s.get("assignment") or {}).get("randomized") == "yes"
                and any(a.get("ai") == "generative_ai" for a in s.get("arms", [])))]


def count_text(part, randomized=True):
    """People analyzed in one study, as the form records them; never a randomized count presented as analyzed.
    With randomized=False the assignment count is not called randomized (the form leaves randomization unconfirmed)."""
    n = part.get("n_analyzed")
    if isinstance(n, int):
        unit = str(part.get("counts_are") or "")
        if unit in ("", "people") or "|" in unit:
            return f"{n:,}"
        who = cell(part.get("who"), table=False)  # in full: the definition of a non-person count must not be cut
        return f"{n:,} {unit}" + (f" ({who})" if unit == "other" and who else "")
    r = part.get("n_randomized")
    if not isinstance(r, int):
        return "not reported"
    return f"not reported ({r:,} randomized)" if randomized else f"not reported ({r:,} assigned; randomization unconfirmed)"


def open_eligibility_items(final):
    """Open items that keep the paper-level verdict open: flagged as affecting eligibility and not resolved by the form itself."""
    return [i for i in (final or {}).get("open_items", []) if i.get("affects_eligibility") and i.get("settled_by") != "nothing_needed"]


def classify(cid, form, dec, retrieval, challenges):
    """Return (status, reason)."""
    if not form:
        if dec.get("path") == "out":
            return "out", f"{dec.get('a_reason')} / {dec.get('b_reason')}"
        if dec.get("path") in ("experiment_full", "experiment_small") and retrieval.get(cid, {}).get("status") != "ok":
            return "no_fulltext", ""
        return "pending", ""
    el = form.get("eligibility", {})
    final = form.get("final") or {}
    core = final.get("core") or el.get("core")
    fulltext = retrieval.get(cid, {}).get("status") == "ok"
    screener = form.get("screener", "")
    if screener.startswith("single_abstract") or (not fulltext and core in ("yes", "unclear")):
        return "no_fulltext", cell(el.get("reason"))
    if core == "yes":
        if final:
            items = open_eligibility_items(final)
            if items:
                return "clarify", " / ".join(cell(i.get("item")) for i in items)
            return "core", ""
        if any(c.get("eligibility_holds") == "no" for c in challenges):
            return "clarify", "a challenge found that an eligibility criterion fails"
        return "core_unfinalized", ""
    if core == "unclear":
        return "clarify", cell(el.get("reason"))
    c1, c2, c3 = (el.get("criterion_1_random_assignment_of_ai"), el.get("criterion_2_at_least_50_people"),
                  el.get("criterion_3_outcome_scored_on_output"))
    if c1 == "met" and c2 == "not_met" and c3 != "not_met":
        studies = rct_studies(form) or form.get("studies", [])
        return "small", "; ".join(count_text(s.get("participants") or {}) for s in studies) or "not reported"
    if el.get("context_class") in ("ai_vs_human", "observational", "synthesis"):
        return "context_" + el["context_class"], ""
    return "excluded", cell(el.get("reason"))


def outcomes_of(form):
    for s in form.get("studies", []):
        for o in s.get("outcomes", []):
            yield s, o


def main():
    cands = load(ROOT / "candidates.json", [])
    FAMILY.update(load(ROOT / "forms" / "citations-family.json", {}))
    LINKS.update(load(ROOT / "link-overrides.json", {}))
    decisions = {d["cid"]: d for d in load(ROOT / "triage" / "decisions.json", [])}
    retrieval = load(ROOT / "retrieval.json", {})
    papers = []
    for c in cands:
        cid = c["cid"]
        form = load(ROOT / "forms" / f"{cid}.json")
        cite = load(ROOT / "forms" / "citations" / f"{cid}.json")
        challenges = [x for x in (load(p) for p in sorted((ROOT / "forms" / "challenges").glob(f"{cid}.*.json"))) if x]
        check = load(ROOT / "forms" / "checks" / f"{cid}.json")
        dec = decisions.get(cid, {})
        status, reason = classify(cid, form, dec, retrieval, challenges)
        label, verified = short_cite(c, cite)
        lv = (cite or {}).get("latest_version") or {}
        if cite:  # the checked record decides the link: the version it names, never an older version's DOI
            doi, url = lv.get("doi"), lv.get("url") or c.get("url")
        else:
            doi, url = c.get("doi"), c.get("url")
        papers.append({"cid": cid, "status": status, "reason": reason, "label": label, "label_verified": verified,
                       "title": lv.get("title") or c.get("title"), "venue": lv.get("venue") or c.get("venue"),
                       "doi": doi, "url": url, "year": lv.get("year") or c.get("year"), "in_library": bool(c.get("library")),
                       "form": form, "cite": cite, "challenges": challenges, "check": check, "dec": dec,
                       "retrieval": retrieval.get(cid, {}), "cand": c})

    counts = Counter(p["status"] for p in papers)
    small_n = {}
    for p in papers:
        if p["status"] == "small":
            ints = [(s.get("participants") or {}).get("n_analyzed") for s in (rct_studies(p["form"]) or p["form"].get("studies", []))]
            ints = [n for n in ints if isinstance(n, int)]
            if ints:
                small_n[p["cid"]] = max(ints)
    data = {"n_candidates": len(cands), "status_counts": dict(counts), "n_library": sum(p["in_library"] for p in papers),
            "status_by_cid": {p["cid"]: p["status"] for p in papers}, "small_n": small_n,
            "n_small_without_analyzed_count": sum(1 for p in papers if p["status"] == "small" and p["cid"] not in small_n),
            "n_small_outcome_unclear": sum(1 for p in papers if p["status"] == "small"
                                           and (p["form"].get("eligibility") or {}).get("criterion_3_outcome_scored_on_output") == "unclear"),
            "n_nofulltext_from_context": sum(1 for p in papers if p["status"] == "no_fulltext"
                                             and p["dec"].get("path") not in ("experiment_full", "experiment_small"))}
    out = []
    w = out.append

    def link(p):
        ov = LINKS.get(p["cid"])
        if ov:
            return ov.get("url") or f"no working link: {ov.get('why')}"
        return ("https://doi.org/" + p["doi"]) if p["doi"] else (p["url"] or "no link on record")

    def paper_cell(p, title_limit=110):
        return f"{p['label']}, \"{cell(p['title'], title_limit, table=False)}\", {cell(p['venue'], 70, table=False)} ({link(p)}) [{p['cid']}]"

    def finding(p):
        if p["form"]:
            return cell(p["form"].get("one_line_finding"), table=False)
        d = p["dec"]
        n = d.get("n_a") if d.get("n_a") is not None else d.get("n_b")
        rand = d.get("randomized_a") if d.get("randomized_a") == d.get("randomized_b") else f"{d.get('randomized_a')}/{d.get('randomized_b')}"
        return cell(f"Abstract only. Random assignment stated: {rand}. Participants stated: {n if n is not None else 'no'}. {d.get('note_a') or ''}", table=False)

    def group(key):
        return sorted((p for p in papers if p["status"] == key), key=lambda p: (p["label"].lower(), p["cid"]))

    w("## Results at a glance\n")
    w("| Status | Papers |\n| --- | --- |")
    names = [("core", "Recommended for the core dataset"), ("core_unfinalized", "Core, final check pending"),
             ("clarify", "Needs clarification"), ("no_fulltext", "Experiment, full text not obtained"),
             ("small", "Randomized experiment under 50 participants"), ("context_ai_vs_human", "Context: AI versus human output"),
             ("context_observational", "Context: observational"), ("context_synthesis", "Context: synthesis"),
             ("excluded", "Excluded after screening"), ("out", "Excluded at triage"), ("pending", "Not screened: search class not an experiment")]
    for key, name in names:
        if counts.get(key):
            w(f"| {name} | {counts[key]} |")
    w(f"| Total | {len(papers):,} |\n")

    core = group("core") + group("core_unfinalized")
    by_q = Counter()
    for p in core:
        qs = {o.get("question") for _, o in outcomes_of(p["form"]) if o.get("question") in QUESTIONS and o.get("scored_on_output", True)}
        qs |= {q for q in ((p["form"].get("final") or {}).get("questions_confirmed") or []) if q in QUESTIONS}
        p["questions"] = [q for q in QUESTIONS if q in qs]
        p["ai_known"] = any(o.get("ai_available_when_produced") is not None for _, o in outcomes_of(p["form"])
                            if o.get("scored_on_output", True))
        for q in p["questions"]:
            by_q[q] += 1
    data["core_by_question"] = dict(by_q)
    data["n_core_no_question"] = sum(1 for p in core if not p["questions"])
    data["n_core_no_question_ai_unknown"] = sum(1 for p in core if not p["questions"] and not p["ai_known"])
    if core:
        w("## Recommended for the core dataset\n")
        w(f"Papers by question: with_ai {by_q.get('with_ai', 0)}, across_people {by_q.get('across_people', 0)}, after_ai {by_q.get('after_ai', 0)}. A paper can answer more than one.\n")
        w("| Paper | People analyzed, by randomized study | Design | Sample | AI role | Task | Questions | Supplement |\n| --- | --- | --- | --- | --- | --- | --- | --- |")
        for p in core:
            f = p["form"]
            rct = rct_studies(f)
            ns = "; ".join(count_text(s.get("participants") or {}) for s in rct) or "not reported"
            designs = "/".join(sorted({str(s.get("design_class") or "not recorded") for s in rct})) or "not recorded"
            pops = "/".join(sorted({str((s.get("participants") or {}).get("population") or "not recorded") for s in rct})) or "not recorded"
            roles = "/".join(sorted({str((s.get("ai_tool") or {}).get("role") or "not recorded") for s in rct})) or "not recorded"
            tasks = "/".join(sorted({str((s.get("task") or {}).get("type") or "not recorded") for s in rct})) or "not recorded"
            sup = (f.get("source") or {}).get("supplement") or {}
            supp = ("on file" if (sup.get("in_this_pdf") or sup.get("on_file")) else "not on file") if sup.get("exists") == "yes" else "none mentioned"
            qtext = ", ".join(p["questions"]) or ("not coded: AI availability during the task not recorded" if not p["ai_known"] else "not coded")
            w(f"| {p['label']} [{p['cid']}] | {cell(ns)} | {designs} | {pops} | {roles} | {tasks} | {qtext} | {supp} |")
        w("")
        w("### Notes on each recommended paper\n")
        for p in core:
            f = p["form"]
            w(f"**{p['label']}** [{p['cid']}], \"{cell(p['title'], table=False)}\". {cell(p['venue'], table=False)}. {link(p)}\n")
            ver = cell((f.get("source") or {}).get("version"), table=False)
            latest = (p["cite"] or {}).get("pdf_is_latest")
            w(f"- Version read: {ver}" + (" A later version exists." if latest is False else ""))
            w(f"- Finding: {finding(p)}")
            overlap = (f.get("sample_overlap") or {}).get("shares_participants_with")
            if overlap:
                w(f"- Sample overlap, as the form records it: {cell(overlap, table=False)}")
            seen = set()
            for s, o in outcomes_of(f):
                q = o.get("question")
                if q in QUESTIONS and q not in seen and o.get("scored_on_output", True):
                    seen.add(q)
                    first = (o.get("contrasts") or [{}])[0]
                    w(f"- `{q}`, {cell(o.get('name'), table=False)} ({o.get('measure')}, unit {o.get('unit')}): "
                      f"{cell(first.get('reported'), table=False)} [{cell(first.get('locator'), table=False)}]")
            for q in (f.get("final") or {}).get("questions_confirmed") or []:
                if q in QUESTIONS and q not in seen:
                    w(f"- `{q}`: confirmed by the finalizer for part of the sample; see the form's final object.")
            fin = f.get("final") or {}
            for item in [i for i in fin.get("open_items", []) if i.get("settled_by") in SETTLED_BY_SOURCE]:
                w(f"- Needs {item.get('settled_by').replace('_', ' ')}: {cell(item.get('item'), table=False)}")
            w("")

    clar = group("clarify")
    if clar:
        w("## Candidates that need clarification\n")
        w("| Paper | People analyzed, by study | What is unsettled |\n| --- | --- | --- |")
        for p in clar:
            crit = ((p["form"].get("final") or {}).get("criteria") or {}).get("random_assignment_of_ai") or (p["form"].get("eligibility") or {}).get("criterion_1_random_assignment_of_ai")
            ns = "; ".join(count_text(s.get("participants") or {},
                                      randomized=(s.get("assignment") or {}).get("randomized") == "yes" and crit == "met")
                           for s in p["form"].get("studies", [])) or "not reported"
            w(f"| {cell(paper_cell(p))} | {cell(ns)} | {cell(p['reason'])} |")
        w("")

    def table(key, heading, cols, rowfn):
        rows = group(key)
        if not rows:
            return
        w(f"## {heading}\n")
        w("| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |")
        for p in rows:
            w("| " + " | ".join(cell(x) for x in rowfn(p)) + " |")
        w("")

    def where(p):
        ov = LINKS.get(p["cid"])
        if ov:
            return ov.get("url") or f"no working link: {ov.get('why')}"
        hint = p["retrieval"].get("suggestion_for_owner")
        urls = re.findall(r"https?://[^\s)\"']+", hint or "")
        return (urls[0].rstrip(".,;") if urls else link(p))

    table("no_fulltext", "Experiments with full text not obtained", ["Paper", "What the available text says", "Where to get it"],
          lambda p: (paper_cell(p), finding(p), where(p)))
    table("small", "Randomized experiments under 50 participants", ["Paper", "People analyzed, by randomized study", "Finding"],
          lambda p: (paper_cell(p), p["reason"], finding(p)))
    table("context_ai_vs_human", "Context: AI versus human output", ["Paper", "Finding"], lambda p: (paper_cell(p), finding(p)))
    table("context_observational", "Context: observational", ["Paper", "Finding"], lambda p: (paper_cell(p), finding(p)))

    def synth(p):
        s = (p["form"] or {}).get("synthesis") or {}
        pooled = "; ".join(f"{cell(x.get('comparison'), table=False)}: {cell(x.get('estimate'), table=False)} {cell(x.get('interval'), table=False)}"
                           for x in s.get("pooled", []) if x.get("estimate"))
        return paper_cell(p), s.get("k_studies"), pooled or finding(p)
    table("context_synthesis", "Context: syntheses", ["Paper", "Studies", "Pooled estimates"], synth)
    table("excluded", "Excluded after screening", ["Paper", "Reason"], lambda p: (paper_cell(p), p["reason"]))
    table("out", "Excluded at triage", ["Paper", "Reasons given by the two screeners"], lambda p: (paper_cell(p), p["reason"]))

    lib = sorted((p for p in papers if p["in_library"]), key=lambda p: (p["label"].lower(), p["cid"]))
    if lib:
        w("## Reclassification of the current collection\n")
        w("| Paper | May 2026 label | New status | Design found | Basis |\n| --- | --- | --- | --- | --- |")
        libinfo = {r["md_path"]: r for r in load(ROOT / "search" / "library.json", [])}
        for p in lib:
            row = libinfo.get(p["cand"]["library"]["md_path"], {})
            old = f"{row.get('current_design_class') or 'not in the JSON'}; {row.get('current_theme') or ''}".strip("; ")
            f = p["form"] or {}
            designs = "/".join(sorted({(s.get("design_class") or "not recorded") for s in f.get("studies", [])}))
            if p["status"] == "small":
                basis = f"people analyzed: {p['reason']}"
            elif p["status"] in ("excluded", "clarify"):
                basis = p["reason"]
            else:
                basis = cell((f.get("eligibility") or {}).get("reason"), table=False)
            w(f"| {p['label']} [{p['cid']}], \"{cell(p['title'], 80, table=False)}\" | {cell(old)} | {p['status']} | {cell(designs)} | {cell(basis)} |")
        w("")

    core_like = core + clar
    rows_div, rows_after, cids_div, cids_after = [], [], set(), set()
    for p in core_like:
        who = f"{p['label']} [{p['cid']}]"
        for s, o in outcomes_of(p["form"]):
            first = (o.get("contrasts") or [{}])[0]
            if o.get("construct") == "diversity" and o.get("question") in QUESTIONS:
                d = o.get("diversity_detail") or {}
                cids_div.add(p["cid"])
                rows_div.append((who, o.get("question"), cell(d.get("metric") or o.get("name")), cell(d.get("computed_over")),
                                 cell(d.get("uncertainty")), o.get("unit"), ", ".join(first.get("statistics_available") or []),
                                 cell(first.get("reported")), cell(first.get("locator"))))
            if o.get("question") == "after_ai":
                cids_after.add(p["cid"])
                rows_after.append((who, o.get("construct"), cell(o.get("name")), o.get("measure"), o.get("unit"),
                                   cell(o.get("delay") or o.get("timing")), cell(first.get("reported")), cell(first.get("locator"))))
    if rows_div:
        w("## The diversity measure: what each experiment reports\n")
        w("| Paper | Question | Measure | Computed over | Uncertainty | Unit | Statistics | Reported | Where |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for r in sorted(rows_div, key=lambda r: str(r)):
            w("| " + " | ".join(str(x) for x in r) + " |")
        w("")
    if rows_after:
        w("## Outcomes measured after AI was removed\n")
        w("| Paper | Construct | Outcome | Measure | Unit | Timing | Reported | Where |\n| --- | --- | --- | --- | --- | --- | --- | --- |")
        for r in sorted(rows_after, key=lambda r: str(r)):
            w("| " + " | ".join(str(x) for x in r) + " |")
        w("")

    w("## Search record\n")
    w("| Source | Queries | Candidates | Found only here | Limits |\n| --- | --- | --- | --- | --- |")
    only = Counter()
    for c in cands:
        if len(c["lanes"]) == 1:
            only[c["lanes"][0]] += 1
    for path in sorted((ROOT / "search").glob("*.json")):
        if path.name == "library.json":
            continue
        d = load(path, {})
        w(f"| {path.stem} | {len(d.get('queries', []))} | {len(d.get('candidates', []))} | {only.get(path.stem, 0)} | {cell(d.get('coverage_limits'), 260)} |")
    w("")

    # Works that the search found and nobody has triaged: listed in a separate file.
    untriaged = [c for c in cands if c["cid"] not in decisions or decisions[c["cid"]].get("path") == "untriaged"]
    untriaged = [c for c in untriaged if not c.get("library")]
    guess = lambda c: max(c["design_guesses"], key=c["design_guesses"].get)
    names = {"randomized_experiment_people": "Experiment, random assignment stated", "experiment_assignment_unclear": "Experiment, assignment not stated",
             "quasi_experiment_people": "Quasi-experiment", "ai_vs_human_output": "AI versus human output", "observational": "Observational",
             "synthesis": "Synthesis", "model_only": "Model only", "other": "Other or unclear"}
    lines = ["# Works identified by the search and not screened\n",
             "Generated from `candidates.json`. The class is the search agent's reading of the abstract. Nobody has checked these records, so authors, years, and counts can be wrong.\n"]
    by_guess = Counter(guess(c) for c in untriaged)
    for key in names:
        rows = sorted((c for c in untriaged if guess(c) == key), key=lambda c: (str(c.get("authors") or "").lower(), str(c.get("year"))))
        if not rows:
            continue
        lines.append(f"## {names[key]}: {len(rows)}\n")
        lines.append("| Paper | Participants reported | Found by |\n| --- | --- | --- |")
        for c in rows:
            ref = ("https://doi.org/" + c["doi"]) if c.get("doi") else (c.get("url") or "")
            n = ", ".join(str(x) for x in c.get("n_participants_reported") or []) or ""
            lanes = ", ".join(x.replace("lane-", "").replace("seed-", "") for x in c["lanes"])
            lines.append(f"| {cell(c.get('authors'), 60)} ({c.get('year')}), \"{cell(c.get('title'), 130)}\", {cell(c.get('venue'), 60)} ({ref}) [{c['cid']}] | {n} | {lanes} |")
        lines.append("")
    with io.open(ROOT / "identified-not-screened.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    data["n_untriaged"] = len(untriaged)
    data["untriaged_by_guess"] = dict(by_guess)

    data["n_diversity_outcomes"] = len(rows_div)
    data["n_after_ai_outcomes"] = len(rows_after)
    data["papers_with_diversity"] = len(cids_div)
    data["papers_with_after_ai"] = len(cids_after)
    data["unverified_labels"] = [f"{p['cid']} {p['label']}" for p in papers if not p["label_verified"] and p["status"] not in ("pending", "out")]
    with io.open(ROOT / "report-generated.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    with io.open(ROOT / "report-data.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(data["status_counts"]), "| by question", dict(by_q), "| diversity rows", len(rows_div), "| after_ai rows", len(rows_after))


if __name__ == "__main__":
    main()
