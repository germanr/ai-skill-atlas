"""Independent reproduction of c010, analyst A.

Run: python -I -B <absolute path to this file>
Only A.json is written. --audit prints the reproduction checks without writing.
Deposited Rmd files were read as text only; none is imported or executed.
"""

import hashlib
import io
import json
import math
import ctypes
import os
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm


BASE = Path('C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening')
DEPOSIT = Path('D:/projects/ai-skill-atlas/creativity-data/osf-rzn87')
SCRIPT = BASE / 'analysis/c010/A.py'
OUTPUT = BASE / 'analysis/c010/A.json'
MANIFEST = Path('D:/projects/ai-skill-atlas/creativity-data/manifest.json')
EXPERIMENTS = dict(zip(['S1', 'S2', 'S3', 'S4', 'S5', 'S6'],
                       ['Exp1', 'Exp2A', 'Exp2B', 'Exp3', 'Exp4', 'Exp5']))
EXCLUDE = {
    'Exp1': '''A2XUJD9Z7ZDLB5 A1OPV8D0GG5Z32 AQ9DVGD3J7MD4 A1TEVUU2U1VYYV
AWKP0M7G5BBCC A1KIL2V6SMJBGX AYMR8UTKYJ2D4 A29N5E8YC6DB9Q
A3PZASM0C12I57 A1U52239IPV7IO A1AB1BMULT9JLE A3TH6B3RUD1MUQ
A15DXD3Z1AHK6C A3BP24ZY0OA5TR A3SQV2L85UE5BK A2LEBJWW395FST
A3HAERGD8FL7WX A8FAQQHLVROLG A3AHD1NV5XCOF A1J9VZ372FV2QZ
A2GZNOA5CIVKUB A30UQ017N4PML5 A1RP17F7OXV0IW A106QH27FETZ88
A2C4R0TBPZGWTD A212P9LUF0URRZ A1RQUOVV8PCXBM'''.split(),
    'Exp2A': '''5a9ab4944eecca0001dd806a 59949236c825cf0001d7dcdc
63d7e54a90879dee84dffb32 62b0cd459238d178b6300581
5f80bc44efa2c013099af460 63c4a90d09909e33d5e82f21'''.split(),
    'Exp2B': '''6572fd344d1080cd9c53a005 5c78b032419dcc0014119082
60ddc7abdf6661b9c294691f 6361b032a20001fc86b0ff1b
63e52f8ab3688f45f842114c 5de5496937e1d50ca63e0fa5
613aad30bcfed65155a026ec 5f47f39d57500a24ca3bbc89
6400e3697879c55c323f34d0 62b20c0065e9809e66d13fa5
5f084a7987a3fe028ff65b8a 610898813e48dc2864965122
627e71af3701230cdc757652 5da25f04c8c2de00139ed46b
643883e97bc73c8245bc31d3'''.split(),
    'Exp3': ['A3SQV2L85UE5BK'],
    'Exp4': '''61549a2caa92d84f392000e9 58dcfe010674970001e928e5
5c0fc9645096c60001f15b12 5ea07a44234e0304542e1c50
62b473736986d2b27c1427d2'''.split(),
    'Exp5': '''5a4d194c87c6f8000137d680 5cb4e2e8dde4050015779d17
643ff216b732bb345c8403e2 63da5521f23372b30f4f0b77
5c1d234d89f035000172aeb7 62e02b26e879244a99e852fa
602471c97db8951797cef086 5f0f6ef654ae12126762bd4e'''.split(),
}
DATA_FILES = []
CACHE = {}
AUDIT = {}
HASHES = {}
R_MATH_DIRECTORY = Path('C:/Program Files/R/R-4.2.2/bin/x64')
R_MATH = None
R_ROUND = None
SECONDARY = Path('D:/projects/ai-skill-atlas/creativity-data/osf-nk6ev/'
                 'Codes_results_data-unpacked/Codes_results_data')
PRINTED_COMPLETE = {'Exp1': 260, 'Exp2A': 298, 'Exp2B': 216,
                    'Exp3': 208, 'Exp4': 405, 'Exp5': 394}
