from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.model import (  # noqa: E402
    DEFAULT_PRIOR_SPECIFICATION,
    PriorSpecification,
    Theta,
    active_prior_specification,
    log_prior,
    prior_specification_from_mapping,
    use_prior_specification,
)


def theta() -> Theta:
    return Theta(
        beta=np.array([-10.0, 0.25, -0.15]),
        state_effect=np.array([-0.20, 0.05, 0.15]),
        year_effect=np.array([-0.10, 0.10]),
        log_sigma_state=float(np.log(0.25)),
        log_sigma_year=float(np.log(0.15)),
        log_kappa=float(np.log(8.0)),
    )


def test_default_profile_reproduces_implicit_default_log_prior() -> None:
    value_implicit = log_prior(theta(), intercept_mean=-10.2)
    value_explicit = log_prior(
        theta(),
        intercept_mean=-10.2,
        prior=DEFAULT_PRIOR_SPECIFICATION,
    )
    assert value_implicit == pytest.approx(value_explicit, abs=1e-12)


def test_config_style_mapping_builds_complete_profile() -> None:
    profile = prior_specification_from_mapping(
        {
            "prior_profile": "broader",
            "intercept_prior_sd": 10.0,
            "fixed_effect_prior_sd": 3.0,
            "sigma_state_prior_sd": 2.0,
            "sigma_year_prior_sd": 2.5,
            "log_kappa_prior_mean": 1.5,
            "log_kappa_prior_sd": 2.5,
        }
    )
    assert profile.name == "broader"
    assert profile.intercept_sd == 10.0
    assert profile.nonintercept_beta_sd == 3.0
    assert profile.state_scale_halfnormal_sd == 2.0
    assert profile.year_scale_halfnormal_sd == 2.5
    assert profile.log_kappa_mean == 1.5
    assert profile.log_kappa_sd == 2.5


def test_alternative_profiles_change_target_density() -> None:
    broader = PriorSpecification(
        name="broader",
        intercept_sd=10.0,
        nonintercept_beta_sd=3.0,
        state_scale_halfnormal_sd=2.0,
        year_scale_halfnormal_sd=2.0,
        log_kappa_mean=float(np.log(10.0)),
        log_kappa_sd=2.5,
    )
    regularizing = PriorSpecification(
        name="regularizing",
        intercept_sd=2.5,
        nonintercept_beta_sd=0.75,
        state_scale_halfnormal_sd=0.5,
        year_scale_halfnormal_sd=0.5,
        log_kappa_mean=float(np.log(10.0)),
        log_kappa_sd=0.75,
    )
    default_value = log_prior(
        theta(),
        intercept_mean=-10.2,
        prior=DEFAULT_PRIOR_SPECIFICATION,
    )
    broader_value = log_prior(theta(), intercept_mean=-10.2, prior=broader)
    regularizing_value = log_prior(theta(), intercept_mean=-10.2, prior=regularizing)
    assert np.isfinite([default_value, broader_value, regularizing_value]).all()
    assert len({round(default_value, 10), round(broader_value, 10), round(regularizing_value, 10)}) == 3


def test_prior_context_is_scoped_and_restored() -> None:
    baseline = active_prior_specification()
    profile = PriorSpecification(name="temporary", nonintercept_beta_sd=2.25)
    with use_prior_specification(profile):
        assert active_prior_specification() == profile
        contextual = log_prior(theta(), intercept_mean=-10.2)
        explicit = log_prior(theta(), intercept_mean=-10.2, prior=profile)
        assert contextual == pytest.approx(explicit, abs=1e-12)
    assert active_prior_specification() == baseline


def test_prior_context_restores_after_exception() -> None:
    baseline = active_prior_specification()
    profile = PriorSpecification(name="temporary", intercept_sd=7.0)
    with pytest.raises(RuntimeError):
        with use_prior_specification(profile):
            raise RuntimeError("intentional")
    assert active_prior_specification() == baseline


def test_invalid_prior_scales_fail_closed() -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        PriorSpecification(intercept_sd=0.0)
    with pytest.raises(ValueError, match="finite and positive"):
        PriorSpecification(log_kappa_sd=float("nan"))
