from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose, assert_array_equal
from scipy.stats import poisson

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.exact_validation import (  # noqa: E402
    empirical_count_kernel_frequencies,
    enumerate_feasible_states,
    exact_conditional_probabilities,
    exact_kernel_diagnostics,
    exact_transition_matrix,
    proposal_events,
)
from bayes_constrained.heatbath import (  # noqa: E402
    amplitude_log_weights,
    feasible_amplitudes,
)
from bayes_constrained.model import (  # noqa: E402
    PRIMARY_TERMS,
    Theta,
    count_logpmf,
    log_likelihood,
    log_posterior_theta,
    make_design,
    mu,
    nb2_logpmf,
    normalize_likelihood_family,
    poisson_logpmf,
)
from bayes_constrained import sampler as sampler_module  # noqa: E402
from bayes_constrained.sampler import (  # noqa: E402
    _proposal_scales,
    _theta_to_rows,
    blocked_refresh,
    build_move_state,
    interval_path_transfer,
    load_chain_checkpoint,
    period_interval_transfer,
    run_mcmc_chain_hpc,
    save_chain_checkpoint,
    state_2x2_swap,
    state_cycle_swap,
    state_year_transfer,
)
from bayes_constrained.validation_cases import (  # noqa: E402
    structural_interval_path_frame,
    structural_interval_path_theta,
    structural_six_cycle_frame,
    structural_six_cycle_theta,
)


POISSON = "poisson"
NB2 = "negative_binomial_2"
INTERACTION_COLUMNS = [
    "primary_rurality_metro_other__x__acute_pandemic",
    "primary_rurality_nonmetro_adjacent__x__acute_pandemic",
    "primary_rurality_nonmetro_nonadjacent__x__acute_pandemic",
    "primary_rurality_metro_other__x__later_period",
    "primary_rurality_nonmetro_adjacent__x__later_period",
    "primary_rurality_nonmetro_nonadjacent__x__later_period",
]


def pandemic_frame() -> pd.DataFrame:
    rurality = [
        "metro_other",
        "nonmetro_adjacent",
        "nonmetro_nonadjacent",
        "metro_other",
        "nonmetro_adjacent",
        "nonmetro_nonadjacent",
    ]
    return pd.DataFrame(
        {
            "state_fips": ["01"] * 6,
            "year": ["2019", "2020", "2021", "2022", "2023", "2024"],
            "population": [1000.0] * 6,
            "primary_rurality": rurality,
            "svi_quartile": ["Q1_lowest"] * 6,
            "z_pct_age65": [0.0] * 6,
            "z_pct_male": [0.0] * 6,
        }
    )


def interval_transfer_frame() -> pd.DataFrame:
    frame = structural_six_cycle_frame().copy()
    frame["q001_period_status"] = "suppressed_1_9"
    frame["q001_period_lower"] = 2
    frame["q001_period_upper"] = 4
    return frame


def two_by_two_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for county, rurality in [
        ("01001", "metro_large"),
        ("01003", "metro_other"),
    ]:
        for year in ["2019", "2020"]:
            rows.append(
                {
                    "county_fips": county,
                    "county_name": county,
                    "state_fips": "01",
                    "state_name": "Toy",
                    "year": year,
                    "population": 1000.0,
                    "q002_count_status": "suppressed_1_9",
                    "q002_lower": 1,
                    "q002_upper": 2,
                    "q001_period_status": "exact",
                    "q001_period_lower": 3,
                    "q001_period_upper": 3,
                    "q004_state_year_total": 3,
                    "q003_national_year_total": 3,
                    "primary_rurality": rurality,
                    "svi_quartile": "Q1_lowest",
                    "z_pct_age65": 0.0,
                    "z_pct_male": 0.0,
                }
            )
    frame = pd.DataFrame(rows)
    frame.attrs["grand_total"] = 6
    return frame


def toy_theta(frame: pd.DataFrame) -> Theta:
    design = make_design(frame)
    return Theta(
        beta=np.linspace(-6.5, 0.4, len(design.columns)),
        state_effect=np.zeros(len(design.states)),
        year_effect=np.linspace(-0.2, 0.2, len(design.years)),
        log_sigma_state=np.log(0.2),
        log_sigma_year=np.log(0.2),
        log_kappa=np.log(3.0),
    )


