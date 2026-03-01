"""
sCO2 Recompression Brayton Cycle solver.
Provides cycle-level calculations that can be used standalone (Dostal validation)
or coupled with the IHX in the full plant solve.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from properties.fluids import co2, CO2_T_CRIT, CO2_P_CRIT
from components.turbomachinery import Turbine, MainCompressor, Recompressor
from components.recuperators import (
    HighTemperatureRecuperator,
    LowTemperatureRecuperator,
    RecuperatorConfig,
    merge_streams
)
from hx.segmented_hx import SolverStatus


@dataclass
class CycleConfig:
    """Configuration for sCO2 recompression cycle."""
    # Pressure bounds
    P_high_min: float = 20e6  # [Pa]
    P_high_max: float = 30e6  # [Pa]
    P_low_min: float = 7.5e6  # [Pa]
    P_low_max: float = 9.0e6  # [Pa]

    # Recompression fraction bounds
    f_recomp_min: float = 0.25
    f_recomp_max: float = 0.45

    # Turbomachinery efficiencies
    eta_turbine: float = 0.90
    eta_MC: float = 0.89
    eta_RC: float = 0.89

    # Supercritical margins
    dT_crit_margin: float = 3.0  # [K]
    dP_crit_margin: float = 0.3e6  # [Pa]

    # Heat exchanger settings
    dT_pinch_min: float = 10.0  # [K]
    n_segments: int = 10  # Reduced for performance

    # Pressure drops
    dP_HTR_hot: float = 50e3  # [Pa]
    dP_HTR_cold: float = 50e3  # [Pa]
    dP_LTR_hot: float = 50e3  # [Pa]
    dP_LTR_cold: float = 50e3  # [Pa]

    # Temperature limit
    T_TIT_max: float = 1073.15  # 800°C in K

    # Unified energy closure tolerance
    energy_closure_tolerance: float = 0.005  # 0.5%


@dataclass
class CycleState:
    """Complete cycle state at all points."""
    # State 1: Main compressor inlet
    T_1: float
    P_1: float
    h_1: float

    # State 2: Main compressor outlet
    T_2: float
    P_2: float
    h_2: float

    # State 2a: LTR cold outlet (main compressor path)
    T_2a: float
    P_2a: float
    h_2a: float

    # State 3: Merge point (before HTR)
    T_3: float
    P_3: float
    h_3: float

    # State 4: HTR cold outlet (IHX inlet)
    T_4: float
    P_4: float
    h_4: float

    # State 5: Turbine inlet (IHX outlet)
    T_5: float
    P_5: float
    h_5: float

    # State 6: Turbine outlet
    T_6: float
    P_6: float
    h_6: float

    # State 6a: HTR hot outlet
    T_6a: float
    P_6a: float
    h_6a: float

    # State 7: LTR hot outlet (pre-cooler inlet / split point)
    T_7: float
    P_7: float
    h_7: float

    # State 8: Pre-cooler outlet (same as state 1 for simple case)
    T_8: float
    P_8: float
    h_8: float

    # State 9: Recompressor outlet
    T_9: float
    P_9: float
    h_9: float

    # Mass flows
    m_dot_total: float  # Total cycle mass flow
    f_recomp: float  # Recompression fraction
    m_dot_MC: float  # Main compressor mass flow = (1-f) * m_dot
    m_dot_RC: float  # Recompressor mass flow = f * m_dot


@dataclass
class CycleResult:
    """Result from cycle solve."""
    converged: bool
    feasible: bool

    # Cycle state
    state: Optional[CycleState]

    # Power
    W_turbine: float
    W_MC: float
    W_RC: float
    W_gross: float  # W_turbine - W_MC - W_RC

    # Heat transfers
    Q_in: float  # Heat input (from IHX or specified)
    Q_HTR: float
    Q_LTR: float
    Q_reject: float  # Heat rejection (to cooler)

    # Pinch data
    dT_pinch_HTR: float
    dT_pinch_LTR: float
    pinch_HTR_segment: int
    pinch_LTR_segment: int

    # Efficiency
    eta_thermal: float  # W_gross / Q_in

    # Feasibility details
    constraints: Dict[str, bool] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    margins: Dict[str, float] = field(default_factory=dict)

    # Diagnostics
    solver_status: str = SolverStatus.CONVERGED.value
    energy_closure_rel: float = 0.0
    diagnostic_breakdown: Dict[str, float] = field(default_factory=dict)
    assumption_mode: str = "cycle_default"

    error_message: Optional[str] = None


class SCO2RecompressionCycle:
    """
    sCO2 Recompression Brayton Cycle solver.

    State points (Dostal numbering):
    1 - Main compressor inlet
    2 - Main compressor outlet
    2a - LTR cold outlet (MC path)
    3 - Merge point (2a + 9)
    4 - HTR cold outlet (IHX inlet)
    5 - Turbine inlet (IHX outlet)
    6 - Turbine outlet
    6a - HTR hot outlet
    7 - LTR hot outlet / split point
    8 - Pre-cooler outlet (= state 1)
    9 - Recompressor outlet
    """

    def __init__(self, config: Optional[CycleConfig] = None):
        self.config = config or CycleConfig()

        # Create components
        self.turbine = Turbine(self.config.eta_turbine)
        self.main_comp = MainCompressor(
            self.config.eta_MC,
            self.config.dT_crit_margin,
            self.config.dP_crit_margin
        )
        self.recomp = Recompressor(self.config.eta_RC)

        htr_config = RecuperatorConfig(
            dP_hot=self.config.dP_HTR_hot,
            dP_cold=self.config.dP_HTR_cold,
            dT_pinch_min=self.config.dT_pinch_min,
            n_segments=self.config.n_segments
        )
        ltr_config = RecuperatorConfig(
            dP_hot=self.config.dP_LTR_hot,
            dP_cold=self.config.dP_LTR_cold,
            dT_pinch_min=self.config.dT_pinch_min,
            n_segments=self.config.n_segments
        )

        self.HTR = HighTemperatureRecuperator(htr_config)
        self.LTR = LowTemperatureRecuperator(ltr_config)

    def solve(self,
              T_1: float,
              T_5: float,
              P_high: float,
              P_low: float,
              m_dot: float,
              f_recomp: float,
              Q_in: Optional[float] = None) -> CycleResult:
        """
        Solve the complete cycle for given boundary conditions.

        Args:
            T_1: Compressor inlet temperature [K]
            T_5: Turbine inlet temperature [K]
            P_high: High-side pressure [Pa]
            P_low: Low-side pressure [Pa]
            m_dot: Total CO2 mass flow rate [kg/s]
            f_recomp: Recompression fraction
            Q_in: Heat input [W] (optional, calculated if not provided)

        Returns:
            CycleResult with all outputs
        """
        config = self.config
        violations = []
        constraints = {}
        margins = {}

        # Mass flows
        m_dot_MC = (1 - f_recomp) * m_dot  # Main compressor
        m_dot_RC = f_recomp * m_dot  # Recompressor

        # Check supercritical margin at state 1
        T_margin_crit = T_1 - CO2_T_CRIT
        P_margin_crit = P_low - CO2_P_CRIT

        margins['T_crit_margin'] = T_margin_crit
        margins['P_crit_margin'] = P_margin_crit

        constraints['T01'] = T_margin_crit >= config.dT_crit_margin
        constraints['T02'] = P_margin_crit >= config.dP_crit_margin

        if not constraints['T01']:
            violations.append(
                f"[T01] T_1={T_1-273.15:.2f}°C too close to T_crit "
                f"(margin={T_margin_crit:.2f}K < {config.dT_crit_margin}K)"
            )
        if not constraints['T02']:
            violations.append(
                f"[T02] P_low={P_low/1e6:.2f}MPa too close to P_crit "
                f"(margin={P_margin_crit/1e6:.3f}MPa < {config.dP_crit_margin/1e6:.2f}MPa)"
            )

        # Check TIT limit
        constraints['T03'] = T_5 <= config.T_TIT_max
        margins['T_TIT_margin'] = config.T_TIT_max - T_5
        if not constraints['T03']:
            violations.append(
                f"[T03] T_5={T_5-273.15:.2f}°C exceeds T_TIT_max={config.T_TIT_max-273.15:.2f}°C"
            )

        try:
            # State 1: Main compressor inlet
            h_1 = co2.h(T_1, P_low)

            # State 2: Main compressor outlet
            # Account for pressure drops in LTR cold side
            P_2 = P_high + config.dP_LTR_cold + config.dP_HTR_cold
            mc_result = self.main_comp.calculate(T_1, P_low, P_2, m_dot_MC)
            T_2 = mc_result.T_out
            h_2 = mc_result.h_out

            # State 5: Turbine inlet
            h_5 = co2.h(T_5, P_high)

            # State 6: Turbine outlet
            # Account for pressure drops in HTR hot side
            P_6 = P_low + config.dP_HTR_hot + config.dP_LTR_hot
            turb_result = self.turbine.calculate(T_5, P_high, P_6, m_dot)
            T_6 = turb_result.T_out
            h_6 = turb_result.h_out

            # Iterative solve for recuperators
            # Initial guess for state 3 (merge point)
            T_3_guess = T_2 + 50  # Guess merge temp higher than MC outlet

            # Runtime-oriented limits for robust convergence without long stalls.
            max_iter = 40
            tol = 0.2  # K

            T_3 = T_3_guess
            converged = False

            for iteration in range(max_iter):
                T_3_old = T_3

                # HTR: hot side 6->6a, cold side 3->4
                P_3 = P_high + config.dP_HTR_cold  # Before HTR cold pressure drop
                htr_result = self.HTR.solve(
                    T_hot_in=T_6,
                    P_hot_in=P_6,
                    T_cold_in=T_3,
                    P_cold_in=P_3,
                    m_dot=m_dot
                )

                if not htr_result.converged:
                    return CycleResult(
                        converged=False, feasible=False, state=None,
                        W_turbine=0, W_MC=0, W_RC=0, W_gross=0,
                        Q_in=0, Q_HTR=0, Q_LTR=0, Q_reject=0,
                        dT_pinch_HTR=0, dT_pinch_LTR=0,
                        pinch_HTR_segment=0, pinch_LTR_segment=0,
                        eta_thermal=0,
                        constraints=constraints, violations=violations, margins=margins,
                        solver_status=SolverStatus.NUMERICAL_FAIL.value,
                        error_message=f"HTR failed to converge: {htr_result.error_message}"
                    )

                T_6a = htr_result.T_hot_out
                h_6a = htr_result.h_hot_out
                P_6a = htr_result.P_hot_out

                T_4 = htr_result.T_cold_out
                h_4 = htr_result.h_cold_out
                P_4 = htr_result.P_cold_out

                # LTR: hot side 6a->7, cold side 2->2a
                P_2_ltr = P_2  # MC outlet pressure
                ltr_result = self.LTR.solve(
                    T_hot_in=T_6a,
                    P_hot_in=P_6a,
                    m_dot_hot=m_dot,
                    T_cold_in=T_2,
                    P_cold_in=P_2_ltr,
                    m_dot_cold=m_dot_MC
                )

                if not ltr_result.converged:
                    return CycleResult(
                        converged=False, feasible=False, state=None,
                        W_turbine=0, W_MC=0, W_RC=0, W_gross=0,
                        Q_in=0, Q_HTR=0, Q_LTR=0, Q_reject=0,
                        dT_pinch_HTR=0, dT_pinch_LTR=0,
                        pinch_HTR_segment=0, pinch_LTR_segment=0,
                        eta_thermal=0,
                        constraints=constraints, violations=violations, margins=margins,
                        solver_status=SolverStatus.NUMERICAL_FAIL.value,
                        error_message=f"LTR failed to converge: {ltr_result.error_message}"
                    )

                T_7 = ltr_result.T_hot_out
                h_7 = ltr_result.h_hot_out
                P_7 = ltr_result.P_hot_out

                T_2a = ltr_result.T_cold_out
                h_2a = ltr_result.h_cold_out
                P_2a = ltr_result.P_cold_out

                # Recompressor: state 7 -> state 9
                # Recompressor inlet is at P_7 (same as LTR hot outlet)
                # Outlet pressure should match merge point pressure
                P_9 = P_3  # Same as HTR cold inlet
                rc_result = self.recomp.calculate(T_7, P_7, P_9, m_dot_RC)
                T_9 = rc_result.T_out
                h_9 = rc_result.h_out

                # Merge: streams 2a and 9 -> state 3
                T_3_new, h_3, _ = merge_streams(
                    h_2a, m_dot_MC,
                    h_9, m_dot_RC,
                    P_3
                )

                # Relaxation
                T_3 = 0.7 * T_3_new + 0.3 * T_3

                if abs(T_3 - T_3_old) < tol:
                    converged = True
                    break

            if not converged:
                return CycleResult(
                    converged=False, feasible=False, state=None,
                    W_turbine=0, W_MC=0, W_RC=0, W_gross=0,
                    Q_in=0, Q_HTR=0, Q_LTR=0, Q_reject=0,
                    dT_pinch_HTR=0, dT_pinch_LTR=0,
                    pinch_HTR_segment=0, pinch_LTR_segment=0,
                    eta_thermal=0,
                    constraints=constraints, violations=violations, margins=margins,
                    solver_status=SolverStatus.NUMERICAL_FAIL.value,
                    error_message="Cycle iteration did not converge"
                )

            # Calculate final values
            W_turbine = turb_result.W_turbine
            W_MC = mc_result.W_compressor
            W_RC = rc_result.W_compressor
            W_gross = W_turbine - W_MC - W_RC

            # Heat input (IHX)
            Q_in_calc = m_dot * (h_5 - h_4)
            Q_in = Q_in if Q_in is not None else Q_in_calc

            # Heat rejection
            Q_reject = m_dot_MC * (h_7 - h_1)

            # Recuperator duties
            Q_HTR = htr_result.Q
            Q_LTR = ltr_result.Q

            # Efficiency
            eta_thermal = W_gross / Q_in if Q_in > 0 else 0

            # Pinch constraints
            dT_pinch_HTR = htr_result.dT_pinch_min
            dT_pinch_LTR = ltr_result.dT_pinch_min

            margins['pinch_HTR_min'] = dT_pinch_HTR - config.dT_pinch_min
            margins['pinch_LTR_min'] = dT_pinch_LTR - config.dT_pinch_min

            constraints['P02'] = htr_result.feasible
            constraints['P03'] = ltr_result.feasible

            if not constraints['P02']:
                violations.append(
                    f"[P02] HTR pinch violation: {dT_pinch_HTR:.2f}K < {config.dT_pinch_min}K "
                    f"at segment {htr_result.pinch_segment}"
                )
            if not constraints['P03']:
                violations.append(
                    f"[P03] LTR pinch violation: {dT_pinch_LTR:.2f}K < {config.dT_pinch_min}K "
                    f"at segment {ltr_result.pinch_segment}"
                )

            # Work constraints
            constraints['E01'] = W_gross > 0
            margins['W_gross'] = W_gross

            if not constraints['E01']:
                violations.append(f"[E01] Negative gross work: {W_gross/1e6:.3f} MW")

            # Energy closure check
            energy_in = Q_in
            energy_out = W_gross + Q_reject
            energy_residual = abs(energy_in - energy_out) / Q_in if Q_in > 0 else 0
            margins['energy_residual'] = energy_residual
            margins['energy_residual_margin'] = config.energy_closure_tolerance - energy_residual
            constraints['E03'] = energy_residual < config.energy_closure_tolerance

            if not constraints['E03']:
                violations.append(
                    f"[E03] Energy balance residual: {energy_residual*100:.3f}% > {config.energy_closure_tolerance*100:.2f}%"
                )

            # Build cycle state
            state = CycleState(
                T_1=T_1, P_1=P_low, h_1=h_1,
                T_2=T_2, P_2=P_2, h_2=h_2,
                T_2a=T_2a, P_2a=P_2a, h_2a=h_2a,
                T_3=T_3, P_3=P_3, h_3=h_3,
                T_4=T_4, P_4=P_4, h_4=h_4,
                T_5=T_5, P_5=P_high, h_5=h_5,
                T_6=T_6, P_6=P_6, h_6=h_6,
                T_6a=T_6a, P_6a=P_6a, h_6a=h_6a,
                T_7=T_7, P_7=P_7, h_7=h_7,
                T_8=T_1, P_8=P_low, h_8=h_1,  # Pre-cooler outlet = state 1
                T_9=T_9, P_9=P_9, h_9=h_9,
                m_dot_total=m_dot,
                f_recomp=f_recomp,
                m_dot_MC=m_dot_MC,
                m_dot_RC=m_dot_RC
            )

            # Overall feasibility
            feasible = all(constraints.values())

            return CycleResult(
                converged=True,
                feasible=feasible,
                state=state,
                W_turbine=W_turbine,
                W_MC=W_MC,
                W_RC=W_RC,
                W_gross=W_gross,
                Q_in=Q_in,
                Q_HTR=Q_HTR,
                Q_LTR=Q_LTR,
                Q_reject=Q_reject,
                dT_pinch_HTR=dT_pinch_HTR,
                dT_pinch_LTR=dT_pinch_LTR,
                pinch_HTR_segment=htr_result.pinch_segment,
                pinch_LTR_segment=ltr_result.pinch_segment,
                eta_thermal=eta_thermal,
                constraints=constraints,
                violations=violations,
                margins=margins,
                solver_status=(SolverStatus.CONVERGED.value if feasible else SolverStatus.INFEASIBLE.value),
                energy_closure_rel=energy_residual,
                diagnostic_breakdown={
                    "energy_in": energy_in,
                    "energy_out": energy_out,
                    "energy_residual": energy_residual,
                    "W_turbine": W_turbine,
                    "W_MC": W_MC,
                    "W_RC": W_RC,
                },
                assumption_mode="cycle_default"
            )

        except Exception as e:
            return CycleResult(
                converged=False, feasible=False, state=None,
                W_turbine=0, W_MC=0, W_RC=0, W_gross=0,
                Q_in=0, Q_HTR=0, Q_LTR=0, Q_reject=0,
                dT_pinch_HTR=0, dT_pinch_LTR=0,
                pinch_HTR_segment=0, pinch_LTR_segment=0,
                eta_thermal=0,
                constraints=constraints, violations=violations, margins=margins,
                solver_status=SolverStatus.NUMERICAL_FAIL.value,
                error_message=f"Cycle calculation error: {e}"
            )
