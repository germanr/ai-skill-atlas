"""Assemble docs/creativity-screening-2026-10-04.md from the hand-written sections and the generated tables.

Usage: python assemble_report.py [<prose.md> [<output.md>]]   (default prose: report-prose.md)

The hand-written file holds the prose sections (scope, method, coverage limits, display options,
Review 1 decisions, implications). Every count in the assembled prose is computed here from
report-data.json and the forms, never typed, so the audit can trace it. Run build_report.py first.
"""
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DOCS = ROOT.parent
OUT = DOCS / "creativity-screening-2026-10-04.md"


def sections(text):
    """Split a markdown file into (title_line, {heading: body}) on '## ' headings, in order."""
    parts, order = {}, []
    title = ""
    cur, buf = None, []
    for line in text.splitlines():
        if line.startswith("# ") and cur is None and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if cur is not None:
                parts[cur] = "\n".join(buf).strip("\n")
            cur = line[3:].strip()
            order.append(cur)
            buf = []
        else:
            buf.append(line)
    if cur is not None:
        parts[cur] = "\n".join(buf).strip("\n")
    return title, parts, order


GUESS_LABEL = {"ai_vs_human_output": "AI versus human output", "observational": "observational", "other": "other or unclear",
               "synthesis": "synthesis", "model_only": "model only", "quasi_experiment_people": "quasi-experiment",
               "randomized_experiment_people": "experiment with random assignment stated", "experiment_assignment_unclear": "experiment with assignment not stated"}


def n(x):
    return f"{x:,}"


