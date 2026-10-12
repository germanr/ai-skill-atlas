# Final mechanical audit, 2026-10-10

`python tools/mech_audit.py` reruns the current mechanical check (`tools/extract_checks.py`) on every extraction file, with the supplement PDFs, and compares the result with the file's last stored check. One file per paper (`<cid>.json`) and `summary.json`. `quote-diagnosis.json` searches each unmatched quote over the whole main PDF and the supplements with all symbols removed.

Run on 51 extraction files (48 finished chains, 3 whose verifier hit the Codex usage limit). No verified paper has a flag that its last stored check did not have.

The audit led to three matcher changes: a minus sign set off by a space ("d = 0.79 and − 0.62"), decimal commas ("4,2"), and a fallback that compares letters, digits, decimal points, and minus signs only (symbols, spacing, line-break hyphens, and ligatures the text layer drops). A changed digit or a dropped minus sign still fails.

Flags left on verified papers, each checked by hand:

| Paper | Flags | What they are | Check |
|---|---|---|---|
| c006 | 40 | Quotes from the AsPredicted preregistration, supplement p. 77; the page's text layer is unreadable | Page rendered; all three sentences are printed word for word |
| c116 | 26 | Cells of the table in Figure 8, PDF p. 9; the text layer is broken | Page rendered; MANUAL 62 (36, 10), DIRECT 72 (35, 12), STRUCTURED 88 (33, 10), FREE-FORM 58 (34, 9) are printed |
| c043 | 4 | Statistics on PDF pp. 5 and 6 typeset as math; the text layer maps "=" to "¼" and "." to ":" | Pages rendered; all four quotes are printed |
| c010 | 2 | Single cells of Supplementary Table 3 (SDs 0.60 and 0.89), supplement p. 40 | Page rendered; both cells are printed. The same table prints t(297) = 2.54 where the main text prints 12.54; the record keeps the main text's value, as its notes say |
| c060 | 1 | "0.06 SDs below the mean" recorded as −0.06 | The sign comes from "below"; no computation |
| c112 | 1 | "two bubble charts" recorded as n_units 2 | A number written as a word |

The two drafts with flags (c117, c126) have an empty se_basis on records the second verifier also flagged; they wait for the residual review.

# Final mechanical audit, 2026-10-11

Rerun on all 84 extraction files after the last chains finished (`codex-jobs/mech-audit-final-1011.log`; `summary.json` and the per-paper files now hold this run). Every chain has finished and every paper is verified. No paper has a flag that its last stored check did not have; no errors. Twelve papers keep flags, all false. The six above are unchanged; the six below were checked on rendered pages on 2026-10-11 (images were made in the session scratchpad and not kept).

| Paper | Flags | What they are | Check |
|---|---|---|---|
| c450 | 10 | One quote, "AI-parallel assistance, where both drafts were developed collaboratively with AI", repeated across records; the PDF prints a "Page 6/20" footer in the middle of the sentence | The sentence is in the text with the footer between "developed" and "collaboratively" (PDF pp. 6-7, Section 2.4) |
| c389 | 8 | Cells of Table 5, PDF p. 28 (Final columns) | Page rendered; Qwen3 -0.005, Style-Embedding -0.033, compression ratio -0.083 and -0.100, self bleu -0.001 and 0.001, rougel -0.003 and 0.002 are printed |
| c793 | 4 | Cells of Table S4, PDF p. 48; the text layer glues cell markers to the numbers ("7B-0.0409") | Page rendered; -0.0409 (0.103), -0.0417 (0.110), -0.0992 (0.096), -0.2314** (0.100) are printed |
| c696 | 3 | Cells of Tables 1 and 2, PDF pp. 5-6, which are images | Pages rendered; Table 2 rows (Human-AI 150 2.94 0.37 3.21 0.22 2.99 [2.95, 3.04]; Human-Search 150 2.85 0.38 2.98 0.31 3.19 [3.15, 3.24]) and Table 1's Condition correlation .39*** are printed. Table 2's adjusted column gives the two arms the opposite values from the prose; the extraction records this as an open item and follows the prose |
| c539 | 2 | "Welch p" labels inside the Figure 6 image, PDF p. 10 | Page rendered; "Welch p = 0.0215" and "Welch p = 0.00249" are printed above the two comparisons |
| c906 | 2 | Table 15 cells, PDF p. 32: the HAI vs. Human column prints "-" in the Length and Root clauses rows | Page rendered; both cells print "-"; the records carry no statistics |