def save_toy_checkpoint(
    path: Path,
    *,
    likelihood_family: str,
) -> None:
    save_chain_checkpoint(
        path,
        y=np.asarray([1, 2]),
        theta=Theta(
            beta=np.asarray([0.0]),
            state_effect=np.asarray([0.0]),
            year_effect=np.asarray([0.0]),
            log_sigma_state=-1.0,
            log_sigma_year=-1.0,
            log_kappa=2.0,
        ),
        rng=np.random.default_rng(123),
        iteration=5,
        saved_draws=0,
        current_lp=-1.0,
        accepted={},
        proposed={},
        param_accept={},
        param_prop={},
        likelihood_family=likelihood_family,
    )


def test_poisson_logpmf_matches_scipy() -> None:
    y = np.arange(8)
    means = np.linspace(0.2, 8.0, 8)
    assert_allclose(poisson_logpmf(y, means), poisson.logpmf(y, means))


def test_likelihood_family_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="Unknown likelihood family"):
        normalize_likelihood_family("quasi_poisson")


@pytest.mark.parametrize("kappa", [None, 0.0, -1.0, np.inf, np.nan])
def test_nb2_dispatch_requires_finite_positive_kappa(kappa: float | None) -> None:
    with pytest.raises(ValueError, match="NB2 requires finite positive kappa"):
        count_logpmf(
            np.asarray([1]),
            np.asarray([2.0]),
            likelihood_family=NB2,
            kappa=kappa,
        )


def test_strict_poisson_posterior_is_kappa_invariant() -> None:
    frame = structural_six_cycle_frame()
    design = make_design(frame, likelihood_family=POISSON)
    y = enumerate_feasible_states(frame)[0]
    first = structural_six_cycle_theta(frame)
    first.log_kappa = -20.0
    second = first.copy()
    second.log_kappa = 20.0
    assert log_posterior_theta(
        y, first, design, intercept_mean=0.0
    ) == log_posterior_theta(y, second, design, intercept_mean=0.0)


def test_poisson_sampler_omits_kappa_proposal_and_draw_row() -> None:
    frame = structural_six_cycle_frame()
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame, likelihood_family=POISSON)
    assert "log_kappa" not in _proposal_scales(
        theta, likelihood_family=design.likelihood_family
    )
    rows = _theta_to_rows(
        theta, design, chain=1, draw=1, iteration=10
    )
    assert "kappa" not in {row["parameter"] for row in rows}


def test_poisson_heatbath_ratio_equals_full_target_ratio() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame, likelihood_family=POISSON)
    indices = np.flatnonzero(states[1] != states[0])
    direction = states[1, indices] - states[0, indices]
    weights = amplitude_log_weights(
        states[0],
        indices,
        direction,
        np.asarray([0, 1]),
        mu(theta, design)[indices],
        None,
        likelihood_family=design.likelihood_family,
    )
    assert weights[1] - weights[0] == pytest.approx(
        log_likelihood(states[1], theta, design)
        - log_likelihood(states[0], theta, design),
        abs=1e-12,
    )


def test_exact_poisson_kernel_has_detailed_balance_and_stationarity() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame, likelihood_family=POISSON)
    probabilities = exact_conditional_probabilities(states, theta, design)
    transition = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "interval_path_transfer": 0.0,
            "swap_2x2": 0.0,
            "cycle_swap": 1.0,
        },
    )
    diagnostics = exact_kernel_diagnostics(probabilities, transition)
    assert diagnostics.row_sum_error < 1e-12
    assert diagnostics.stationarity_error < 1e-12
    assert diagnostics.detailed_balance_error < 1e-12
    assert diagnostics.strongly_connected_components == 1


