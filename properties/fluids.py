"""
Fluid properties module using CoolProp for sCO2 and Helium.
Provides thermodynamic property calculations with phase boundary checks.
"""

import CoolProp.CoolProp as CP
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


# CO2 critical properties
CO2_T_CRIT = 304.13  # K
CO2_P_CRIT = 7.377e6  # Pa

# Helium properties (ideal gas approximation valid for He)
HE_CP = 5193.0  # J/(kg·K) - constant for ideal gas
HE_MW = 4.0026e-3  # kg/mol


@dataclass
class FluidState:
    """Thermodynamic state of a fluid."""
    T: float  # Temperature [K]
    P: float  # Pressure [Pa]
    h: float  # Specific enthalpy [J/kg]
    s: float  # Specific entropy [J/(kg·K)]
    rho: float  # Density [kg/m³]
    cp: float  # Specific heat at constant pressure [J/(kg·K)]
    mu: float  # Dynamic viscosity [Pa·s]
    k: float  # Thermal conductivity [W/(m·K)]
    phase: str  # Phase description


class CO2Properties:
    """CoolProp wrapper for CO2 with supercritical checks."""

    def __init__(self):
        self.fluid = "CO2"
        self.T_crit = CO2_T_CRIT
        self.P_crit = CO2_P_CRIT

    def get_state(self, T: float, P: float) -> FluidState:
        """Get full thermodynamic state at T, P."""
        try:
            h = CP.PropsSI('H', 'T', T, 'P', P, self.fluid)
            s = CP.PropsSI('S', 'T', T, 'P', P, self.fluid)
            rho = CP.PropsSI('D', 'T', T, 'P', P, self.fluid)
            cp = CP.PropsSI('C', 'T', T, 'P', P, self.fluid)
            mu = CP.PropsSI('V', 'T', T, 'P', P, self.fluid)
            k = CP.PropsSI('L', 'T', T, 'P', P, self.fluid)

            # Determine phase
            if P > self.P_crit and T > self.T_crit:
                phase = "supercritical"
            elif P > self.P_crit:
                phase = "supercritical_liquid"
            elif T > self.T_crit:
                phase = "supercritical_gas"
            else:
                phase_code = CP.PropsSI('Phase', 'T', T, 'P', P, self.fluid)
                if phase_code == 0:
                    phase = "liquid"
                elif phase_code == 6:
                    phase = "gas"
                else:
                    phase = "two-phase"

            return FluidState(T=T, P=P, h=h, s=s, rho=rho, cp=cp, mu=mu, k=k, phase=phase)
        except Exception as e:
            raise ValueError(f"CO2 property calculation failed at T={T:.2f} K, P={P/1e6:.3f} MPa: {e}")

    def get_state_Ph(self, P: float, h: float) -> FluidState:
        """Get state from pressure and enthalpy."""
        try:
            T = CP.PropsSI('T', 'P', P, 'H', h, self.fluid)
            return self.get_state(T, P)
        except Exception as e:
            raise ValueError(f"CO2 property calculation failed at P={P/1e6:.3f} MPa, h={h/1e3:.2f} kJ/kg: {e}")

    def get_state_Ps(self, P: float, s: float) -> FluidState:
        """Get state from pressure and entropy (for isentropic processes)."""
        try:
            T = CP.PropsSI('T', 'P', P, 'S', s, self.fluid)
            return self.get_state(T, P)
        except Exception as e:
            raise ValueError(f"CO2 property calculation failed at P={P/1e6:.3f} MPa, s={s:.2f} J/(kg·K): {e}")

    def h(self, T: float, P: float) -> float:
        """Get enthalpy at T, P."""
        return CP.PropsSI('H', 'T', T, 'P', P, self.fluid)

    def s(self, T: float, P: float) -> float:
        """Get entropy at T, P."""
        return CP.PropsSI('S', 'T', T, 'P', P, self.fluid)

    def T_from_Ph(self, P: float, h: float) -> float:
        """Get temperature from P and h."""
        return CP.PropsSI('T', 'P', P, 'H', h, self.fluid)

    def T_from_Ps(self, P: float, s: float) -> float:
        """Get temperature from P and s."""
        return CP.PropsSI('T', 'P', P, 'S', s, self.fluid)

    def rho(self, T: float, P: float) -> float:
        """Get density at T, P."""
        return CP.PropsSI('D', 'T', T, 'P', P, self.fluid)

    def cp(self, T: float, P: float) -> float:
        """Get specific heat at T, P."""
        return CP.PropsSI('C', 'T', T, 'P', P, self.fluid)

    def mu(self, T: float, P: float) -> float:
        """Get dynamic viscosity at T, P."""
        return CP.PropsSI('V', 'T', T, 'P', P, self.fluid)

    def k_thermal(self, T: float, P: float) -> float:
        """Get thermal conductivity at T, P."""
        return CP.PropsSI('L', 'T', T, 'P', P, self.fluid)

    def is_supercritical(self, T: float, P: float) -> bool:
        """Check if state is supercritical."""
        return T > self.T_crit and P > self.P_crit

    def supercritical_margin(self, T: float, P: float) -> Tuple[float, float]:
        """Return margin above critical point (T_margin, P_margin)."""
        return (T - self.T_crit, P - self.P_crit)


