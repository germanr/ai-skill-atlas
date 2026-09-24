/*
  Reconstruct AI-versus-control gain precision from verified author data.
  Source: Zenodo record 20285307, merged_data_pseudonymized.csv, as
  reconstructed in mode_of_use/contrasts/replication/bassner on 2026-09-12.
  Pinned input: exact numeric contents of verified_arm_statistics.csv.
  Original file SHA256:
  371dfd8ad2b0232ff640ac905deb2a6b0696d5a91ccb73793bda61721c309153
  Author raw CSV SHA256:
  4ecbb52a605481fbb075f0f39c72817f2f4e0740d21608084c2929f7dba73be6
  The existing replication preserves the authors' timestamp convention.
  The pooled pre-test SD is the original Morris d_ppc2 standardizer.
  Treating that estimated denominator as fixed is an approximation.
  Optional first argument: directory containing the pinned input CSV.
*/
#delimit;
clear all;
set more off;

args audit_dir;
if "`audit_dir'" == "" local audit_dir "C:/Dropbox/Admin/website/ai-skill-atlas/code/audit";
import delimited "`audit_dir'/bassner_arm_statistics.csv", clear varnames(1) asdouble;

quietly summarize n if experiment_group == "NOAI", meanonly;
local n_control = r(mean);
quietly summarize pre_sd if experiment_group == "NOAI", meanonly;
local pre_sd_control = r(mean);
quietly summarize gain_sd if experiment_group == "NOAI", meanonly;
local gain_sd_control = r(mean);
quietly summarize gain_mean if experiment_group == "NOAI", meanonly;
local gain_mean_control = r(mean);

keep if inlist(experiment_group, "IRIS", "CHATGPT");
rename n n_treatment;
generate double n_control = `n_control';
generate double n_total = n_treatment + n_control;
generate double pooled_pre_sd = sqrt(((n_treatment-1)*pre_sd^2 +
    (n_control-1)*`pre_sd_control'^2)/(n_total-2));
generate double raw_gain_difference = gain_mean - `gain_mean_control';
generate double raw_gain_se = sqrt(gain_sd^2/n_treatment +
    `gain_sd_control'^2/n_control);
generate double exact_effect_size_sd = raw_gain_difference/pooled_pre_sd;
generate double se_fixed_denominator = raw_gain_se/pooled_pre_sd;
generate double existing_rounded_effect = cond(experiment_group == "IRIS", -.073, -.011);
generate double ci_lower = exact_effect_size_sd - invnormal(.975)*se_fixed_denominator;
generate double ci_upper = exact_effect_size_sd + invnormal(.975)*se_fixed_denominator;
generate str35 estimate_id = cond(experiment_group == "IRIS",
    "bassner_etal_2026__est59", "bassner_etal_2026__est60");
order estimate_id experiment_group n_treatment n_control n_total;
format pooled_pre_sd raw_gain_difference raw_gain_se exact_effect_size_sd
    se_fixed_denominator existing_rounded_effect ci_lower ci_upper %21.15g;
sort estimate_id;
export delimited using "`audit_dir'/bassner_gain_precision.csv", replace;
list estimate_id pooled_pre_sd exact_effect_size_sd se_fixed_denominator
    existing_rounded_effect ci_lower ci_upper, noobs abbreviate(32);