def main():
    fixed_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "report-prose.md"
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    title, fixed, _ = sections(io.open(fixed_path, encoding="utf-8").read())
    _, gen, gen_order = sections(io.open(ROOT / "report-generated.md", encoding="utf-8").read())
    data = json.load(io.open(ROOT / "report-data.json", encoding="utf-8"))
    sc = data["status_counts"]
    forms = {}
    for p in (ROOT / "forms").glob("c*.json"):
        if p.stem[1:].isdigit():
            try:
                forms[p.stem] = json.load(io.open(p, encoding="utf-8")).get("screener") or ""
            except Exception:
                pass
    n_final = sum(1 for s in forms.values() if s == "final")
    n_recon = sum(1 for s in forms.values() if s == "reconciled")
    n_short = sum(1 for s in forms.values() if s.startswith("single"))
    n_screened = len(forms)
    core = sc.get("core", 0)
    core_unf = sc.get("core_unfinalized", 0)
    q = data.get("core_by_question", {})
    untri = data.get("n_untriaged", 0)
    ug = data.get("untriaged_by_guess", {})
    decisions = json.load(io.open(ROOT / "triage" / "decisions.json", encoding="utf-8"))
    n_triaged = sum(1 for d in decisions if d.get("path") != "untriaged")

    # Counts for the hand-written prose: every {{name}} in report-prose.md is filled here.
    cands = json.load(io.open(ROOT / "candidates.json", encoding="utf-8"))
    dec_by = {d["cid"]: d for d in decisions}
    search_files = [pp for pp in sorted((ROOT / "search").glob("*.json")) if pp.name != "library.json"]
    sdata = [json.load(io.open(pp, encoding="utf-8")) for pp in search_files]
    seed_works = [c for c in cands if any(l.startswith("seed-") for l in c["lanes"])]
    lane_works = [c for c in cands if not any(l.startswith("seed-") for l in c["lanes"])]
    triaged = lambda c: dec_by.get(c["cid"], {}).get("path", "untriaged") != "untriaged"
    if not all(triaged(c) or c.get("library") for c in seed_works):
        print("WARNING: some non-library seed works are untriaged:", [c["cid"] for c in seed_works if not triaged(c) and not c.get("library")][:20])
    retrieval = json.load(io.open(ROOT / "retrieval.json", encoding="utf-8"))
    # Screening jobs only: the raw-data checks run after Review 1 (job names "data-<cid>") are not part of the screening.
    n_jobs = sum(sum(1 for line in io.open(pp, encoding="utf-8") if line.strip() and not json.loads(line).get("job", "").startswith("data-"))
                 for pp in (ROOT / "codex-jobs").glob("jobs-*.jsonl"))
    small_ns = [int(v) for v in data.get("small_n", {}).values() if isinstance(v, int) or str(v).isdigit()]
    audits = [json.load(io.open(pp, encoding="utf-8")) for pp in sorted((ROOT / "audit").glob("*/summary.json"))]

    def series(items):
        return items[0] if len(items) == 1 else ", ".join(items[:-1]) + (", and " if len(items) > 2 else " and ") + items[-1]
    fills = {
        "n_lanes": n(sum(1 for pp in search_files if pp.name.startswith("lane-"))),
        "n_queries": n(sum(len(d.get("queries", [])) if isinstance(d, dict) else 0 for d in sdata)),
        "n_records": n(sum(len(d.get("candidates", [])) if isinstance(d, dict) else len(d) for d in sdata)),
        "n_works": n(len(cands)),
        "max_id": str(max(int(c["cid"][1:]) for c in cands)),
        "n_seed_works": n(len(seed_works)),
        "n_library": n(sum(1 for c in seed_works if c.get("library"))),
        "n_seed_triaged": n(sum(1 for c in seed_works if triaged(c))),
        "n_lane_works": n(len(lane_works)),
        "n_lane_triaged": n(sum(1 for c in lane_works if triaged(c))),
        "n_untriaged": n(untri),
        "n_owner": n(sum(1 for v in retrieval.values() if v.get("source") == "owner")),
        "n_codex_jobs": n(n_jobs),
        "n_small": n(sc.get("small", 0)),
        "small_min": n(min(small_ns)) if small_ns else "?",
        "small_max": n(max(small_ns)) if small_ns else "?",
        "n_small_unreported": n(data.get("n_small_without_analyzed_count", 0)),
        "n_audit_rounds": n(len(audits)),
        "audit_confirmed_by_round": series([n(a.get("confirmed", 0)) for a in audits]),
    }

    def fill(text):
        for k, v in fills.items():
            text = text.replace("{{" + k + "}}", v)
        left = re.findall(r"\{\{(\w+)\}\}", text)
        if left:
            raise SystemExit(f"unfilled placeholders: {left}")
        return text

    fixed = {k: fill(v) for k, v in fixed.items()}
    print("filled:", fills)

    def download_sentence():
        html = io.open(ROOT / "to-download.html", encoding="utf-8").read()
        dl = set(re.findall(r"\[(c\d{3,4})\]", html))
        nf = {c for c, s in data.get("status_by_cid", {}).items() if s == "no_fulltext"}
        both, extra, missing = dl & nf, dl - nf, nf - dl
        text = (f"`docs/creativity-screening/to-download.html` lists the {n(len(dl))} papers on the screening paths that have no full text on file, with every link found: "
                f"the {n(len(both))} papers in this table and {n(len(extra))} papers that appear in other sections.")
        if missing:
            text += f" It omits {n(len(missing))} papers of this table ({', '.join(sorted(missing))})."
        return text

    out = [f"# {title}", ""]

    def add(heading, body):
        out.append(f"## {heading}")
        out.append("")
        out.append(body.strip("\n"))
        out.append("")

    add("Scope and decision rule", fixed["Scope and decision rule"])
    add("How the screening was done", fixed["How the screening was done"])
    add("Coverage limits", fixed["Coverage limits"])

    glance = [
        f"The search identified {n(data['n_candidates'])} works. Of these, {n(n_triaged)} were triaged from their abstracts, and the {n(data.get('n_library', 0))} papers of the May collection went straight to full-text screening. "
        f"The other {n(untri)} were not screened, because their search class was not an experiment of any kind; `docs/creativity-screening/identified-not-screened.md` lists them ({', '.join(f'{GUESS_LABEL.get(k, k)} {v}' for k, v in sorted(ug.items(), key=lambda kv: -kv[1]))}). "
        f"A screening form exists for {n(n_screened)} papers: {n(n_final)} went through the two-screener pipeline to a final verdict"
        + (f", {n(n_recon)} are reconciled and await a final verdict" if n_recon else "")
        + f", and {n(n_short)} went through the short form. "
        f"The core recommendation covers {n(core)} papers{(', and ' + n(core_unf) + ' more are core on their current form but not yet finalized') if core_unf else ''}. "
        f"Another {n(sc.get('clarify', 0))} need a clarification before they can enter, {n(sc.get('small', 0))} are randomized experiments with fewer than 50 people, "
        f"and {n(sc.get('no_fulltext', 0))} experiments have no full text on file and are listed with where to get them. "
        f"Context papers number {n(sc.get('context_ai_vs_human', 0) + sc.get('context_observational', 0) + sc.get('context_synthesis', 0))}. "
        f"Screening excluded {n(sc.get('excluded', 0))} papers after reading and triage excluded {n(sc.get('out', 0))}.",
        "",
        gen["Results at a glance"],
    ]
    add("Results at a glance", "\n".join(glance))
    rev = fixed["Decisions for Review 1"]
    add("Decisions for Review 1", rev)

    nq = data.get("n_core_no_question", 0)
    rec_intro = (f"The {n(core)} recommended papers are randomized experiments in which people were assigned to generative-AI assistance, with at least 50 people analyzed and creativity or diversity scored on the output. "
                 f"By question, {n(q.get('with_ai', 0))} answer `with_ai`, {n(q.get('across_people', 0))} answer `across_people`, and {n(q.get('after_ai', 0))} answer `after_ai`; a paper can answer more than one. "
                 + (f"For {n(nq)} of them no question is coded yet, because the form does not record whether AI was available while the output was produced. " if nq and nq == data.get("n_core_no_question_ai_unknown") else
                    f"For {n(nq)} of them no question is coded yet. " if nq else "") +
                 "The table gives the people analyzed in each randomized study, the design, the sample, the role of the AI, the task, and whether the paper's supplement is on file. The statistics quoted in the notes come from the PDF or, where no PDF exists, from the publisher's article text. The notes give the version read, the one-line finding, any sample overlap the form records, the first reported contrast for each question, and what would settle each open item.")
    body = gen["Recommended for the core dataset"]
    body = re.sub(r"^Papers by question:.*?\n\n", "", body, count=1, flags=re.S)
    add("Recommended for the core dataset", rec_intro + "\n\n" + body)

    if "Candidates that need clarification" in gen:
        add("Candidates that need clarification",
            f"For these {n(sc.get('clarify', 0))} papers one criterion rests on a passage the paper does not contain, usually how people came to be in each condition, or a checker found that a criterion fails. Each row says what is unsettled and, where the form records it, what would settle it (a supplement, posted data, the authors, or the journal version).\n\n" + gen["Candidates that need clarification"])
    if "Experiments with full text not obtained" in gen:
        add("Experiments with full text not obtained",
            (f"These {n(sc.get('no_fulltext', 0))} papers have no full text on file: neither the retrieval script nor the retrieval agents could obtain one through a legitimate route. Triage called {n(sc.get('no_fulltext', 0) - data['n_nofulltext_from_context'])} of them experiments. The other {n(data['n_nofulltext_from_context'])} went to the context path at triage, but their abstracts or records do not rule out a randomized experiment, so they also wait for the full text. "
               if data.get("n_nofulltext_from_context") else
               f"These {n(sc.get('no_fulltext', 0))} papers were called experiments at triage, and neither the retrieval script nor the retrieval agents could obtain a full text through a legitimate route. ")
            + "The middle column repeats what the abstract or the short form says, and the author labels come from the search records. "
            + download_sentence() + " Files saved by hand into `Research/ai-lab/literature/creativity/_inbox/` are matched to papers by title (`tools/ingest_inbox.py`) and then enter the two-screener pipeline.\n\n" + gen["Experiments with full text not obtained"])
    if "Randomized experiments under 50 participants" in gen:
        add("Randomized experiments under 50 participants",
            f"These {n(sc.get('small', 0))} papers randomize people to generative-AI assistance, but fewer than 50 people were analyzed, so under the current rule they are listed and left out of the dataset whatever their outcome. "
            + (f"For {n(data.get('n_small_outcome_unclear', 0))} of them it is also unclear whether creativity or diversity is scored on the output. " if data.get('n_small_outcome_unclear') else "")
            + "Review 1 decides whether the rule holds.\n\n" + gen["Randomized experiments under 50 participants"])
    for h in ("Context: AI versus human output", "Context: observational", "Context: syntheses"):
        if h in gen:
            add(h, gen[h])
    for h in ("Excluded after screening", "Excluded at triage"):
        if h in gen:
            add(h, gen[h])
    if "Reclassification of the current collection" in gen:
        add("Reclassification of the current collection",
            f"The {n(data.get('n_library', 0))} papers of the May 2026 collection went through the same forms as every other candidate. The table gives each paper's label in the May JSON, its status under the new rules, the design found in the full text, and the basis of the decision.\n\n" + gen["Reclassification of the current collection"])

    div_fixed = fixed["The diversity measure: how it could be displayed"]
    div_fixed = re.sub(r"^\[filled from the generated table.*?\]\n*", "", div_fixed, flags=re.S).strip("\n")
    div_table = gen.get("The diversity measure: what each experiment reports", "")
    div_intro = (f"A diversity or similarity outcome is reported by {n(data.get('papers_with_diversity', 0))} recommended or unsettled papers, {n(data.get('n_diversity_outcomes', 0))} outcomes in all. The table gives, for each, the measure, what it was computed over, how its uncertainty was obtained, the unit of analysis, the statistics available, and the reported values with their location.")
    add("The diversity measure", div_intro + "\n\n" + div_table + "\n\n" + div_fixed)
    if "Outcomes measured after AI was removed" in gen:
        add("Outcomes measured after AI was removed",
            f"Creative work after AI was taken away is measured by {n(data.get('papers_with_after_ai', 0))} recommended or unsettled papers, {n(data.get('n_after_ai_outcomes', 0))} outcomes in all. These answer the `after_ai` question, the direct parallel of the learning section's default view.\n\n" + gen["Outcomes measured after AI was removed"])
    add("Search record", gen["Search record"])

    add("Implications for extraction", fixed["Implications for extraction"])

    io.open(out_path, "w", encoding="utf-8", newline="\n").write("\n".join(out).rstrip("\n") + "\n")
    print("wrote", out_path, "|", len(out), "lines |", sum(len(x) for x in out), "chars")
    missing = [h for h in gen_order if h not in {"Results at a glance", "Recommended for the core dataset", "Candidates that need clarification", "Experiments with full text not obtained", "Randomized experiments under 50 participants", "Context: AI versus human output", "Context: observational", "Context: syntheses", "Excluded after screening", "Excluded at triage", "Reclassification of the current collection", "The diversity measure: what each experiment reports", "Outcomes measured after AI was removed", "Search record"}]
    if missing:
        print("generated sections not placed:", missing)


if __name__ == "__main__":
    main()
