from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.special import gammaln

from .data import RURAL_ORDER, SVI_ORDER
from .target_density import centered_normal_log_density


PRIMARY_TERMS = [
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
    "z_pct_age65",
    "z_pct_male",
]


@dataclass
class Design:
    x: np.ndarray
    columns: list[str]
    offset: np.ndarray
    state_index: np.ndarray
    year_index: np.ndarray
    states: list[str]
    years: list[str]


@dataclass
class Theta:
    beta: np.ndarray
    state_effect: np.ndarray
    year_effect: np.ndarray
    log_sigma_state: float
    log_sigma_year: float
    log_kappa: float

    def copy(self) -> "Theta":
        return Theta(
            beta=self.beta.copy(),
            state_effect=self.state_effect.copy(),
            year_effect=self.year_effect.copy(),
            log_sigma_state=float(self.log_sigma_state),
            log_sigma_year=float(self.log_sigma_year),
            log_kappa=float(self.log_kappa),
        )


def nb2_logpmf(y: np.ndarray | float, mu: np.ndarray | float, kappa: float) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    kappa = float(kappa)
    mu = np.clip(mu, 1e-12, np.inf)
    return (
        gammaln(y + kappa)
        - gammaln(kappa)
        - gammaln(y + 1.0)
        + kappa * (np.log(kappa) - np.log(kappa + mu))
        + y * (np.log(mu) - np.log(kappa + mu))
    )


def make_design(frame: pd.DataFrame, *, model: str = "primary") -> Design:
    x = pd.DataFrame(index=frame.index)
    x["Intercept"] = 1.0
    if model == "binary_rucc":
        binary = pd.Categorical(frame["rucc_1_3_vs_4_9"], categories=["RUCC_1_3", "RUCC_4_9"])
        d = pd.get_dummies(binary, prefix="rucc_binary", dtype=float)
        if "rucc_binary_RUCC_4_9" in d:
            x["rucc_binary_RUCC_4_9"] = d["rucc_binary_RUCC_4_9"]
    elif model == "nchs":
        cats = sorted([c for c in frame["rurality_nchs"].dropna().astype(str).unique()])
        if cats:
            ref = cats[0]
            d = pd.get_dummies(pd.Categorical(frame["rurality_nchs"].astype(str), categories=cats), prefix="nchs", dtype=float)
            for col in d.columns:
                if col != f"nchs_{ref}":
                    x[col] = d[col]
    else:
        rural = pd.Categorical(frame["primary_rurality"], categories=RURAL_ORDER)
        d = pd.get_dummies(rural, prefix="primary_rurality", dtype=float)
        for col in d.columns:
            if col != "primary_rurality_metro_large":
                x[col] = d[col]

    if model not in {"rurality_only", "binary_rucc_no_svi"}:
        svi = pd.Categorical(frame["svi_quartile"], categories=SVI_ORDER)
        svi_d = pd.get_dummies(svi, prefix="svi_quartile", dtype=float)
        for col in svi_d.columns:
            if col != "svi_quartile_Q1_lowest":
                x[col] = svi_d[col]

    x["z_pct_age65"] = pd.to_numeric(frame["z_pct_age65"], errors="coerce").fillna(0.0)
    x["z_pct_male"] = pd.to_numeric(frame["z_pct_male"], errors="coerce").fillna(0.0)
    x = x.fillna(0.0)
    states = sorted(frame["state_fips"].astype(str).unique())
    years = sorted(frame["year"].astype(str).unique())
    state_map = {state: idx for idx, state in enumerate(states)}
    year_map = {year: idx for idx, year in enumerate(years)}
    return Design(
        x=x.to_numpy(dtype=float),
        columns=list(x.columns),
        offset=np.log(pd.to_numeric(frame["population"], errors="coerce").clip(lower=1).to_numpy(dtype=float)),
        state_index=frame["state_fips"].astype(str).map(state_map).to_numpy(dtype=int),
        year_index=frame["year"].astype(str).map(year_map).to_numpy(dtype=int),
        states=states,
        years=years,
    )


def crude_intercept_prior(frame: pd.DataFrame) -> float:
    deaths = float(frame.drop_duplicates("year")["q003_national_year_total"].sum())
    exposure = float(pd.to_numeric(frame["population"], errors="coerce").sum())
    return np.log(max(deaths / exposure, 1e-12))


