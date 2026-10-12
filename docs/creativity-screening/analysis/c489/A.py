"""Independent analyst A reanalysis for c489.

Run with: python -I -B A.py
Only A.json is written. No downloaded executable content is opened or run.

Source review: complete main markdown (69,821 characters) and supplementary
markdown (60,667 characters), including all appendices, were read in chunks.
Main PDF pp. 3-8 and supplement PDF pp. 2, 5-7 were checked with PyMuPDF.
Rules: creativity-codebook.md sections 7-11, extraction-spec.md, and the brief.

The paper randomizes writers between conditions. Recipient pairing is used
only to reproduce the paper's F tests; recipients are not AI-assigned writers.
Unreproduced estimates retain diagnostic checks and have null computed fields.
Skipped estimates have no validated outcome/procedure. These two lists partition
the extraction's slugs. No treatment effect is calculated until every relevant
reproduction check for that estimate passes.
"""

import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
import pandas as pd
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein
from scipy import stats
import statsmodels.api as sm


ROOT = Path(r'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening')
DEPOSIT = Path(r'D:/projects/ai-skill-atlas/creativity-data/osf-jx2es')
MANIFEST = Path(r'D:/projects/ai-skill-atlas/creativity-data/manifest.json')
SCRIPT = ROOT / 'analysis/c489/A.py'
OUTPUT = ROOT / 'analysis/c489/A.json'
EXTRACTION = ROOT / 'extraction/c489.json'
FILES = {
    'S1': DEPOSIT / 'Experiment 1/data.csv',
    'S2': DEPOSIT / 'Experiment 2/data.csv',
    'S3': DEPOSIT / 'Experiment 3/data.csv',
    'S4': DEPOSIT / 'Experiment 4/S4_data.csv',
    'S5': DEPOSIT / 'SI Appendix/SI_study1/SA1_data.csv',
    'S6': DEPOSIT / 'SI Appendix/SI_study2/SA2_data.csv',
    'S7': DEPOSIT / 'SI Appendix/SI_study3/SA3_data.csv',
}
COMPUTED_KEYS = (
    'n_treatment', 'n_control', 'treatment_mean', 'treatment_sd',
    'control_mean', 'control_sd', 'difference', 'difference_se',
    'se_type', 'n_clusters',
)


def null_computed():
    return dict.fromkeys(COMPUTED_KEYS)


def check(statistic, printed, computed, decimals=None):
    """Compare at the source's printed precision, not an arbitrary tolerance."""
    if isinstance(computed, np.generic):
        computed = computed.item()
    if isinstance(printed, str) and printed.startswith('<'):
        match = computed is not None and computed < float(printed[1:])
    elif computed is None:
        match = False
    elif decimals is None:
        match = computed == printed
    else:
        match = f'{computed:.{decimals}f}' == f'{printed:.{decimals}f}'
    return {'statistic': statistic, 'printed': printed,
            'computed': computed, 'match': bool(match)}


def passed(checks):
    return bool(checks) and all(c['match'] for c in checks)


def hc2(treatment, control):
    """One outcome per randomized writer; OLS intercept plus treatment, HC2."""
    t = np.asarray(treatment, dtype=float)
    c = np.asarray(control, dtype=float)
    assert t.ndim == c.ndim == 1 and min(len(t), len(c)) > 1
    assert np.isfinite(t).all() and np.isfinite(c).all()
    y = np.concatenate([c, t])
    arm = np.concatenate([np.zeros(len(c)), np.ones(len(t))])
    fit = sm.OLS(y, sm.add_constant(arm)).fit(cov_type='HC2')
    tm, cm = float(t.mean()), float(c.mean())
    ts, cs = float(t.std(ddof=1)), float(c.std(ddof=1))
    difference = tm - cm
    se = float(fit.bse[1])
    assert math.isclose(float(fit.params[1]), difference, abs_tol=1e-11)
    # In this saturated two-arm model HC2 equals the unpooled means SE.
    assert math.isclose(se, math.sqrt(ts**2 / len(t) + cs**2 / len(c)),
                        rel_tol=1e-11, abs_tol=1e-12)
    return {
        'n_treatment': int(len(t)), 'n_control': int(len(c)),
        'treatment_mean': tm, 'treatment_sd': ts,
        'control_mean': cm, 'control_sd': cs,
        'difference': difference, 'difference_se': se,
        'se_type': 'HC2', 'n_clusters': None,
    }


