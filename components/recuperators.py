"""
Recuperator components: High-Temperature Recuperator (HTR) and Low-Temperature Recuperator (LTR).
Uses segmented enthalpy-based model with per-segment pinch checks.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from properties.fluids import co2, FluidState
from hx.segmented_hx import SegmentedHXSolver, HXResult


@dataclass
class RecuperatorConfig:
    """Recuperator configuration parameters."""
    # Pressure drops
    dP_hot: float = 50e3  # Hot side pressure drop [Pa]
    dP_cold: float = 50e3  # Cold side pressure drop [Pa]

    # Pinch constraints
    dT_pinch_min: float = 10.0  # Minimum pinch [K]

    # Discretization
    n_segments: int = 10

    # Geometry and pressure-drop mode
    D_h: float = 2e-3  # Hydraulic diameter [m]
    L_channel: float = 0.5  # Channel length [m]
    A_flow: float = 0.02  # Flow area per side [m²]
    use_friction_dP: bool = False
    use_ua_limit: bool = True


@dataclass
class RecuperatorResult:
    """Result from recuperator solve."""
    # Convergence status
    converged: bool
    feasible: bool

    # Hot side (turbine exhaust -> cooler/LTR)
    T_hot_in: float
    T_hot_out: float
    P_hot_in: float
    P_hot_out: float
    h_hot_in: float
    h_hot_out: float

    # Cold side (compressor outlet -> IHX/HTR)
    T_cold_in: float
    T_cold_out: float
    P_cold_in: float
    P_cold_out: float
    h_cold_in: float
    h_cold_out: float

    # Mass flows
    m_dot_hot: float
    m_dot_cold: float

    # Heat duty and pinch
    Q: float  # Heat transferred [W]
    dT_pinch_min: float  # Minimum pinch [K]
    pinch_segment: int  # Segment where pinch occurs

    # Detailed results
    hx_result: Optional[HXResult] = None
    error_message: Optional[str] = None


class HighTemperatureRecuperator:
    """
    High-Temperature Recuperator (HTR).

    Hot side: Turbine exhaust (state 6) -> HTR hot out (state 6a)
    Cold side: Mixed stream after LTR (state 3) -> IHX inlet (state 4)

    Both sides have same mass flow (full flow through HTR).
    """

    def __init__(self, config: Optional[RecuperatorConfig] = None):
        self.config = config or RecuperatorConfig()
        self.hx_solver = SegmentedHXSolver(
            n_segments=self.config.n_segments,
            dT_pinch_min=self.config.dT_pinch_min
        )

    def solve(self,
              T_hot_in: float,
              P_hot_in: float,
              T_cold_in: float,
              P_cold_in: float,
              m_dot: float) -> RecuperatorResult:
        """
        Solve HTR for given inlet conditions.

        Args:
            T_hot_in: Hot side inlet temperature [K] (state 6)
            P_hot_in: Hot side inlet pressure [Pa]
            T_cold_in: Cold side inlet temperature [K] (state 3)
            P_cold_in: Cold side inlet pressure [Pa]
            m_dot: Mass flow rate [kg/s] (same both sides)

        Returns:
            RecuperatorResult with all outputs
        """
        # Get inlet enthalpies
        try:
            h_hot_in = co2.h(T_hot_in, P_hot_in)
            h_cold_in = co2.h(T_cold_in, P_cold_in)
        except Exception as e:
            return RecuperatorResult(
                converged=False, feasible=False,
                T_hot_in=T_hot_in, T_hot_out=T_hot_in,
                P_hot_in=P_hot_in, P_hot_out=P_hot_in,
                h_hot_in=0, h_hot_out=0,
                T_cold_in=T_cold_in, T_cold_out=T_cold_in,
                P_cold_in=P_cold_in, P_cold_out=P_cold_in,
                h_cold_in=0, h_cold_out=0,
                m_dot_hot=m_dot, m_dot_cold=m_dot,
                Q=0, dT_pinch_min=0, pinch_segment=0,
                error_message=f"Property error at inlet: {e}"
            )

        # Solve using segmented HX solver
        hx_result = self.hx_solver.solve(
            T_hot_in=T_hot_in,
            P_hot_in=P_hot_in,
            m_dot_hot=m_dot,
            T_cold_in=T_cold_in,
            P_cold_in=P_cold_in,
            m_dot_cold=m_dot,
            h_func_hot=co2.h,
            T_from_Ph_hot=co2.T_from_Ph,
            h_func_cold=co2.h,
            T_from_Ph_cold=co2.T_from_Ph,
            rho_func_hot=co2.rho,
            mu_func_hot=co2.mu,
            rho_func_cold=co2.rho,
            mu_func_cold=co2.mu,
            dP_hot_total=self.config.dP_hot,
            dP_cold_total=self.config.dP_cold,
            D_h=self.config.D_h,
            L_channel=self.config.L_channel,
            A_flow_hot=self.config.A_flow,
            A_flow_cold=self.config.A_flow,
            use_friction_dP=self.config.use_friction_dP,
            cp_func_hot=co2.cp,
            cp_func_cold=co2.cp,
            use_ua_limit=self.config.use_ua_limit,
        )

        return RecuperatorResult(
            converged=hx_result.converged,
            feasible=hx_result.feasible,
            T_hot_in=T_hot_in,
            T_hot_out=hx_result.T_hot_out,
            P_hot_in=P_hot_in,
            P_hot_out=hx_result.P_hot_out,
            h_hot_in=h_hot_in,
            h_hot_out=hx_result.h_hot_out,
            T_cold_in=T_cold_in,
            T_cold_out=hx_result.T_cold_out,
            P_cold_in=P_cold_in,
            P_cold_out=hx_result.P_cold_out,
            h_cold_in=h_cold_in,
            h_cold_out=hx_result.h_cold_out,
            m_dot_hot=m_dot,
            m_dot_cold=m_dot,
            Q=hx_result.Q_total,
            dT_pinch_min=hx_result.dT_pinch_min,
            pinch_segment=hx_result.pinch_segment,
            hx_result=hx_result,
            error_message=hx_result.error_message
        )


class LowTemperatureRecuperator:
    """
    Low-Temperature Recuperator (LTR).

    Hot side: HTR hot outlet (state 6a) -> Pre-cooler/split (state 7)
              Full mass flow m_dot
    Cold side: Main compressor outlet (state 2) -> Merge point (state 2a)
               Partial mass flow (1-f) * m_dot where f is recompression fraction

    Note: The hot side has higher mass flow than cold side in recompression cycle.
    """

    def __init__(self, config: Optional[RecuperatorConfig] = None):
        self.config = config or RecuperatorConfig()
        self.hx_solver = SegmentedHXSolver(
            n_segments=self.config.n_segments,
            dT_pinch_min=self.config.dT_pinch_min
        )

    def solve(self,
              T_hot_in: float,
              P_hot_in: float,
              m_dot_hot: float,
              T_cold_in: float,
              P_cold_in: float,
              m_dot_cold: float) -> RecuperatorResult:
        """
        Solve LTR for given inlet conditions.

        Args:
            T_hot_in: Hot side inlet temperature [K] (state 6a from HTR)
            P_hot_in: Hot side inlet pressure [Pa]
            m_dot_hot: Hot side mass flow [kg/s] (full flow)
            T_cold_in: Cold side inlet temperature [K] (state 2 from MC)
            P_cold_in: Cold side inlet pressure [Pa]
            m_dot_cold: Cold side mass flow [kg/s] ((1-f)*m_dot)

        Returns:
            RecuperatorResult with all outputs
        """
        # Get inlet enthalpies
        try:
            h_hot_in = co2.h(T_hot_in, P_hot_in)
            h_cold_in = co2.h(T_cold_in, P_cold_in)
        except Exception as e:
            return RecuperatorResult(
                converged=False, feasible=False,
                T_hot_in=T_hot_in, T_hot_out=T_hot_in,
                P_hot_in=P_hot_in, P_hot_out=P_hot_in,
                h_hot_in=0, h_hot_out=0,
                T_cold_in=T_cold_in, T_cold_out=T_cold_in,
                P_cold_in=P_cold_in, P_cold_out=P_cold_in,
                h_cold_in=0, h_cold_out=0,
                m_dot_hot=m_dot_hot, m_dot_cold=m_dot_cold,
                Q=0, dT_pinch_min=0, pinch_segment=0,
                error_message=f"Property error at inlet: {e}"
            )

        # Solve using segmented HX solver
        # Note: mass flows are different for hot and cold sides
        hx_result = self.hx_solver.solve(
            T_hot_in=T_hot_in,
            P_hot_in=P_hot_in,
            m_dot_hot=m_dot_hot,
            T_cold_in=T_cold_in,
            P_cold_in=P_cold_in,
            m_dot_cold=m_dot_cold,
            h_func_hot=co2.h,
            T_from_Ph_hot=co2.T_from_Ph,
            h_func_cold=co2.h,
            T_from_Ph_cold=co2.T_from_Ph,
            rho_func_hot=co2.rho,
            mu_func_hot=co2.mu,
            rho_func_cold=co2.rho,
            mu_func_cold=co2.mu,
            dP_hot_total=self.config.dP_hot,
            dP_cold_total=self.config.dP_cold,
            D_h=self.config.D_h,
            L_channel=self.config.L_channel,
            A_flow_hot=self.config.A_flow,
            A_flow_cold=self.config.A_flow,
            use_friction_dP=self.config.use_friction_dP,
            cp_func_hot=co2.cp,
            cp_func_cold=co2.cp,
            use_ua_limit=self.config.use_ua_limit,
        )

        return RecuperatorResult(
            converged=hx_result.converged,
            feasible=hx_result.feasible,
            T_hot_in=T_hot_in,
            T_hot_out=hx_result.T_hot_out,
            P_hot_in=P_hot_in,
            P_hot_out=hx_result.P_hot_out,
            h_hot_in=h_hot_in,
            h_hot_out=hx_result.h_hot_out,
            T_cold_in=T_cold_in,
            T_cold_out=hx_result.T_cold_out,
            P_cold_in=P_cold_in,
            P_cold_out=hx_result.P_cold_out,
            h_cold_in=h_cold_in,
            h_cold_out=hx_result.h_cold_out,
            m_dot_hot=m_dot_hot,
            m_dot_cold=m_dot_cold,
            Q=hx_result.Q_total,
            dT_pinch_min=hx_result.dT_pinch_min,
            pinch_segment=hx_result.pinch_segment,
            hx_result=hx_result,
            error_message=hx_result.error_message
        )


def merge_streams(h_1: float, m_dot_1: float,
                  h_2: float, m_dot_2: float,
                  P: float) -> tuple:
    """
    Adiabatic mixing of two streams at constant pressure.

    Args:
        h_1, m_dot_1: Enthalpy and mass flow of stream 1
        h_2, m_dot_2: Enthalpy and mass flow of stream 2
        P: Pressure [Pa]

    Returns:
        (T_mix, h_mix, m_dot_total)
    """
    m_dot_total = m_dot_1 + m_dot_2
    h_mix = (h_1 * m_dot_1 + h_2 * m_dot_2) / m_dot_total
    T_mix = co2.T_from_Ph(P, h_mix)

    return T_mix, h_mix, m_dot_total
