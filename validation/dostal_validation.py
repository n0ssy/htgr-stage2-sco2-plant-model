"""
Dostal-style validation case for sCO2 recompression cycle.
Reference: Dostal, V. (2004) "A Supercritical Carbon Dioxide Cycle for Next Generation Nuclear Reactors"
MIT PhD Thesis
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cycle.sco2_cycle import SCO2RecompressionCycle, CycleConfig


@dataclass
class DostalReferenceCase:
    """Dostal reference case parameters and expected results."""
    # Operating conditions
    T_1: float = 305.15  # 32°C - compressor inlet
    T_5: float = 823.15  # 550°C - turbine inlet
    P_high: float = 20e6  # 20 MPa
    P_low: float = 7.7e6  # 7.7 MPa
    f_recomp: float = 0.35  # Recompression fraction (typical optimal)

    # Component efficiencies
    eta_turbine: float = 0.90
    eta_MC: float = 0.89
    eta_RC: float = 0.89

    # Expected efficiency (approximate from Dostal thesis)
    eta_thermal_expected: float = 0.45  # ~45% for these conditions
    # Stage-2 interim acceptance band until RR provides a tighter requirement.
    eta_thermal_tolerance: float = 0.05  # ±5% tolerance


def run_dostal_validation(verbose: bool = True) -> Tuple[bool, Dict]:
    """
    Run Dostal-style validation case.

    Args:
        verbose: Print detailed output

    Returns:
        (passed, results_dict)
    """
    ref = DostalReferenceCase()

    # Configure cycle with Dostal parameters
    config = CycleConfig(
        eta_turbine=ref.eta_turbine,
        eta_MC=ref.eta_MC,
        eta_RC=ref.eta_RC,
        dT_pinch_min=5.0,  # Relaxed for validation
        n_segments=20,
        dT_crit_margin=1.0,  # Relaxed for benchmark comparability
        dP_crit_margin=0.2e6
    )

    cycle = SCO2RecompressionCycle(config)

    # Run with reference mass flow (calculated to give reasonable power)
    # For 100 MW thermal input
    Q_th = 100e6  # 100 MW thermal
    m_dot_estimate = Q_th / (1200 * (ref.T_5 - ref.T_1))  # Rough estimate
    m_dot = 250  # kg/s typical for 100 MW

    result = cycle.solve(
        T_1=ref.T_1,
        T_5=ref.T_5,
        P_high=ref.P_high,
        P_low=ref.P_low,
        m_dot=m_dot,
        f_recomp=ref.f_recomp
    )

    results = {
        'converged': result.converged,
        'feasible': result.feasible,
        'eta_thermal': result.eta_thermal,
        'eta_expected': ref.eta_thermal_expected,
        'eta_tolerance': ref.eta_thermal_tolerance,
        'W_gross_MW': result.W_gross / 1e6,
        'Q_in_MW': result.Q_in / 1e6,
        'Q_reject_MW': result.Q_reject / 1e6,
        'Q_HTR_MW': result.Q_HTR / 1e6,
        'Q_LTR_MW': result.Q_LTR / 1e6,
        'W_turbine_MW': result.W_turbine / 1e6,
        'W_MC_MW': result.W_MC / 1e6,
        'W_RC_MW': result.W_RC / 1e6,
        'dT_pinch_HTR': result.dT_pinch_HTR,
        'dT_pinch_LTR': result.dT_pinch_LTR,
        'violations': result.violations,
        'margins': result.margins
    }

    if result.state:
        results['state'] = {
            'T_1': result.state.T_1 - 273.15,  # °C
            'T_2': result.state.T_2 - 273.15,
            'T_3': result.state.T_3 - 273.15,
            'T_4': result.state.T_4 - 273.15,
            'T_5': result.state.T_5 - 273.15,
            'T_6': result.state.T_6 - 273.15,
            'T_7': result.state.T_7 - 273.15,
            'T_9': result.state.T_9 - 273.15,
        }

    # Check pass/fail
    eta_error = abs(result.eta_thermal - ref.eta_thermal_expected)
    passed = (
        result.converged and
        eta_error <= ref.eta_thermal_tolerance
    )

    results['passed'] = passed
    results['eta_error'] = eta_error

    if verbose:
        print("\n" + "=" * 60)
        print("DOSTAL VALIDATION CASE")
        print("=" * 60)
        print(f"Operating Conditions:")
        print(f"  T_1 (compressor inlet): {ref.T_1 - 273.15:.1f}°C")
        print(f"  T_5 (turbine inlet):    {ref.T_5 - 273.15:.1f}°C")
        print(f"  P_high:                 {ref.P_high / 1e6:.1f} MPa")
        print(f"  P_low:                  {ref.P_low / 1e6:.2f} MPa")
        print(f"  f_recomp:               {ref.f_recomp:.2f}")
        print(f"  m_dot:                  {m_dot:.1f} kg/s")
        print()
        print(f"Results:")
        print(f"  Converged:              {result.converged}")
        print(f"  Feasible:               {result.feasible}")
        print(f"  Thermal efficiency:     {result.eta_thermal * 100:.2f}%")
        print(f"  Expected efficiency:    {ref.eta_thermal_expected * 100:.1f}% ± {ref.eta_thermal_tolerance * 100:.1f}%")
        print(f"  Efficiency error:       {eta_error * 100:.2f}%")
        print()
        print(f"  W_turbine:              {result.W_turbine / 1e6:.2f} MW")
        print(f"  W_MC:                   {result.W_MC / 1e6:.2f} MW")
        print(f"  W_RC:                   {result.W_RC / 1e6:.2f} MW")
        print(f"  W_gross:                {result.W_gross / 1e6:.2f} MW")
        print(f"  Q_in:                   {result.Q_in / 1e6:.2f} MW")
        print(f"  Q_reject:               {result.Q_reject / 1e6:.2f} MW")
        print()
        print(f"  HTR duty:               {result.Q_HTR / 1e6:.2f} MW")
        print(f"  LTR duty:               {result.Q_LTR / 1e6:.2f} MW")
        print(f"  HTR pinch:              {result.dT_pinch_HTR:.1f} K")
        print(f"  LTR pinch:              {result.dT_pinch_LTR:.1f} K")

        if result.state:
            print()
            print("State Points (°C):")
            for key, val in results['state'].items():
                print(f"  {key}: {val:.1f}°C")

        print()
        if passed:
            print("VALIDATION: PASSED")
        else:
            print("VALIDATION: FAILED")
            if not result.converged:
                print("  - Cycle did not converge")
            if eta_error > ref.eta_thermal_tolerance:
                print(f"  - Efficiency outside tolerance: {eta_error * 100:.2f}% > {ref.eta_thermal_tolerance * 100:.1f}%")
            if result.violations:
                print("  - Constraint violations:")
                for v in result.violations:
                    print(f"    {v}")

        print("=" * 60)

    return passed, results


def run_sensitivity_analysis() -> Dict:
    """Run sensitivity analysis on key parameters."""
    results = {}

    # Vary recompression fraction
    f_values = [0.25, 0.30, 0.35, 0.40, 0.45]
    f_results = []

    config = CycleConfig(
        eta_turbine=0.90,
        eta_MC=0.89,
        eta_RC=0.89,
        dT_pinch_min=5.0,
        n_segments=20
    )
    cycle = SCO2RecompressionCycle(config)

    for f in f_values:
        result = cycle.solve(
            T_1=305.15,
            T_5=823.15,
            P_high=20e6,
            P_low=7.7e6,
            m_dot=250,
            f_recomp=f
        )
        f_results.append({
            'f_recomp': f,
            'eta_thermal': result.eta_thermal if result.converged else None,
            'converged': result.converged,
            'feasible': result.feasible
        })

    results['f_recomp_sensitivity'] = f_results

    return results


if __name__ == "__main__":
    passed, results = run_dostal_validation(verbose=True)