PRINTED_LAY_JUDGES = {'Exp1': 331, 'Exp2A': 232, 'Exp2B': 241,
                      'Exp3': 158, 'Exp4': 321, 'Exp5': 310}


def read_csv(relative):
    path = DEPOSIT / relative
    if relative not in CACHE:
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == HASHES[relative], relative
        # pandas' default NA vocabulary includes the valid Exp2A arm "None".
        CACHE[relative] = pd.read_csv(io.BytesIO(raw), keep_default_na=False,
                                     na_values=['', 'NA'], low_memory=False)
        DATA_FILES.append(path.as_posix())
    return CACHE[relative].copy()


def long_enough(series, minimum):
    return series.astype('string').str.len().ge(minimum).fillna(False)


def main_sample(exp):
    d = read_csv(f'{exp}/{exp}.main.qualtrics.csv')
    if exp not in ('Exp1', 'Exp3'):
        d['workerId'] = d['PROLIFIC_PID']
    d = d.loc[long_enough(d['workerId'], 13)].copy()
    if exp == 'Exp2A':
        d = d.loc[long_enough(d['mturk'], 13)].copy()
    d = d.loc[pd.to_numeric(d['Finished'], errors='coerce').eq(1)].copy()
    required = ['gender_f'] if exp == 'Exp2B' else ['age', 'gender_f']
    d = d.dropna(subset=required)
    if exp == 'Exp1':
        d = d.dropna(subset=['idea', 'idea_count'])
        d = d.loc[long_enough(d['idea'], 1)].copy()
    complete = len(d)
    if exp in ('Exp2A', 'Exp2B', 'Exp3', 'Exp5'):
        d = d.loc[pd.to_numeric(d['attention_check_2'], errors='coerce').eq(2)].copy()
    after_attention = len(d)
    d = d.loc[~d['workerId'].isin(EXCLUDE[exp])].copy()
    AUDIT[exp] = {'complete': complete, 'attention_excluded': complete - after_attention,
                  'listed_excluded': after_attention - len(d), 'n_human': len(d)}
    assert d['workerId'].is_unique and d['ResponseId'].is_unique, exp
    if exp == 'Exp1':
        hand = read_csv('Exp1/Exp1.main.qualtrics.handcoded.csv')
        d = d.merge(hand[['ResponseId', 'idea_count_jc']], on='ResponseId',
                    how='left', validate='one_to_one')
    if exp == 'Exp2B':
        co = read_csv('Exp2B/Exp2B.main.ChatbotOnly.csv')
        co['ResponseId'] = ['R_AAAAAAAAAA' + str(i) for i in range(1, len(co) + 1)]
        co['workerId'] = ['wwwwwwwww' + str(i) for i in range(1, len(co) + 1)]
        d = pd.concat([d, co], ignore_index=True)
    keep = ['workerId', 'ResponseId', 'Condition']
    keep += [c for c in ['NumCon', 'Empathy', 'idea_count_jc'] if c in d]
    return d[keep].copy()


def links(exp, expert=False):
    if exp == 'Exp5':
        items = []
        for suffix, prefix in [('Baseline', 'B'), ('EmpathyHigh', 'H')]:
            d = read_csv(f'{exp}/{exp}.rating.link_{suffix}.csv')
            d['idea_key'] = prefix + d.iloc[:, 0].astype(int).astype(str)
            items.append(d)
        return pd.concat(items, ignore_index=True)
    d = read_csv(f'{exp}/{exp}.rating.link.csv')
    # Exp1 lay uses idea_text_id; expert code uses the exported row index.
    source = 'idea_text_id' if exp == 'Exp1' and not expert else d.columns[0]
    d['idea_key'] = d[source].astype(int).astype(str)
    assert d['idea_key'].is_unique
    return d


def strict_group_mean(d, keys, values):
    # Mirrors R mean(...), which propagates missing values by default.
    return d.groupby(keys, as_index=False, sort=False)[values].agg(
        lambda x: x.mean(skipna=False))