class HeliumProperties:
    """Helium properties (ideal gas with real-gas corrections where needed)."""

    def __init__(self):
        self.fluid = "Helium"
        self.cp = HE_CP
        self.R = 2077.22  # J/(kg·K) specific gas constant

    def get_state(self, T: float, P: float) -> FluidState:
        """Get full thermodynamic state at T, P."""
        try:
            h = CP.PropsSI('H', 'T', T, 'P', P, self.fluid)
            s = CP.PropsSI('S', 'T', T, 'P', P, self.fluid)
            rho = CP.PropsSI('D', 'T', T, 'P', P, self.fluid)
            cp = CP.PropsSI('C', 'T', T, 'P', P, self.fluid)
            mu = CP.PropsSI('V', 'T', T, 'P', P, self.fluid)
            k = CP.PropsSI('L', 'T', T, 'P', P, self.fluid)

            return FluidState(T=T, P=P, h=h, s=s, rho=rho, cp=cp, mu=mu, k=k, phase="gas")
        except Exception as e:
            raise ValueError(f"Helium property calculation failed at T={T:.2f} K, P={P/1e6:.3f} MPa: {e}")

    def get_state_Ph(self, P: float, h: float) -> FluidState:
        """Get state from pressure and enthalpy."""
        try:
            T = CP.PropsSI('T', 'P', P, 'H', h, self.fluid)
            return self.get_state(T, P)
        except Exception as e:
            raise ValueError(f"Helium property calculation failed at P={P/1e6:.3f} MPa, h={h/1e3:.2f} kJ/kg: {e}")

    def h(self, T: float, P: float) -> float:
        """Get enthalpy at T, P."""
        return CP.PropsSI('H', 'T', T, 'P', P, self.fluid)

    def s(self, T: float, P: float) -> float:
        """Get entropy at T, P."""
        return CP.PropsSI('S', 'T', T, 'P', P, self.fluid)

    def T_from_Ph(self, P: float, h: float) -> float:
        """Get temperature from P and h."""
        return CP.PropsSI('T', 'P', P, 'H', h, self.fluid)

    def rho(self, T: float, P: float) -> float:
        """Get density at T, P."""
        return CP.PropsSI('D', 'T', T, 'P', P, self.fluid)

    def cp_func(self, T: float, P: float) -> float:
        """Get specific heat at T, P."""
        return CP.PropsSI('C', 'T', T, 'P', P, self.fluid)

    def mu(self, T: float, P: float) -> float:
        """Get dynamic viscosity at T, P."""
        return CP.PropsSI('V', 'T', T, 'P', P, self.fluid)

    def k_thermal(self, T: float, P: float) -> float:
        """Get thermal conductivity at T, P."""
        return CP.PropsSI('L', 'T', T, 'P', P, self.fluid)


class AirProperties:
    """Air properties for dry cooler calculations."""

    def __init__(self):
        self.fluid = "Air"
        self.cp_nominal = 1006.0  # J/(kg·K)
        self.R = 287.0  # J/(kg·K)

    def rho(self, T: float, P: float = 101325.0) -> float:
        """Get density at T, P (default atmospheric)."""
        return CP.PropsSI('D', 'T', T, 'P', P, self.fluid)

    def cp(self, T: float, P: float = 101325.0) -> float:
        """Get specific heat at T, P."""
        return CP.PropsSI('C', 'T', T, 'P', P, self.fluid)

    def mu(self, T: float, P: float = 101325.0) -> float:
        """Get dynamic viscosity at T, P."""
        return CP.PropsSI('V', 'T', T, 'P', P, self.fluid)

    def k_thermal(self, T: float, P: float = 101325.0) -> float:
        """Get thermal conductivity at T, P."""
        return CP.PropsSI('L', 'T', T, 'P', P, self.fluid)

    def Pr(self, T: float, P: float = 101325.0) -> float:
        """Get Prandtl number."""
        return self.cp(T, P) * self.mu(T, P) / self.k_thermal(T, P)


# Global instances
co2 = CO2Properties()
helium = HeliumProperties()
air = AirProperties()