def test_empirical_poisson_kernel_matches_exact_probabilities() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame, likelihood_family=POISSON)
    probabilities = exact_conditional_probabilities(states, theta, design)
    empirical = empirical_count_kernel_frequencies(
        states[0],
        states,
        frame,
        theta,
        likelihood_family=POISSON,
        steps=40_000,
        burn_in=2_000,
        seed=20260818,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "interval_path_transfer": 0.0,
            "swap_2x2": 0.0,
            "cycle_swap": 1.0,
        },
    )
    assert_allclose(empirical, probabilities, atol=0.02, rtol=0.0)


def test_default_nb2_exact_probabilities_are_unchanged() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    probabilities = exact_conditional_probabilities(
        states, theta, make_design(frame)
    )
    assert_allclose(
        probabilities,
        np.asarray([0.53319485446001524, 0.46680514553998531]),
        atol=1e-14,
        rtol=0.0,
    )


def test_pandemic_interaction_design_has_exact_six_columns_and_coding() -> None:
    design = make_design(pandemic_frame(), model="pandemic_interaction")
    assert [column for column in design.columns if "__x__" in column] == (
        INTERACTION_COLUMNS
    )
    selected = design.x[
        :, [design.columns.index(column) for column in INTERACTION_COLUMNS]
    ]
    assert_array_equal(
        selected,
        np.asarray(
            [
                [0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 1],
            ],
            dtype=float,
        ),
    )
    assert not any("period" in column for column in design.columns if "__x__" not in column)


def test_pandemic_interaction_rejects_years_outside_2019_through_2024() -> None:
    frame = pandemic_frame()
    frame.loc[0, "year"] = "2025"
    with pytest.raises(ValueError, match="2019 through 2024"):
        make_design(frame, model="pandemic_interaction")


def test_pandemic_interactions_are_not_standalone_primary_terms() -> None:
    assert not set(INTERACTION_COLUMNS).intersection(PRIMARY_TERMS)


def test_poisson_scalar_and_mixed_broadcast_shapes_are_finite() -> None:
    scalar = poisson_logpmf(3, 2.5)
    assert scalar.shape == ()
    assert np.isfinite(scalar)
    assert scalar == pytest.approx(poisson.logpmf(3, 2.5))

    y = np.asarray([[0], [2], [5]])
    means = np.asarray([[0.2, 1.0, 3.5, 8.0]])
    broadcast = poisson_logpmf(y, means)
    assert broadcast.shape == (3, 4)
    assert np.all(np.isfinite(broadcast))
    assert_allclose(broadcast, poisson.logpmf(y, means))
    assert_allclose(
        count_logpmf(y, means, likelihood_family=POISSON),
        broadcast,
    )


def test_nb2_dispatch_matches_direct_nb2_under_mixed_broadcasting() -> None:
    y = np.asarray([[0], [2], [5]])
    means = np.asarray([[0.2, 1.0, 3.5, 8.0]])
    dispatched = count_logpmf(
        y,
        means,
        likelihood_family=NB2,
        kappa=3.25,
    )
    direct = nb2_logpmf(y, means, 3.25)
    assert dispatched.shape == (3, 4)
    assert np.all(np.isfinite(dispatched))
    assert_allclose(dispatched, direct, atol=0.0, rtol=0.0)


def move_fixture(move_name: str) -> tuple[pd.DataFrame, Theta]:
    if move_name in {"state_year_transfer", "county_period_exploration"}:
        frame = interval_transfer_frame()
        return frame, structural_six_cycle_theta(frame)
    if move_name == "interval_path_transfer":
        frame = structural_interval_path_frame()
        return frame, structural_interval_path_theta(frame)
    if move_name == "swap_2x2":
        frame = two_by_two_frame()
        return frame, toy_theta(frame)
    frame = structural_six_cycle_frame()
    return frame, structural_six_cycle_theta(frame)