def lay_scores(exp):
    r = read_csv(f'{exp}/{exp}.rating.qualtrics.csv')
    idcol = 'workerId' if exp in ('Exp1', 'Exp3') else 'PROLIFIC_PID'
    r = r.loc[long_enough(r[idcol], 12)].copy()
    if exp == 'Exp2B':
        r = r.dropna(subset=['age'])
    else:
        confirmation = 'prolific' if exp in ('Exp2A', 'Exp5') else 'mturk'
        r = r.loc[long_enough(r[confirmation], 12)
                  & pd.to_numeric(r['Finished'], errors='coerce').eq(1)].copy()
        r = r.dropna(subset=['gender_f'])
    assert r['ResponseId'].is_unique, exp
    AUDIT[exp]['n_lay_judges'] = len(r)
    cols = [c for c in r.columns if re.match(r'^\d+_', c)]
    z = r.melt(id_vars='ResponseId', value_vars=cols,
               var_name='variable', value_name='score').dropna(subset=['score'])
    z['score'] = pd.to_numeric(z['score'], errors='raise')
    assert z['score'].between(1, 7).all()
    parts = z['variable'].str.split('_', expand=True)
    if exp == 'Exp5':
        z['idea_key'] = parts[2] + parts[0]
        z['dimension'] = parts[1] + '_' + parts[3]
    else:
        z['idea_key'] = parts[0]
        z['dimension'] = parts[1] + parts[2].fillna('').map(lambda x: '_' + x if x else '')
    if exp == 'Exp1':
        z = z.drop_duplicates(['ResponseId', 'idea_key', 'dimension', 'score'])
    assert not z.duplicated(['ResponseId', 'idea_key', 'dimension']).any()
    wide = z.pivot(index=['ResponseId', 'idea_key'], columns='dimension', values='score')
    dims = list(wide.columns)
    idea = strict_group_mean(wide.reset_index(), ['idea_key'], dims)
    idea['originality'] = idea[[f'creative_{i}' for i in (1, 2, 3)]].mean(axis=1, skipna=False)
    idea['appropriateness'] = idea[[f'practical_{i}' for i in (1, 2, 3)]].mean(axis=1, skipna=False)
    idea['creativity'] = (idea['originality'] + idea['appropriateness']) / 2
    outcomes = ['originality', 'appropriateness', 'creativity']
    if exp == 'Exp3':
        clarity = [f'clarity_{i}' for i in (1, 2, 3)]
        idea['clarity'] = idea[clarity].mean(axis=1, skipna=False)
        idea['articulateness'] = idea[clarity + ['complexity', 'thought']].mean(axis=1, skipna=False)
        idea['thoughtfulness'] = idea['thought']
        outcomes += ['clarity', 'articulateness', 'complexity', 'thoughtfulness']
    linked = links(exp).merge(idea[['idea_key'] + outcomes], on='idea_key',
                              how='left', validate='one_to_one')
    return strict_group_mean(linked, ['workerId', 'ResponseId'], outcomes)


def expert_scores(exp):
    if exp == 'Exp5':
        frames = []
        for suffix, prefix in [('Baseline', 'B'), ('High', 'H')]:
            d = read_csv(f'Robustness_Experts/{exp}.rating.experts_{suffix}.csv')
            d['idea_key'] = prefix + d['idea_id'].astype(int).astype(str)
            frames.append(d)
        r = pd.concat(frames, ignore_index=True)
    else:
        r = read_csv(f'Robustness_Experts/{exp}.rating.experts.csv')
        r['idea_key'] = r['idea_id'].astype(int).astype(str)
    assert r['idea_key'].is_unique
    mapping = {'originality': 'Novelty_', 'appropriateness': 'Practicality_',
               'verbosity': 'Verbosity_', 'articulateness': 'Articulate_',
               'not_new': 'notnew_', 'incrementally_new': 'incnew_',
               'radically_new': 'radnew_'}
    outcomes = []
    for out, prefix in mapping.items():
        cols = [c for c in r if c.startswith(prefix)]
        if cols:
            assert len(cols) == 3 and r[cols].notna().all().all()
            r[out] = r[cols].mean(axis=1, skipna=False)
            if out in ('not_new', 'incrementally_new', 'radically_new'):
                assert r[cols].isin([0, 1]).all().all()
                r[out] *= 100  # Percent, the units printed by the paper.
            outcomes.append(out)
    r['creativity'] = (r['originality'] + r['appropriateness']) / 2
    outcomes.append('creativity')
    linked = links(exp, expert=True).merge(r[['idea_key'] + outcomes], on='idea_key',
                                          how='left', validate='one_to_one')
    return strict_group_mean(linked, ['workerId', 'ResponseId'], outcomes)


