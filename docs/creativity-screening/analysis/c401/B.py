"""Independent analyst B replication for c401.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c401/B.py
Only B.json is written. Author scripts are read as text, never executed or imported.
All estimates are gated on reproduction at the paper's printed precision.
"""
import sys
sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf
import statsmodels.api as sm

ROOT = Path('C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening')
DEPOSIT = Path('D:/projects/ai-skill-atlas/creativity-data/osf-kzuge')
PACKAGE = DEPOSIT / 'osf_package'
SCRIPT = ROOT / 'analysis/c401/B.py'
OUTPUT = ROOT / 'analysis/c401/B.json'
MANIFEST = Path('D:/projects/ai-skill-atlas/creativity-data/manifest.json')
READ_FILES = []


def remember(path):
    path = Path(path)
    assert path.is_absolute()
    name = path.as_posix()
    if name not in READ_FILES:
        READ_FILES.append(name)
    return path


def read_text(path):
    return remember(path).read_text(encoding='utf-8-sig')


def read_csv(relative, manifest):
    path = remember(PACKAGE / relative)
    entry = manifest['deposits']['osf-kzuge']['files']['osf_package/' + relative]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], relative
    return pd.read_csv(path)


def check(statistic, printed, computed, decimals=0):
    actual = int(computed) if decimals == 0 and float(computed).is_integer() else float(computed)
    return {
        'statistic': statistic,
        'printed': printed,
        'computed': actual,
        'match': bool(round(float(actual), decimals) == float(printed)),
    }


def participant_contrast(frame, outcome, treatment):
    # Randomization was between individuals; there was one final campaign each.
    # Explicitly average within person before taking arm means and sample SDs.
    sub = frame.loc[frame.randomization.isin([treatment, 'basegpt']),
                    ['participant_id', 'randomization', outcome]].dropna()
    assert sub.groupby('participant_id').randomization.nunique().eq(1).all()
    people = sub.groupby(['participant_id', 'randomization'], as_index=False)[outcome].mean()
    t = people.loc[people.randomization.eq(treatment), outcome]
    c = people.loc[people.randomization.eq('basegpt'), outcome]
    indicator = people.randomization.eq(treatment).astype(float)
    design = pd.DataFrame({'intercept': 1.0, 'treatment': indicator})
    fit = sm.OLS(people[outcome].astype(float), design).fit(cov_type='HC2')
    difference = float(t.mean() - c.mean())
    se = float(fit.bse['treatment'])
    # For an intercept plus a binary indicator, HC2 equals the sum of the
    # arm-specific sample-variance / sample-size terms (Welch variance).
    assert np.isclose(fit.params['treatment'], difference, rtol=1e-11, atol=1e-10)
    assert np.isclose(se ** 2, t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c),
                      rtol=1e-11, atol=1e-10)
    return {
        'n_treatment': int(len(t)),
        'n_control': int(len(c)),
        'treatment_mean': float(t.mean()),
        'treatment_sd': float(t.std(ddof=1)),
        'control_mean': float(c.mean()),
        'control_sd': float(c.std(ddof=1)),
        'difference': difference,
        'difference_se': se,
        'se_type': 'HC2',
        'n_clusters': None,
    }


def add_if_reproduced(results, skipped, slug, checks, frame, outcome, treatment, notes):
    failed = [x for x in checks if not x['match']]
    if failed:
        # Do not calculate the requested new statistics when reproduction fails.
        results.append({
            'slug': slug, 'round': 'all', 'reproduced': checks,
            'computed': {k: None for k in [
                'n_treatment', 'n_control', 'treatment_mean', 'treatment_sd',
                'control_mean', 'control_sd', 'difference', 'difference_se',
                'se_type', 'n_clusters']},
            'notes': notes + ' Reproduction failed; no participant contrast computed: ' +
                     json.dumps(failed, ensure_ascii=True),
        })
        return
    results.append({
        'slug': slug,
        'round': 'all',
        'reproduced': checks,
        'computed': participant_contrast(frame, outcome, treatment),
        'notes': notes,
    })


