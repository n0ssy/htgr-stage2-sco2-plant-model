import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

if "CoolProp" not in sys.modules:
    coolprop_pkg = types.ModuleType("CoolProp")
    coolprop_module = types.ModuleType("CoolProp.CoolProp")
    coolprop_module.PropsSI = lambda *_args, **_kwargs: 1.0
    coolprop_pkg.CoolProp = coolprop_module
    sys.modules["CoolProp"] = coolprop_pkg
    sys.modules["CoolProp.CoolProp"] = coolprop_module

if "scipy" not in sys.modules:
    scipy_pkg = types.ModuleType("scipy")
    scipy_optimize = types.ModuleType("scipy.optimize")

    class _Bounds:
        def __init__(self, lb, ub):
            self.lb = lb
            self.ub = ub

    def _minimize(*_args, **_kwargs):
        return SimpleNamespace(
            x=[],
            success=True,
            status=0,
            message="stub-minimize",
            fun=0.0,
        )

    scipy_optimize.Bounds = _Bounds
    scipy_optimize.minimize = _minimize
    scipy_pkg.optimize = scipy_optimize
    sys.modules["scipy"] = scipy_pkg
    sys.modules["scipy.optimize"] = scipy_optimize

import run_tests
from cycle.operating_point_search import (
    SearchBounds,
    SearchCandidate,
    SearchConfig,
    SearchOutcome,
    search_operating_point,
)


class _FakeFeasibilityReport:
    def __init__(self, feasible: bool = True):
        self.feasible = feasible
        self.converged = feasible
        self.constraints = {"E03_plant": feasible}
        self.violations = []
        self.margins = {
            "energy_residual_plant_margin_rel": 0.002 if feasible else -0.002,
            "pinch_IHX_min": 1.0,
            "pinch_HTR_min": 1.0,
            "pinch_LTR_min": 1.0,
            "W_net": 9.5e6,
            "T_He_return_margin_K": 1.0 if feasible else -1.0,
        }
        self.iterations = 6
        self.residual_norm = 0.02
        self.solve_time_seconds = 0.01

    def format_report(self) -> str:
        return "fake-report"


def _make_fake_plant_result(config, feasible: bool = True):
    state = SimpleNamespace(
        T_1=323.15,
        T_2=330.15,
        T_2a=332.15,
        T_3=410.15,
        T_4=620.15,
        T_5=790.15,
        T_6=700.15,
        T_6a=500.15,
        T_7=460.15,
        T_9=450.15,
    )
    cycle_result = SimpleNamespace(
        W_turbine=31e6,
        W_MC=3.5e6,
        W_RC=5.5e6,
        Q_HTR=80e6,
        Q_LTR=24e6,
        solver_status="CONVERGED",
        state=state,
    )
    return SimpleNamespace(
        converged=feasible,
        feasible=feasible,
        cycle_result=cycle_result,
        W_gross=10.0e6,
        W_fan=0.12e6,
        W_aux=0.1e6,
        W_net=9.78e6,
        Q_thermal=config.Q_thermal,
        Q_IHX=config.Q_thermal * 0.99,
        Q_reject=config.Q_thermal * 0.67,
        T_1=323.15,
        T_5=790.15,
        T_He_out=669.15,
        P_high=22e6,
        P_low=8e6,
        m_dot_CO2=160.0,
        m_dot_He=12.5,
        m_dot_air=0.0,
        f_recomp=0.35,
        eta_thermal=0.33,
        eta_net=0.325,
        feasibility_report=_FakeFeasibilityReport(feasible=feasible),
        dP_air=0.0,
        heat_rejection_mode=config.heat_rejection_mode,
        assumption_mode="htgr_only",
        energy_closure_rel=0.003,
        convergence_reason="converged_tolerance" if feasible else "max_iterations_reached",
        diagnostic_breakdown={"energy_residual": 0.003},
        solve_trace=[{"iteration": 1, "residual_norm": 0.5}],
    )


class _FakeSolver:
    def __init__(self, config):
        self.config = config

    def solve(
        self,
        P_high=None,
        P_low=None,
        f_recomp=None,
        initial_guess=None,
        return_trace=False,
        verbose=False,
    ):
        _ = (P_high, P_low, f_recomp, initial_guess, return_trace, verbose)
        return _make_fake_plant_result(self.config, feasible=True)


def _fake_search(*_args, **_kwargs):
    cand = SearchCandidate(
        P_high=22e6,
        P_low=8e6,
        f_recomp=0.35,
        score=0.0,
        converged=True,
        feasible=True,
        iterations=6,
        energy_closure_rel=0.003,
        W_net=9.78e6,
        constraints_failed=[],
        margins={},
        convergence_reason="converged_tolerance",
    )
    return SearchOutcome(best=cand, ranked=[cand], stage="coarse")


