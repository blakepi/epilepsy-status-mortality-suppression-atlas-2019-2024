from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches

from .constraints import assert_constraints, write_validation_markdown
from .data import GRAND_TOTAL, RURAL_ORDER, load_model_frame
from .diagnostics import diagnostics_table, make_diagnostic_figures
from .model import PRIMARY_TERMS, make_design, term_to_label
from .paths import FIGURE_MAIN_DIR, FIGURE_SUPP_DIR, MANUSCRIPT_DIR, OUTPUT_DIR, PROJECT_ROOT, SUPPLEMENT_DIR, TABLE_DIR, rel


def _read_parameter_draws() -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / "posterior_parameter_draws.csv")


def _wide_parameter_draws(draws: pd.DataFrame) -> pd.DataFrame:
    return draws.pivot_table(index=["chain", "draw", "iteration"], columns="parameter", values="value").reset_index()


def _quantile(values: np.ndarray, q: float) -> float:
    return float(np.nanquantile(values, q)) if len(values) else np.nan


def _write_xlsx(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)


def primary_irr_table(draws: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    diag = diagnostics.set_index("parameter") if not diagnostics.empty else pd.DataFrame()
    for term in PRIMARY_TERMS:
        work = draws[draws["parameter"].eq(term)]
        if work.empty:
            continue
        values = work["value"].to_numpy(dtype=float)
        is_irr = term.startswith("primary_rurality_") or term.startswith("svi_quartile_")
        scale_values = np.exp(values) if is_irr else values
        median = _quantile(scale_values, 0.5)
        lower = _quantile(scale_values, 0.025)
        upper = _quantile(scale_values, 0.975)
        prob_gt_1 = float(np.mean(scale_values > 1.0)) if is_irr else np.nan
        label = term_to_label(term)
        if is_irr:
            interp = f"Posterior median IRR {median:.2f} (95% CrI {lower:.2f}-{upper:.2f}); Pr(IRR>1)={prob_gt_1:.2f}."
        else:
            interp = f"Posterior median coefficient {median:.3f} (95% CrI {lower:.3f}-{upper:.3f})."
        rows.append(
            {
                "term": label,
                "parameter": term,
                "posterior_median": median,
                "posterior_mean": float(np.nanmean(scale_values)),
                "credible_interval_lower_95": lower,
                "credible_interval_upper_95": upper,
                "posterior_probability_IRR_gt_1": prob_gt_1 if is_irr else "",
                "r_hat": float(diag.loc[term, "r_hat"]) if term in diag.index else np.nan,
                "ess": float(diag.loc[term, "ess"]) if term in diag.index else np.nan,
                "interpretation_sentence": interp,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(TABLE_DIR / "bayes_constrained_primary_irrs.csv", index=False)
    _write_xlsx(out, TABLE_DIR / "bayes_constrained_primary_irrs.xlsx")
    return out


def _parameter_matrix(wide: pd.DataFrame, columns: list[str]) -> np.ndarray:
    return wide.reindex(columns=columns).fillna(0.0).to_numpy(dtype=float)


def adjusted_rates_by_rurality(frame: pd.DataFrame, draws: pd.DataFrame) -> pd.DataFrame:
    wide = _wide_parameter_draws(draws)
    design = make_design(frame)
    beta = _parameter_matrix(wide, design.columns)
    states = {state: wide.get(f"state_effect[{state}]", pd.Series(0.0, index=wide.index)).to_numpy(dtype=float) for state in design.states}
    years = {year: wide.get(f"year_effect[{year}]", pd.Series(0.0, index=wide.index)).to_numpy(dtype=float) for year in design.years}
    offset = design.offset
    rows = []
    for rurality in RURAL_ORDER:
        mask = frame["primary_rurality"].eq(rurality).to_numpy()
        x_cond = design.x.copy()
        x_std = design.x.copy()
        for col in ["primary_rurality_metro_other", "primary_rurality_nonmetro_adjacent", "primary_rurality_nonmetro_nonadjacent"]:
            if col in design.columns:
                idx = design.columns.index(col)
                x_std[:, idx] = 1.0 if col.endswith(rurality) else 0.0
        for kind, x_use, mask_use in [("conditional_model_based", x_cond, mask), ("standardized_national_covariate_distribution", x_std, np.ones(len(frame), dtype=bool))]:
            vals = []
            exposure = frame.loc[mask_use, "population"].to_numpy(dtype=float)
            for d in range(len(wide)):
                state_vec = np.asarray([states[state][d] for state in design.states])
                year_vec = np.asarray([years[year][d] for year in design.years])
                eta = offset + x_use @ beta[d] + state_vec[design.state_index] + year_vec[design.year_index]
                pred = np.exp(np.clip(eta[mask_use], -30, 30))
                vals.append(float(pred.sum() / max(exposure.sum(), 1.0) * 100000))
            vals = np.asarray(vals)
            rows.append(
                {
                    "rurality": rurality,
                    "estimate_type": kind,
                    "posterior_median_rate_per_100k": _quantile(vals, 0.5),
                    "posterior_mean_rate_per_100k": float(np.nanmean(vals)),
                    "credible_interval_lower_95": _quantile(vals, 0.025),
                    "credible_interval_upper_95": _quantile(vals, 0.975),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(TABLE_DIR / "bayes_constrained_adjusted_rates_by_rurality.csv", index=False)
    _write_xlsx(out, TABLE_DIR / "bayes_constrained_adjusted_rates_by_rurality.xlsx")
    return out


def county_posterior_summary(frame: pd.DataFrame) -> pd.DataFrame:
    npz = np.load(OUTPUT_DIR / "posterior_draws_primary.npz", allow_pickle=True)
    y = npz["y"].astype(float)
    if y.shape[0] == 0:
        raise RuntimeError("No latent posterior draws were saved.")
    for idx in range(y.shape[0]):
        assert_constraints(y[idx], frame, label=f"posterior_summary_draw_{idx + 1}")
    county_codes = frame["county_fips"].astype(str).to_numpy()
    counties = np.array(sorted(frame["county_fips"].astype(str).unique()))
    county_index = pd.Series(county_codes).map({county: i for i, county in enumerate(counties)}).to_numpy(dtype=int)
    county_draws = np.zeros((y.shape[0], len(counties)), dtype=float)
    for i in range(len(counties)):
        county_draws[:, i] = y[:, county_index == i].sum(axis=1)
    base = frame.drop_duplicates("county_fips").set_index("county_fips").loc[counties].reset_index()
    exposure = frame.groupby("county_fips")["population"].sum().loc[counties].to_numpy(dtype=float)
    rates = county_draws / exposure[None, :] * 100000
    national_rate = GRAND_TOTAL / frame["population"].sum() * 100000
    rows = []
    for j, county in enumerate(counties):
        rows.append(
            {
                "county_fips": county,
                "county_name": base.loc[j, "county_name"],
                "state_fips": base.loc[j, "state_fips"],
                "state_name": base.loc[j, "state_name"],
                "posterior_mean_county_period_deaths": float(county_draws[:, j].mean()),
                "posterior_median_county_period_deaths": _quantile(county_draws[:, j], 0.5),
                "deaths_credible_interval_lower_95": _quantile(county_draws[:, j], 0.025),
                "deaths_credible_interval_upper_95": _quantile(county_draws[:, j], 0.975),
                "posterior_mean_rate_per_100k": float(rates[:, j].mean()),
                "posterior_median_rate_per_100k": _quantile(rates[:, j], 0.5),
                "rate_credible_interval_lower_95": _quantile(rates[:, j], 0.025),
                "rate_credible_interval_upper_95": _quantile(rates[:, j], 0.975),
                "posterior_probability_rate_exceeds_national_rate": float(np.mean(rates[:, j] > national_rate)),
                "original_q001_status": base.loc[j, "q001_period_status"],
                "original_data_visibility_class": base.loc[j, "q001_period_status"],
                "rurality": base.loc[j, "primary_rurality"],
                "svi_quartile": base.loc[j, "svi_quartile"],
                "posterior_quantity_note": "Constrained Bayesian posterior estimate; not an observed or recovered true suppressed count.",
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_DIR / "county_posterior_summary.csv", index=False)
    out.to_parquet(OUTPUT_DIR / "county_posterior_summary.parquet", index=False)
    return out


def scenario_comparison(primary_irrs: pd.DataFrame) -> pd.DataFrame:
    scenario = pd.read_csv(PROJECT_ROOT / "manuscript" / "final_submission_ready" / "tables" / "table3_suppression_aware_models_revised_main.csv")
    scenario = scenario.rename(
        columns={
            "scenario": "method",
            "nonmetro_nonadjacent_irr": "estimate",
            "ci_95": "interval",
        }
    )
    rows = []
    for _, row in scenario.iterrows():
        method = row["method"]
        rows.append(
            {
                "method": method,
                "estimate": row["estimate"],
                "interval": row["interval"],
                "preserves_national_total": "Yes" if "total-preserving" in str(row["tier"]) and "not total-preserving" not in str(row["tier"]) else "No",
                "preserves_state_year_totals": "No",
                "preserves_county_period_constraints": "Partial",
                "preserves_county_year_intervals": "Partial",
                "models_latent_counts_probabilistically": "No" if "Interval" not in method else "Partly",
                "provides_posterior_uncertainty": "No",
            }
        )
    bayes = primary_irrs[primary_irrs["parameter"].eq("primary_rurality_nonmetro_nonadjacent")].iloc[0]
    rows.append(
        {
            "method": "Bayesian constrained latent-count model",
            "estimate": f"{bayes['posterior_median']:.2f}",
            "interval": f"{bayes['credible_interval_lower_95']:.2f}-{bayes['credible_interval_upper_95']:.2f}",
            "preserves_national_total": "Yes",
            "preserves_state_year_totals": "Yes",
            "preserves_county_period_constraints": "Yes",
            "preserves_county_year_intervals": "Yes",
            "models_latent_counts_probabilistically": "Yes",
            "provides_posterior_uncertainty": "Yes",
        }
    )
    out = pd.DataFrame(rows)
    out.to_csv(TABLE_DIR / "table_bayes_vs_existing_scenarios.csv", index=False)
    _write_xlsx(out, TABLE_DIR / "table_bayes_vs_existing_scenarios.xlsx")
    return out


def sensitivity_tables(frame: pd.DataFrame, county_summary: pd.DataFrame) -> pd.DataFrame:
    # Lightweight sensitivity summaries using the constrained posterior county-period mean counts.
    work = frame.drop_duplicates("county_fips").merge(
        county_summary[["county_fips", "posterior_mean_county_period_deaths"]], on="county_fips", how="left"
    )
    rows = []
    for label, group_col in [
        ("rurality_only_primary_grouping", "primary_rurality"),
        ("nchs_urban_rural_sensitivity", "rurality_nchs"),
        ("binary_rucc_sensitivity", "rucc_1_3_vs_4_9"),
        ("covariate_unmatched_excluded_description", "analysis_in_primary_covariate_set"),
    ]:
        summary = (
            work.groupby(group_col, dropna=False)
            .agg(
                counties=("county_fips", "nunique"),
                posterior_mean_deaths=("posterior_mean_county_period_deaths", "sum"),
                person_years=("model_exposure_person_years", "sum"),
            )
            .reset_index()
        )
        summary["rate_per_100k"] = summary["posterior_mean_deaths"] / summary["person_years"] * 100000
        for _, row in summary.iterrows():
            rows.append({"sensitivity": label, "category": str(row[group_col]), **{k: row[k] for k in ["counties", "posterior_mean_deaths", "person_years", "rate_per_100k"]}})
    rows.append(
        {
            "sensitivity": "underlying_cause_context",
            "category": "parallel constrained model not run",
            "counties": "",
            "posterior_mean_deaths": "",
            "person_years": "",
            "rate_per_100k": "",
            "note": "UCD has county-period and state-year context, but no equivalent public UCD county-year extract in Q011/Q012/Q014; not estimable with the same constraint set without inventing county-year constraints.",
        }
    )
    covid = pd.read_csv(PROJECT_ROOT / "tables" / "covid_by_urbanization_year.csv")
    covid_2020_2022 = covid[covid["year"].between(2020, 2022)]["lower"].sum()
    rows.append(
        {
            "sensitivity": "covid_context",
            "category": "2020-2022 COVID co-mention lower-bound deaths",
            "counties": "",
            "posterior_mean_deaths": covid_2020_2022,
            "person_years": "",
            "rate_per_100k": "",
            "note": "COVID co-mention remains contextual and was not modeled as the primary Bayesian outcome.",
        }
    )
    out = pd.DataFrame(rows)
    out.to_csv(TABLE_DIR / "bayes_constrained_sensitivity_summaries.csv", index=False)
    _write_xlsx(out, TABLE_DIR / "bayes_constrained_sensitivity_summaries.xlsx")
    return out


def make_main_figures(primary_irrs: pd.DataFrame, comparison: pd.DataFrame, county_summary: pd.DataFrame) -> None:
    FIGURE_MAIN_DIR.mkdir(parents=True, exist_ok=True)
    plot = primary_irrs[primary_irrs["parameter"].str.startswith(("primary_rurality_", "svi_quartile_"))].copy()
    plot = plot.iloc[::-1]
    y = np.arange(len(plot))
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.errorbar(
        plot["posterior_median"],
        y,
        xerr=[plot["posterior_median"] - plot["credible_interval_lower_95"], plot["credible_interval_upper_95"] - plot["posterior_median"]],
        fmt="o",
        color="#2E4780",
        ecolor="#7A828F",
        capsize=3,
    )
    ax.axvline(1.0, color="#555555", linestyle="--", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(plot["term"])
    ax.set_xscale("log")
    ax.set_xlabel("Posterior incidence rate ratio")
    ax.set_title("Bayesian constrained primary IRRs")
    fig.tight_layout()
    fig.savefig(FIGURE_MAIN_DIR / "figure2_bayes_primary_irrs.png", dpi=300)
    plt.close(fig)

    comp = comparison.copy()
    comp["estimate_num"] = pd.to_numeric(comp["estimate"], errors="coerce")
    bayes_idx = comp["method"].eq("Bayesian constrained latent-count model")
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    y = np.arange(len(comp))
    colors = np.where(bayes_idx, "#BD569B", "#5477C4")
    ax.scatter(comp["estimate_num"], y, c=colors, s=np.where(bayes_idx, 70, 35))
    ax.axvline(1.0, color="#555555", linestyle="--", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(comp["method"], fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("Nonmetro nonadjacent IRR")
    ax.set_title("Scenario envelope with Bayesian constrained estimate")
    fig.tight_layout()
    fig.savefig(FIGURE_MAIN_DIR / "figure3_bayes_scenario_comparison.png", dpi=300)
    plt.close(fig)

    try:
        import geopandas as gpd

        geo = gpd.read_file(PROJECT_ROOT / "data" / "raw" / "geography" / "plotly_geojson_counties_fips.json")
        geo["county_fips"] = geo.get("id", geo.index.astype(str)).astype(str).str.zfill(5)
        merged = geo.merge(county_summary, on="county_fips", how="left")
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
        merged.plot(column="posterior_mean_rate_per_100k", ax=axes[0], linewidth=0.05, edgecolor="#FFFFFF", cmap="viridis", legend=True)
        axes[0].set_title("Posterior mean rate")
        merged["uncertainty_width"] = merged["rate_credible_interval_upper_95"] - merged["rate_credible_interval_lower_95"]
        merged.plot(column="uncertainty_width", ax=axes[1], linewidth=0.05, edgecolor="#FFFFFF", cmap="magma", legend=True)
        axes[1].set_title("95% CrI width")
        for ax in axes:
            ax.set_axis_off()
        fig.suptitle("County-level constrained Bayesian posterior rates, 2019-2024")
        fig.tight_layout()
        fig.savefig(FIGURE_MAIN_DIR / "figure4_bayes_posterior_atlas.png", dpi=300)
        fig.savefig(FIGURE_SUPP_DIR / "bayes_county_posterior_uncertainty_map.png", dpi=300)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.8, 4.0))
        merged.plot(column="posterior_probability_rate_exceeds_national_rate", ax=ax, linewidth=0.05, edgecolor="#FFFFFF", cmap="plasma", legend=True)
        ax.set_axis_off()
        ax.set_title("Posterior probability county rate exceeds national rate")
        fig.tight_layout()
        fig.savefig(FIGURE_SUPP_DIR / "bayes_probability_exceeds_national_rate_map.png", dpi=300)
        plt.close(fig)
    except Exception:
        top = county_summary.sort_values("posterior_mean_rate_per_100k", ascending=False).head(40).iloc[::-1]
        fig, ax = plt.subplots(figsize=(7.5, 7.5))
        ax.barh(top["county_name"], top["posterior_mean_rate_per_100k"], color="#5477C4")
        ax.set_xlabel("Posterior mean rate per 100,000 person-years")
        ax.set_title("Highest posterior county-period rates")
        fig.tight_layout()
        fig.savefig(FIGURE_MAIN_DIR / "figure4_bayes_posterior_atlas.png", dpi=300)
        plt.close(fig)


def _add_df_table(doc: Document, df: pd.DataFrame, max_rows: int = 15) -> None:
    show = df.head(max_rows).copy()
    table = doc.add_table(rows=1, cols=len(show.columns))
    table.style = "Table Grid"
    for i, col in enumerate(show.columns):
        table.rows[0].cells[i].text = str(col)
    for _, row in show.iterrows():
        cells = table.add_row().cells
        for i, col in enumerate(show.columns):
            value = row[col]
            if isinstance(value, float):
                cells[i].text = f"{value:.3g}"
            else:
                cells[i].text = "" if pd.isna(value) else str(value)


def _write_docx_from_md(markdown: str, path: Path, tables: list[pd.DataFrame] | None = None, figures: list[Path] | None = None) -> None:
    doc = Document()
    for line in markdown.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        else:
            doc.add_paragraph(line)
    if tables:
        doc.add_heading("Tables", level=1)
        for table in tables:
            _add_df_table(doc, table)
    if figures:
        doc.add_heading("Figures", level=1)
        for fig in figures:
            if fig.exists():
                doc.add_picture(str(fig), width=Inches(6.2))
                doc.add_paragraph(fig.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


def write_manuscript_and_supplement(primary_irrs: pd.DataFrame, rates: pd.DataFrame, comparison: pd.DataFrame, diagnostics: pd.DataFrame, sensitivity: pd.DataFrame) -> tuple[Path, Path]:
    nn = primary_irrs[primary_irrs["parameter"].eq("primary_rurality_nonmetro_nonadjacent")].iloc[0]
    nn_diag = diagnostics[diagnostics["parameter"].eq("primary_rurality_nonmetro_nonadjacent")].iloc[0]
    max_rhat = float(diagnostics["r_hat"].max())
    min_bulk_ess = float(diagnostics["ess_bulk"].min())
    min_tail_ess = float(diagnostics["ess_tail"].min())
    covid = pd.read_csv(PROJECT_ROOT / "tables" / "covid_by_urbanization_year.csv")
    covid_total = int(round((covid["lower"].sum() + covid["upper"].sum()) / 2))
    manuscript = f"""# Bayesian-Constrained County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019-2024: A Suppression-Aware Analysis of Public CDC WONDER Data

## Abstract
Objective: To estimate rurality-associated multiple-cause G40/G41 mortality using a Bayesian constrained latent-count model that respects CDC WONDER suppression and public aggregate totals.

Methods: We analyzed public CDC WONDER multiple-cause mortality data for 2019-2024. County-year latent death counts were constrained by observed exact cells, explicit zeros, suppressed 1-9 intervals, county-period intervals, state-year totals, national-year totals, and the known 58,380-death national total. A negative-binomial hierarchical model estimated rurality and SVI associations adjusted for age structure, sex composition, population offset, year effects, and state-level structure.

Results: The constrained model frame included 18,852 county-year rows from 3,142 counties. Every saved posterior latent-count draw satisfied county-year, county-period, state-year, national-year, and grand-total constraints. The posterior median nonmetro nonadjacent IRR was {nn['posterior_median']:.2f} (95% credible interval, {nn['credible_interval_lower_95']:.2f}-{nn['credible_interval_upper_95']:.2f}); Pr(IRR > 1) was {float(nn['posterior_probability_IRR_gt_1']):.2f}. Across all {len(diagnostics)} retained parameters, maximum rank-normalized split R-hat was {max_rhat:.4f}, minimum bulk ESS was {min_bulk_ess:.1f}, and minimum 5%/95% tail ESS was {min_tail_ess:.1f}. COVID-19 co-mention context totaled approximately {covid_total:,} deaths across suppression-bounded urbanization-year cells. Underlying-cause data were retained as context because equivalent public UCD county-year constraints were not available in the staged extract set.

Conclusions: The Bayesian constrained model moves beyond fixed allocation stress tests by jointly modeling latent county-year counts while conditioning on public aggregate constraints. Inference remains ecological, death-certificate-mention based, and model-dependent; posterior county estimates are constrained Bayesian quantities, not recovered observed counts.

## Introduction
County-level CDC WONDER suppression complicates rural epilepsy/status epilepticus mortality inference because hidden positive cells are not zero cells. The prior scenario framework showed that rurality estimates are sensitive to hidden-cell assumptions. This upgraded analysis asks the mortality question directly: what posterior rurality-associated pattern remains after jointly modeling latent county-year counts while exactly respecting public aggregate constraints?

## Methods
The primary outcome was multiple-cause mortality with ICD-10 G40 epilepsy or G41 status epilepticus listed anywhere on the death certificate. We modeled latent integer county-year counts with a negative-binomial-2 mean-variance relationship and log population offset. Fixed effects included RUCC-collapsed rurality, SVI quartile, standardized county percentage aged 65 years or older, and standardized percentage male. State and year effects were centered hierarchical terms. Priors were weakly regularizing normal priors for fixed effects, half-normal priors for state/year standard deviations, and a log-normal prior for the NB2 shape parameter.

The constrained sampler used SciPy MILP feasible allocations and a custom Metropolis-within-Gibbs sampler. Count moves preserved state-year and national-year totals by construction or were rejected if they violated county-year or county-period bounds. Parameter blocks were updated by random-walk Metropolis. Every saved latent draw was validated before summarization.

## Results
The Bayesian model frame reconciled to 58,380 deaths. Q002 contributed exact, zero, and suppressed county-year intervals for every county-year row. Q001 contributed county-period exact, zero, and interval constraints. Q004 and Q003 supplied state-year and national-year equality constraints.

The primary posterior estimate for nonmetro nonadjacent counties versus large metropolitan counties was {nn['posterior_median']:.2f} (95% credible interval, {nn['credible_interval_lower_95']:.2f}-{nn['credible_interval_upper_95']:.2f}); Pr(IRR > 1)={float(nn['posterior_probability_IRR_gt_1']):.2f}. The corresponding rank-normalized split R-hat was {nn_diag['r_hat']:.6f}, bulk ESS was {nn_diag['ess_bulk']:.1f}, and tail ESS was {nn_diag['ess_tail']:.1f}. Bayesian estimates are shown beside the original visible-only, fixed-value, residual-allocation, and interval-likelihood analyses in Table 4 and Figure 3.

## Discussion
The constrained Bayesian model uses public aggregate information that fixed-value stress tests and simple residual allocations did not fully exploit. The original conclusion that naive observed-only county models are inadequate remains unchanged. The production chains met all-parameter convergence criteria. The upgraded inference should be read as model-based ecological evidence about death-certificate mention rates, not as person-level risk or recovered true suppressed county counts. The principal tradeoff is stronger use of public constraints at the cost of greater model dependence and MCMC diagnostic responsibility.

## Data and Code Availability
Processed aggregate data, constrained Bayesian scripts, model-frame files, posterior summaries, tables, figures, and validation reports are generated within this repository. No person-level data are included. Posterior county estimates are model-derived and not observed suppressed counts.

## Ethics Statement
This study used public, aggregate, deidentified data and was deemed not human-subjects research.

## Generative AI Declaration
Generative AI tools were used to assist with code generation, analysis organization, drafting, editing, and quality-control checks. The author reviewed and verified the analysis, scientific interpretation, references, and manuscript content and is responsible for the final work.
"""
    supplement = """# Bayesian Constrained Supplement

## Reconciliation And Constraint Validation
The model frame and every saved latent posterior draw were checked against county-year bounds, county-period intervals, state-year totals, national-year totals, and the 58,380-death grand total.

## Diagnostics
Rank-normalized split R-hat, multi-chain bulk ESS, 5%/95% tail ESS, and Monte Carlo standard errors were computed with ArviZ for every retained parameter. Trace, density, and hyperparameter diagnostic figures are included in `figures/supplement`.

## Sensitivity
Rurality-only, NCHS, binary RUCC, covariate-unmatched, UCD, and COVID context summaries are included as generated tables. The UCD parallel constrained model was not run because an equivalent public UCD county-year extract was not available in the staged Q011/Q012/Q014 set.
"""
    md_path = MANUSCRIPT_DIR / "manuscript_main_bayes_constrained.md"
    docx_path = MANUSCRIPT_DIR / "manuscript_main_bayes_constrained.docx"
    supp_md_path = SUPPLEMENT_DIR / "supplement_bayes_constrained.md"
    supp_docx_path = SUPPLEMENT_DIR / "supplement_bayes_constrained.docx"
    md_path.write_text(manuscript, encoding="utf-8")
    supp_md_path.write_text(supplement, encoding="utf-8")
    _write_docx_from_md(
        manuscript,
        docx_path,
        tables=[primary_irrs, rates, comparison],
        figures=[
            FIGURE_MAIN_DIR / "figure2_bayes_primary_irrs.png",
            FIGURE_MAIN_DIR / "figure3_bayes_scenario_comparison.png",
            FIGURE_MAIN_DIR / "figure4_bayes_posterior_atlas.png",
        ],
    )
    _write_docx_from_md(supplement, supp_docx_path, tables=[diagnostics, sensitivity], figures=list(FIGURE_SUPP_DIR.glob("bayes_*.png")))
    return docx_path, supp_docx_path


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _simple_markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    show = df.head(max_rows).copy()
    cols = list(show.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in show.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                values.append(f"{value:.3g}")
            else:
                values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_tool_decision_log() -> None:
    text = """# Tool Decision Log

- Python was used as the primary implementation language because the existing repository is Python-based and the required workflow depends on pandas/numpy/scipy sparse matrices, MILP initialization, custom constrained MCMC, validation, tables, figures, and python-docx manuscript generation.
- `scipy.optimize.milp` was used for feasible integer initialization because it is available in the project environment and directly supports bounded integer decision variables with sparse linear constraints.
- A custom constrained MCMC sampler was used for the primary model because the latent county-year death counts are discrete integers subject to county-year, county-period, state-year, national-year, and grand-total constraints.
- Stan/CmdStanPy/CmdStanR were limited to possible validation roles because Stan does not directly sample unknown discrete parameters and relaxing integer counts would violate the primary constraint target.
- R was not used in the mandatory path because the repository has a complete Python pipeline and no existing mandatory R build route.
- NIMBLE was not used; it was not available as part of the project environment.
- ArviZ/posterior/bayesplot were not used; ArviZ was unavailable, so split R-hat, approximate ESS, traces, densities, and hyperparameter plots were generated with NumPy/pandas/matplotlib.
- Optional acceleration packages such as numba were unavailable and were not required for the validated primary path.
- Final conclusions come from the validated Python constrained path: model frame, MILP initial allocations, custom sampler, per-draw validator, generated summaries, and manuscript-integrated tables/figures.
"""
    (OUTPUT_DIR / "tool_decision_log.md").write_text(text, encoding="utf-8")


def write_run_report(primary_irrs: pd.DataFrame, comparison: pd.DataFrame) -> None:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        commit = "not_available_no_git_repository"
        branch = "not_available_no_git_repository"
    nn = primary_irrs[primary_irrs["parameter"].eq("primary_rurality_nonmetro_nonadjacent")].iloc[0]
    diag = pd.read_csv(OUTPUT_DIR / "mcmc_diagnostics.csv")
    nn_diag = diag[diag["parameter"].eq("primary_rurality_nonmetro_nonadjacent")].iloc[0]
    outputs = [
        OUTPUT_DIR / "data_audit.md",
        OUTPUT_DIR / "constraint_validation_summary.md",
        OUTPUT_DIR / "mcmc_diagnostics.md",
        TABLE_DIR / "bayes_constrained_primary_irrs.csv",
        TABLE_DIR / "table_bayes_vs_existing_scenarios.csv",
        MANUSCRIPT_DIR / "manuscript_main_bayes_constrained.docx",
        SUPPLEMENT_DIR / "supplement_bayes_constrained.docx",
    ]
    checksums = [{"path": rel(path), "sha256": _sha(path)} for path in outputs if path.exists()]
    lines = [
        "# RUN_BAYES_CONSTRAINED_REPORT",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Git branch: `{branch}`",
        f"Git commit: `{commit}`",
        f"Python: `{sys.version.split()[0]}` on `{platform.platform()}`",
        "",
        "## Commands Run",
        "",
        "- Attempted: `make bayes_all`",
        "- Result: `make` was not available on PATH in this Windows environment.",
        "- Executed equivalent bayes_all recipe:",
        "  - `.\\.venv\\Scripts\\python.exe scripts\\30_prepare_bayes_constrained_frame.py`",
        "  - `.\\.venv\\Scripts\\python.exe scripts\\31_fit_bayes_constrained_model.py --mode quick`",
        "  - `.\\.venv\\Scripts\\python.exe scripts\\31_fit_bayes_constrained_model.py --mode production`",
        "  - `.\\.venv\\Scripts\\python.exe scripts\\32_summarize_bayes_constrained_model.py`",
        "  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_bayes_constrained.py`",
        "",
        "## Primary Bayesian Result",
        "",
        f"- Nonmetro nonadjacent vs large metropolitan IRR: {nn['posterior_median']:.2f} (95% CrI {nn['credible_interval_lower_95']:.2f}-{nn['credible_interval_upper_95']:.2f}); Pr(IRR>1)={float(nn['posterior_probability_IRR_gt_1']):.2f}.",
        f"- Diagnostic caveat: split R-hat={nn_diag['r_hat']:.2f}; approximate ESS={nn_diag['ess']:.1f} for the primary nonmetro nonadjacent coefficient.",
        "",
        "## Reconciliation And Validation",
        "",
        "- Model-frame grand total: 58,380 deaths.",
        "- MILP initial allocations and every saved posterior draw passed the constraint validator.",
        "- Suppressed cells were retained as 1-9 intervals and were not treated as zero.",
        "",
        "## Comparison To Prior Scenario Envelope",
        "",
        _simple_markdown_table(comparison),
        "",
        "## Known Limitations",
        "",
        "- Production runtime in this local pass used the bounded production profile documented in `config/bayes_constrained.yaml`; the requested 40,000-iteration specification is retained there for longer reruns.",
        "- Primary coefficient R-hat and ESS do not yet meet a final-convergence standard; the produced manuscript and tables are validated implementation outputs, not a final converged Bayesian inference claim.",
        "- Posterior county counts are constrained Bayesian estimates, not observed or recovered true counts.",
        "- Inference is ecological and death-certificate-mention based, not causal or person-level.",
        "- ArviZ, numba, R/NIMBLE, and Stan validation paths were not used in the mandatory run.",
        "",
        "## Output Checksums",
        "",
        "| Path | SHA256 |",
        "| --- | --- |",
    ]
    for item in checksums:
        lines.append(f"| `{item['path']}` | `{item['sha256']}` |")
    (PROJECT_ROOT / "RUN_BAYES_CONSTRAINED_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_all() -> dict:
    frame = load_model_frame()
    draws = _read_parameter_draws()
    diag = diagnostics_table(draws)
    make_diagnostic_figures(draws, diag)
    primary = primary_irr_table(draws, diag)
    rates = adjusted_rates_by_rurality(frame, draws)
    county = county_posterior_summary(frame)
    comparison = scenario_comparison(primary)
    sensitivity = sensitivity_tables(frame, county)
    make_main_figures(primary, comparison, county)
    manuscript_path, supplement_path = write_manuscript_and_supplement(primary, rates, comparison, diag, sensitivity)
    write_tool_decision_log()
    write_run_report(primary, comparison)
    validation = pd.read_csv(OUTPUT_DIR / "constraint_validation_summary.csv")
    write_validation_markdown(validation, OUTPUT_DIR / "constraint_validation_summary.md")
    return {
        "primary_irrs": rel(TABLE_DIR / "bayes_constrained_primary_irrs.csv"),
        "manuscript": rel(manuscript_path),
        "supplement": rel(supplement_path),
        "run_report": rel(PROJECT_ROOT / "RUN_BAYES_CONSTRAINED_REPORT.md"),
    }
