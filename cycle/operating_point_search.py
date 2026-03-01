"""
Operating-point search utilities for coupled HTGR+sCO2 solves.

This module performs a deterministic two-stage search:
1) Coarse bounded grid scan over (P_high, P_low, f_recomp)
2) Local refinement around the best coarse candidate
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class SearchBounds:
    """Bounded domain for operating-point search."""

    P_high_min: float = 20e6
    P_high_max: float = 30e6
    P_low_min: float = 7.5e6
    P_low_max: float = 9.0e6
    f_recomp_min: float = 0.25
    f_recomp_max: float = 0.45


@dataclass(frozen=True)
class SearchConfig:
    """Search discretization and scoring settings."""

    bounds: SearchBounds = field(default_factory=SearchBounds)
    n_P_high: int = 4
    n_P_low: int = 4
    n_f_recomp: int = 5
    local_rounds: int = 2
    local_radius_scale: float = 0.5
    top_k: int = 10


@dataclass
class SearchCandidate:
    """Single evaluated operating-point candidate."""

    P_high: float
    P_low: float
    f_recomp: float
    score: float
    converged: bool
    feasible: bool
    iterations: int
    energy_closure_rel: float
    W_net: float
    constraints_failed: List[str]
    margins: Dict[str, float]
    convergence_reason: str


@dataclass
class SearchOutcome:
    """Search result payload."""

    best: SearchCandidate
    ranked: List[SearchCandidate]
    stage: str


def _clip(v: float, v_min: float, v_max: float) -> float:
    return float(np.clip(v, v_min, v_max))


def _candidate_score(result) -> Tuple[float, List[str]]:
    """Penalty-based score for candidate ranking (lower is better)."""
    constraints_failed = [
        name for name, ok in result.feasibility_report.constraints.items() if not ok
    ]

    score = 0.0
    if not result.converged:
        score += 1e6
    if not result.feasible:
        score += 2e5

    score += 5e4 * len(constraints_failed)

    # Penalize specific physical misses.
    margins = result.feasibility_report.margins
    plant_margin = margins.get("energy_residual_plant_margin_rel", margins.get("energy_closure", 0.0))
    if plant_margin < 0:
        score += 1e7 * abs(float(plant_margin))

    t_he_margin = margins.get("T_He_return_margin_K", margins.get("T_He_return", 0.0))
    if t_he_margin < 0:
        score += 2e4 * abs(float(t_he_margin))

    # Prefer positive net output and lower residual for tie-breaks.
    if result.W_net < 0:
        score += 1e5 + 10.0 * abs(result.W_net)
    score += 1e3 * float(result.energy_closure_rel)
    score += max(0.0, 50.0 - result.W_net / 1e6)

    return float(score), constraints_failed


def _evaluate_with_solver(solver, P_high: float, P_low: float, f_recomp: float, initial_guess: Optional[Dict[str, float]]):
    return solver.solve(
        P_high=P_high,
        P_low=P_low,
        f_recomp=f_recomp,
        initial_guess=initial_guess,
        return_trace=False,
        verbose=False,
    )


def _make_candidate(P_high: float, P_low: float, f_recomp: float, result) -> SearchCandidate:
    score, constraints_failed = _candidate_score(result)
    return SearchCandidate(
        P_high=P_high,
        P_low=P_low,
        f_recomp=f_recomp,
        score=score,
        converged=bool(result.converged),
        feasible=bool(result.feasible),
        iterations=int(result.feasibility_report.iterations),
        energy_closure_rel=float(result.energy_closure_rel),
        W_net=float(result.W_net),
        constraints_failed=constraints_failed,
        margins=dict(result.feasibility_report.margins),
        convergence_reason=str(result.convergence_reason),
    )


def _rank(candidates: List[SearchCandidate]) -> List[SearchCandidate]:
    return sorted(
        candidates,
        key=lambda c: (
            0 if c.feasible else 1,
            0 if c.converged else 1,
            c.score,
            abs(c.energy_closure_rel),
            -c.W_net,
        ),
    )


def search_operating_point(
    solver,
    config: Optional[SearchConfig] = None,
    initial_guess: Optional[Dict[str, float]] = None,
    evaluate_fn: Optional[Callable[[float, float, float], object]] = None,
) -> SearchOutcome:
    """
    Search bounded (P_high, P_low, f_recomp) space and return best candidate.

    Args:
        solver: CoupledPlantSolver or compatible object.
        config: Search configuration.
        initial_guess: Optional initial guess passed into solver.
        evaluate_fn: Optional evaluator hook for tests; receives (P_high, P_low, f_recomp).
    """
    cfg = config or SearchConfig()
    bounds = cfg.bounds
    evaluator = evaluate_fn or (
        lambda ph, pl, fr: _evaluate_with_solver(solver, ph, pl, fr, initial_guess)
    )

    p_high_grid = np.linspace(bounds.P_high_min, bounds.P_high_max, cfg.n_P_high)
    p_low_grid = np.linspace(bounds.P_low_min, bounds.P_low_max, cfg.n_P_low)
    f_grid = np.linspace(bounds.f_recomp_min, bounds.f_recomp_max, cfg.n_f_recomp)

    coarse: List[SearchCandidate] = []
    for p_high in p_high_grid:
        for p_low in p_low_grid:
            if p_low >= p_high:
                continue
            for f in f_grid:
                result = evaluator(float(p_high), float(p_low), float(f))
                coarse.append(_make_candidate(float(p_high), float(p_low), float(f), result))

    coarse_ranked = _rank(coarse)
    best = coarse_ranked[0]
    best_stage = "coarse"

    # Local refinement around top candidates.
    refined: List[SearchCandidate] = list(coarse_ranked[: cfg.top_k])
    if cfg.local_rounds > 0:
        p_high_step = (bounds.P_high_max - bounds.P_high_min) / max(cfg.n_P_high - 1, 1)
        p_low_step = (bounds.P_low_max - bounds.P_low_min) / max(cfg.n_P_low - 1, 1)
        f_step = (bounds.f_recomp_max - bounds.f_recomp_min) / max(cfg.n_f_recomp - 1, 1)

        radius_high = p_high_step
        radius_low = p_low_step
        radius_f = f_step

        for _ in range(cfg.local_rounds):
            seeds = _rank(refined)[: min(3, len(refined))]
            next_round: List[SearchCandidate] = []
            for seed in seeds:
                for d_high in (-radius_high, 0.0, radius_high):
                    for d_low in (-radius_low, 0.0, radius_low):
                        for d_f in (-radius_f, 0.0, radius_f):
                            ph = _clip(seed.P_high + d_high, bounds.P_high_min, bounds.P_high_max)
                            pl = _clip(seed.P_low + d_low, bounds.P_low_min, bounds.P_low_max)
                            fr = _clip(seed.f_recomp + d_f, bounds.f_recomp_min, bounds.f_recomp_max)
                            if pl >= ph:
                                continue
                            result = evaluator(ph, pl, fr)
                            next_round.append(_make_candidate(ph, pl, fr, result))

            refined.extend(next_round)
            refined = _rank(refined)[: max(cfg.top_k, 20)]
            best = refined[0]
            best_stage = "refined"

            radius_high *= cfg.local_radius_scale
            radius_low *= cfg.local_radius_scale
            radius_f *= cfg.local_radius_scale

    ranked = _rank(refined if refined else coarse_ranked)
    return SearchOutcome(best=ranked[0], ranked=ranked[: cfg.top_k], stage=best_stage)

