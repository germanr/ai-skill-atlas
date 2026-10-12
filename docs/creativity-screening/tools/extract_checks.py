"""Mechanical checks for the Phase 2 extraction files (no model involved).

diff_extractions(a, b)  -> the differences between the two independent extractions, for the reconciler.
mechanical_check(ext, pdf_path) -> problems the verifier must look at: numbers missing from their quotes, quotes not
found on the cited PDF page, invalid codes, duplicate slugs, numbers without a source.
"""
import io
import json
import math
import re
import unicodedata

ENUMS = {
    "question": {"with_ai", "across_people", "after_ai"},
    "construct": {"overall_creativity", "novelty", "usefulness", "fluency", "flexibility", "elaboration", "convergent", "diversity", "other"},
    "measure": {None, "human_raters", "expert_raters", "embedding_similarity", "lexical_overlap", "category_count", "automated_score", "behavioral", "length", "text_features"},
    "unit": {None, "participant", "team", "output", "rating", "pair", "set"},
    "outcome_timing": {"immediate", "delayed"},
    "comparison_type": {"ai_vs_bau", "ai_vs_active", "ai_design"},
    "within_person": {None, "first_round", "paired"},
    "higher_is": {"more_creative", "less_creative", "more_diverse", "more_similar", "more_ideas", "more_accurate", "other"},
    "se_basis": {"participant", "cluster", "output", "rating", "pair", "set", "not_reported", "unclear"},
}
STAT_KEYS = ["treatment_mean", "treatment_sd", "treatment_se", "control_mean", "control_sd", "control_se", "difference",
             "difference_se", "ci_lower", "ci_upper"]
COUNT_KEYS = ["n_treatment", "n_control", "n_total", "n_units"]


def load(path):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return None


def numbers_of(est):
    """{field name: value} for every number recorded in an estimate (stats, nested stats, counts)."""
    out = {}
    st = est.get("stats") or {}
    for k in STAT_KEYS:
        if isinstance(st.get(k), (int, float)):
            out[k] = st[k]
    for blk, keys in (("regression", ["coef", "se"]), ("test", ["value", "df"]), ("paper_effect", ["value", "se", "ci_lower", "ci_upper"])):
        b = st.get(blk)
        if isinstance(b, dict):
            for k in keys:
                v = b.get(k)
                if isinstance(v, (int, float)):
                    out[f"{blk}.{k}"] = v
                elif isinstance(v, list):
                    for i, x in enumerate(v):
                        if isinstance(x, (int, float)):
                            out[f"{blk}.{k}[{i}]"] = x
    if isinstance(st.get("p_value"), (int, float)):
        out["p_value"] = st["p_value"]
    for k in COUNT_KEYS:
        if isinstance(est.get(k), (int, float)):
            out[k] = est[k]
    return out


def norm_text(t):
    t = unicodedata.normalize("NFKC", str(t or ""))
    t = t.replace("−", "-").replace("–", "-").replace("—", "-").replace("‐", "-").replace("‑", "-")
    t = re.sub(r"-\s*\n\s*", "-", t)
    t = re.sub(r"(?<=[A-Za-z])- (?=[a-z])", "-", t)  # a hyphen left by a line break: "ChatGPT- assisted"
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def number_forms(v):
    """Printed forms a recorded number may take: 0.5 / .5 / 0.50 / 1,234 / -0.31."""
    forms = set()
    if isinstance(v, bool):
        return forms
    if isinstance(v, int) or (isinstance(v, float) and v.is_integer() and abs(v) >= 1):
        i = int(v)
        forms |= {str(i), f"{i:,}", f"{abs(i)}", f"{abs(i):,}"}
    else:
        s = repr(float(v))
        if "e" in s:
            s = f"{v:.10f}".rstrip("0")
        a = s.lstrip("-")
        forms |= {s, a}
        if a.startswith("0."):
            forms.add(a[1:])
        # trailing zeros the source may print
        if "." in a:
            for extra in range(1, 4):
                forms.add(a + "0" * extra)
                if a.startswith("0."):
                    forms.add(a[1:] + "0" * extra)
    return forms


