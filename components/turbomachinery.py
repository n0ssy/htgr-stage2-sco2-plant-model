"""
Turbomachinery components: Turbine, Main Compressor, and Recompressor.
Uses isentropic efficiency with real-gas property calculations.
"""

from dataclasses import dataclass
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from properties.fluids import co2, FluidState, CO2_T_CRIT, CO2_P_CRIT


@dataclass
class TurbineResult:
    """Result from turbine calculation."""
    # Inlet state
    T_in: float  # [K]
    P_in: float  # [Pa]
    h_in: float  # [J/kg]
    s_in: float  # [J/(kg·K)]

    # Outlet state
    T_out: float  # [K]
    P_out: float  # [Pa]
    h_out: float  # [J/kg]
    s_out: float  # [J/(kg·K)]

    # Performance
    W_turbine: float  # Turbine power output [W]
    m_dot: float  # Mass flow rate [kg/s]
    eta_isentropic: float  # Isentropic efficiency

    # Isentropic reference
    T_out_isentropic: float
    h_out_isentropic: float


@dataclass
class CompressorResult:
    """Result from compressor calculation."""
    # Inlet state
    T_in: float  # [K]
    P_in: float  # [Pa]
    h_in: float  # [J/kg]
    s_in: float  # [J/(kg·K)]

    # Outlet state
    T_out: float  # [K]
    P_out: float  # [Pa]
    h_out: float  # [J/kg]
    s_out: float  # [J/(kg·K)]

    # Performance
    W_compressor: float  # Compressor power consumption [W]
    m_dot: float  # Mass flow rate [kg/s]
    eta_isentropic: float  # Isentropic efficiency

    # Isentropic reference
    T_out_isentropic: float
    h_out_isentropic: float

    # Supercritical check
    T_margin_crit: float  # Margin above T_critical at inlet [K]
    P_margin_crit: float  # Margin above P_critical at inlet [Pa]
    inlet_supercritical: bool


class Turbine:
    """
    sCO2 turbine with isentropic efficiency model.
    State 5 -> State 6
    """

    def __init__(self, eta_isentropic: float = 0.90):
        """
        Args:
            eta_isentropic: Isentropic efficiency (default 0.90 from Dostal)
        """
        self.eta = eta_isentropic

    def calculate(self,
                  T_in: float,
                  P_in: float,
                  P_out: float,
                  m_dot: float) -> TurbineResult:
        """
        Calculate turbine performance.

        Args:
            T_in: Inlet temperature [K] (state 5)
            P_in: Inlet pressure [Pa]
            P_out: Outlet pressure [Pa]
            m_dot: Mass flow rate [kg/s]

        Returns:
            TurbineResult with all states and power
        """
        # Inlet state
        state_in = co2.get_state(T_in, P_in)

        # Isentropic expansion
        s_in = state_in.s
        state_out_s = co2.get_state_Ps(P_out, s_in)

        # Actual outlet with efficiency
        h_out_s = state_out_s.h
        h_out = state_in.h - self.eta * (state_in.h - h_out_s)
        state_out = co2.get_state_Ph(P_out, h_out)

        # Turbine power
        W_turbine = m_dot * (state_in.h - state_out.h)

        return TurbineResult(
            T_in=T_in,
            P_in=P_in,
            h_in=state_in.h,
            s_in=state_in.s,
            T_out=state_out.T,
            P_out=P_out,
            h_out=state_out.h,
            s_out=state_out.s,
            W_turbine=W_turbine,
            m_dot=m_dot,
            eta_isentropic=self.eta,
            T_out_isentropic=state_out_s.T,
            h_out_isentropic=h_out_s
        )