def datasets():
    out = {}
    for exp in EXPERIMENTS.values():
        d = main_sample(exp)
        for judge, scores in [('lay', lay_scores(exp)), ('expert', expert_scores(exp))]:
            joined = d.merge(scores, on=['workerId', 'ResponseId'], how='left',
                             validate='one_to_one')
            required = ['originality', 'appropriateness', 'creativity']
            if exp == 'Exp3' and judge == 'lay':
                required += ['articulateness']
            joined = joined.dropna(subset=required)
            assert joined['workerId'].is_unique and joined['ResponseId'].is_unique
            assert joined['Condition'].notna().all(), (exp, judge)
            AUDIT[exp][judge + '_n'] = len(joined)
            AUDIT[exp][judge + '_counts'] = joined.groupby('Condition').size().to_dict()
            out[(exp, judge)] = joined
    s1 = out[('Exp1', 'lay')]
    cutoff = float(s1['creativity'].quantile(0.8, interpolation='linear'))
    s1['top_ranked_creativity_share'] = (s1['creativity'] > cutoff).astype(float) * 100
    s1['fluency'] = pd.to_numeric(s1['idea_count_jc'], errors='raise')
    AUDIT['Exp1']['top20_threshold'] = cutoff
    return out


def secondary_crosscheck(all_data):
    """Compare individual values, not just summaries, to the second deposit."""
    for exp, filename in [('Exp1', 'My_Exp1_cleaned.xlsx'),
                          ('Exp3', 'My_Exp3.analysis.dataset.xlsx')]:
        path = SECONDARY / filename
        old = pd.read_excel(path)
        DATA_FILES.append(path.as_posix())
        new = all_data[(exp, 'lay')]
        assert set(old['ResponseId']) == set(new['ResponseId']), filename
        paired = new.merge(old, on='ResponseId', validate='one_to_one')
        mapping = [('creativity', 'OVERALL'), ('originality', 'ORIGINALITY'),
                   ('appropriateness', 'APPROPRIATENESS')]
        if exp == 'Exp3':
            mapping += [('articulateness', 'DELIVERY'), ('complexity', 'Complexity'),
                        ('thoughtfulness', 'Thought')]
        for ours, theirs in mapping:
            assert np.allclose(paired[ours], paired[theirs], rtol=0, atol=1e-12), (filename, ours)
        if exp == 'Exp1':
            assert np.array_equal(paired['idea_count_jc_x'], paired['idea_count_jc_y'])
        AUDIT[exp]['secondary_individual_scores_match'] = True


def select_contrast(e, all_data):
    exp = EXPERIMENTS[e['study_id']]
    judge = 'expert' if '_expert_' in e['slug'] else 'lay'
    outcome = e['slug'].split('_', 1)[1].split('_chatgpt_', 1)[0]
    for suffix in ('_expert', '_lay'):
        if outcome.endswith(suffix):
            outcome = outcome[:-len(suffix)]
    full = all_data[(exp, judge)]
    d = full
    if e['slug'].endswith('_high_constraints'):
        d = d.loc[d['NumCon'].eq('High')]
    elif e['slug'].endswith('_low_constraints'):
        d = d.loc[d['NumCon'].eq('Low')]
    elif e['slug'].endswith('_high_empathy'):
        d = d.loc[d['Empathy'].eq('High')]
    elif e['slug'].endswith('_baseline_empathy'):
        d = d.loc[d['Empathy'].eq('Baseline')]
    treated = 'ChatbotHuman' if exp == 'Exp2B' else 'Chatbot'
    if exp == 'Exp1':
        control = 'Control'
    elif '_vs_human' in e['slug']:
        control = 'HumanOnly' if exp == 'Exp2B' else 'None'
    else:
        control = 'Google'
    t = d.loc[d['Condition'].eq(treated), outcome].dropna()
    c = d.loc[d['Condition'].eq(control), outcome].dropna()
    return exp, judge, outcome, full, d, treated, control, t, c