# A number token: optional sign (only when the sign does not follow a letter or digit, so "Control-0.31" reads 0.31),
# digits with optional thousands commas and decimals, or a leading-dot decimal, and an optional exponent.
# A number token. A sign counts only when it does not follow a letter or digit ("Control-0.31" reads 0.31), but the digits
# may follow a letter, as in a subscripted degree of freedom ("t231" reads 231).
NUM_TOKEN = re.compile(r"(?:(?<![\w.])[-+])?(?<![\d.])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?:e[-+]?\d+)?", re.I)
# Scientific notation as typeset: 2.87 x 10-4, 2.87 × 10^-4, 2.87e-4.
SCI = re.compile(r"(\d+(?:\.\d+)?)\s*[x\u00d7*]\s*10\s*\^?\s*([-+])?\s*(\d+)", re.I)
MINUS_SPACED = re.compile(r"(?<![\w.])-\s+(\d+(?:\.\d+)?|\.\d+)(?!\d|,\d)")
DECIMAL_COMMA = re.compile(r"(?<![\d.,])(\d+),(\d{1,3})(?!\d|,\d)")
# Letters that a broken ligature drops from a PDF's text layer ("signi?cant"); removed from both sides when it happens.
LIGATURE = re.compile("ffi|ffl|ff|fi|fl|[\uffff\ufffd]")
# Everything but letters, digits, decimal points, and minus signs (a hyphen inside a word is dropped, a minus before a digit kept).
BARE = re.compile(r"[^a-z0-9.\-]|-(?![\d.])|(?<![\d])\.(?![\d])")


def numbers_in(text):
    q = norm_text(text)
    vals = []
    for mant, sign, exp in SCI.findall(q):
        try:
            vals.append(float(mant) * 10 ** (-int(exp) if sign == "-" else int(exp)))
        except ValueError:
            pass
    for tok in NUM_TOKEN.findall(q):
        try:
            vals.append(float(tok.replace(",", "")))
        except ValueError:
            pass
        if "," in tok:  # "F(1,198)": a pair of degrees of freedom, not one thousand one hundred ninety-eight
            for part in tok.split(","):
                try:
                    vals.append(float(part))
                except ValueError:
                    pass
    # A minus sign set off by a space, as typeset in "d = 0.79 and - 0.62", also reads as a negative number.
    for tok in MINUS_SPACED.findall(q):
        vals.append(-float(tok))
    # A decimal comma, as in "4,2 versus 2 categories", also reads as a decimal point.
    for a, b in DECIMAL_COMMA.findall(q):
        vals.append(float(f"{a}.{b}"))
    return vals


def number_in_quote(v, quote):
    """True if the quote prints the value: numbers are compared by value, so 1.210000, 1.21, and 2.87 x 10-4 all match."""
    try:
        target = float(v)
    except (TypeError, ValueError):
        return False
    return any(math.isclose(f, target, rel_tol=1e-9, abs_tol=1e-12) for f in numbers_in(quote))


_PDF_CACHE = {}


def pdf_pages(pdf_path):
    if pdf_path in _PDF_CACHE:
        return _PDF_CACHE[pdf_path]
    pages = None
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        pages = [norm_text(p.get_text()) for p in doc]
    except Exception:
        pages = None
    _PDF_CACHE[pdf_path] = pages
    return pages


def cited_pages(locator):
    """PDF page numbers named in a locator: 'PDF p. 12', 'p. 12', 'pp. 12-13'."""
    loc = str(locator or "")
    m = re.findall(r"PDF pp?\.\s*(\d+)(?:\s*[-–]\s*(\d+))?", loc)
    if not m:
        m = re.findall(r"\bpp?\.\s*(\d+)(?:\s*[-–]\s*(\d+))?", loc)
    pages = []
    for a, b in m:
        a = int(a)
        b = int(b) if b else a
        pages += list(range(a, min(b, a + 5) + 1))
    return pages