def main():
    extraction = json.loads(read_text(ROOT / 'extraction/c401.json'))
    retrieval = json.loads(read_text(ROOT / 'retrieval.json'))['c401']
    manifest = json.loads(read_text(MANIFEST))
    estimates = {x['slug']: x for x in extraction['estimates']}
    read_text(ROOT.parent / 'creativity-codebook.md')
    read_text(ROOT / 'extraction-spec.md')
    # Full markdown, including the appended supplementary materials, was read
    # in contiguous chunks during analysis. Also register it as a source here.
    manuscript = read_text(Path(retrieval['md_path']))
    assert len(manuscript) == 151997
    pdf = remember(Path(retrieval['pdf_path']))
    with pymupdf.open(pdf) as doc:
        assert len(doc) == 62
        source_pages = {n: doc[n - 1].get_text() for n in [10, 19, 23, 32, 50, 51, 52, 61]}
    assert '355.4' in source_pages[19] and '148.0' in source_pages[19]
    assert '158.2' in source_pages[32]
    assert '80.5%' in source_pages[51] and '64.5%' in source_pages[51]

    # Read the relevant author code solely as documentation of variables,
    # preprocessing, scoring, and the model behind the printed editing levels.
    preprocessing = read_text(PACKAGE / 'code/preprocessing/preprocessing.R')
    edit_source = read_text(PACKAGE / 'code/preprocessing/extract_campaign_edits.R')
    count_source = read_text(PACKAGE / 'code/figures/fig4_causal_mediation/compute_CI_measures.R')
    diversity_source = read_text(PACKAGE / 'code/figures/fig2_quality_creativity/creativity_analysis.R')
    assert 'duration_seconds >= 1800' in preprocessing
    assert 'glm(AI_overlap ~ randomization + msg_count - 1' in edit_source
    assert 'cohort1$campaign_wc = unlist(lapply(cohort1$marketing_answer, count_words))' in count_source
    assert 'text-embedding-3-large' in diversity_source

    paths = [
        'data/codebook.csv',
        'data/processed/creativity_df_CI.csv',
        'data/processed/campaign_text_overlap.csv',
        'data/evaluations/human/human_campaign_evaluations.csv',
        'data/processed/Batch_5322742_batch_results.csv',
        'data/supplementary/human_expertise_campaigns.csv',
        'data/supplementary/all_campaigns.csv',
        'data/supplementary/creativity_df_evaluated_scored.csv',
        'data/evaluations/elo_ratings/elo_ratings_gpt-4o-mini.csv',
        'data/evaluations/llm_scores/campaign_evaluations_gpt-4o-mini.csv',
        'data/evaluations/elo_ratings/elo_real_vs_simulated.csv',
        'data/evaluations/elo_runs/elo_eval_run_1_gpt-4o-mini.csv',
        'data/supplementary/simulated_campaigns.csv',
    ]
    data = {p: read_csv(p, manifest) for p in paths}
    cohort = data['data/processed/creativity_df_CI.csv'].copy()
    assert len(cohort) == cohort.participant_id.nunique() == 331
    counts = cohort.randomization.value_counts().to_dict()
    assert counts == {'basegpt': 116, 'creativegpt': 114, 'creativegpt_rand': 101}
    assert cohort.BFI_44_30.eq('Agree a Little').all()
    assert cohort.PANAS_9.eq('A Little').all()
    assert cohort.LLM_check.eq('No').all()
    assert cohort.duration_seconds.ge(1800).all()
    assert cohort.msg_count_interview.gt(0).all() and cohort.response_count.gt(0).all()
    assert cohort[['campaign_wc', 'msg_count']].notna().all().all()

    # The deposited human ratings are five MTurk Likert ratings per campaign,
    # not the manuscript's expert Prolific pairwise-Elo validation data.
    human_raw = data['data/processed/Batch_5322742_batch_results.csv']
    human_means = data['data/evaluations/human/human_campaign_evaluations.csv']
    domains = ['elaboration', 'feasibility', 'novelty', 'overall', 'value']
    assert human_raw.groupby('participant_id').size().eq(5).all()
    averaged = human_raw.groupby('participant_id')[[f'Answer.{x}' for x in domains]].mean()
    averaged.columns = domains
    assert np.allclose(averaged.sort_index(),
                       human_means.set_index('participant_id')[domains].sort_index())
    for p in ['data/supplementary/human_expertise_campaigns.csv', 'data/supplementary/all_campaigns.csv']:
        assert list(data[p].columns) == ['index', 'condition', 'campaign_id', 'batch_num', 'local_id', 'marketing_score']
    assert 'marketing_answer' not in cohort.columns
    assert not (PACKAGE / 'data/processed/campaign_themes.rds').exists()

    results, skipped = [], []
    # An unadjusted three-arm Gaussian OLS reproduces both printed betas and
    # conventional p-values. The requested precision is separately computed
    # with HC2 for each two-arm participant-level contrast.
    design = pd.DataFrame({
        'intercept': 1.0,
        'creativegpt': cohort.randomization.eq('creativegpt').astype(float),
        'creativegpt_rand': cohort.randomization.eq('creativegpt_rand').astype(float),
    })
    word_fit = sm.OLS(cohort.campaign_wc.astype(float), design).fit()
    word_notes = (
        'PDF p. 19 and Table S2 (PDF p. 52): analyzed sample after the stated exclusions, '
        '116 Generic AI (basegpt), 114 Personalized AI (creativegpt), and 101 Partially '
        'personalized AI (creativegpt_rand). All 331 deposited rows are unique people and '
        'pass the posted attention, other-AI, engagement, and >=30-minute exclusion rules. '
        'No further exclusions, trimming, or winsorization were applied. One final campaign '
        'per person; outcome is the deposited campaign_wc. Author code '
        'code/figures/fig4_causal_mediation/compute_CI_measures.R lines 35-39 and 266-268 '
        'defines alphabetic-word counting with internal hyphens/apostrophes; the underlying '
        'human campaign text is not deposited, so the stored count is used. '
        'The printed betas and p-values reproduce using campaign_wc ~ randomization '
        'on all three arms with ordinary OLS. The computed fields use an unadjusted '
        'two-arm OLS with participant-level HC2, SD denominator n-1. Units: words. '
        'Higher word count indicates length, not necessarily creativity. '
        'The two contrasts share the Generic AI control. This is a between-person '
        'experiment, so first_round is inapplicable.'
    )
    for suffix, treatment in [('personalized', 'creativegpt'),
                              ('partially_personalized', 'creativegpt_rand')]:
        slug = f's1_campaign_word_count_{suffix}_vs_generic'
        e = estimates[slug]
        checks = [
            check('n_treatment', e['n_treatment'], counts[treatment]),
            check('n_control', e['n_control'], counts['basegpt']),
            check('study_n_analyzed', 331, len(cohort)),
            check('regression.coef', e['stats']['regression']['coef'], word_fit.params[treatment], 1),
            check('p_value_conventional_OLS_three_arms', e['stats']['p_value'], word_fit.pvalues[treatment], 2),
            check('overall_word_count_mean_PDF_p19', 355.4, cohort.campaign_wc.mean(), 1),
            check('overall_word_count_sd_PDF_p19', 148.0, cohort.campaign_wc.std(ddof=1), 1),
            check('overall_word_count_min_PDF_p19', 128, cohort.campaign_wc.min()),
            check('overall_word_count_max_PDF_p19', 2217, cohort.campaign_wc.max()),
        ]
        add_if_reproduced(results, skipped, slug, checks, cohort, 'campaign_wc', treatment, word_notes)

    # row_index is a 1-based POSITION in creativity_df_CI.csv, not participant_id.
    # The author code sorts this index before assigning overlap to cohort1.
    overlap = data['data/processed/campaign_text_overlap.csv'].sort_values('row_index')
    assert len(overlap) == overlap.row_index.nunique() == len(cohort)
    assert np.array_equal(overlap.row_index.to_numpy(), np.arange(1, len(cohort) + 1))
    assert overlap.overlap_score.notna().all() and overlap.overlap_score.between(0, 1).all()
    assert np.array_equal(overlap.is_base.to_numpy(), cohort.randomization.eq('basegpt').to_numpy())
    assert overlap.loc[overlap.column_name.isna(), 'overlap_score'].eq(0).all()
    cohort['word_changes_percent'] = 100.0 * (1.0 - overlap.overlap_score.to_numpy())
    edit_design = pd.DataFrame({
        'basegpt': cohort.randomization.eq('basegpt').astype(float),
        'creativegpt': cohort.randomization.eq('creativegpt').astype(float),
        'creativegpt_rand': cohort.randomization.eq('creativegpt_rand').astype(float),
        'msg_count': cohort.msg_count.astype(float),
    })
    edit_fit = sm.OLS(cohort.word_changes_percent, edit_design).fit()
    slug = 's1_final_campaign_word_changes_personalized_vs_generic'
    e = estimates[slug]
    checks = [
        check('printed_treatment_level_adjusted_arm_intercept_percent', e['stats']['treatment_mean'],
              edit_fit.params['creativegpt'], 1),
        check('printed_control_level_adjusted_arm_intercept_percent', e['stats']['control_mean'],
              edit_fit.params['basegpt'], 1),
        check('n_treatment_study_arm_PDF_p19_Table_S2', 114, counts['creativegpt']),
        check('n_control_study_arm_PDF_p19_Table_S2', 116, counts['basegpt']),
        check('study_n_analyzed', 331, edit_fit.nobs),
    ]
    notes = (
        'PDF pp. 50-51 (supplement pp. 22-23) prints 64.5% Personalized and 80.5% Generic. '
        'These are NOT unadjusted arm means: they reproduce as the condition intercepts '
        'at msg_count=0 of the Gaussian model AI_overlap ~ randomization + msg_count - 1 '
        '(author code code/preprocessing/extract_campaign_edits.R lines 373-378). '
        'The fitted levels in percentage units are 64.50667946207133 and 80.54665312600216. '
        'The unadjusted observed means are 51.20245519082224 and 61.209651297272956. '
        'This resolves the extraction open item: the published percentages condition on '
        'post-treatment chat turns and should be flagged under extraction rule 5. '
        'As requested by this data-analysis brief, computed fields provide the unadjusted '
        'participant-level contrast from the reproduced underlying outcome; they do not '
        'reuse the adjusted intercept difference. '
        'Read campaign_text_overlap.csv, sort by row_index, and attach it positionally to '
        'creativity_df_CI.csv exactly as the author code does. row_index is not the anonymous '
        'participant_id. Its 331 unique positions and Generic-versus-other flags agree with '
        'the cohort. Outcome = 100*(1-overlap_score), in percentage points. '
        'The posted score is the maximum Jaccard overlap of unique lowercased word sets '
        'between the final campaign and any AI response classified as containing a full '
        'or partial campaign (author code lines 218-261 and 290-336). The maximum is the '
        'definition of one participant outcome, not a set of repeated ratings to average. '
        'The authors assign zero overlap when no qualifying draft is detected: 53 Generic, '
        '14 Personalized, and 15 Partial participants. Preserve these zeros as part of the '
        'published measure, yielding 100% difference for those people. This is not a literal '
        'percentage of token-level edits and more editing does not imply more creativity. '
        'No additional exclusions; one outcome per person, HC2 for individual assignment, '
        'sample SDs with denominator n-1. The paper gives no estimate-specific counts; '
        'the reproduction counts use the study totals on PDF p. 19/Table S2. '
        'Construct other; never pool as a creativity effect. First_round is inapplicable.'
    )
    add_if_reproduced(results, skipped, slug, checks, cohort,
                      'word_changes_percent', 'creativegpt', notes)

    skipped.append({
        'slug': 's1_quality_expert_elo_personalized_vs_generic',
        'reason': (
            'Cannot reproduce the expert-human Elo coefficient 158.2 (p=0.14), PDF p. 32. '
            'The deposit lacks expert Prolific pairwise choices or the corresponding '
            'campaign-level human Elo scores and model specification. '
            'human_campaign_evaluations.csv instead has five-domain Likert means for all '
            '331 campaigns; they exactly equal the averages of five MTurk ratings per '
            'participant in Batch_5322742_batch_results.csv (1655 ratings). These are not '
            'the expert pairwise-Elo validation of 100 campaigns. The 100-row files '
            'human_expertise_campaigns.csv and all_campaigns.csv contain only index, '
            'condition, campaign_id, batch_num, local_id, and marketing_score, not human '
            'Elo scores or pairwise decisions. The available Elo ratings/runs are LLM '
            'judgments; substituting those would change the outcome. No participant '
            'effect or uncertainty is computed.'
        ),
    })
    diversity_reason = (
        'Cannot exactly rerun the campaign-theme diversity procedure required by rule 5. '
        'The author code creativity_analysis.R extracts themes with GPT-4o, embeds them '
        'with text-embedding-3-large, constructs a pooled centroid including 100 AI-only '
        'campaigns, and maps 1-cosine-similarity to percentiles. The posted '
        'elo_real_vs_simulated.csv has 431 downstream creativity scores and condition '
        'labels, but the original campaign_themes.rds, the original human campaign texts, '
        'and the 3072-dimensional theme embeddings are absent. The published aggregate '
        'levels cannot be independently recomputed using the same texts and embeddings. '
        'Response/message embeddings and simulated campaign text describe different '
        'objects and cannot replace these inputs. Do not treat stored diversity '
        'percentiles as independent participant outcomes or invent a participant SD/HC2 SE.'
    )
    for suffix in ['personalized', 'partially_personalized']:
        skipped.append({
            'slug': f's1_theme_diversity_{suffix}_vs_generic',
            'reason': diversity_reason,
        })

    order = {e['slug']: i for i, e in enumerate(extraction['estimates'])}
    results.sort(key=lambda x: order[x['slug']])
    skipped.sort(key=lambda x: order[x['slug']])
    assert {r['slug'] for r in results} | {r['slug'] for r in skipped} == set(estimates)
    assert not ({r['slug'] for r in results} & {r['slug'] for r in skipped})
    output = {
        'cid': 'c401',
        'analyst': 'B',
        'script': SCRIPT.as_posix(),
        'data_files': READ_FILES,
        'results': results,
        'skipped': skipped,
    }
    # User-specified JSON serialization. Write no other file.
    with OUTPUT.open('w', encoding='utf-8') as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding='utf-8') as fh:
        parsed = json.load(fh)
    assert parsed == output
    summary = {
        'cid': 'c401',
        'n_results': len(parsed['results']),
        'n_reproduced': sum(all(c['match'] for c in r['reproduced'])
                            for r in parsed['results']),
        'n_skipped': len(parsed['skipped']),
    }
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