class OperatingPointSearchTests(unittest.TestCase):
    def test_search_is_deterministic(self):
        bounds = SearchBounds(
            P_high_min=20e6,
            P_high_max=24e6,
            P_low_min=7.5e6,
            P_low_max=8.5e6,
            f_recomp_min=0.25,
            f_recomp_max=0.35,
        )
        config = SearchConfig(
            bounds=bounds,
            n_P_high=3,
            n_P_low=3,
            n_f_recomp=3,
            local_rounds=1,
            top_k=5,
        )

        def evaluator(p_high, p_low, f_rec):
            # Deterministic pseudo-plant objective with known optimum near:
            # P_high=22e6, P_low=8.0e6, f_recomp=0.30
            err = abs(p_high - 22e6) / 1e6 + abs(p_low - 8e6) / 1e6 + abs(f_rec - 0.30) * 10.0
            feasible = err < 1.0
            energy_closure = min(0.02, 0.001 + 0.001 * err)
            margins = {
                "energy_residual_plant_margin_rel": 0.005 - energy_closure,
                "T_He_return_margin_K": 2.0 - err,
            }
            return SimpleNamespace(
                converged=True,
                feasible=feasible,
                feasibility_report=SimpleNamespace(
                    constraints={"E03_plant": feasible},
                    margins=margins,
                    iterations=5,
                ),
                energy_closure_rel=energy_closure,
                W_net=10e6 - err * 1e5,
                convergence_reason="converged_tolerance",
            )

        out1 = search_operating_point(solver=None, config=config, evaluate_fn=evaluator)
        out2 = search_operating_point(solver=None, config=config, evaluate_fn=evaluator)

        self.assertEqual(out1.best.P_high, out2.best.P_high)
        self.assertEqual(out1.best.P_low, out2.best.P_low)
        self.assertEqual(out1.best.f_recomp, out2.best.f_recomp)
        self.assertEqual(out1.best.score, out2.best.score)


class FailFastControlTests(unittest.TestCase):
    def test_fail_fast_without_override(self):
        self.assertTrue(
            run_tests._should_fail_fast_after_headline(
                headline_feasible=False,
                allow_infeasible_diagnostic=False,
            )
        )

    def test_override_env_enables_diagnostic_continue(self):
        with mock.patch.dict("os.environ", {"ALLOW_INFEASIBLE_DIAGNOSTIC": "1"}, clear=False):
            self.assertTrue(run_tests._is_allow_infeasible_diagnostic_enabled())
            self.assertFalse(
                run_tests._should_fail_fast_after_headline(
                    headline_feasible=False,
                    allow_infeasible_diagnostic=run_tests._is_allow_infeasible_diagnostic_enabled(),
                )
            )

    def test_fail_fast_output_generation_skips_co2_files(self):
        fake_config = SimpleNamespace(Q_thermal=30e6, heat_rejection_mode="fixed_boundary")
        fake_result = _make_fake_plant_result(fake_config, feasible=False)
        baseline_results = {
            "status": {
                "converged": False,
                "feasible": False,
                "convergence_reason": "max_iterations_reached",
                "iterations": 40,
                "residual_norm": 0.9,
                "solve_time_seconds": 1.0,
                "energy_closure_rel": 0.009,
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            run_tests.write_output_files(
                output_dir=tmp,
                baseline_results=baseline_results,
                baseline_plant_result=fake_result,
                include_co2_outputs=False,
                verbose=False,
            )
            root = Path(tmp)
            self.assertTrue((root / "results_baseline.json").exists())
            self.assertTrue((root / "feasibility_report.txt").exists())
            self.assertFalse((root / "co2_reduction_results.json").exists())
            self.assertFalse((root / "co2_reduction_report.txt").exists())


class TuningMetadataTests(unittest.TestCase):
    @mock.patch("run_tests.search_operating_point", side_effect=_fake_search)
    @mock.patch("run_tests.CoupledPlantSolver", side_effect=lambda config: _FakeSolver(config))
    def test_moderate_tuning_guard_and_metadata_persistence(self, _solver_mock, _search_mock):
        results, _ = run_tests.run_full_plant_solve(
            T_ambient_C=40.0,
            heat_rejection_mode="fixed_boundary",
            cooling_aux_fraction=0.5,  # intentionally outside allowed range
            auto_tune=True,
            tuning_mode="moderate",
            verbose=False,
        )
        selected = results["metadata"]["selected_tuning_parameters"]
        self.assertGreaterEqual(selected["cooling_aux_fraction"], 0.005)
        self.assertLessEqual(selected["cooling_aux_fraction"], 0.02)
        self.assertIn("convergence_reason", results["status"])
        self.assertIn("selected_attempt_label", results["metadata"])
        self.assertTrue(results["metadata"]["tuning_guard"]["applied"])


class CanonicalFeasibilityGateTests(unittest.TestCase):
    @mock.patch("run_tests.report_gate_check", return_value=None)
    @mock.patch(
        "run_tests.run_stage2_scenarios",
        return_value=(
            {
                "S0_BASE_30MW_OPONLY": {
                    "scenario": {"scenario_id": "S0_BASE_30MW_OPONLY"},
                    "plant": {
                        "status": {"converged": False, "feasible": False},
                        "metadata": {"scenario_id": "S0_BASE_30MW_OPONLY"},
                    },
                    "co2": {"metadata": {"scenario_id": "S0_BASE_30MW_OPONLY"}},
                }
            },
            {
                "S0_BASE_30MW_OPONLY": {
                    "scenario_id": "S0_BASE_30MW_OPONLY",
                    "converged": False,
                    "feasible": False,
                }
            },
        ),
    )
    def test_require_feasible_writes_failure_report_and_stops(self, _scenarios_mock, _gate_mock):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                run_tests.generate_stage2_canonical_pack(
                    output_dir=tmp,
                    uq_samples=3,
                    require_feasible=True,
                    verbose=False,
                )
            root = Path(tmp) / "outputs" / "canonical_pack"
            failure_report = root / "feasibility_failure_report.json"
            self.assertTrue(failure_report.exists())
            self.assertFalse((root / "canonical_pack_index.json").exists())
            data = json.loads(failure_report.read_text())
            self.assertTrue(data["failed_scenarios"])


if __name__ == "__main__":
    unittest.main()