@pytest.mark.parametrize(
    "move_name",
    [
        "state_year_transfer",
        "county_period_exploration",
        "interval_path_transfer",
        "swap_2x2",
        "cycle_swap",
    ],
)
def test_each_move_line_has_poisson_weights_equal_to_full_target(
    move_name: str,
) -> None:
    frame, theta = move_fixture(move_name)
    states = enumerate_feasible_states(frame)
    source = states[0]
    move = build_move_state(frame, source.copy())
    selected: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    for event in proposal_events(move, move_name):
        if event.indices is None or event.delta is None:
            continue
        indices = np.asarray(event.indices, dtype=int)
        direction = np.asarray(event.delta, dtype=int)
        amplitudes = feasible_amplitudes(
            source,
            indices,
            direction,
            lower=move.lower,
            upper=move.upper,
            county_code=move.county_code,
            period_total=move.period_total,
            period_lower=move.period_lower,
            period_upper=move.period_upper,
        )
        if len(amplitudes) > 1:
            selected = indices, direction, amplitudes
            break
    assert selected is not None, f"No nontrivial {move_name} line in fixture"
    indices, direction, amplitudes = selected
    design = make_design(frame, likelihood_family=POISSON)
    local = amplitude_log_weights(
        source,
        indices,
        direction,
        amplitudes,
        mu(theta, design)[indices],
        None,
        likelihood_family=POISSON,
    )
    full = []
    for amplitude in amplitudes:
        proposed = source.copy()
        proposed[indices] += int(amplitude) * direction
        full.append(log_likelihood(proposed, theta, design))
    zero = int(np.flatnonzero(amplitudes == 0)[0])
    assert_allclose(
        local - local[zero],
        np.asarray(full) - full[zero],
        atol=1e-12,
        rtol=0.0,
    )


@pytest.mark.parametrize(
    ("move_name", "move_function"),
    [
        ("state_year_transfer", state_year_transfer),
        ("county_period_exploration", period_interval_transfer),
        ("interval_path_transfer", interval_path_transfer),
        ("swap_2x2", state_2x2_swap),
        ("cycle_swap", state_cycle_swap),
    ],
)
def test_each_production_move_propagates_poisson_family(
    move_name: str,
    move_function: object,
) -> None:
    frame, theta = move_fixture(move_name)
    y = enumerate_feasible_states(frame)[0].copy()
    design = make_design(frame, likelihood_family=POISSON)
    move = build_move_state(frame, y)
    kwargs = {"likelihood_family": POISSON}
    if move_name == "cycle_swap":
        kwargs["max_cycle_half_length"] = 6
    result = move_function(  # type: ignore[operator]
        y,
        move,
        mu(theta, design),
        None,
        np.random.default_rng(20260818),
        **kwargs,
    )
    assert isinstance(result, (bool, np.bool_))


def test_blocked_refresh_propagates_poisson_family() -> None:
    frame = structural_six_cycle_frame()
    theta = structural_six_cycle_theta(frame)
    y = enumerate_feasible_states(frame)[0].copy()
    design = make_design(frame, likelihood_family=POISSON)
    accepted = blocked_refresh(
        y,
        build_move_state(frame, y),
        mu(theta, design),
        None,
        np.random.default_rng(20260818),
        attempts=3,
        likelihood_family=POISSON,
    )
    assert 0 <= accepted <= 3


@pytest.mark.parametrize(
    ("stored_family", "requested_family"),
    [(NB2, POISSON), (POISSON, NB2)],
)
def test_checkpoint_rejects_cross_family_load(
    tmp_path: Path,
    stored_family: str,
    requested_family: str,
) -> None:
    path = tmp_path / "checkpoint_iter_000000005.npz"
    save_toy_checkpoint(path, likelihood_family=stored_family)
    with pytest.raises(ValueError, match="likelihood family mismatch"):
        load_chain_checkpoint(
            path,
            expected_likelihood_family=requested_family,
        )