def check(statistic, printed, computed, digits=2):
    value = float(computed)
    tolerance = 0.5 * 10 ** (-digits)
    match = abs(value - float(printed)) < tolerance
    return {'statistic': statistic, 'printed': printed, 'computed': value,
            'match': bool(match)}


def summary_display(value):
    """Reconstruct the three-decimal summary followed by explicit R round(., 2).

    The posted code calls rstatix::get_summary_stats(type='mean_sd'), then
    mutate(mean=round(mean,2), sd=round(sd,2)). The three-then-two-decimal
    display reproduces all printed means and all but one SD; a direct
    single rounding does not. That distinction is explicitly disclosed in
    every result. The final participant statistics never use rounded data.

    Call only the trusted, installed R math rounding routine through Python.
    No R interpreter is started, no deposited program is run, and no
    temporary R files/directories are created.
    """
    return float(R_ROUND(R_ROUND(float(value), 3.0), 2.0))


def hc2(t, c):
    y = np.r_[t.to_numpy(dtype=float), c.to_numpy(dtype=float)]
    arm = np.r_[np.ones(len(t)), np.zeros(len(c))]
    fit = sm.OLS(y, sm.add_constant(arm)).fit(cov_type='HC2')
    direct_se = math.sqrt(t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c))
    assert np.isclose(fit.bse[1], direct_se, rtol=1e-11)
    assert np.isclose(fit.params[1], t.mean() - c.mean(), atol=1e-12)
    return {'n_treatment': len(t), 'n_control': len(c),
            'treatment_mean': float(t.mean()), 'treatment_sd': float(t.std(ddof=1)),
            'control_mean': float(c.mean()), 'control_sd': float(c.std(ddof=1)),
            'difference': float(t.mean() - c.mean()), 'difference_se': float(fit.bse[1]),
            'se_type': 'HC2', 'n_clusters': None}


def printed_factorial_test(exp, full):
    """R treatment coding plus car::Anova(type=3), recreated in Python.

    Chatbot and the alphabetically first task level are reference levels.
    With the interaction included, the technology coefficient is a simple
    contrast at High constraints (Exp4) or Baseline empathy (Exp5).
    """
    factor = 'NumCon' if exp == 'Exp4' else 'Empathy'
    second_level = 'Low' if exp == 'Exp4' else 'High'
    technology = full['Condition'].eq('Google').to_numpy(dtype=float)
    task = full[factor].eq(second_level).to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(full)), technology, task, technology * task])
    fit = sm.OLS(full['creativity'].to_numpy(dtype=float), design).fit()
    f_value = float(fit.tvalues[1] ** 2)
    return f_value, float(fit.df_resid), float(stats.f.sf(f_value, 1, fit.df_resid))