def arm_codes(e):
    if e['study_id'] == 'S3':
        return 'AI', 'Google'
    if e['study_id'] == 'S5':
        codes = {'LLM': 'gpt', 'LLM + real-time web links': 'link',
                 'Web search': 'google'}
        return codes[e['treatment_arm']], codes[e['control_arm']]
    return 'gpt', 'google'


def wordlike_count(text):
    return sum(bool(re.search(r'\w', token)) for token in text.split())


def text_key(text):
    # Match formatting variants only: preserve words, case and punctuation,
    # remove whitespace and a leading spreadsheet-protection apostrophe.
    return ''.join(text.split()).lstrip("'")


def raw_edit_diagnostics(frame):
    """Attempt raw-string pairwise Levenshtein replication, with both denominators.

    No stored distance column is treated as an independent participant outcome.
    No effect or uncertainty is derived from these unsuccessful diagnostics.
    """
    out = {}
    for arm, group in frame.groupby('condition', sort=True):
        texts = group['advice'].tolist()
        dist = process.cdist(texts, texts, scorer=Levenshtein.distance,
                             dtype=np.uint32, workers=1)
        n = len(texts)
        total = float(dist.sum(dtype=np.uint64))
        out[arm] = {'n': n, 'with_self': total / (n * n),
                    'without_self': total / (n * (n - 1))}
        print(f'Raw edit-distance diagnostic: {arm}, n={n}', flush=True)
    return out


def writer_link_audit(writers, ratings):
    audit = {}
    assert not writers['advice'].map(text_key).duplicated().any()
    for writer_arm, rating_arm, text_col in [
            ('AI', 'gpt', '1.advice'), ('Google', 'google', '0.advice')]:
        source = set(writers.loc[writers['condition'] == writer_arm,
                                 'advice'].map(text_key))
        keys = ratings[text_col].map(text_key)
        matched = keys.isin(source)
        audit[rating_arm] = {
            'distinct_texts': int(keys.nunique()),
            'matched_writers': int(keys[matched].nunique()),
            'matched_ratings': int(matched.sum()),
            'unmatched_ratings': int((~matched).sum()),
            'unmatched_texts': int(keys[~matched].nunique()),
        }
    assert ratings['0.key'].eq('google').all()
    assert ratings['1.key'].eq('gpt').all()
    return audit