def test_legacy_checkpoint_defaults_only_to_nb2(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint_iter_000000005.npz"
    save_toy_checkpoint(path, likelihood_family=NB2)
    with np.load(path, allow_pickle=True) as stored:
        legacy = {
            key: stored[key]
            for key in stored.files
            if key != "likelihood_family"
        }
    np.savez_compressed(path, **legacy)
    assert load_chain_checkpoint(
        path, expected_likelihood_family=NB2
    )["likelihood_family"] == NB2
    with pytest.raises(ValueError, match="likelihood family mismatch"):
        load_chain_checkpoint(path, expected_likelihood_family=POISSON)


@pytest.mark.parametrize(
    ("stored_family", "requested_family"),
    [(NB2, POISSON), (POISSON, NB2)],
)
def test_completed_chain_reuse_rejects_cross_family_status(
    tmp_path: Path,
    stored_family: str,
    requested_family: str,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "run": {
                    "likelihood_family": requested_family,
                    "random_seeds": [123],
                }
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    chain_dir = out_dir / "chains" / "chain_01"
    chain_dir.mkdir(parents=True)
    (chain_dir / "chain_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "likelihood_family": stored_family,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="likelihood family mismatch"):
        run_mcmc_chain_hpc(
            structural_six_cycle_frame(),
            config_path=config_path,
            mode="production",
            chain_id=1,
            out_dir=out_dir,
        )


def test_legacy_completed_status_is_reusable_only_as_nb2(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"run": {"random_seeds": [123]}}), encoding="utf-8"
    )
    out_dir = tmp_path / "out"
    chain_dir = out_dir / "chains" / "chain_01"
    chain_dir.mkdir(parents=True)
    legacy_status = {"status": "completed", "saved_draws": 10}
    (chain_dir / "chain_status.json").write_text(
        json.dumps(legacy_status), encoding="utf-8"
    )
    reused = run_mcmc_chain_hpc(
        structural_six_cycle_frame(),
        config_path=config_path,
        mode="production",
        chain_id=1,
        out_dir=out_dir,
    )
    assert reused["likelihood_family"] == NB2


def hpc_test_config(likelihood_family: str) -> dict[str, object]:
    return {
        "run": {
            "likelihood_family": likelihood_family,
            "random_seeds": [123],
            "n_iter": 1,
            "burn_in": 0,
            "thin": 1,
            "max_count_proposals_per_iter": 1,
            "count_move_sweeps_per_iter": 1.0,
            "blocked_refresh_frequency": 1,
            "blocked_refresh_attempts": 1,
            "move_weights": {
                "state_year_transfer": 1.0,
                "county_period_exploration": 0.0,
                "interval_path_transfer": 0.0,
                "swap_2x2": 0.0,
                "cycle_swap": 0.0,
            },
        }
    }


def test_hpc_resume_rejects_cross_family_checkpoint(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(hpc_test_config(POISSON)), encoding="utf-8"
    )
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_path = checkpoint_dir / "checkpoint_iter_000000005.npz"
    save_toy_checkpoint(checkpoint_path, likelihood_family=NB2)
    with pytest.raises(ValueError, match="likelihood family mismatch"):
        run_mcmc_chain_hpc(
            structural_six_cycle_frame(),
            config_path=config_path,
            mode="production",
            chain_id=1,
            out_dir=tmp_path / "out",
            checkpoint_dir=checkpoint_dir,
            resume=True,
        )


def test_hpc_dispatch_loop_propagates_poisson_and_records_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = structural_six_cycle_frame()
    initial = tmp_path / "initial.parquet"
    pd.DataFrame(
        {"latent_count": enumerate_feasible_states(frame)[0]}
    ).to_parquet(initial, index=False)
    monkeypatch.setattr(
        sampler_module, "_initial_allocation_path", lambda _chain_id: initial
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(hpc_test_config(POISSON)), encoding="utf-8"
    )
    out_dir = tmp_path / "out"
    status = run_mcmc_chain_hpc(
        frame,
        config_path=config_path,
        mode="production",
        chain_id=1,
        out_dir=out_dir,
        checkpoint_every=1,
        model_name="rurality_only",
    )
    assert status["status"] == "completed"
    assert status["likelihood_family"] == POISSON
    chain_dir = out_dir / "chains" / "chain_01"
    parameters = pd.read_parquet(chain_dir / "draws_params.parquet")
    assert "kappa" not in set(parameters["parameter"])
    checkpoint = load_chain_checkpoint(
        chain_dir / "checkpoints" / "checkpoint_iter_000000001.npz",
        expected_likelihood_family=POISSON,
    )
    assert checkpoint["likelihood_family"] == POISSON
