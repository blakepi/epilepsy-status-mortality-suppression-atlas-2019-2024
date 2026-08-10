from __future__ import annotations

import numpy as np


def centered_normal_log_density(values: np.ndarray, sigma: float) -> float:
    """Log density kernel for a zero-sum Gaussian random-effect vector.

    ``values`` is interpreted with respect to Lebesgue measure on the
    ``n - 1`` dimensional subspace whose entries sum to zero. Constants that
    do not depend on ``values`` or ``sigma`` are omitted.

    The dimension matters: using ``n`` rather than ``n - 1`` adds an
    unintended ``-log(sigma)`` term to the target density and over-shrinks the
    random-effect scale.
    """

    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError("values must be a one-dimensional random-effect vector")
    sigma = float(sigma)
    if not np.isfinite(sigma) or sigma <= 0:
        return -np.inf
    if arr.size == 0:
        return 0.0
    centered = arr - arr.mean()
    dimension = max(int(centered.size) - 1, 0)
    return float(-0.5 * np.square(centered / sigma).sum() - dimension * np.log(sigma))