def quote_on_pages(quote, pages_text, pages):
    """True if the quote (or each of its long pieces) appears on one of the pages, allowing one page either side."""
    q = norm_text(quote)
    if not q or not pages_text:
        return None
    pieces = [x.strip() for x in re.split(r"\s*(?:\.\.\.|…|\|)\s*", q) if len(x.strip()) >= 12] or [q]
    cand = set()
    for p in pages:
        cand |= {p - 1, p, p + 1}
    cand = [p for p in sorted(cand) if 1 <= p <= len(pages_text)]
    if not cand:
        cand = list(range(1, len(pages_text) + 1))
    text = " ".join(pages_text[p - 1] for p in cand)
    squeezed = re.sub(r"\s+", "", text)
    if all(piece in text or re.sub(r"\s+", "", piece) in squeezed for piece in pieces):
        return True
    if "\uffff" in text or "\ufffd" in text:
        lig_text = LIGATURE.sub("", squeezed)
        if all(LIGATURE.sub("", re.sub(r"\s+", "", piece)) in lig_text for piece in pieces):
            return True
    # Symbols, punctuation, and line-break hyphens differ between a quote and a PDF's text layer ("ps <=0.002",
    # "Access-to-\nCue"). Compare letters, digits, decimal points, and minus signs only; a piece needs 15 such characters.
    bare_text = BARE.sub("", text)
    bare_pieces = [BARE.sub("", piece) for piece in pieces]
    if all(len(b) >= 15 for b in bare_pieces) and all(b in bare_text for b in bare_pieces):
        return True
    if all(len(b) >= 15 for b in bare_pieces) and ("\uffff" in text or "\ufffd" in text):
        lig_bare = LIGATURE.sub("", bare_text)
        if all(LIGATURE.sub("", b) in lig_bare for b in bare_pieces):
            return True
    # A quote assembled from table cells is rarely a continuous string of the page's text. Accept it when every number in
    # the quote is printed on the cited pages: a wrong page still fails.
    qnums = numbers_in(quote)
    if len(qnums) >= 2:
        page_nums = numbers_in(text)
        if all(any(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12) for b in page_nums) for a in qnums):
            return True
    return False


def mechanical_check(ext, pdf_path, extra_pdfs=None):
    """extra_pdfs: supplement PDFs; a quote not found on the cited main-PDF page may sit anywhere in a supplement."""
    problems = []
    if not isinstance(ext, dict):
        return [{"where": "file", "problem": "missing or unparseable"}]
    pages_text = pdf_pages(pdf_path) if pdf_path else None
    slugs = [e.get("slug") for e in ext.get("estimates", [])]
    for s in {x for x in slugs if slugs.count(x) > 1}:
        problems.append({"where": s, "problem": "duplicate slug"})
    studies = {s.get("study_id") for s in ext.get("studies", [])}
    units = {s.get("study_id"): s.get("assignment_unit") for s in ext.get("studies", [])}
    for e in ext.get("estimates", []):
        slug = e.get("slug")
        if not re.fullmatch(r"[a-z0-9_]+", str(slug or "")):
            problems.append({"where": slug, "problem": "slug must be lowercase letters, digits, and underscores"})
        if e.get("study_id") not in studies:
            problems.append({"where": slug, "problem": f"study_id {e.get('study_id')} is not a study of this file"})
        for k, allowed in ENUMS.items():
            v = e.get(k)
            if v == "null":
                v = None
            if k in e and v not in allowed:
                problems.append({"where": slug, "problem": f"{k} = {v!r} is not one of {sorted(map(str, allowed))}"})
        if e.get("se_basis") == "cluster" and units.get(e.get("study_id")) not in ("team", "class", "session"):
            problems.append({"where": f"{slug}.se_basis", "problem": "se_basis is cluster, but the study did not randomize clusters "
                             f"(assignment_unit {units.get(e.get('study_id'))}); standard errors clustered by raters or items are "
                             "output or rating (extraction file, field notes)"})
        nums = numbers_of(e)
        covered = {}
        for src in e.get("sources") or []:
            for f in src.get("fields") or []:
                covered[f] = src
        for f, v in nums.items():
            base = f.split("[")[0]
            src = covered.get(f) or covered.get(base) or covered.get(f.split(".")[0]) or covered.get("stats." + f)
            if src is None:
                problems.append({"where": f"{slug}.{f}", "problem": f"number {v} has no source"})
                continue
            if not number_in_quote(v, src.get("quote")):
                problems.append({"where": f"{slug}.{f}", "problem": f"number {v} does not appear in its quote", "quote": src.get("quote")})
        for src in e.get("sources") or []:
            ok = quote_on_pages(src.get("quote"), pages_text, cited_pages(src.get("locator")))
            if ok is False and extra_pdfs:
                for extra in extra_pdfs:
                    if quote_on_pages(src.get("quote"), pdf_pages(extra), []):
                        ok = True
                        break
            if ok is False:
                problems.append({"where": slug, "problem": "quote not found on the cited PDF page (or the next or previous page)",
                                 "locator": src.get("locator"), "quote": src.get("quote")})
    return problems


