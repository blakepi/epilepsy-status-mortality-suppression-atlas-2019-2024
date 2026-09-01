from __future__ import annotations

import numpy as np
import pandas as pd


IRR_PREFIXES = ("primary_rurality_", "svi_quartile_", "rucc_binary_")


def normalized_centered_prior_weights(wide_draws: pd.DataFrame) -> np.ndarray:
    """Importance weights mapping the archived target to corrected subspace priors.

    The v1.1.1 state and year Gaussian normalizers each contain one extra
    factor of 1/sigma. The corrected joint posterior is therefore proportional
    to the archived joint posterior times sigma_state * sigma_year.
    """

    required = {"sigma_state", "sigma_year"}
    missing = required - set(wide_draws.columns)
    if missing:
        raise ValueError(f"Missing scale parameters required for reweighting: {sorted(missing)}")
    raw = (
        pd.to_numeric(wide_draws["sigma_state"], errors="raise").to_numpy(dtype=float)
        * pd.to_numeric(wide_draws["sigma_year"], errors="raise").to_numpy(dtype=float)
    )
    if not np.isfinite(raw).all() or np.any(raw <= 0):
        raise ValueError("Importance weights must be finite and strictly positive.")
    return raw / raw.sum()


def weighted_quantile(values: np.ndarray, weights: np.ndarray, probabilities: list[float]) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    cumulative = np.cumsum(sorted_weights)
    cumulative /= cumulative[-1]
    return np.interp(np.asarray(probabilities, dtype=float), cumulative, sorted_values)


def importance_effective_sample_size(weights: np.ndarray) -> float:
    normalized = np.asarray(weights, dtype=float)
    normalized /= normalized.sum()
    return float(1.0 / np.square(normalized).sum())


def reweighted_parameter_summary(long_draws: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    required = {"chain", "draw", "parameter", "value"}
    missing = required - set(long_draws.columns)
    if missing:
        raise ValueError(f"Parameter draws missing required columns: {sorted(missing)}")
    wide = long_draws.pivot(index=["chain", "draw"], columns="parameter", values="value").sort_index()
    weights = normalized_centered_prior_weights(wide)
    rows: list[dict[str, object]] = []

    for parameter in wide.columns:
        values = wide[parameter].to_numpy(dtype=float)
        report_values = np.exp(values) if parameter.startswith(IRR_PREFIXES) else values
        unweighted = np.quantile(report_values, [0.025, 0.5, 0.975])
        weighted = weighted_quantile(report_values, weights, [0.025, 0.5, 0.975])
        rows.append(
            {
                "parameter": parameter,
                "scale": "mortality_rate_ratio" if parameter.startswith(IRR_PREFIXES) else "model_parameter",
                "v111_mean": float(report_values.mean()),
                "v111_median": float(unweighted[1]),
                "v111_lower_95": float(unweighted[0]),
                "v111_upper_95": float(unweighted[2]),
                "corrected_prior_reweighted_mean": float(np.sum(weights * report_values)),
                "corrected_prior_reweighted_median": float(weighted[1]),
                "corrected_prior_reweighted_lower_95": float(weighted[0]),
                "corrected_prior_reweighted_upper_95": float(weighted[2]),
                "median_absolute_shift": float(weighted[1] - unweighted[1]),
                "median_relative_shift_percent": float((weighted[1] / unweighted[1] - 1.0) * 100.0) if unweighted[1] != 0 else np.nan,
            }
        )

    diagnostics = {
        "draws": float(len(wide)),
        "importance_effective_sample_size": importance_effective_sample_size(weights),
        "importance_ess_fraction": importance_effective_sample_size(weights) / len(wide),
        "maximum_normalized_weight": float(weights.max()),
        "minimum_normalized_weight": float(weights.min()),
        "weight_coefficient_of_variation": float(weights.std(ddof=1) / weights.mean()),
    }
    return pd.DataFrame(rows), diagnostics
