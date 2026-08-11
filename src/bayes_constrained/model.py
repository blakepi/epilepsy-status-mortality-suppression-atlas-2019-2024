from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Mapping

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


@dataclass(frozen=True)
class PriorSpecification:
    """Complete prior profile for the constrained negative-binomial model.

    The default values reproduce the corrected primary target. Alternative
    profiles are activated explicitly by sensitivity runners and are recorded in
    resolved configuration files; they never silently alter the primary model.
    """

    intercept_sd: float = 5.0
    nonintercept_beta_sd: float = 1.5
    state_scale_halfnormal_sd: float = 1.0
    year_scale_halfnormal_sd: float = 1.0
    log_kappa_mean: float = float(np.log(10.0))
    log_kappa_sd: float = 1.5
    name: str = "default"

    def __post_init__(self) -> None:
        scales = {
            "intercept_sd": self.intercept_sd,
            "nonintercept_beta_sd": self.nonintercept_beta_sd,
            "state_scale_halfnormal_sd": self.state_scale_halfnormal_sd,
            "year_scale_halfnormal_sd": self.year_scale_halfnormal_sd,
            "log_kappa_sd": self.log_kappa_sd,
        }
        invalid = {
            key: value
            for key, value in scales.items()
            if not np.isfinite(value) or float(value) <= 0
        }
        if invalid:
            raise ValueError(f"Prior scales must be finite and positive: {invalid}")
        if not np.isfinite(self.log_kappa_mean):
            raise ValueError("log_kappa_mean must be finite")

    def to_dict(self) -> dict[str, float | str]:
        return {
            "name": self.name,
            "intercept_sd": float(self.intercept_sd),
            "nonintercept_beta_sd": float(self.nonintercept_beta_sd),
            "state_scale_halfnormal_sd": float(
                self.state_scale_halfnormal_sd
            ),
            "year_scale_halfnormal_sd": float(self.year_scale_halfnormal_sd),
            "log_kappa_mean": float(self.log_kappa_mean),
            "log_kappa_sd": float(self.log_kappa_sd),
        }


DEFAULT_PRIOR_SPECIFICATION = PriorSpecification()
_ACTIVE_PRIOR_SPECIFICATION: PriorSpecification | None = None


def prior_specification_from_mapping(
    mapping: Mapping[str, object] | None,
    *,
    name: str | None = None,
) -> PriorSpecification:
    """Build a prior profile from either manuscript or config-style keys."""

    values = dict(mapping or {})

    def get(*keys: str, default: float) -> float:
        for key in keys:
            if key in values and values[key] is not None:
                return float(values[key])
        return float(default)

    profile_name = str(
        name
        if name is not None
        else values.get("prior_profile", values.get("name", "default"))
    )
    return PriorSpecification(
        name=profile_name,
        intercept_sd=get(
            "intercept_sd",
            "intercept_prior_sd",
            default=DEFAULT_PRIOR_SPECIFICATION.intercept_sd,
        ),
        nonintercept_beta_sd=get(
            "nonintercept_beta_sd",
            "fixed_effect_prior_sd",
            default=DEFAULT_PRIOR_SPECIFICATION.nonintercept_beta_sd,
        ),
        state_scale_halfnormal_sd=get(
            "state_scale_halfnormal_sd",
            "sigma_state_prior_sd",
            default=DEFAULT_PRIOR_SPECIFICATION.state_scale_halfnormal_sd,
        ),
        year_scale_halfnormal_sd=get(
            "year_scale_halfnormal_sd",
            "sigma_year_prior_sd",
            default=DEFAULT_PRIOR_SPECIFICATION.year_scale_halfnormal_sd,
        ),
        log_kappa_mean=get(
            "log_kappa_mean",
            "log_kappa_prior_mean",
            default=DEFAULT_PRIOR_SPECIFICATION.log_kappa_mean,
        ),
        log_kappa_sd=get(
            "log_kappa_sd",
            "log_kappa_prior_sd",
            default=DEFAULT_PRIOR_SPECIFICATION.log_kappa_sd,
        ),
    )


def active_prior_specification() -> PriorSpecification:
    return _ACTIVE_PRIOR_SPECIFICATION or DEFAULT_PRIOR_SPECIFICATION


@contextmanager
def use_prior_specification(
    specification: PriorSpecification,
) -> Iterator[PriorSpecification]:
    """Temporarily activate a recorded prior profile in the current process.

    Production and sensitivity chains run in separate processes. A context-local
    process override therefore permits the existing validated sampler to target
    an alternative prior without hidden environment variables or duplicated
    transition code. The previous profile is restored even after an exception.
    """

    global _ACTIVE_PRIOR_SPECIFICATION
    previous = _ACTIVE_PRIOR_SPECIFICATION
    _ACTIVE_PRIOR_SPECIFICATION = specification
    try:
        yield specification
    finally:
        _ACTIVE_PRIOR_SPECIFICATION = previous


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