def run(audit_only=False):
    global R_MATH, R_ROUND
    extraction = json.loads((BASE / 'extraction/c010.json').read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    HASHES.update({name: rec['sha256'] for name, rec in
                   manifest['deposits']['osf-rzn87']['files'].items() if 'sha256' in rec})
    with os.add_dll_directory(str(R_MATH_DIRECTORY)):
        R_MATH = ctypes.CDLL(str(R_MATH_DIRECTORY / 'R.dll'))
    R_ROUND = R_MATH.Rf_fround
    R_ROUND.argtypes = [ctypes.c_double, ctypes.c_double]
    R_ROUND.restype = ctypes.c_double
    all_data = datasets()
    secondary_crosscheck(all_data)
    studies = {s['study_id']: s for s in extraction['studies']}
    results, skipped = [], []
    for e in extraction['estimates']:
        exp, judge, outcome, full, d, treatment, control, t, c = select_contrast(e, all_data)
        reproduced = []
        people = full.loc[~full['Condition'].eq('ChatbotOnly')]
        reproduced.append(check('study_n_analyzed', studies[e['study_id']]['n_analyzed'],
                                people['workerId'].nunique(), digits=0))
        reproduced.append(check('study_complete_human_responses', PRINTED_COMPLETE[exp],
                                AUDIT[exp]['complete'], digits=0))
        if judge == 'lay':
            reproduced.append(check('n_lay_judges', PRINTED_LAY_JUDGES[exp],
                                    AUDIT[exp]['n_lay_judges'], digits=0))
        if e['n_total'] is not None:
            reproduced.append(check('contrast_n_total', e['n_total'], len(t) + len(c), digits=0))
        if e['n_units'] is not None:
            reproduced.append(check('paper_model_n_outputs', e['n_units'], len(full), digits=0))
        is_anova = e['slug'].endswith('_anova_main_effect')
        if outcome == 'fluency':
            test = stats.ttest_ind(t, c, equal_var=True)
            reproduced.append(check('absolute_t', e['stats']['test']['value'], abs(test.statistic)))
            reproduced.append(check('test_df', e['stats']['test']['df'], len(t) + len(c) - 2, digits=0))
            reproduced.append(check('p_value', e['stats']['p_value'], test.pvalue, digits=3))
            pooled = math.sqrt(((len(t)-1)*t.var(ddof=1)+(len(c)-1)*c.var(ddof=1))/(len(t)+len(c)-2))
            reproduced.append(check('absolute_paper_d', e['stats']['paper_effect']['value'],
                                    abs(t.mean()-c.mean()) / pooled))
            reproduced.append(check('grand_mean_ideas_main_Methods', 1.69,
                                    full['fluency'].mean()))
        elif is_anova:
            f_value, df_resid, p_value = printed_factorial_test(exp, full)
            reproduced.append(check('paper_type_III_F', e['stats']['test']['value'], f_value))
            reproduced.append(check('paper_F_df_numerator', e['stats']['test']['df'][0], 1, digits=0))
            reproduced.append(check('paper_F_df_denominator', e['stats']['test']['df'][1], df_resid, digits=0))
            reproduced.append(check('paper_F_p_value', e['stats']['p_value'], p_value,
                                    digits=3 if exp == 'Exp4' else 13))
            reproduced.append(check('paper_partial_eta_squared', e['stats']['paper_effect']['value'],
                                    f_value / (f_value + df_resid)))
            # The same named pooled arms have printed means in Supplementary
            # Table 1. Check those as well, rather than approving a record on
            # sample counts alone when its own means are null.
            sibling_slug = e['slug'].replace('_anova_main_effect', '_pooled')
            sibling = next(s for s in extraction['estimates'] if s['slug'] == sibling_slug)
            for label, value in [('treatment_mean', t.mean()), ('control_mean', c.mean()),
                                 ('treatment_sd', t.std(ddof=1)), ('control_sd', c.std(ddof=1))]:
                reproduced.append(check('same_arms_supplement_' + label, sibling['stats'][label],
                                        summary_display(value)))
        else:
            digits = 1 if outcome in ('top_ranked_creativity_share', 'not_new',
                                       'incrementally_new', 'radically_new') else 2
            for label, value in [('treatment_mean', t.mean()), ('control_mean', c.mean()),
                                 ('treatment_sd', t.std(ddof=1)), ('control_sd', c.std(ddof=1))]:
                if e['stats'][label] is not None:
                    display = summary_display(value) if digits == 2 else value
                    reproduced.append(check(label, e['stats'][label], display, digits=digits))
        fail = [r for r in reproduced if not r['match']]
        if audit_only:
            print(e['slug'], 'PASS' if not fail else 'FAIL',
                  'n=', (len(t), len(c)),
                  'mean_sd=', [round(float(v), 6) for v in (t.mean(), t.std(ddof=1), c.mean(), c.std(ddof=1))],
                  'failed=', json.dumps(fail))
        notes = (f'{exp}; {judge} ratings; exclusions transcribed from '
                 f'{(DEPOSIT / exp / (exp + ".analyze.Rmd")).as_posix()}, read as text only. '
                 'Each retained person is counted once. Printed arm means, printed SDs when available, '
                 'and printed participant totals are the reproduction checks. Per-arm counts are recovered '
                 'from distinct retained participant IDs; the paper does not print them. ')
        if outcome not in ('fluency', 'top_ranked_creativity_share', 'not_new',
                            'incrementally_new', 'radically_new'):
            notes += ('Reproduced mean/SD entries show the author-summary display: round the summary '
                      'to three decimals, then use R round(.,2), as in the posted summary-statistics '
                      'pipeline. This accounts for near-boundary discrepancies from direct rounding. '
                      'All final computed means, SDs and SEs use unrounded participant data. ')
        notes += (f"Filters retain {AUDIT[exp]['complete']} completed human responses before "
                  f"{AUDIT[exp]['attention_excluded']} attention failures and "
                  f"{AUDIT[exp]['listed_excluded']} explicitly listed exclusions. ")
        if judge == 'lay':
            notes += ('Average each of the six rating items across retained judges for each idea; '
                      'originality averages creative_1:3, appropriateness averages practical_1:3, '
                      'and creativity averages all six. Average idea scores within each participant. ')
        else:
            notes += ('Join expert idea_id to the link-file row index. Average the three expert '
                      'ratings and then ideas within each participant. Creativity averages Novelty '
                      'and Practicality; other outcomes use their respective expert columns. '
                      f'Method reference: {(DEPOSIT / "Robustness_Experts/experts_analyze.Rmd").as_posix()}, '
                      'read as text only. ')
        if exp in ('Exp1', 'Exp3') and judge == 'lay':
            notes += ('All reconstructed participant creativity, originality and appropriateness '
                      'values also agree with the osf-nk6ev spreadsheet within 1e-12. ')
        if exp == 'Exp2A':
            notes += ('Human-only is the literal Condition value "None", preserved rather than parsed '
                      'as missing. Study total 291 includes all three human arms; this result uses '
                      'only the named pair. ')
        if exp == 'Exp2B':
            notes += ('The paper model includes 100 unedited ChatbotOnly responses; these are '
                      'retained solely to reconstruct the published model population and never '
                      'counted as people or used in the final two-human-arm HC2 regression. ')
        if exp in ('Exp4', 'Exp5'):
            notes += ('For pooled contrasts, final arm means weight each person equally across both '
                      'task conditions; HC2 is from the requested two-arm regression. Published '
                      'factorial-model marginal contrasts and their conventional SEs are different '
                      'estimands/precision calculations and are not substituted for HC2. ')
        if is_anova:
            reference = 'High constraints' if exp == 'Exp4' else 'Baseline empathy'
            notes += ('This newly added extraction record prints only the ANOVA test. Its F, df, '
                      'p and partial eta squared are separately reproduced using OLS creativity ~ '
                      'Condition * task_factor with R treatment coding and the posted type-III test. '
                      f'The printed technology F actually tests the simple contrast at {reference}, '
                      'because the interaction is included and the factors use treatment coding; '
                      'it is not an equally weighted main effect. Arm mean/SD checks come from the '
                      'same named pooled arms in Supplementary Table 1. The final computed block '
                      'follows the requested pooled participant-level two-arm HC2 contrast and '
                      'therefore intentionally matches the sibling pooled record. ')
        if exp == 'Exp5':
            notes += ('The deposited link filename is Exp5.rating.link_EmpathyHigh.csv, corresponding '
                      'to link_High in the Rmd. Prefix high-empathy idea indices with H and baseline '
                      'indices with B to match rating columns and prevent cross-condition joins. ')
        if outcome in ('articulateness', 'clarity', 'complexity', 'thoughtfulness') and judge == 'lay':
            notes += ('Articulateness is the average of clarity_1:3, complexity and thought; clarity '
                      'averages clarity_1:3; complexity and thoughtfulness each use their single item. ')
        if outcome == 'top_ranked_creativity_share':
            notes += (f"Exp1.analyze.Rmd lines 226-228 define a participant indicator for creativity "
                      f"> the aggregate-sample type-7 80th percentile, {AUDIT['Exp1']['top20_threshold']:.15g}. "
                      f"It flags {int((t > 0).sum())}/{len(t)} treated and "
                      f"{int((c > 0).sum())}/{len(c)} controls. The posted code resolves the extraction's "
                      'uncertain output denominator: this is a participant-level binary outcome. '
                      'Scores are 0/100; difference and SE are percentage points. ')
        if outcome in ('not_new', 'incrementally_new', 'radically_new'):
            notes += ('Use 100 times the mean of the three binary expert ratings for each person; '
                      f'there are {3*len(t)} treatment and {3*len(c)} control judgments. '
                      'Arm means equal the printed rating percentages because all people have three '
                      'ratings. SD and HC2 SE count people, not judgments or judges. Difference and '
                      'SE are percentage points; the raw treatment-minus-control sign is preserved, '
                      'including the negative difference for not-new judgments. The paper reports '
                      'judge-random-intercept logistic z tests; those are not the HC2 model. ')
        if e['slug'] in ('s3_originality_expert_chatgpt_vs_human',
                          's3_articulateness_expert_chatgpt_vs_human'):
            notes += ('The extraction flags a likely missing leading digit in the supplementary '
                      't statistic. Reproduction here is established from the printed arm means, '
                      'SDs and sample counts, not by asserting that the printed t statistic is correct. ')
        if not fail:
            computed = hc2(t, c)
            notes += ('Difference is treatment minus control in the original outcome units. '
                      'SDs use n-1; SE is OLS on an intercept and treatment indicator with HC2. ')
        else:
            computed = {k: None for k in ['n_treatment', 'n_control', 'treatment_mean', 'treatment_sd',
                                         'control_mean', 'control_sd', 'difference', 'difference_se',
                                         'se_type', 'n_clusters']}
            reason = '; '.join(f"{r['statistic']}: printed {r['printed']}, recomputed {r['computed']:.12g}"
                               for r in fail)
            if outcome == 'fluency':
                reason += ('. The posted analysis uses idea_count_jc. Its absolute pooled-variance '
                           't is 1.44939239321 (1.45), not 1.42; df=231, p=0.149 and d=0.19 '
                           'otherwise reproduce. No printed arm means or difference are available '
                           'to independently establish this estimate under the reproduction rule.')
            elif e['slug'] == 's5_originality_expert_chatgpt_vs_web':
                reason += (f'. Raw treatment SD={t.std(ddof=1):.15g}; direct and author-pipeline '
                           'rounding both give 1.18, not 1.17 (Supplementary Table 3, PDF p. 41). '
                           'Means and counts match, but this printed SD discrepancy remains unresolved.')
            notes += 'Reproduction failed at printed precision. No participant contrast computed. ' + reason
            skipped.append({'slug': e['slug'], 'reason': reason})
        results.append({'slug': e['slug'], 'round': 'all', 'reproduced': reproduced,
                        'computed': computed, 'notes': notes})
    if audit_only:
        print('AUDIT', json.dumps(AUDIT, indent=1))
        return
    obj = {'cid': 'c010', 'analyst': 'A', 'script': SCRIPT.as_posix(),
           'data_files': DATA_FILES, 'results': results, 'skipped': skipped}
    with OUTPUT.open('w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
    with OUTPUT.open(encoding='utf-8') as fh:
        reread = json.load(fh)
    assert len(reread['results']) == len(extraction['estimates'])
    assert len({r['slug'] for r in reread['results']}) == len(extraction['estimates'])
    for result in reread['results']:
        passed = all(x['match'] for x in result['reproduced'])
        assert passed == (result['computed']['difference'] is not None)
        if passed:
            assert result['computed']['n_treatment'] > 1
            assert result['computed']['n_control'] > 1
    print(json.dumps({'cid': 'c010', 'n_results': len(results),
                      'n_reproduced': sum(r['computed']['difference'] is not None for r in results),
                      'n_skipped': len(skipped)}))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    run(audit_only='--audit' in sys.argv)