def _key(e):
    arms = (str(e.get("treatment_arm") or "").lower().strip(), str(e.get("control_arm") or "").lower().strip())
    return (e.get("study_id"), e.get("form_outcome_id") or norm_text(e.get("outcome"))[:40], arms, e.get("within_person"))


def diff_extractions(a, b):
    """Differences between extractions A and B: per study and per estimate, matched by slug, then by outcome and arms."""
    out = {"studies": [], "estimates": [], "only_in_a": [], "only_in_b": []}
    sa = {s.get("study_id"): s for s in (a or {}).get("studies", [])}
    sb = {s.get("study_id"): s for s in (b or {}).get("studies", [])}
    for sid in sorted(set(sa) | set(sb), key=str):
        if sid not in sa or sid not in sb:
            out["studies"].append({"study_id": sid, "difference": "only in " + ("A" if sid in sa else "B")})
            continue
        for k in ["design_class", "assignment_unit", "clusters_per_arm", "n_randomized", "n_analyzed", "population", "task_type",
                  "ai_role", "ai_tool", "arms"]:
            va, vb = sa[sid].get(k), sb[sid].get(k)
            if k == "ai_tool":  # compare the model and year, not the wording of the locator
                va, vb = [{x: (v or {}).get(x) for x in ("name", "year")} for v in (va, vb)]
                va["name"], vb["name"] = norm_text(va["name"]), norm_text(vb["name"])
            if k == "arms":  # compare names, AI status, and counts, not the wording of the descriptions
                va, vb = [sorted([[norm_text(a.get("name")), a.get("ai"), a.get("n_randomized"), a.get("n_analyzed")] for a in (v or [])],
                                 key=json.dumps) for v in (va, vb)]
            if json.dumps(va, sort_keys=True) != json.dumps(vb, sort_keys=True):
                out["studies"].append({"study_id": sid, "field": k, "a": sa[sid].get(k), "b": sb[sid].get(k)})
    ea = list((a or {}).get("estimates", []))
    eb = list((b or {}).get("estimates", []))
    pairs, used_b = [], set()
    by_slug_b = {e.get("slug"): i for i, e in enumerate(eb)}
    rest_a = []
    for e in ea:
        i = by_slug_b.get(e.get("slug"))
        if i is not None and i not in used_b:
            pairs.append((e, eb[i])); used_b.add(i)
        else:
            rest_a.append(e)
    by_key_b = {}
    for i, e in enumerate(eb):
        if i not in used_b:
            by_key_b.setdefault(_key(e), []).append(i)
    for e in rest_a:
        lst = by_key_b.get(_key(e)) or []
        lst = [i for i in lst if i not in used_b]
        if lst:
            pairs.append((e, eb[lst[0]])); used_b.add(lst[0])
        else:
            out["only_in_a"].append({"slug": e.get("slug"), "study_id": e.get("study_id"), "outcome": e.get("outcome"),
                                     "treatment_arm": e.get("treatment_arm"), "control_arm": e.get("control_arm")})
    for i, e in enumerate(eb):
        if i not in used_b:
            out["only_in_b"].append({"slug": e.get("slug"), "study_id": e.get("study_id"), "outcome": e.get("outcome"),
                                     "treatment_arm": e.get("treatment_arm"), "control_arm": e.get("control_arm")})
    fields = ["question", "construct", "measure", "unit", "n_units", "outcome_timing", "delay_days", "outcome_with_ai",
              "comparison_type", "within_person", "n_treatment", "n_control", "n_total", "higher_is", "se_basis"]
    for x, y in pairs:
        d = []
        for k in fields:
            if json.dumps(x.get(k)) != json.dumps(y.get(k)):
                d.append({"field": k, "a": x.get(k), "b": y.get(k)})
        nx, ny = numbers_of(x), numbers_of(y)
        for k in sorted(set(nx) | set(ny)):
            vx, vy = nx.get(k), ny.get(k)
            if vx is None or vy is None or not math.isclose(float(vx), float(vy), rel_tol=1e-9, abs_tol=1e-12):
                d.append({"field": k, "a": vx, "b": vy})
        if d:
            out["estimates"].append({"slug_a": x.get("slug"), "slug_b": y.get("slug"), "outcome": x.get("outcome"),
                                     "differences": d})
    out["n_pairs"] = len(pairs)
    return out
