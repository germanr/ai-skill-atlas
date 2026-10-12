"""Independent analyst B reanalysis of c194.

Run: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c194/B.py
Only B.json is written. Deposit programs are never executed or imported.
The paper markdown, including all appendices, was read in contiguous chunks
covering characters 0:119358. Numerical sources were checked with PyMuPDF:
Table 1 on PDF p. 14, Table 2 on p. 16, and Table 5 on p. 23.
The separately deposited appendix has identical extracted page text to the
bound appendix (PDF pp. 30-54).
"""

import sys
sys.dont_write_bytecode = True

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf
import statsmodels.api as sm


ROOT = Path('C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening')
SCRIPT = ROOT / 'analysis/c194/B.py'
OUTPUT = ROOT / 'analysis/c194/B.json'
EXTRACTION = ROOT / 'extraction/c194.json'
RETRIEVAL = ROOT / 'retrieval.json'
CODEBOOK = ROOT.parent / 'creativity-codebook.md'
SPEC = ROOT / 'extraction-spec.md'
DEPOSITS = Path('D:/projects/ai-skill-atlas/creativity-data')
MANIFEST = DEPOSITS / 'manifest.json'
FIGSHARE = DEPOSITS / 'figshare-32132980'
MENDELEY = DEPOSITS / 'mendeley-t93pf5r6fp-v2'
ORIGINAL = FIGSHARE / 'Final Dataset Human AI creativity, ACMPS 2026.dta'
SEPTEMBER = MENDELEY / 'Final Dataset Human AI creativity, ACMPS 2026 - Sept 2026.dta'
ORIGINAL_CODE = FIGSHARE / 'Analysis Human AI creativity, ACMPS 2026.do'
SEPTEMBER_CODE = MENDELEY / 'Analysis Human AI creativity, ACMPS 2026 - Sept 2026.do'
README = FIGSHARE / 'README.txt'
APPENDIX = FIGSHARE / 'Online appendix - Human AI creativity, ACMPS 2026.pdf'

ARM_CODES = {
    'T': 'T_NoAI', 'PR': 'PR_NoAI', 'L': 'LOT_NoAI',
    'T&AI': 'T_AI', 'PR&AI': 'PR_AI', 'L&AI': 'LOT_AI',
}
OUTCOMES = {
    'creativity': 'participant_rating_mean',
    'characters': 'n_characters',
    'dat': 'dat_score',
}
COMPUTED_KEYS = [
    'n_treatment', 'n_control', 'treatment_mean', 'treatment_sd',
    'control_mean', 'control_sd', 'difference', 'difference_se',
    'se_type', 'n_clusters',
]


