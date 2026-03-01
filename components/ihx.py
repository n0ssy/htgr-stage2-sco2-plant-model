"""
Intermediate Heat Exchanger (IHX) component.
Couples helium (hot) and sCO2 (cold) sides with segmented enthalpy-based model.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from properties.fluids import co2, helium, FluidState
from hx.segmented_hx import SegmentedHXSolver, HXResult, InfeasibilityType


@dataclass
class IHXConfig:
    """IHX configuration parameters."""
    # Pressure drops
    dP_He: float = 50e3  # Helium side pressure drop [Pa]
    dP_CO2: float = 100e3  # CO2 side pressure drop [Pa]

    # Pinch constraints
    dT_pinch_min: float = 10.0  # Minimum pinch [K]
    dT_approach: float = 30.0  # Design approach temperature [K]

    # Discretization
    n_segments: int = 10

    # Geometry and pressure-drop mode
    D_h: float = 2e-3  # Hydraulic diameter [m]
    L_channel: float = 0.5  # Channel length [m]
    A_flow_He: float = 0.05  # Helium flow area [m²]
    A_flow_CO2: float = 0.05  # CO2 flow area [m²]
    use_friction_dP: bool = False
    use_ua_limit: bool = True


@dataclass
class IHXResult:
    """Result from IHX solve."""
    # Convergence status
    converged: bool
    feasible: bool

    # Helium side
    T_He_in: float
    T_He_out: float
    P_He_in: float
    P_He_out: float
    h_He_in: float
    h_He_out: float
    m_dot_He: float

    # CO2 side
    T_CO2_in: float
    T_CO2_out: float  # This is T_5 (turbine inlet)
    P_CO2_in: float
    P_CO2_out: float
    h_CO2_in: float
    h_CO2_out: float
    m_dot_CO2: float

    # Heat duty and pinch
    Q_IHX: float  # Heat transferred [W]
    dT_pinch_min: float  # Minimum pinch [K]
    pinch_segment: int  # Segment where pinch occurs
    dT_approach_hot: float  # T_He_in - T_CO2_out
    dT_approach_cold: float  # T_He_out - T_CO2_in

    # Detailed results
    hx_result: Optional[HXResult] = None
    error_message: Optional[str] = None


class IHX:
    """
    Intermediate Heat Exchanger coupling helium primary loop to sCO2 cycle.
    Uses segmented enthalpy-based solver with embedded pinch checks.
    """

    def __init__(self, config: Optional[IHXConfig] = None):
        self.config = config or IHXConfig()
        self.hx_solver = SegmentedHXSolver(
            n_segments=self.config.n_segments,
            dT_pinch_min=self.config.dT_pinch_min
        )

    def solve(self,
              T_He_in: float,
              P_He_in: float,
              m_dot_He: float,
              T_CO2_in: float,
              P_CO2_in: float,
              m_dot_CO2: float) -> IHXResult:
        """
        Solve IHX for given inlet conditions.

        Args:
            T_He_in: Helium inlet temperature [K]
            P_He_in: Helium inlet pressure [Pa]
            m_dot_He: Helium mass flow rate [kg/s]
            T_CO2_in: CO2 inlet temperature [K] (state 4 - HTR cold outlet)
            P_CO2_in: CO2 inlet pressure [Pa]
            m_dot_CO2: CO2 mass flow rate [kg/s]

        Returns:
            IHXResult with all outputs
        """
        # Get inlet enthalpies
        try:
            h_He_in = helium.h(T_He_in, P_He_in)
            h_CO2_in = co2.h(T_CO2_in, P_CO2_in)
        except Exception as e:
            return IHXResult(
                converged=False, feasible=False,
                T_He_in=T_He_in, T_He_out=T_He_in,
                P_He_in=P_He_in, P_He_out=P_He_in,
                h_He_in=0, h_He_out=0, m_dot_He=m_dot_He,
                T_CO2_in=T_CO2_in, T_CO2_out=T_CO2_in,
                P_CO2_in=P_CO2_in, P_CO2_out=P_CO2_in,
                h_CO2_in=0, h_CO2_out=0, m_dot_CO2=m_dot_CO2,
                Q_IHX=0, dT_pinch_min=0, pinch_segment=0,
                dT_approach_hot=T_He_in - T_CO2_in,
                dT_approach_cold=0,
                error_message=f"Property error at inlet: {e}"
            )

        # Solve using segmented HX solver
        hx_result = self.hx_solver.solve(
            T_hot_in=T_He_in,
            P_hot_in=P_He_in,
            m_dot_hot=m_dot_He,
            T_cold_in=T_CO2_in,
            P_cold_in=P_CO2_in,
            m_dot_cold=m_dot_CO2,
            h_func_hot=helium.h,
            T_from_Ph_hot=helium.T_from_Ph,
            h_func_cold=co2.h,
            T_from_Ph_cold=co2.T_from_Ph,
            rho_func_hot=helium.rho,
            mu_func_hot=helium.mu,
            rho_func_cold=co2.rho,
            mu_func_cold=co2.mu,
            dP_hot_total=self.config.dP_He,
            dP_cold_total=self.config.dP_CO2,
            D_h=self.config.D_h,
            L_channel=self.config.L_channel,
            A_flow_hot=self.config.A_flow_He,
            A_flow_cold=self.config.A_flow_CO2,
            use_friction_dP=self.config.use_friction_dP,
            cp_func_hot=helium.cp_func,
            cp_func_cold=co2.cp,
            use_ua_limit=self.config.use_ua_limit,
        )

        # Calculate approach temperatures
        dT_approach_hot = T_He_in - hx_result.T_cold_out  # Hot approach
        dT_approach_cold = hx_result.T_hot_out - T_CO2_in  # Cold approach

        return IHXResult(
            converged=hx_result.converged,
            feasible=hx_result.feasible,
            T_He_in=T_He_in,
            T_He_out=hx_result.T_hot_out,
            P_He_in=P_He_in,
            P_He_out=hx_result.P_hot_out,
            h_He_in=h_He_in,
            h_He_out=hx_result.h_hot_out,
            m_dot_He=m_dot_He,
            T_CO2_in=T_CO2_in,
            T_CO2_out=hx_result.T_cold_out,  # This is T_5 (turbine inlet)
            P_CO2_in=P_CO2_in,
            P_CO2_out=hx_result.P_cold_out,
            h_CO2_in=h_CO2_in,
            h_CO2_out=hx_result.h_cold_out,
            m_dot_CO2=m_dot_CO2,
            Q_IHX=hx_result.Q_total,
            dT_pinch_min=hx_result.dT_pinch_min,
            pinch_segment=hx_result.pinch_segment,
            dT_approach_hot=dT_approach_hot,
            dT_approach_cold=dT_approach_cold,
            hx_result=hx_result,
            error_message=hx_result.error_message
        )

    def solve_for_T5(self,
                     T_He_in: float,
                     P_He_in: float,
                     m_dot_He: float,
                     T_CO2_in: float,
                     P_CO2_in: float,
                     m_dot_CO2: float,
                     T_5_target: float) -> IHXResult:
        """
        Solve IHX with target CO2 outlet temperature (turbine inlet).
        This is used in coupled solve to match T_5 requirement.

        Args:
            T_5_target: Target turbine inlet temperature [K]

        Returns:
            IHXResult with feasibility based on achieving target
        """
        result = self.solve(
            T_He_in, P_He_in, m_dot_He,
            T_CO2_in, P_CO2_in, m_dot_CO2
        )

        # Check if achieved T_5 matches target (within tolerance)
        T_5_achieved = result.T_CO2_out
        T_error = abs(T_5_achieved - T_5_target)

        # Update feasibility based on target
        if T_error > 1.0:  # More than 1K error
            result.feasible = False
            result.error_message = (
                f"T_5 mismatch: achieved {T_5_achieved:.2f} K, "
                f"target {T_5_target:.2f} K, error {T_error:.2f} K"
            )

        return result

    def required_He_flow(self,
                         Q_th: float,
                         T_He_in: float,
                         T_He_out: float,
                         P_He: float) -> float:
        """
        Calculate required helium mass flow rate for given thermal duty.

        Args:
            Q_th: Thermal power [W]
            T_He_in: Helium inlet temperature [K]
            T_He_out: Helium outlet (return) temperature [K]
            P_He: Helium pressure [Pa]

        Returns:
            Required helium mass flow rate [kg/s]
        """
        h_He_in = helium.h(T_He_in, P_He)
        h_He_out = helium.h(T_He_out, P_He)

        if h_He_in <= h_He_out:
            raise ValueError("Helium inlet enthalpy must be greater than outlet")

        return Q_th / (h_He_in - h_He_out)
