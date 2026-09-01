from __future__ import annotations

import numpy as np

from .model import DEFAULT_LIKELIHOOD_FAMILY, count_logpmf


def feasible_amplitudes(
    y: np.ndarray,
    indices: np.ndarray,
    direction: np.ndarray,
    *,
    lower: np.ndarray,
    upper: np.ndarray,
    county_code: np.ndarray,
    period_total: np.ndarray,
    period_lower: np.ndarray,
    period_upper: np.ndarray,
) -> np.ndarray:
    """Return every integer amplitude allowed along a count-move direction."""

    indices = np.asarray(indices, dtype=int)
    direction = np.asarray(direction, dtype=int)
    if indices.ndim != 1 or direction.ndim != 1 or len(indices) != len(direction):
        raise ValueError("indices and direction must be one-dimensional arrays of equal length")
    if not len(indices):
        return np.asarray([0], dtype=int)
    if np.any(direction == 0):
        raise ValueError("heat-bath direction entries must be nonzero")

    minimum = -10**9
    maximum = 10**9
    current = np.asarray(y[indices], dtype=int)
    for value, low, high, coefficient in zip(
        current,
        lower[indices],
        upper[indices],
        direction,
    ):
        if coefficient > 0:
            minimum = max(minimum, int(np.ceil((int(low) - int(value)) / int(coefficient))))
            maximum = min(maximum, int(np.floor((int(high) - int(value)) / int(coefficient))))
        else:
            minimum = max(minimum, int(np.ceil((int(high) - int(value)) / int(coefficient))))
            maximum = min(maximum, int(np.floor((int(low) - int(value)) / int(coefficient))))
    if minimum > maximum:
        return np.asarray([0], dtype=int)

    affected = np.unique(county_code[indices])
    valid: list[int] = []
    for amplitude in range(minimum, maximum + 1):
        allowed = True
        for county in affected:
            coefficient = int(direction[county_code[indices] == county].sum())
            proposed_total = int(period_total[county]) + amplitude * coefficient
            if proposed_total < int(period_lower[county]) or proposed_total > int(period_upper[county]):
                allowed = False
                break
        if allowed:
            valid.append(int(amplitude))
    if 0 not in valid:
        raise AssertionError("The current state must be a feasible heat-bath amplitude.")
    return np.asarray(valid, dtype=int)


def amplitude_log_weights(
    y: np.ndarray,
    indices: np.ndarray,
    direction: np.ndarray,
    amplitudes: np.ndarray,
    mu_values: np.ndarray,
    kappa: float | None,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> np.ndarray:
    indices = np.asarray(indices, dtype=int)
    direction = np.asarray(direction, dtype=int)
    amplitudes = np.asarray(amplitudes, dtype=int)
    current = np.asarray(y[indices], dtype=int)
    values = current[None, :] + amplitudes[:, None] * direction[None, :]
    return np.asarray(
        [
            float(
                count_logpmf(
                    row,
                    mu_values,
                    likelihood_family=likelihood_family,
                    kappa=kappa,
                ).sum()
            )
            for row in values
        ],
        dtype=float,
    )


def amplitude_probabilities(log_weights: np.ndarray) -> np.ndarray:
    values = np.asarray(log_weights, dtype=float)
    shifted = values - np.max(values)
    probabilities = np.exp(shifted)
    probabilities /= probabilities.sum()
    return probabilities


def sample_amplitude(
    y: np.ndarray,
    indices: np.ndarray,
    direction: np.ndarray,
    amplitudes: np.ndarray,
    mu_values: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> int:
    probabilities = amplitude_probabilities(
        amplitude_log_weights(
            y,
            indices,
            direction,
            amplitudes,
            mu_values,
            kappa,
            likelihood_family=likelihood_family,
        )
    )
    return int(rng.choice(amplitudes, p=probabilities))
