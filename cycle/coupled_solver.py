"""
Coupled Plant Solver.
Solves IHX and sCO2 cycle as a simultaneous system with embedded feasibility constraints.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from properties.fluids import CO2_T_CRIT
from components.ihx import IHX, IHXConfig
from components.dry_cooler import DryCooler, DryCoolerConfig
from cycle.sco2_cycle import SCO2RecompressionCycle, CycleConfig, CycleResult
from hx.segmented_hx import SolverStatus


@dataclass
class PlantConfig:
    """Complete plant configuration."""

    # Reactor conditions (HTTR defaults)
    Q_thermal: float = 30e6
    T_He_hot: float = 1123.15
    T_He_cold: float = 668.15
    P_He: float = 4.0e6

    # Ambient conditions
    T_ambient: float = 313.15

    # Cycle configuration
    cycle_config: CycleConfig = field(default_factory=CycleConfig)

    # IHX configuration
    ihx_config: IHXConfig = field(default_factory=IHXConfig)

    # Dry cooler configuration (kept for optional sensitivity mode)
    cooler_config: DryCoolerConfig = field(default_factory=DryCoolerConfig)

    # Solver settings
    max_iterations: int = 100
    tolerance: float = 0.1
    energy_closure_tolerance: float = 0.005  # 0.5%

    # HTGR-only boundary mode options
    heat_rejection_mode: str = "fixed_boundary"  # fixed_boundary | coupled_cooler
    T_1_boundary_target: Optional[float] = None
    cooling_aux_fraction: float = 0.01
    W_cooling_aux_assumed: Optional[float] = None
    headline_fom_mode: str = "htgr_only"


@dataclass
class ConstraintViolation:
    """Single constraint violation."""

    constraint_id: str
    description: str
    actual_value: float
    required_value: float
    margin: float
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class FeasibilityReport:
    """Comprehensive feasibility assessment."""

    feasible: bool
    converged: bool
    constraints: Dict[str, bool]
    violations: List[ConstraintViolation]
    margins: Dict[str, float]
    iterations: int
    residual_norm: float
    solve_time_seconds: float = 0.0

    def primary_failure(self) -> Optional[ConstraintViolation]:
        if self.feasible or not self.violations:
            return None
        return min(self.violations, key=lambda v: v.margin)

    def format_report(self) -> str:
        lines = [
            "=" * 60,
            "FEASIBILITY REPORT",
            "=" * 60,
            f"Status: {'FEASIBLE' if self.feasible else 'INFEASIBLE'}",
            f"Converged: {self.converged}",
            f"Iterations: {self.iterations}",
            f"Residual norm: {self.residual_norm:.2e}",
            "",
        ]

        if not self.feasible:
            lines.append("VIOLATIONS:")
            for v in self.violations:
                lines.append(f"  [{v.constraint_id}] {v.description}")
                lines.append(
                    f"      Actual: {v.actual_value:.3f}, Required: {v.required_value:.3f}, Margin: {v.margin:.3f}"
                )
                if v.location:
                    lines.append(f"      Location: {v.location}")
                if v.suggestion:
                    lines.append(f"      Suggestion: {v.suggestion}")

        lines.append("")
        lines.append("MARGINS (distance to constraint boundary):")
        for name, margin in sorted(self.margins.items()):
            status = "OK" if margin >= 0 else "VIOLATED"
            lines.append(f"  {name}: {margin:.2f} [{status}]")

        lines.append("=" * 60)
        return "\n".join(lines)


@dataclass
class PlantResult:
    """Complete plant solution result."""

    converged: bool
    feasible: bool

    cycle_result: Optional[CycleResult]

    W_gross: float
    W_fan: float
    W_aux: float
    W_net: float

    Q_thermal: float
    Q_IHX: float
    Q_reject: float

    T_1: float
    T_5: float
    T_He_out: float

    P_high: float
    P_low: float

    m_dot_CO2: float
    m_dot_He: float
    m_dot_air: float

    f_recomp: float

    eta_thermal: float
    eta_net: float

    feasibility_report: FeasibilityReport

    dP_air: float

    # New diagnostics/metadata
    heat_rejection_mode: str = "fixed_boundary"
    assumption_mode: str = "htgr_only"
    energy_closure_rel: float = 0.0
    diagnostic_breakdown: Dict[str, float] = field(default_factory=dict)
    report_gate_passed: bool = False


class CoupledPlantSolver:
    """
    Coupled solver for HTGR + sCO2 plant.

    Two operating modes:
    - fixed_boundary: HTGR headline mode; cooling is represented by boundary assumptions
    - coupled_cooler: optional sensitivity mode using detailed dry-cooler model
    """

    def __init__(self, config: Optional[PlantConfig] = None):
        self.config = config or PlantConfig()

        self.cycle = SCO2RecompressionCycle(self.config.cycle_config)
        self.ihx = IHX(self.config.ihx_config)
        self.cooler = DryCooler(self.config.cooler_config)

    def _build_cooler_assumption(
        self,
        cycle_result: CycleResult,
        T_1_min: float,
    ) -> Dict[str, float]:
        cfg = self.config
        T_1_assumed = max(cfg.T_1_boundary_target or T_1_min, T_1_min)

        if cfg.W_cooling_aux_assumed is not None:
            W_cooling_aux = max(cfg.W_cooling_aux_assumed, 0.0)
            assumption_mode = "fixed_cooling_aux"
        else:
            W_cooling_aux = max(cfg.cooling_aux_fraction * max(cycle_result.W_gross, 0.0), 0.0)
            assumption_mode = "fractional_cooling_aux"

        return {
            "T_1_new": T_1_assumed,
            "W_cooling_aux": W_cooling_aux,
            "m_dot_air": 0.0,
            "dP_air": 0.0,
            "Q_model": cycle_result.Q_reject,
            "Q_error_rel": 0.0,
            "solver_status": SolverStatus.CONVERGED.value,
            "assumption_mode": assumption_mode,
        }

    def solve(
        self,
        P_high: Optional[float] = None,
        P_low: Optional[float] = None,
        f_recomp: Optional[float] = None,
        m_dot_CO2: Optional[float] = None,
    ) -> PlantResult:
        import time

        start_time = time.time()
        cfg = self.config
        cycle_cfg = cfg.cycle_config

        mode = cfg.heat_rejection_mode
        if mode not in {"fixed_boundary", "coupled_cooler"}:
            return self._failed_result(
                f"Unknown heat_rejection_mode: {mode}",
                0,
                float("inf"),
                0.0,
            )

        P_high = P_high or 0.5 * (cycle_cfg.P_high_min + cycle_cfg.P_high_max)
        P_low = P_low or 0.5 * (cycle_cfg.P_low_min + cycle_cfg.P_low_max)
        f_recomp = 0.35 if f_recomp is None else f_recomp

        m_dot_He = self.ihx.required_He_flow(
            cfg.Q_thermal,
            cfg.T_He_hot,
            cfg.T_He_cold,
            cfg.P_He,
        )

        if m_dot_CO2 is None:
            m_dot_CO2 = cfg.Q_thermal / (1200.0 * 200.0)

        T_1_min = max(
            CO2_T_CRIT + cycle_cfg.dT_crit_margin,
            cfg.T_ambient + cfg.cooler_config.dT_approach_min,
        )

        if mode == "fixed_boundary":
            T_1 = max(cfg.T_1_boundary_target or T_1_min, T_1_min)
        else:
            T_1 = T_1_min + 2.0

        T_5 = cfg.T_He_hot - cfg.ihx_config.dT_approach

        max_iter = cfg.max_iterations
        tol = cfg.tolerance
        converged = False
        residual_norm = float("inf")
        last_good_state: Optional[Dict[str, float]] = None
        cool_converged = False

        cooler_diag = {
            "W_cooling_aux": 0.0,
            "m_dot_air": 0.0,
            "dP_air": 0.0,
            "Q_model": 0.0,
            "Q_error_rel": 0.0,
            "solver_status": SolverStatus.CONVERGED.value,
            "assumption_mode": "not_set",
        }

        for iteration in range(max_iter):
            T_1_old = T_1
            T_5_old = T_5
            m_old = m_dot_CO2

            cycle_result = self.cycle.solve(
                T_1=T_1,
                T_5=T_5,
                P_high=P_high,
                P_low=P_low,
                m_dot=m_dot_CO2,
                f_recomp=f_recomp,
            )
            if not cycle_result.converged:
                if mode == "coupled_cooler" and last_good_state is not None:
                    T_1 = last_good_state["T_1"]
                    T_5 = last_good_state["T_5"]
                    m_dot_CO2 = last_good_state["m_dot_CO2"]
                    converged = last_good_state["converged"]
                    residual_norm = last_good_state["residual_norm"]
                    break
                solve_time = time.time() - start_time
                return self._failed_result(
                    f"Cycle failed: {cycle_result.error_message}",
                    iteration,
                    residual_norm,
                    solve_time,
                )

            T_4 = cycle_result.state.T_4
            P_4 = cycle_result.state.P_4
            ihx_result = self.ihx.solve(
                T_He_in=cfg.T_He_hot,
                P_He_in=cfg.P_He,
                m_dot_He=m_dot_He,
                T_CO2_in=T_4,
                P_CO2_in=P_4,
                m_dot_CO2=m_dot_CO2,
            )
            if not ihx_result.converged:
                if mode == "coupled_cooler" and last_good_state is not None:
                    T_1 = last_good_state["T_1"]
                    T_5 = last_good_state["T_5"]
                    m_dot_CO2 = last_good_state["m_dot_CO2"]
                    converged = last_good_state["converged"]
                    residual_norm = last_good_state["residual_norm"]
                    break
                solve_time = time.time() - start_time
                return self._failed_result(
                    f"IHX failed: {ihx_result.error_message}",
                    iteration,
                    residual_norm,
                    solve_time,
                )

            T_5_new = ihx_result.T_CO2_out

            if mode == "coupled_cooler":
                cool = self.cooler.solve(
                    T_CO2_in=cycle_result.state.T_7,
                    P_CO2_in=cycle_result.state.P_7,
                    m_dot_CO2=m_dot_CO2 * (1 - f_recomp),
                    Q_reject=cycle_result.Q_reject,
                    T_ambient=cfg.T_ambient,
                )
                if cool.solver_status == SolverStatus.NUMERICAL_FAIL.value:
                    solve_time = time.time() - start_time
                    return self._failed_result(
                        f"Cooler failed: {cool.error_message}",
                        iteration,
                        residual_norm,
                        solve_time,
                    )

                T_1_new = max(cool.T_CO2_out, T_1_min)
                cooler_diag = {
                    "W_cooling_aux": cool.W_fan,
                    "m_dot_air": cool.m_dot_air,
                    "dP_air": cool.dP_air,
                    "Q_model": cool.Q_model,
                    "Q_error_rel": cool.Q_error_rel,
                    "solver_status": cool.solver_status,
                    "assumption_mode": "coupled_cooler",
                }
                cool_converged = bool(cool.converged and cool.feasible)
            else:
                assumption = self._build_cooler_assumption(cycle_result, T_1_min)
                T_1_new = assumption["T_1_new"]
                cooler_diag = {
                    "W_cooling_aux": assumption["W_cooling_aux"],
                    "m_dot_air": assumption["m_dot_air"],
                    "dP_air": assumption["dP_air"],
                    "Q_model": assumption["Q_model"],
                    "Q_error_rel": assumption["Q_error_rel"],
                    "solver_status": assumption["solver_status"],
                    "assumption_mode": assumption["assumption_mode"],
                }
                cool_converged = True

            if mode == "coupled_cooler":
                last_good_state = {
                    "T_1": T_1,
                    "T_5": T_5,
                    "m_dot_CO2": m_dot_CO2,
                    "converged": bool(cool_converged),
                    "residual_norm": residual_norm,
                }

            Q_target = cfg.Q_thermal
            Q_actual = ihx_result.Q_IHX
            if Q_actual > 0:
                m_factor = Q_target / Q_actual
                m_new = m_dot_CO2 * (0.7 + 0.3 * m_factor)
            else:
                m_new = m_dot_CO2 * 1.1
            m_new = float(np.clip(m_new, 10.0, 500.0))

            if mode == "coupled_cooler" and cycle_result.Q_reject > 0:
                # Couple mass-flow update to cooler thermal capability to avoid runaway
                # toward infeasible high-rejection operating points.
                cooling_ratio = cooler_diag["Q_model"] / max(cycle_result.Q_reject, 1.0)
                m_new *= float(np.clip(cooling_ratio, 0.4, 1.0))
                m_new = float(np.clip(m_new, 10.0, 500.0))

            alpha = 0.5
            if mode == "fixed_boundary":
                T_1 = T_1_new
            else:
                T_1 = alpha * T_1_new + (1 - alpha) * T_1
            T_5 = alpha * T_5_new + (1 - alpha) * T_5
            m_dot_CO2 = alpha * m_new + (1 - alpha) * m_dot_CO2

            dT_5 = abs(T_5 - T_5_old)
            dm_rel = abs(m_dot_CO2 - m_old) / max(m_dot_CO2, 1e-9)
            if mode == "fixed_boundary":
                dT_1 = 0.0
            else:
                dT_1 = abs(T_1 - T_1_old)

            residual_norm = max(dT_1, dT_5, dm_rel * 10.0)
            if mode == "fixed_boundary":
                if dT_5 < tol and dm_rel < 0.001:
                    converged = True
                    break
            else:
                if cool_converged and dT_5 < tol and dm_rel < 0.001 and dT_1 < tol:
                    converged = True
                    break

        solve_time = time.time() - start_time

        cycle_result = self.cycle.solve(
            T_1=T_1,
            T_5=T_5,
            P_high=P_high,
            P_low=P_low,
            m_dot=m_dot_CO2,
            f_recomp=f_recomp,
        )
        if (
            mode == "coupled_cooler"
            and not cycle_result.converged
            and last_good_state is not None
        ):
            T_1 = last_good_state["T_1"]
            T_5 = last_good_state["T_5"]
            m_dot_CO2 = last_good_state["m_dot_CO2"]
            cycle_result = self.cycle.solve(
                T_1=T_1,
                T_5=T_5,
                P_high=P_high,
                P_low=P_low,
                m_dot=m_dot_CO2,
                f_recomp=f_recomp,
            )
        if not cycle_result.converged:
            return self._failed_result(
                f"Final cycle solve failed: {cycle_result.error_message}",
                iteration,
                residual_norm,
                solve_time,
            )

        ihx_result = self.ihx.solve(
            T_He_in=cfg.T_He_hot,
            P_He_in=cfg.P_He,
            m_dot_He=m_dot_He,
            T_CO2_in=cycle_result.state.T_4,
            P_CO2_in=cycle_result.state.P_4,
            m_dot_CO2=m_dot_CO2,
        )
        if not ihx_result.converged:
            return self._failed_result(
                f"Final IHX solve failed: {ihx_result.error_message}",
                iteration,
                residual_norm,
                solve_time,
            )

        if mode == "coupled_cooler":
            cool = self.cooler.solve(
                T_CO2_in=cycle_result.state.T_7,
                P_CO2_in=cycle_result.state.P_7,
                m_dot_CO2=m_dot_CO2 * (1 - f_recomp),
                Q_reject=cycle_result.Q_reject,
                T_ambient=cfg.T_ambient,
            )
            if cool.solver_status == SolverStatus.NUMERICAL_FAIL.value:
                return self._failed_result(
                    f"Final cooler solve failed: {cool.error_message}",
                    iteration,
                    residual_norm,
                    solve_time,
                )
            cooler_diag = {
                "W_cooling_aux": cool.W_fan,
                "m_dot_air": cool.m_dot_air,
                "dP_air": cool.dP_air,
                "Q_model": cool.Q_model,
                "Q_error_rel": cool.Q_error_rel,
                "solver_status": cool.solver_status,
                "assumption_mode": "coupled_cooler",
            }
        else:
            assumption = self._build_cooler_assumption(cycle_result, T_1_min)
            cooler_diag = {
                "W_cooling_aux": assumption["W_cooling_aux"],
                "m_dot_air": assumption["m_dot_air"],
                "dP_air": assumption["dP_air"],
                "Q_model": assumption["Q_model"],
                "Q_error_rel": assumption["Q_error_rel"],
                "solver_status": assumption["solver_status"],
                "assumption_mode": assumption["assumption_mode"],
            }

        constraints: Dict[str, bool] = {}
        margins: Dict[str, float] = {}
        violations: List[ConstraintViolation] = []

        constraints.update(cycle_result.constraints)
        margins.update(cycle_result.margins)
        for v in cycle_result.violations:
            violations.append(
                ConstraintViolation(
                    constraint_id=v.split("]")[0].strip("[") if "]" in v else "CYCLE",
                    description=v,
                    actual_value=0.0,
                    required_value=0.0,
                    margin=0.0,
                )
            )

        constraints["P01"] = ihx_result.feasible
        margins["pinch_IHX_min"] = ihx_result.dT_pinch_min - cfg.ihx_config.dT_pinch_min
        if not ihx_result.feasible:
            violations.append(
                ConstraintViolation(
                    constraint_id="P01",
                    description=f"IHX pinch violation at segment {ihx_result.pinch_segment}",
                    actual_value=ihx_result.dT_pinch_min,
                    required_value=cfg.ihx_config.dT_pinch_min,
                    margin=margins["pinch_IHX_min"],
                    location=f"IHX segment {ihx_result.pinch_segment}",
                )
            )

        if mode == "coupled_cooler":
            constraints["P04"] = cool.feasible
            margins["cooling_closure"] = 1.0 - cooler_diag["Q_error_rel"]
            margins["cooling_Q_error_rel"] = cooler_diag["Q_error_rel"]
            if not constraints["P04"]:
                violations.append(
                    ConstraintViolation(
                        constraint_id="P04",
                        description=(
                            "Coupled cooler did not satisfy thermal-closure/approach/pinch "
                            f"(status={cool.solver_status})"
                        ),
                        actual_value=cooler_diag["Q_error_rel"] * 100.0,
                        required_value=cfg.cooler_config.q_closure_tolerance * 100.0,
                        margin=(cfg.cooler_config.q_closure_tolerance - cooler_diag["Q_error_rel"]) * 100.0,
                        location="Dry cooler model",
                        suggestion="Use fixed_boundary headline mode or adjust coupled-cooler assumptions/geometry.",
                    )
                )
        else:
            constraints["P04"] = True
            margins["cooling_closure"] = 1.0
            margins["cooling_assumed_aux_MW"] = cooler_diag["W_cooling_aux"] / 1e6

        T_He_return = ihx_result.T_He_out
        constraints["T04"] = T_He_return >= cfg.T_He_cold - 10.0
        margins["T_He_return"] = T_He_return - cfg.T_He_cold
        if not constraints["T04"]:
            violations.append(
                ConstraintViolation(
                    constraint_id="T04",
                    description="Helium return temperature too low",
                    actual_value=T_He_return - 273.15,
                    required_value=cfg.T_He_cold - 273.15,
                    margin=margins["T_He_return"],
                    location="IHX helium outlet",
                )
            )

        W_gross = cycle_result.W_gross
        W_fan = cooler_diag["W_cooling_aux"]
        W_aux = 0.01 * W_gross
        W_net = W_gross - W_fan - W_aux

        constraints["E02"] = W_net > 0
        margins["W_net"] = W_net
        if not constraints["E02"]:
            violations.append(
                ConstraintViolation(
                    constraint_id="E02",
                    description="Negative net power output",
                    actual_value=W_net / 1e6,
                    required_value=0.0,
                    margin=W_net / 1e6,
                    location="Plant output",
                )
            )

        Q_in = cfg.Q_thermal
        Q_out = W_net + cycle_result.Q_reject + W_fan + W_aux
        energy_residual = abs(Q_in - Q_out) / max(Q_in, 1.0)
        constraints["E03_plant"] = energy_residual < cfg.energy_closure_tolerance
        margins["energy_residual"] = energy_residual
        margins["energy_closure"] = cfg.energy_closure_tolerance - energy_residual
        if not constraints["E03_plant"]:
            violations.append(
                ConstraintViolation(
                    constraint_id="E03",
                    description="Plant energy balance not closed",
                    actual_value=energy_residual * 100.0,
                    required_value=cfg.energy_closure_tolerance * 100.0,
                    margin=(cfg.energy_closure_tolerance - energy_residual) * 100.0,
                    location="Plant energy balance",
                )
            )

        feasible = converged and all(constraints.values())
        feasibility_report = FeasibilityReport(
            feasible=feasible,
            converged=converged,
            constraints=constraints,
            violations=violations,
            margins=margins,
            iterations=iteration + 1,
            residual_norm=residual_norm,
            solve_time_seconds=solve_time,
        )

        diagnostic_breakdown = {
            "Q_thermal": cfg.Q_thermal,
            "Q_IHX": ihx_result.Q_IHX,
            "Q_reject_cycle": cycle_result.Q_reject,
            "W_gross": W_gross,
            "W_cooling_aux": W_fan,
            "W_aux_other": W_aux,
            "W_net": W_net,
            "energy_residual": energy_residual,
            "cooling_Q_model": cooler_diag["Q_model"],
            "cooling_Q_error_rel": cooler_diag["Q_error_rel"],
            "cooling_closure_margin": margins.get("cooling_closure", 0.0),
            "cycle_energy_closure_rel": cycle_result.energy_closure_rel,
        }
        report_gate_passed = bool(
            feasible
            and cycle_result.converged
            and cycle_result.energy_closure_rel <= cycle_cfg.energy_closure_tolerance
            and energy_residual <= cfg.energy_closure_tolerance
        )

        return PlantResult(
            converged=converged,
            feasible=feasible,
            cycle_result=cycle_result,
            W_gross=W_gross,
            W_fan=W_fan,
            W_aux=W_aux,
            W_net=W_net,
            Q_thermal=cfg.Q_thermal,
            Q_IHX=ihx_result.Q_IHX,
            Q_reject=cycle_result.Q_reject,
            T_1=T_1,
            T_5=T_5,
            T_He_out=T_He_return,
            P_high=P_high,
            P_low=P_low,
            m_dot_CO2=m_dot_CO2,
            m_dot_He=m_dot_He,
            m_dot_air=cooler_diag["m_dot_air"],
            f_recomp=f_recomp,
            eta_thermal=cycle_result.eta_thermal,
            eta_net=W_net / cfg.Q_thermal,
            feasibility_report=feasibility_report,
            dP_air=cooler_diag["dP_air"],
            heat_rejection_mode=mode,
            assumption_mode=("htgr_only" if mode == "fixed_boundary" else "coupled_cooler_sensitivity"),
            energy_closure_rel=energy_residual,
            diagnostic_breakdown=diagnostic_breakdown,
            report_gate_passed=report_gate_passed,
        )

    def _failed_result(
        self,
        error_msg: str,
        iteration: int,
        residual_norm: float,
        solve_time: float,
    ) -> PlantResult:
        feasibility_report = FeasibilityReport(
            feasible=False,
            converged=False,
            constraints={"C01": False},
            violations=[
                ConstraintViolation(
                    constraint_id="C01",
                    description=error_msg,
                    actual_value=0.0,
                    required_value=0.0,
                    margin=-1.0,
                )
            ],
            margins={},
            iterations=iteration + 1,
            residual_norm=residual_norm,
            solve_time_seconds=solve_time,
        )

        return PlantResult(
            converged=False,
            feasible=False,
            cycle_result=None,
            W_gross=0.0,
            W_fan=0.0,
            W_aux=0.0,
            W_net=0.0,
            Q_thermal=self.config.Q_thermal,
            Q_IHX=0.0,
            Q_reject=0.0,
            T_1=0.0,
            T_5=0.0,
            T_He_out=0.0,
            P_high=0.0,
            P_low=0.0,
            m_dot_CO2=0.0,
            m_dot_He=0.0,
            m_dot_air=0.0,
            f_recomp=0.0,
            eta_thermal=0.0,
            eta_net=0.0,
            feasibility_report=feasibility_report,
            dP_air=0.0,
            heat_rejection_mode=self.config.heat_rejection_mode,
            assumption_mode="failed",
            energy_closure_rel=1.0,
            diagnostic_breakdown={"error": error_msg},
            report_gate_passed=False,
        )
