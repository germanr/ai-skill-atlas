"""Second fix round for extraction papers whose second verifier left problems open.

For each paper whose status shows reverify problems that no review resolution closes: a fixer reads those problems
(checks/<cid>.reverify.json) and corrects or defends each against the source; a third verifier rechecks the estimates it
touched (checks/<cid>.reverify2.json). Whatever is still open after that goes to the main session for a written resolution.

Usage: python tools/codex_round2.py [--workers 6] [--only c031 ...]
"""
import argparse
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import codex_extract as E
import codex_pipeline as P

R = P.R
EXT = E.EXT


def fix2_prompt(cid):
    return "\n".join([
        f"You are the second-round fixer for one paper. {E.INTRO}",
        "", P.HOW_TO_WORK, "",
        E.inputs_block(cid), "",
        f"The extraction file is {R}/extraction/{cid}.json. A first fixer already worked on it (keys \"fixes\" and \"kept\"), and a second "
        f"verifier still reported the problems in {R}/extraction/checks/{cid}.reverify.json. For each, check the paper (and any supplement "
        "named in the file's sources). Correct the file where the problem is real; keep the value where the verifier is wrong, with the "
        "passage that shows it. Where the extraction file's rules leave the case open, say so plainly instead of forcing a code.",
        "",
        f"Rewrite {R}/extraction/{cid}.json in place, keeping everything else, with two more keys: \"fixes2\" (slug, field, old, new, locator, "
        "quote, basis) and \"kept2\" (slug, field, value, locator, quote, why_the_flag_is_wrong).",
        "",
        P.SUMMARY_NOTE + '"cid", "n_fixes", "n_kept", and "open_cases".',
    ])


def chain(cid):
    ext = P.load(EXT / f"{cid}.json") or {}
    if "fixes2" not in ext:
        P.run_until(f"fix2-{cid}", fix2_prompt(cid), EXT / f"{cid}.json")
        ext = P.load(EXT / f"{cid}.json") or {}
    if "fixes2" not in ext:
        P.log_line(f"STOP   {cid}: no second fix round")
        return
    changed = sorted({f.get("slug") for f in (ext.get("fixes2") or []) + (ext.get("kept2") or []) if f.get("slug")})
    problems = E.mech(cid, "mech3")
    rv = EXT / "checks" / f"{cid}.reverify2.json"
    if changed and P.load(rv) is None:
        P.run_until(f"reverify2-{cid}", E.verify_prompt(cid, problems, only=changed).replace(f"{cid}.reverify.json", f"{cid}.reverify2.json"), rv)
    if changed and P.load(rv) is None:
        P.log_line(f"STOP   {cid}: no third-verifier output")
        return
    status = P.load(EXT / "status" / f"{cid}.json") or {"cid": cid}
    status["round2"] = {"fixes": len(ext.get("fixes2") or []), "kept": len(ext.get("kept2") or []), "mech3_problems": len(problems),
                        "reverify2_problems": len((P.load(rv) or {}).get("problems") or []) if changed else 0,
                        "finished_at": datetime.now().isoformat(timespec="seconds")}
    E.save(EXT / "status" / f"{cid}.json", status)
    P.log_line(f"FINAL  {cid} round 2: {status['round2']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    cids = a.only
    if not cids:
        cids = []
        for st in sorted((EXT / "status").glob("c*.json")):
            s = P.load(st) or {}
            ext = P.load(EXT / f"{st.stem}.json") or {}
            resolved = {(r.get("slug"), r.get("field")) for r in ext.get("review_resolutions") or [] if r.get("check") == "reverify"}
            probs = (P.load(EXT / "checks" / f"{st.stem}.reverify.json") or {}).get("problems") or []
            if s.get("reverify_problems") and "round2" not in s and any((p.get("slug"), p.get("field")) not in resolved for p in probs):
                cids.append(st.stem)
    P.SLOTS = threading.Semaphore(a.workers)
    P.log_line(f"round 2: {len(cids)} papers: {' '.join(cids)}")
    with ThreadPoolExecutor(max(1, a.workers)) as pool:
        list(pool.map(chain, cids))


if __name__ == "__main__":
    main()