def analyze():
    extraction = json.loads(EXTRACTION.read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    records = manifest['deposits']['osf-jx2es']['files']
    frames = {}
    for sid, path in FILES.items():
        rel = path.relative_to(DEPOSIT).as_posix()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == records[rel]['sha256']
        frames[sid] = pd.read_csv(path, encoding='utf-8-sig')
    # S7 was inspected for inventory/provenance only. The extraction contains no
    # eligible S7 estimate, so its recipient data supply no additional contrasts.
    studies = {s['study_id']: s for s in extraction['studies']}
    assert all(s['assignment_unit'] == 'individual' for s in studies.values())
    s5 = frames['S5']
    assert (s5['advice'].map(wordlike_count) == s5['wordcount']).all()
    ratings = frames['S4']
    audit = writer_link_audit(frames['S3'], ratings)
    edit_cache = {}
    results, skipped = [], []

    for e in extraction['estimates']:
        slug, sid = e['slug'], e['study_id']
        d = frames[sid]
        t_code, c_code = arm_codes(e)
        printed = e['stats']

        if e['construct'] == 'diversity':
            if 'cosine' in slug:
                reason = (
                    'Set-level diversity outcome. The paper uses separately fitted LDA '
                    'topic models and PCA, not a named neural embedding model '
                    '(main PDF p. 4). The deposit contains advice and precomputed '
                    'cosine_similarity values, but no fitted models, topic vectors, '
                    'vocabulary, preprocessing code, topic/PCA dimensions or random '
                    'seeds. Exact reproduction from the same texts and model cannot '
                    'be established. Averaging the posted column is not an independent '
                    'recomputation of the set measure, and no participant SD/HC2 SE '
                    'is calculated from it.'
                )
            else:
                if sid not in edit_cache:
                    print(f'Checking raw edit distances for {sid}', flush=True)
                    edit_cache[sid] = raw_edit_diagnostics(d)
                td, cd = edit_cache[sid][t_code], edit_cache[sid][c_code]
                reason = (
                    'Set-level pairwise Levenshtein outcome (main PDF p. 4). '
                    'The exact text preprocessing and aggregation implementation are '
                    'not supplied. A direct Levenshtein calculation on the deposited '
                    'raw advice does not reproduce the printed means. Treatment/control '
                    f'printed: {printed["treatment_mean"]}/{printed["control_mean"]}; '
                    'raw all-pairs means including self-pairs: '
                    f'{td["with_self"]:.9f}/{cd["with_self"]:.9f}; '
                    'excluding self-pairs: '
                    f'{td["without_self"]:.9f}/{cd["without_self"]:.9f}. '
                    f'Deposited writer rows: {td["n"]}/{cd["n"]}. '
                    'The precomputed edit_distance column is not a replacement for '
                    'an exactly reproduced text-processing procedure. No participant '
                    'SD, mean difference or standard error is calculated.'
                )
            if sid == 'S6':
                reason += (
                    ' In addition, SA2_data.csv contains 1,999 rows versus the '
                    'reported final sample of 1,976 (supplement p. 6); the reported '
                    'exclusions cannot be reconstructed from the available columns.'
                )
            skipped.append({'slug': slug, 'reason': reason})
            continue

        if ('word_count' in slug or '_words_' in slug) and sid != 'S5':
            # There are no deposited LIWC scores in these CSVs. These are explicitly
            # diagnostic alternative counts, never used to estimate a treatment effect.
            ttext = d.loc[d['condition'] == t_code, 'advice']
            ctext = d.loc[d['condition'] == c_code, 'advice']
            simple_t = float(ttext.str.split().str.len().mean())
            simple_c = float(ctext.str.split().str.len().mean())
            word_t = float(ttext.map(wordlike_count).mean())
            word_c = float(ctext.map(wordlike_count).mean())
            reason = (
                'The paper specifies LIWC 2022 word counts (main PDF p. 4), but '
                'this CSV contains advice text and no word-count/LIWC output column. '
                f'Printed treatment/control means: {printed["treatment_mean"]}/'
                f'{printed["control_mean"]}; whitespace-token diagnostics: '
                f'{simple_t:.9f}/{simple_c:.9f}; whitespace tokens containing a '
                f'word character: {word_t:.9f}/{word_c:.9f}. Neither diagnostic '
                'reproduces both means at printed precision. The latter rule matches '
                'every posted S5 wordcount value but does not reproduce this study. '
                'No substitute tokenizer or treatment contrast is used. '
                f'Deposited treatment/control rows: {len(ttext)}/{len(ctext)}.'
            )
            if sid == 'S6':
                reason += (
                    ' The 1,999 deposited rows also disagree with the reported '
                    'final sample of 1,976; exclusion flags are absent.'
                )
            skipped.append({'slug': slug, 'reason': reason})
            continue

        if sid == 'S3' and e['unit'] in ('rating', 'pair'):
            checks = [check('n_recipient_participants', 1493, len(ratings))]
            if e['unit'] == 'rating':
                field = {
                    's3_helpfulness_ai_overview_vs_google_standard': 'helpful',
                    's3_informativeness_ai_overview_vs_google_standard': 'informative',
                    's3_trustworthiness_ai_overview_vs_google_standard': 'trust',
                    's3_apparent_effort_ai_overview_vs_google_standard': 'effort',
                }[slug]
                tr = ratings['gpt_' + field]
                cr = ratings['google_' + field]
                assert tr.notna().all() and cr.notna().all()
                test = stats.ttest_rel(tr, cr)
                checks += [
                    check('treatment_mean_recipient_ratings', printed['treatment_mean'],
                          float(tr.mean()), 3),
                    check('control_mean_recipient_ratings', printed['control_mean'],
                          float(cr.mean()), 3),
                    check('F_repeated_measures_recipient', printed['test']['value'],
                          float(test.statistic**2), 3),
                    check('F_df_numerator', printed['test']['df'][0], 1),
                    check('F_df_denominator', printed['test']['df'][1], len(ratings)-1),
                    check('p_value', printed['p_value'], float(test.pvalue)),
                ]
                notes = (
                    'Main PDF p. 8: all 1,493 recipient means and repeated-measures '
                    'F tests reproduce. However, the writer sample cannot be '
                    'reproduced for the full set of ratings. '
                )
            else:
                counts = ratings['choice'].value_counts()
                check_compare = ratings['compare'].map({
                    'The advice from my 1st friend was more helpful': 'google',
                    'I found both of their advice similarly helpful': 'similar',
                    'The advice from my 2nd friend was more helpful': 'gpt',
                })
                assert check_compare.equals(ratings['choice'])
                chi = stats.chisquare([counts['gpt'], counts['google'], counts['similar']])
                checks += [
                    check('treatment_choice_percent', printed['treatment_mean'],
                          100 * int(counts['gpt']) / len(ratings), 1),
                    check('control_choice_percent', printed['control_mean'],
                          100 * int(counts['google']) / len(ratings), 1),
                    check('treatment_choice_count', 756, int(counts['gpt'])),
                    check('control_choice_count', 367, int(counts['google'])),
                    check('chi_square', printed['test']['value'], float(chi.statistic), 3),
                    check('chi_square_df', printed['test']['df'], 2),
                    check('p_value', printed['p_value'], float(chi.pvalue)),
                ]
                notes = (
                    'Main PDF p. 8 prints the condition labels in the opposite '
                    'direction from the deposited choice variable: gpt is chosen '
                    '367 times (24.6%), google 756 times (50.6%), and similar '
                    '370 times. The compare strings agree with choice and the '
                    '0.key=google / 1.key=gpt mapping. The overall chi-square '
                    'reproduces, but the arm percentages and counts as extracted '
                    'do not. The extraction is not silently relabeled. '
                )
            checks += [
                check('treatment_distinct_advice_pool_texts', 125,
                      audit['gpt']['distinct_texts']),
                check('control_distinct_advice_pool_texts', 125,
                      audit['google']['distinct_texts']),
            ]
            notes += (
                'The method specifies a source pool of 125 texts per arm. '
                f'The ratings contain {audit["gpt"]["distinct_texts"]} AI and '
                f'{audit["google"]["distinct_texts"]} Google texts. Formatting-only '
                'matching (whitespace and leading spreadsheet apostrophe) uniquely '
                'links all 250 deposited S3 writers, but one additional AI text '
                f'({audit["gpt"]["unmatched_ratings"]} ratings) and two additional '
                f'Google texts ({audit["google"]["unmatched_ratings"]} ratings) '
                'have no matching S3 writer. There are no writer IDs or exclusion '
                'flags resolving these extra texts. They are not assumed to be '
                'additional randomized people; discarding them would change the '
                'published rating sample. Therefore all computed fields are null. '
                'The advice-pool checks count texts, not people. Recipient paired '
                'SEs would not be writer-level SEs. No first_round result is '
                'appropriate because writers were assigned between people.'
            )
            assert not passed(checks)
            results.append({'slug': slug, 'round': 'all', 'reproduced': checks,
                            'computed': null_computed(), 'notes': notes})
            continue

        # Participant-level columns: one advice output per row/writer.
        if sid == 'S5':
            column = 'wordcount' if '_words_' in slug else 'n_unique_entities'
            digits = 2
        else:
            column = 'num_unique_entities'
            digits = 3 if sid in ('S1', 'S3') else 2
        t = d.loc[d['condition'] == t_code, column]
        c = d.loc[d['condition'] == c_code, column]
        assert t.notna().all() and c.notna().all()
        checks = [
            check('treatment_mean', printed['treatment_mean'], float(t.mean()), digits),
            check('control_mean', printed['control_mean'], float(c.mean()), digits),
        ]
        if sid == 'S5':
            checks.append(check('n_study_analyzed_all_three_arms',
                                studies[sid]['n_analyzed'], len(d)))
            if e['n_treatment'] is not None:
                checks.append(check('n_treatment', e['n_treatment'], len(t)))
            if e['n_control'] is not None:
                checks.append(check('n_control', e['n_control'], len(c)))
            ftest = stats.f_oneway(*(g[column].to_numpy()
                                    for _, g in d.groupby('condition')))
            f_print, p_print = ((0.43, 0.648) if column == 'wordcount'
                                else (15.44, '<.001'))
            checks += [
                check('F_omnibus_all_three_arms', f_print, float(ftest.statistic), 2),
                check('F_omnibus_df_numerator', 2, d['condition'].nunique()-1),
                check('F_omnibus_df_denominator', 2399, len(d)-d['condition'].nunique()),
                check('p_omnibus_all_three_arms', p_print, float(ftest.pvalue), 3),
            ]
            notes = (
                'Supplement PDF pp. 2 and 5. SA1_data.csv has the reported 2,402 '
                'analyzed writers: 803 gpt, 812 link and 787 google. All rows are '
                'used; no further exclusion is applied. The paper reports no '
                'two-arm total for this contrast, so the reproduced 2,402 is '
                'explicitly the full three-arm study count. The printed omnibus '
                'F/p values validate the outcome, not a pairwise test. '
            )
        else:
            checks.append(check('n_study_analyzed', studies[sid]['n_analyzed'], len(d)))
            ftest = stats.f_oneway(t, c)
            checks += [
                check('F', printed['test']['value'], float(ftest.statistic), 2),
                check('F_df_numerator', printed['test']['df'][0], 1),
                check('F_df_denominator', printed['test']['df'][1], len(t)+len(c)-2),
                check('p_value', printed['p_value'], float(ftest.pvalue), 3),
            ]
            if sid == 'S6':
                notes = (
                    'Supplement PDF pp. 6-7. SA2_data.csv contains 1,999 rows '
                    '(975 gpt, 1,024 google), whereas the paper states a final '
                    'sample of 1,976 and prints F denominators of 1,971. The '
                    'treatment mean is 2.915897, which rounds to 2.92 rather '
                    'than the printed 2.91. Although F and p round to the printed '
                    'values, the means/counts do not jointly reproduce. The '
                    'available CSV has no attention-check, unrelated-advice, '
                    'technical-error or analysis-inclusion flags identifying the '
                    'additional exclusions. No outcome-driven exclusions are '
                    'inferred and no participant contrast is computed.'
                )
            else:
                pages = {'S1': '3 and 5', 'S2': '6', 'S3': '7'}[sid]
                notes = (
                    f'Main PDF pp. {pages}. The deposited data have exactly the '
                    'reported analyzed study count, with one advice output per '
                    f'writer: {len(t)} treatment and {len(c)} control rows. '
                    'All deposited rows are used; no further exclusion is applied. '
                )
        if passed(checks):
            computed = hc2(t, c)
            notes += (
                f'Outcome column: {column}. Means/SDs use the participant-level '
                'posted outcome, with SD denominator n-1. Named-entity scores '
                'are the deposited scores, not newly generated NLP scores. '
                'The difference is treatment minus control in original outcome '
                'units. SE is from participant-level OLS with intercept and arm '
                'indicator, covariance HC2, independently checked against '
                'sqrt(s_treatment^2/n_treatment + s_control^2/n_control). '
                'Assignment is individual and between people; round=all and '
                'n_clusters=null. The paper reports conventional F tests, '
                'which are reproduced separately from the requested robust SE.'
            )
        else:
            computed = null_computed()
        results.append({'slug': slug, 'round': 'all', 'reproduced': checks,
                        'computed': computed, 'notes': notes})

    expected = {e['slug'] for e in extraction['estimates']}
    result_slugs = {r['slug'] for r in results}
    skip_slugs = {s['slug'] for s in skipped}
    assert not result_slugs.intersection(skip_slugs)
    assert result_slugs.union(skip_slugs) == expected
    assert len(results) == len(result_slugs) and len(skipped) == len(skip_slugs)
    for r in results:
        assert set(r['computed']) == set(COMPUTED_KEYS)
        if not passed(r['reproduced']):
            assert all(v is None for v in r['computed'].values())
    obj = {'cid': 'c489', 'analyst': 'A', 'script': SCRIPT.as_posix(),
           'data_files': [p.as_posix() for p in FILES.values()],
           'results': results, 'skipped': skipped}
    with OUTPUT.open('w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding='utf-8') as fh:
        parsed = json.load(fh)
    assert parsed == obj
    summary = {'cid': 'c489', 'n_results': len(results),
               'n_reproduced': sum(passed(r['reproduced']) for r in results),
               'n_skipped': len(skipped)}
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    analyze()