class MainCompressor:
    """
    Main compressor for sCO2 cycle.
    State 1 -> State 2
    Handles (1-f) fraction of total mass flow.
    """

    def __init__(self,
                 eta_isentropic: float = 0.89,
                 dT_crit_margin: float = 3.0,
                 dP_crit_margin: float = 0.3e6):
        """
        Args:
            eta_isentropic: Isentropic efficiency (default 0.89 from Dostal)
            dT_crit_margin: Minimum temperature margin above critical [K]
            dP_crit_margin: Minimum pressure margin above critical [Pa]
        """
        self.eta = eta_isentropic
        self.dT_crit_margin = dT_crit_margin
        self.dP_crit_margin = dP_crit_margin

    def calculate(self,
                  T_in: float,
                  P_in: float,
                  P_out: float,
                  m_dot: float) -> CompressorResult:
        """
        Calculate main compressor performance.

        Args:
            T_in: Inlet temperature [K] (state 1)
            P_in: Inlet pressure [Pa]
            P_out: Outlet pressure [Pa]
            m_dot: Mass flow rate [kg/s] ((1-f) * m_dot_total)

        Returns:
            CompressorResult with all states and power
        """
        # Check supercritical margin at inlet
        T_margin = T_in - CO2_T_CRIT
        P_margin = P_in - CO2_P_CRIT
        inlet_supercritical = (T_margin >= self.dT_crit_margin and
                               P_margin >= self.dP_crit_margin)

        # Inlet state
        state_in = co2.get_state(T_in, P_in)

        # Isentropic compression
        s_in = state_in.s
        state_out_s = co2.get_state_Ps(P_out, s_in)

        # Actual outlet with efficiency
        h_out_s = state_out_s.h
        h_out = state_in.h + (h_out_s - state_in.h) / self.eta
        state_out = co2.get_state_Ph(P_out, h_out)

        # Compressor power (positive = consumption)
        W_compressor = m_dot * (state_out.h - state_in.h)

        return CompressorResult(
            T_in=T_in,
            P_in=P_in,
            h_in=state_in.h,
            s_in=state_in.s,
            T_out=state_out.T,
            P_out=P_out,
            h_out=state_out.h,
            s_out=state_out.s,
            W_compressor=W_compressor,
            m_dot=m_dot,
            eta_isentropic=self.eta,
            T_out_isentropic=state_out_s.T,
            h_out_isentropic=h_out_s,
            T_margin_crit=T_margin,
            P_margin_crit=P_margin,
            inlet_supercritical=inlet_supercritical
        )


class Recompressor:
    """
    Recompressor for sCO2 recompression cycle.
    State 7a -> State 9
    Handles fraction f of total mass flow.
    Inlet is at higher temperature than main compressor.
    """

    def __init__(self, eta_isentropic: float = 0.89):
        """
        Args:
            eta_isentropic: Isentropic efficiency (default 0.89 from Dostal)
        """
        self.eta = eta_isentropic

    def calculate(self,
                  T_in: float,
                  P_in: float,
                  P_out: float,
                  m_dot: float) -> CompressorResult:
        """
        Calculate recompressor performance.

        Args:
            T_in: Inlet temperature [K] (state 7a - split from LTR hot outlet)
            P_in: Inlet pressure [Pa]
            P_out: Outlet pressure [Pa]
            m_dot: Mass flow rate [kg/s] (f * m_dot_total)

        Returns:
            CompressorResult with all states and power
        """
        # Inlet state (typically well above critical point)
        state_in = co2.get_state(T_in, P_in)

        # Check supercritical (usually not an issue for recompressor)
        T_margin = T_in - CO2_T_CRIT
        P_margin = P_in - CO2_P_CRIT
        inlet_supercritical = (T_in > CO2_T_CRIT and P_in > CO2_P_CRIT)

        # Isentropic compression
        s_in = state_in.s
        state_out_s = co2.get_state_Ps(P_out, s_in)

        # Actual outlet with efficiency
        h_out_s = state_out_s.h
        h_out = state_in.h + (h_out_s - state_in.h) / self.eta
        state_out = co2.get_state_Ph(P_out, h_out)

        # Compressor power (positive = consumption)
        W_compressor = m_dot * (state_out.h - state_in.h)

        return CompressorResult(
            T_in=T_in,
            P_in=P_in,
            h_in=state_in.h,
            s_in=state_in.s,
            T_out=state_out.T,
            P_out=P_out,
            h_out=state_out.h,
            s_out=state_out.s,
            W_compressor=W_compressor,
            m_dot=m_dot,
            eta_isentropic=self.eta,
            T_out_isentropic=state_out_s.T,
            h_out_isentropic=h_out_s,
            T_margin_crit=T_margin,
            P_margin_crit=P_margin,
            inlet_supercritical=inlet_supercritical
        )


@dataclass
class TurbomachinerySet:
    """Complete set of turbomachinery for recompression cycle."""
    turbine: Turbine
    main_compressor: MainCompressor
    recompressor: Recompressor

    @classmethod
    def default(cls) -> 'TurbomachinerySet':
        """Create turbomachinery set with Dostal default efficiencies."""
        return cls(
            turbine=Turbine(eta_isentropic=0.90),
            main_compressor=MainCompressor(eta_isentropic=0.89),
            recompressor=Recompressor(eta_isentropic=0.89)
        )


def calculate_cycle_work(turbine_result: TurbineResult,
                         mc_result: CompressorResult,
                         rc_result: CompressorResult) -> dict:
    """
    Calculate cycle work summary.

    Returns:
        Dict with W_turbine, W_MC, W_RC, W_gross, W_net
    """
    W_turbine = turbine_result.W_turbine
    W_MC = mc_result.W_compressor
    W_RC = rc_result.W_compressor

    W_gross = W_turbine - W_MC - W_RC

    return {
        'W_turbine': W_turbine,
        'W_MC': W_MC,
        'W_RC': W_RC,
        'W_gross': W_gross,
        'W_net_cycle': W_gross  # Before parasitics
    }