def nb2_logpmf(
    y: np.ndarray | float,
    mu: np.ndarray | float,
    kappa: float,
) -> np.ndarray:
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
        binary = pd.Categorical(
            frame["rucc_1_3_vs_4_9"],
            categories=["RUCC_1_3", "RUCC_4_9"],
        )
        d = pd.get_dummies(binary, prefix="rucc_binary", dtype=float)
        if "rucc_binary_RUCC_4_9" in d:
            x["rucc_binary_RUCC_4_9"] = d["rucc_binary_RUCC_4_9"]
    elif model == "nchs":
        cats = sorted(
            [
                category
                for category in frame["rurality_nchs"]
                .dropna()
                .astype(str)
                .unique()
            ]
        )
        if cats:
            ref = cats[0]
            d = pd.get_dummies(
                pd.Categorical(
                    frame["rurality_nchs"].astype(str),
                    categories=cats,
                ),
                prefix="nchs",
                dtype=float,
            )
            for column in d.columns:
                if column != f"nchs_{ref}":
                    x[column] = d[column]
    else:
        rural = pd.Categorical(frame["primary_rurality"], categories=RURAL_ORDER)
        d = pd.get_dummies(rural, prefix="primary_rurality", dtype=float)
        for column in d.columns:
            if column != "primary_rurality_metro_large":
                x[column] = d[column]

    if model not in {"rurality_only", "binary_rucc_no_svi"}:
        svi = pd.Categorical(frame["svi_quartile"], categories=SVI_ORDER)
        svi_d = pd.get_dummies(svi, prefix="svi_quartile", dtype=float)
        for column in svi_d.columns:
            if column != "svi_quartile_Q1_lowest":
                x[column] = svi_d[column]

    x["z_pct_age65"] = pd.to_numeric(
        frame["z_pct_age65"],
        errors="coerce",
    ).fillna(0.0)
    x["z_pct_male"] = pd.to_numeric(
        frame["z_pct_male"],
        errors="coerce",
    ).fillna(0.0)
    x = x.fillna(0.0)
    states = sorted(frame["state_fips"].astype(str).unique())
    years = sorted(frame["year"].astype(str).unique())
    state_map = {state: index for index, state in enumerate(states)}
    year_map = {year: index for index, year in enumerate(years)}
    return Design(
        x=x.to_numpy(dtype=float),
        columns=list(x.columns),
        offset=np.log(
            pd.to_numeric(frame["population"], errors="coerce")
            .clip(lower=1)
            .to_numpy(dtype=float)
        ),
        state_index=frame["state_fips"].astype(str).map(state_map).to_numpy(dtype=int),
        year_index=frame["year"].astype(str).map(year_map).to_numpy(dtype=int),
        states=states,
        years=years,
    )


def crude_intercept_prior(frame: pd.DataFrame) -> float:
    deaths = float(
        frame.drop_duplicates("year")["q003_national_year_total"].sum()
    )
    exposure = float(pd.to_numeric(frame["population"], errors="coerce").sum())
    return np.log(max(deaths / exposure, 1e-12))


def linear_predictor(theta: Theta, design: Design) -> np.ndarray:
    state = theta.state_effect - theta.state_effect.mean()
    year = theta.year_effect - theta.year_effect.mean()
    return (
        design.offset
        + design.x @ theta.beta
        + state[design.state_index]
        + year[design.year_index]
    )


def mu(theta: Theta, design: Design) -> np.ndarray:
    return np.exp(np.clip(linear_predictor(theta, design), -30, 30))


def log_likelihood(y: np.ndarray, theta: Theta, design: Design) -> float:
    return float(
        nb2_logpmf(y, mu(theta, design), np.exp(theta.log_kappa)).sum()
    )


def log_prior(
    theta: Theta,
    *,
    intercept_mean: float,
    prior: PriorSpecification | None = None,
) -> float:
    specification = prior or active_prior_specification()
    beta = theta.beta
    lp = (
        -0.5
        * ((beta[0] - intercept_mean) / specification.intercept_sd) ** 2
        - np.log(specification.intercept_sd)
    )
    if len(beta) > 1:
        lp += float(
            (
                -0.5
                * (beta[1:] / specification.nonintercept_beta_sd) ** 2
                - np.log(specification.nonintercept_beta_sd)
            ).sum()
        )
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
    # Half-normal scale priors on sigma, including the log-sigma Jacobian.
    lp += (
        -0.5
        * (sigma_state / specification.state_scale_halfnormal_sd) ** 2
        - np.log(specification.state_scale_halfnormal_sd)
        + theta.log_sigma_state
    )
    lp += (
        -0.5
        * (sigma_year / specification.year_scale_halfnormal_sd) ** 2
        - np.log(specification.year_scale_halfnormal_sd)
        + theta.log_sigma_year
    )
    lp += (
        -0.5
        * (
            (theta.log_kappa - specification.log_kappa_mean)
            / specification.log_kappa_sd
        )
        ** 2
        - np.log(specification.log_kappa_sd)
    )
    return float(lp)


def log_posterior_theta(
    y: np.ndarray,
    theta: Theta,
    design: Design,
    *,
    intercept_mean: float,
    prior: PriorSpecification | None = None,
) -> float:
    prior_density = log_prior(
        theta,
        intercept_mean=intercept_mean,
        prior=prior,
    )
    if not np.isfinite(prior_density):
        return -np.inf
    return prior_density + log_likelihood(y, theta, design)


def initialize_theta(frame: pd.DataFrame, y: np.ndarray, design: Design) -> Theta:
    try:
        import statsmodels.api as sm

        model = sm.GLM(
            y.astype(float),
            design.x,
            family=sm.families.NegativeBinomial(alpha=1.0),
            offset=design.offset,
        )
        result = model.fit(maxiter=100)
        beta = np.asarray(result.params, dtype=float)
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
        "primary_rurality_nonmetro_adjacent": (
            "nonmetro_adjacent vs metro_large"
        ),
        "primary_rurality_nonmetro_nonadjacent": (
            "nonmetro_nonadjacent vs metro_large"
        ),
        "svi_quartile_Q2": "SVI Q2 vs Q1",
        "svi_quartile_Q3": "SVI Q3 vs Q1",
        "svi_quartile_Q4_highest": "SVI Q4 vs Q1",
        "z_pct_age65": "pct_age65 coefficient",
        "z_pct_male": "pct_male coefficient",
        "rucc_binary_RUCC_4_9": "RUCC 4-9 vs RUCC 1-3",
    }.get(term, term)