def linear_predictor(theta: Theta, design: Design) -> np.ndarray:
    state = theta.state_effect - theta.state_effect.mean()
    year = theta.year_effect - theta.year_effect.mean()
    return design.offset + design.x @ theta.beta + state[design.state_index] + year[design.year_index]


def mu(theta: Theta, design: Design) -> np.ndarray:
    return np.exp(np.clip(linear_predictor(theta, design), -30, 30))


def log_likelihood(y: np.ndarray, theta: Theta, design: Design) -> float:
    return float(nb2_logpmf(y, mu(theta, design), np.exp(theta.log_kappa)).sum())


def log_prior(theta: Theta, *, intercept_mean: float) -> float:
    beta = theta.beta
    lp = -0.5 * ((beta[0] - intercept_mean) / 5.0) ** 2 - np.log(5.0)
    if len(beta) > 1:
        lp += float((-0.5 * (beta[1:] / 1.5) ** 2 - np.log(1.5)).sum())
    sigma_state = np.exp(theta.log_sigma_state)
    sigma_year = np.exp(theta.log_sigma_year)
    if sigma_state <= 0 or sigma_year <= 0:
        return -np.inf
    state = theta.state_effect - theta.state_effect.mean()
    year = theta.year_effect - theta.year_effect.mean()
    # The effects live on sum-to-zero subspaces of dimensions S-1 and T-1.
    # Counting S or T Gaussian normalizers would add an unintended -log(sigma)
    # term and over-shrink the corresponding hierarchical scale.
    lp += centered_normal_log_density(state, sigma_state)
    lp += centered_normal_log_density(year, sigma_year)
    # HalfNormal(1) on sigma with Jacobian from log sigma.
    lp += -0.5 * sigma_state**2 + theta.log_sigma_state
    lp += -0.5 * sigma_year**2 + theta.log_sigma_year
    lp += -0.5 * ((theta.log_kappa - np.log(10.0)) / 1.5) ** 2 - np.log(1.5)
    return float(lp)


def log_posterior_theta(y: np.ndarray, theta: Theta, design: Design, *, intercept_mean: float) -> float:
    prior = log_prior(theta, intercept_mean=intercept_mean)
    if not np.isfinite(prior):
        return -np.inf
    return prior + log_likelihood(y, theta, design)


def initialize_theta(frame: pd.DataFrame, y: np.ndarray, design: Design) -> Theta:
    try:
        import statsmodels.api as sm

        model = sm.GLM(
            y.astype(float),
            design.x,
            family=sm.families.NegativeBinomial(alpha=1.0),
            offset=design.offset,
        )
        res = model.fit(maxiter=100)
        beta = np.asarray(res.params, dtype=float)
        if len(beta) != design.x.shape[1] or not np.all(np.isfinite(beta)):
            raise ValueError("bad GLM beta")
    except Exception:
        beta = np.zeros(design.x.shape[1], dtype=float)
        beta[0] = crude_intercept_prior(frame)
    state_effect = np.zeros(len(design.states), dtype=float)
    year_effect = np.zeros(len(design.years), dtype=float)
    fitted = np.exp(np.clip(design.offset + design.x @ beta, -30, 30))
    ratio = np.var(y - fitted) / max(np.mean(fitted), 1e-6)
    if not np.isfinite(ratio) or ratio <= 0:
        kappa = 10.0
    else:
        kappa = float(np.clip(10.0 / max(ratio, 0.5), 0.5, 50.0))
    return Theta(
        beta=beta,
        state_effect=state_effect,
        year_effect=year_effect,
        log_sigma_state=np.log(0.2),
        log_sigma_year=np.log(0.2),
        log_kappa=np.log(kappa),
    )


def term_to_label(term: str) -> str:
    return {
        "primary_rurality_metro_other": "metro_other vs metro_large",
        "primary_rurality_nonmetro_adjacent": "nonmetro_adjacent vs metro_large",
        "primary_rurality_nonmetro_nonadjacent": "nonmetro_nonadjacent vs metro_large",
        "svi_quartile_Q2": "SVI Q2 vs Q1",
        "svi_quartile_Q3": "SVI Q3 vs Q1",
        "svi_quartile_Q4_highest": "SVI Q4 vs Q1",
        "z_pct_age65": "pct_age65 coefficient",
        "z_pct_male": "pct_male coefficient",
        "rucc_binary_RUCC_4_9": "RUCC 4-9 vs RUCC 1-3",
    }.get(term, term)