def manifest_records(obj):
    if isinstance(obj, dict):
        if 'path' in obj and 'sha256' in obj:
            yield obj
        for value in obj.values():
            yield from manifest_records(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from manifest_records(value)


def normalized_path(path):
    return str(path).replace('\\', '/').casefold()


def check(statistic, printed, computed, decimals=3):
    """Tables print all relevant non-count statistics to three decimals."""
    if decimals is None:
        computed = int(computed)
        matched = computed == printed
    else:
        computed = float(computed)
        matched = math.isfinite(computed) and (
            format(computed, f'.{decimals}f') == format(printed, f'.{decimals}f')
        )
    return {
        'statistic': statistic, 'printed': printed,
        'computed': computed, 'match': bool(matched),
    }


def arm_codes(display_name):
    names = display_name.removesuffix(' (combined)').split(' and ')
    return [ARM_CODES[name] for name in names]


def load_inputs():
    extraction = json.loads(EXTRACTION.read_text(encoding='utf-8'))
    retrieval = json.loads(RETRIEVAL.read_text(encoding='utf-8'))['c194']
    paper_pdf = Path(retrieval['pdf_path'])
    paper_md = Path(retrieval['md_path'])
    # Read documentation as text, without executing any deposit code.
    for path in [CODEBOOK, SPEC, paper_md, README, ORIGINAL_CODE, SEPTEMBER_CODE]:
        text = path.read_text(encoding='utf-8-sig')
        assert text, f'Empty documentation file: {path}'
    with pymupdf.open(paper_pdf) as main, pymupdf.open(APPENDIX) as appendix:
        assert len(main) == 54 and len(appendix) == 25
        for i in range(len(appendix)):
            assert main[i + 29].get_text() == appendix[i].get_text()
        # Source pages have been read and checked; do not use figure estimates.
        for i in [6, 7, 8, 13, 15, 22, 29, 30, 31]:
            assert main[i].get_text().strip()

    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    expected = {
        normalized_path(record['path']): record['sha256']
        for record in manifest_records(manifest)
    }
    for path in [ORIGINAL, SEPTEMBER, ORIGINAL_CODE, SEPTEMBER_CODE, README, APPENDIX]:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected[normalized_path(path)], f'Hash mismatch: {path}'

    original = pd.read_stata(ORIGINAL, convert_categoricals=False)
    september = pd.read_stata(SEPTEMBER, convert_categoricals=False)
    for frame in [original, september]:
        assert frame['id_code'].notna().all()
        assert frame['id_code'].ne('').all()
        assert frame['id_code'].is_unique
        assert frame['id_prog'].is_unique
    original = original.set_index('id_code').sort_index()
    september = september.set_index('id_code').sort_index()
    # All 57 shared variables, including texts and session assignments, agree.
    pd.testing.assert_frame_equal(
        original, september.loc[:, original.columns], check_exact=True
    )
    assert set(original['treatment']) == set(ARM_CODES.values())
    assert original.groupby('session')['treatment'].nunique().eq(1).all()

    ratings = september[[f'grade_{i}' for i in range(1, 5)]].astype(np.float64)
    assert ratings.notna().all().all()
    rating_means = ratings.mean(axis=1)
    np.testing.assert_array_equal(rating_means, original['grade_mean'])

    participants = original[['treatment', 'session', 'n_characters', 'dat_score']].copy()
    participants['participant_rating_mean'] = rating_means
    for outcome in OUTCOMES.values():
        participants[outcome] = participants[outcome].astype(np.float64)
        assert np.isfinite(participants[outcome]).all()
    assert participants['session'].notna().all()
    # Preserve the actual published measure: it is a UTF-8 byte count.
    byte_counts = original['writing'].map(lambda value: len(value.encode('utf-8')))
    np.testing.assert_array_equal(byte_counts, participants['n_characters'])
    assert int((original['writing'].str.len() == byte_counts).sum()) == 12

    data_files = [
        ORIGINAL, SEPTEMBER, ORIGINAL_CODE, SEPTEMBER_CODE, README, APPENDIX,
        MANIFEST, EXTRACTION, RETRIEVAL, CODEBOOK, SPEC, paper_md, paper_pdf,
    ]
    return extraction, participants, data_files


def reproduce(estimate, subset, outcome, treatment_codes):
    treatment = subset['treatment'].isin(treatment_codes)
    treated = subset.loc[treatment, outcome]
    control = subset.loc[~treatment, outcome]
    checks = [
        check('n_treatment', estimate['n_treatment'], len(treated), None),
        check('n_control', estimate['n_control'], len(control), None),
    ]
    if estimate['n_total'] is not None:
        checks.append(check('n_total', estimate['n_total'], len(subset), None))
    stats = estimate['stats']
    summaries = {
        'treatment_mean': treated.mean(), 'treatment_sd': treated.std(ddof=1),
        'control_mean': control.mean(), 'control_sd': control.std(ddof=1),
    }
    for name, value in summaries.items():
        if stats[name] is not None:
            checks.append(check(name, stats[name], value))

    if stats['regression'] is not None:
        # Reproduce the authors' Table 5 specification and Stata robust HC1 SE.
        x = pd.DataFrame({
            'const': 1.0,
            'AI': treatment.astype(float),
            'tournament': subset['treatment'].isin(['T_AI', 'T_NoAI']).astype(float),
            'piece_rate': subset['treatment'].isin(['PR_AI', 'PR_NoAI']).astype(float),
        }, index=subset.index)
        fitted = sm.OLS(subset[outcome], x).fit(cov_type='HC1', use_t=True)
        checks.extend([
            check('regression.coef', stats['regression']['coef'], fitted.params['AI']),
            check('regression.se', stats['regression']['se'], fitted.bse['AI']),
        ])
        assert int(fitted.nobs) == len(subset)
        if stats['p_value'] is not None:
            assert stats['p_value'] == '<0.01'
            p_value = float(fitted.pvalues['AI'])
            checks.append({
                'statistic': 'p_value', 'printed': stats['p_value'],
                'computed': p_value, 'match': bool(p_value < 0.01),
            })
    return checks


def compute_contrast(subset, outcome, treatment_codes):
    treatment = subset['treatment'].isin(treatment_codes)
    treated = subset.loc[treatment, outcome]
    control = subset.loc[~treatment, outcome]
    x = pd.DataFrame({'const': 1.0, 'AI': treatment.astype(float)}, index=subset.index)
    # Arm-homogeneous sessions are treated as the allocation clusters. The
    # allocation protocol itself is not described; every result records this.
    fitted = sm.OLS(subset[outcome], x).fit(
        cov_type='cluster',
        cov_kwds={
            'groups': subset['session'].to_numpy(),
            'use_correction': True,
            'df_correction': True,
        },
        use_t=True,
    )
    clusters = int(subset['session'].nunique())
    difference = float(treated.mean() - control.mean())
    standard_error = float(fitted.bse['AI'])
    np.testing.assert_allclose(fitted.params['AI'], difference, rtol=1e-11, atol=1e-11)

    # Independent check specialized to arm-homogeneous clusters: square each
    # session's sum of participant residuals and divide by its arm's n squared.
    # This also confirms that participants, rather than sessions, get equal weight.
    squared_sums = []
    for mask, values in [(treatment, treated), (~treatment, control)]:
        residuals = values - values.mean()
        session_sums = residuals.groupby(subset.loc[mask, 'session']).sum()
        squared_sums.append(float(np.square(session_sums).sum()) / len(values) ** 2)
    n = len(subset)
    correction = clusters / (clusters - 1) * (n - 1) / (n - 2)
    direct_se = math.sqrt(correction * sum(squared_sums))
    np.testing.assert_allclose(standard_error, direct_se, rtol=1e-11, atol=1e-11)

    return {
        'n_treatment': int(len(treated)), 'n_control': int(len(control)),
        'treatment_mean': float(treated.mean()),
        'treatment_sd': float(treated.std(ddof=1)),
        'control_mean': float(control.mean()),
        'control_sd': float(control.std(ddof=1)),
        'difference': difference, 'difference_se': standard_error,
        'se_type': 'cluster', 'n_clusters': clusters,
    }


def make_notes(estimate, subset, outcome_name, treatment_codes):
    treatment = subset['treatment'].isin(treatment_codes)
    g_t = int(subset.loc[treatment, 'session'].nunique())
    g_c = int(subset.loc[~treatment, 'session'].nunique())
    outcome_note = {
        'creativity': (
            'Each participant has one composition. Average the four complete raw '
            'ratings grade_1 through grade_4 within id_code in the September data; '
            'the average equals Figshare grade_mean exactly for all 360 people. '
            'No rating is counted as a separate participant.'
        ),
        'characters': (
            'Use posted n_characters, the variable summarized and regressed by '
            'the authors. It equals len(writing.encode("utf-8")) for all 360 '
            'people; ordinary Unicode len(writing) agrees for only 12. Thus the '
            'paper labels a UTF-8 byte count as number of characters. Retain '
            'this published unit without rescoring or normalizing the texts.'
        ),
        'dat': (
            'Use the posted participant-level dat_score, collected in the '
            'post-experiment questionnaire after ChatGPT access ended. The '
            'underlying word lists and scoring model are not supplied in these '
            'datasets, so the underlying DAT scoring is not rerun. This is a '
            'participant-level flexibility score, not diversity across people.'
        ),
    }[outcome_name]
    if estimate['stats']['regression'] is not None:
        reproduction_note = (
            'Reproduced the AI coefficient and HC1 robust SE from Table 5 '
            '(PDF p. 23, printed p. 20): outcome on an intercept, AI, tournament, '
            'and piece_rate, with lottery omitted. Counts are checked against '
            'Table 5 and Table 2 (PDF p. 16). Computed difference instead uses '
            'the requested unadjusted treatment-minus-control arm means; it '
            'therefore need not equal the reproduced incentive-adjusted coefficient.'
        )
    else:
        reproduction_note = (
            'Reproduced both arm means, both participant SDs, and both people '
            'counts from Table 1 (PDF p. 14, printed p. 11).'
        )
    return ' '.join([
        'The Figshare dataset corresponds to the extracted paper; all 57 shared '
        'columns agree exactly with the September Mendeley dataset after '
        'matching id_code. There are 360 unique id_code and id_prog values, '
        'one row per participant, and complete data for all three outcomes. '
        'No posted records or AI nonusers are excluded. Numbers originally '
        'randomized and any exclusions before deposition remain unknown.',
        'Treatment codes: ' + ', '.join(arm_codes(estimate['treatment_arm'])) +
        '; control codes: ' + ', '.join(arm_codes(estimate['control_arm'])) + '.',
        outcome_note,
        reproduction_note,
        'Counts are compared exactly; means, SDs, coefficients, and printed '
        'SEs are compared at the printed three-decimal precision. Analysis '
        'uses float64 arithmetic and SD denominator n - 1.',
        'The session variable identifies 21 observed sessions, each containing '
        'only one of the six arms: four sessions per AI arm and three per '
        'no-AI arm. The paper mentions sessions conducted under the tournament '
        'condition (PDF p. 8) and common instructions read aloud (PDF p. 30), '
        'but does not explicitly document whether randomization assigned '
        'sessions or individuals. For uncertainty, sessions are treated as '
        'allocation clusters based on this evidence; this is an analysis '
        'assumption, not confirmation of the allocation protocol. Observed '
        'session sizes are 8 to 24, despite the paper saying up to 20.',
        f'This contrast has {g_t} treatment and {g_c} control sessions; '
        'n_clusters counts the observed sessions in the contrast, not people. '
        'The SE is from participant-level OLS on an intercept and AI only, '
        'clustered by session, with the CR1 multiplier '
        'G/(G-1) * (N-1)/(N-2). It is independently checked using the squared '
        'session sums of arm-centered residuals divided by arm sample sizes '
        'squared. Means and SDs remain across participants, with equal '
        'participant weights. This clustered SE is distinct from the HC1 '
        'SE used solely to reproduce the paper.',
        'The design is between subjects with one writing task per person, '
        'so round=all and no first_round record applies. Combined-arm and '
        'same-incentive results share participants and are not independent samples.',
    ])


def main():
    extraction, participants, data_files = load_inputs()
    assert extraction['cid'] == 'c194'
    results = []
    skipped = []
    for estimate in extraction['estimates']:
        slug = estimate['slug']
        assert estimate['within_person'] is None
        outcome_name = slug.split('_')[1]
        if outcome_name not in OUTCOMES:
            skipped.append({'slug': slug, 'reason': 'No confirmed outcome mapping.'})
            continue
        outcome = OUTCOMES[outcome_name]
        treatment_codes = arm_codes(estimate['treatment_arm'])
        control_codes = arm_codes(estimate['control_arm'])
        subset = participants.loc[
            participants['treatment'].isin(treatment_codes + control_codes)
        ].copy()
        checks = reproduce(estimate, subset, outcome, treatment_codes)
        notes = make_notes(estimate, subset, outcome_name, treatment_codes)
        failed = [item for item in checks if not item['match']]
        if failed:
            details = '; '.join(
                f"{item['statistic']}: printed {item['printed']}, computed {item['computed']}"
                for item in failed
            )
            reason = 'Printed statistics not reproduced; no new contrast computed. ' + details
            skipped.append({'slug': slug, 'reason': reason})
            computed = {key: None for key in COMPUTED_KEYS}
            notes += ' ' + reason
        else:
            # No new contrast is computed until every reproduction check passes.
            computed = compute_contrast(subset, outcome, treatment_codes)
        results.append({
            'slug': slug, 'round': 'all', 'reproduced': checks,
            'computed': computed, 'notes': notes,
        })
    obj = {
        'cid': 'c194', 'analyst': 'B', 'script': SCRIPT.as_posix(),
        'data_files': [path.as_posix() for path in data_files],
        'results': results, 'skipped': skipped,
    }
    with OUTPUT.open('w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
        fh.write('\n')
    # Confirm that the written UTF-8 JSON parses and exactly preserves the object.
    with OUTPUT.open(encoding='utf-8') as fh:
        parsed = json.load(fh)
    assert parsed == obj
    print(json.dumps({
        'cid': 'c194', 'n_results': len(results),
        'n_reproduced': sum(all(item['match'] for item in r['reproduced']) for r in results),
        'n_skipped': len(skipped),
    }))


if __name__ == '__main__':
    main()
