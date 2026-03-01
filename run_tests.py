#!/usr/bin/env python3
"""
Test runner script for sCO2 plant simulation.

Executes:
1. Cycle-only validation case (Dostal-style) - prints pass/fail and tolerance
2. Full coupled plant solve at T_amb = 40°C - prints feasibility report
3. CO2 reduction calculation with process allocation

Generates:
- assumptions.yaml
- results_baseline.json
- feasibility_report.txt
- co2_reduction_report.txt
"""

import sys
import os
import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import numpy as np

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validation.dostal_validation import run_dostal_validation
from cycle.coupled_solver import CoupledPlantSolver, PlantConfig
from cycle.sco2_cycle import CycleConfig
from components.ihx import IHXConfig
from components.dry_cooler import DryCoolerConfig, DryCoolerGeometry
from properties.fluids import CO2_T_CRIT, CO2_P_CRIT
from process.allocation import (
    ProcessAllocator, AllocationConfig, AllocationObjective,
    DACConfig, HTSEConfig, MethanolConfig,
    calculate_plant_co2_reduction
)


def get_assumptions() -> dict:
    """
    Collect all assumptions and default values used in the simulation.
    """
    assumptions = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'description': 'Complete list of assumptions and default values used in the sCO2 plant simulation'
        },

        'fluid_properties': {
            'CO2_critical_temperature_K': CO2_T_CRIT,
            'CO2_critical_pressure_Pa': CO2_P_CRIT,
            'property_source': 'CoolProp library',
            'helium_model': 'CoolProp (real gas)',
            'air_model': 'CoolProp'
        },

        'reactor_conditions': {
            'Q_thermal_W': 30e6,
            'Q_thermal_MW': 30.0,
            'T_He_hot_K': 1123.15,
            'T_He_hot_C': 850.0,
            'T_He_cold_K': 668.15,
            'T_He_cold_C': 395.0,
            'P_He_Pa': 4.0e6,
            'P_He_MPa': 4.0,
            'reference': 'HTTR design parameters'
        },

        'ambient_conditions': {
            'T_ambient_design_K': 313.15,
            'T_ambient_design_C': 40.0,
            'atmospheric_pressure_Pa': 101325.0
        },

        'cycle_parameters': {
            'pressure_bounds': {
                'P_high_min_MPa': 20.0,
                'P_high_max_MPa': 30.0,
                'P_low_min_MPa': 7.5,
                'P_low_max_MPa': 9.0
            },
            'recompression_fraction_bounds': {
                'f_recomp_min': 0.25,
                'f_recomp_max': 0.45
            },
            'turbomachinery_efficiencies': {
                'eta_turbine': 0.90,
                'eta_main_compressor': 0.89,
                'eta_recompressor': 0.89,
                'reference': 'Dostal (2004)'
            },
            'supercritical_margins': {
                'dT_crit_margin_K': 3.0,
                'dP_crit_margin_Pa': 0.3e6,
                'dP_crit_margin_MPa': 0.3
            },
            'temperature_limits': {
                'T_TIT_max_K': 1073.15,
                'T_TIT_max_C': 800.0,
                'description': 'Maximum turbine inlet temperature (material limit)'
            }
        },

        'heat_exchanger_parameters': {
            'discretization': {
                'n_segments': 10,
                'description': 'Number of segments for enthalpy-based HX models'
            },
            'pinch_constraints': {
                'dT_pinch_min_K': 10.0,
                'description': 'Minimum pinch temperature difference (all HX)'
            },
            'IHX': {
                'dP_He_Pa': 50e3,
                'dP_He_kPa': 50.0,
                'dP_CO2_Pa': 100e3,
                'dP_CO2_kPa': 100.0,
                'dT_approach_K': 30.0,
                'description': 'He-CO2 intermediate heat exchanger'
            },
            'HTR': {
                'dP_hot_Pa': 50e3,
                'dP_hot_kPa': 50.0,
                'dP_cold_Pa': 50e3,
                'dP_cold_kPa': 50.0,
                'description': 'High-temperature recuperator'
            },
            'LTR': {
                'dP_hot_Pa': 50e3,
                'dP_hot_kPa': 50.0,
                'dP_cold_Pa': 50e3,
                'dP_cold_kPa': 50.0,
                'description': 'Low-temperature recuperator'
            }
        },

        'dry_cooler_parameters': {
            'role_in_htgr_scope': 'Boundary-condition sensitivity only (not headline FoM driver)',
            'dT_approach_min_K': 10.0,
            'dT_pinch_min_K': 5.0,
            'dP_CO2_Pa': 30e3,
            'dP_CO2_kPa': 30.0,
            'eta_fan': 0.70,
            'eta_motor': 0.95,
            'fan_power_model': 'Physical (NOT constant factor)',
            'fan_power_equation': 'W_fan = (V_dot_air * dP_air) / (eta_fan * eta_motor)',
            'air_side_dP_correlation': 'Kays & London method for finned tube banks',
            'geometry': {
                'tube_OD_m': 0.0254,
                'tube_ID_m': 0.0229,
                'tube_length_m': 6.0,
                'n_tubes': 200,
                'n_rows': 4,
                'fin_pitch_m': 0.003,
                'face_width_m': 8.0,
                'face_height_m': 3.0
            }
        },

        'solver_settings': {
            'max_iterations': 100,
            'temperature_tolerance_K': 0.1,
            'mass_flow_tolerance_relative': 0.001,
            'energy_closure_tolerance': 0.005,
            'relaxation_factor': 0.5
        },

        'htgr_headline_modes': {
            'heat_rejection_mode_default': 'fixed_boundary',
            'headline_fom_mode': 'htgr_only',
            'coupled_cooler_mode': 'sensitivity_appendix_only',
            'cooling_aux_fraction_default': 0.01
        },

        'feasibility_constraints': {
            'embedded_in_solver': True,
            'constraints_list': [
                'T01: T_comp_inlet > T_critical + margin',
                'T02: P_low > P_critical + margin',
                'T03: T_TIT <= T_TIT_max',
                'T04: T_He_return >= T_He_in_required',
                'P01: IHX pinch >= dT_pinch_min at all segments',
                'P02: HTR pinch >= dT_pinch_min at all segments',
                'P03: LTR pinch >= dT_pinch_min at all segments',
                'P04: Cooling closure satisfied (fixed-boundary assumption or coupled cooler solve)',
                'E01: W_turbine > W_comp_main + W_comp_recomp',
                'E02: W_net > 0 (after parasitics)',
                'E03: Energy closure < 0.5%'
            ]
        },

        'process_allocation': {
            'DAC_solid_sorbent_TVSA': {
                'heat_intensity_kWh_th_per_t_CO2': 1750,
                'elec_intensity_kWh_e_per_t_CO2': 250,
                'T_regen_min_C': 100,
                'capacity_factor': 0.90,
                'reference': 'Climeworks-type solid sorbent DAC'
            },
            'HTSE_SOEC': {
                'elec_intensity_kWh_e_per_kg_H2': 37.5,
                'heat_intensity_kWh_th_per_kg_H2': 6.5,
                'capacity_factor': 0.90,
                'reference': 'Idaho National Laboratory HTSE studies'
            },
            'methanol_synthesis': {
                'kg_CO2_per_kg_MeOH': 1.375,
                'kg_H2_per_kg_MeOH': 0.1875,
                'overall_conversion': 0.97,
                'reference': 'CO2 + 3H2 -> CH3OH + H2O stoichiometry'
            },
            'grid_parameters': {
                'grid_CO2_intensity_g_per_kWh': 400,
                'allow_grid_export_default': False,
                'description': 'Average grid emission factor for optional displaced electricity scenario'
            },
            'objective': 'max_CO2_net',
            'co2_accounting_mode_headline': 'operational_only',
            'co2_boundary_mode_headline': 'operational_only',
            'apply_neutrality_condition_default': True,
            'fuel_emission_factor_kgco2_per_kg_default': 3.15,
            'displacement_factor_default': 1.0,
            'enforce_htse_heat_constraint_default': True,
            'description': 'Constrained optimization to maximize net CO2 reduction under HTGR-only scope'
        }
    }

    return assumptions


def run_full_plant_solve(
    T_ambient_C: float = 40.0,
    heat_rejection_mode: str = "fixed_boundary",
    Q_thermal_MW: float = 30.0,
    scenario_id: str = "S0_BASE_30MW_OPONLY",
    baseline_or_sensitivity: str = "baseline",
    source_assumptions_version: str = "v2",
    cooling_aux_fraction: float = 0.01,
    verbose: bool = True,
) -> dict:
    """
    Run the full plant solve.

    Args:
        T_ambient_C: Ambient temperature in Celsius
        heat_rejection_mode: fixed_boundary (headline) or coupled_cooler (sensitivity)
        verbose: Print detailed output

    Returns:
        Results dictionary
    """
    if heat_rejection_mode not in {"fixed_boundary", "coupled_cooler"}:
        raise ValueError(
            "heat_rejection_mode must be 'fixed_boundary' or 'coupled_cooler'"
        )

    T_ambient = T_ambient_C + 273.15

    cycle_config = CycleConfig(
        P_high_min=20e6,
        P_high_max=30e6,
        P_low_min=7.5e6,
        P_low_max=9.0e6,
        f_recomp_min=0.25,
        f_recomp_max=0.45,
        eta_turbine=0.90,
        eta_MC=0.89,
        eta_RC=0.89,
        dT_crit_margin=3.0,
        dP_crit_margin=0.3e6,
        dT_pinch_min=10.0,
        n_segments=20,
        dP_HTR_hot=50e3,
        dP_HTR_cold=50e3,
        dP_LTR_hot=50e3,
        dP_LTR_cold=50e3,
        T_TIT_max=1073.15,
        energy_closure_tolerance=0.005,
    )

    ihx_config = IHXConfig(
        dP_He=50e3,
        dP_CO2=100e3,
        dT_pinch_min=10.0,
        dT_approach=30.0,
        n_segments=20,
    )

    if heat_rejection_mode == "coupled_cooler":
        # Sensitivity-only coupled cooler uses an explicit larger reference geometry
        # so the appendix comparison reflects a physically achievable duty.
        cooler_geometry = DryCoolerGeometry(
            tube_length=8.0,
            n_tubes=900,
            n_rows=6,
            face_width=40.0,
            face_height=15.0,
        )
        cooler_config = DryCoolerConfig(
            eta_fan=0.70,
            eta_motor=0.95,
            dT_approach_min=10.0,
            dT_pinch_min=5.0,
            n_segments=10,
            dP_CO2=30e3,
            q_closure_tolerance=0.02,
            geometry=cooler_geometry,
        )
        energy_tol = 0.005
    else:
        cooler_config = DryCoolerConfig(
            eta_fan=0.70,
            eta_motor=0.95,
            dT_approach_min=10.0,
            dT_pinch_min=5.0,
            n_segments=10,
            dP_CO2=30e3,
            q_closure_tolerance=0.02,
        )
        energy_tol = 0.005

    plant_config = PlantConfig(
        Q_thermal=Q_thermal_MW * 1e6,
        T_He_hot=1123.15,
        T_He_cold=668.15,
        P_He=4.0e6,
        T_ambient=T_ambient,
        cycle_config=cycle_config,
        ihx_config=ihx_config,
        cooler_config=cooler_config,
        max_iterations=100,
        tolerance=0.1,
        energy_closure_tolerance=energy_tol,
        heat_rejection_mode=heat_rejection_mode,
        T_1_boundary_target=None,
        cooling_aux_fraction=cooling_aux_fraction,
        headline_fom_mode="htgr_only",
    )

    solver = CoupledPlantSolver(plant_config)

    # Mid-range pressure settings and recompression split.
    P_high = 25e6
    P_low = 8.0e6
    f_recomp = 0.35

    result = solver.solve(
        P_high=P_high,
        P_low=P_low,
        f_recomp=f_recomp,
    )

    cooling_block = {
        "heat_rejection_mode": result.heat_rejection_mode,
        "W_cooling_aux_MW": result.W_fan / 1e6,
        "dP_air_Pa": result.dP_air,
        "m_dot_air_kg_s": result.m_dot_air,
        "assumption_mode": result.assumption_mode,
    }
    if result.heat_rejection_mode == "fixed_boundary":
        cooling_block.update(
            {
                "description": "HTGR headline mode using cooling boundary assumptions",
                "cooling_aux_fraction_assumed": plant_config.cooling_aux_fraction,
            }
        )
    else:
        cooling_block.update(
            {
                "description": "Optional coupled cooler sensitivity mode",
                "fan_power_model": "Physical (W_fan = V_dot * dP / eta)",
            }
        )

    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "T_ambient_C": T_ambient_C,
            "solver_version": "2.0.0-htgr-only",
            "heat_rejection_mode": result.heat_rejection_mode,
            "assumption_mode": result.assumption_mode,
            "headline_fom_mode": plant_config.headline_fom_mode,
            "energy_closure_tolerance_rel": plant_config.energy_closure_tolerance,
            "scenario_id": scenario_id,
            "baseline_or_sensitivity": baseline_or_sensitivity,
            "source_assumptions_version": source_assumptions_version,
            "reactor_basis_MWth": Q_thermal_MW,
        },
        "status": {
            "converged": result.converged,
            "feasible": result.feasible,
            "iterations": result.feasibility_report.iterations,
            "residual_norm": result.feasibility_report.residual_norm,
            "solve_time_seconds": result.feasibility_report.solve_time_seconds,
            "energy_closure_rel": result.energy_closure_rel,
            "cycle_solver_status": (
                result.cycle_result.solver_status if result.cycle_result else "N/A"
            ),
        },
        "power_MW": {
            "W_gross": result.W_gross / 1e6,
            "W_cooling_aux": result.W_fan / 1e6,
            "W_aux_other": result.W_aux / 1e6,
            "W_net": result.W_net / 1e6,
            "W_turbine": result.cycle_result.W_turbine / 1e6 if result.cycle_result else 0,
            "W_MC": result.cycle_result.W_MC / 1e6 if result.cycle_result else 0,
            "W_RC": result.cycle_result.W_RC / 1e6 if result.cycle_result else 0,
        },
        "heat_duties_MW": {
            "Q_thermal": result.Q_thermal / 1e6,
            "Q_IHX": result.Q_IHX / 1e6,
            "Q_reject": result.Q_reject / 1e6,
            "Q_HTR": result.cycle_result.Q_HTR / 1e6 if result.cycle_result else 0,
            "Q_LTR": result.cycle_result.Q_LTR / 1e6 if result.cycle_result else 0,
        },
        "temperatures_C": {
            "T_1_compressor_inlet": result.T_1 - 273.15,
            "T_5_turbine_inlet": result.T_5 - 273.15,
            "T_He_return": result.T_He_out - 273.15,
            "T_ambient": T_ambient_C,
        },
        "pressures_MPa": {
            "P_high": result.P_high / 1e6,
            "P_low": result.P_low / 1e6,
        },
        "mass_flows_kg_s": {
            "m_dot_CO2": result.m_dot_CO2,
            "m_dot_He": result.m_dot_He,
            "m_dot_air": result.m_dot_air,
        },
        "recompression": {
            "f_recomp": result.f_recomp,
            "m_dot_MC": result.m_dot_CO2 * (1 - result.f_recomp),
            "m_dot_RC": result.m_dot_CO2 * result.f_recomp,
        },
        "efficiencies": {
            "eta_thermal": result.eta_thermal,
            "eta_thermal_percent": result.eta_thermal * 100,
            "eta_net": result.eta_net,
            "eta_net_percent": result.eta_net * 100,
        },
        "cooling": cooling_block,
        "pinch_temperatures_K": {
            "IHX": result.feasibility_report.margins.get("pinch_IHX_min", 0) + 10,
            "HTR": result.feasibility_report.margins.get("pinch_HTR_min", 0) + 10,
            "LTR": result.feasibility_report.margins.get("pinch_LTR_min", 0) + 10,
            "cooler": (
                result.feasibility_report.margins.get("pinch_cooler_min", 0) + 5
                if heat_rejection_mode == "coupled_cooler"
                else None
            ),
        },
        "diagnostic_breakdown": result.diagnostic_breakdown,
        "margins": result.feasibility_report.margins,
    }

    if result.cycle_result and result.cycle_result.state:
        state = result.cycle_result.state
        results["cycle_states_C"] = {
            "T_1": state.T_1 - 273.15,
            "T_2": state.T_2 - 273.15,
            "T_2a": state.T_2a - 273.15,
            "T_3": state.T_3 - 273.15,
            "T_4": state.T_4 - 273.15,
            "T_5": state.T_5 - 273.15,
            "T_6": state.T_6 - 273.15,
            "T_6a": state.T_6a - 273.15,
            "T_7": state.T_7 - 273.15,
            "T_9": state.T_9 - 273.15,
        }

    if verbose:
        print("\n" + "=" * 60)
        print("HTGR PLANT SOLVE")
        print("=" * 60)
        print(f"Ambient Temperature: {T_ambient_C}°C")
        print(f"Heat Rejection Mode: {heat_rejection_mode}")
        print()
        print(result.feasibility_report.format_report())
        print()
        print("KEY RESULTS:")
        print(f"  Net Power Output:       {result.W_net / 1e6:.3f} MW")
        print(f"  Thermal Efficiency:     {result.eta_thermal * 100:.2f}%")
        print(f"  Net Efficiency:         {result.eta_net * 100:.2f}%")
        print(f"  Energy Closure:         {result.energy_closure_rel * 100:.3f}%")
        print(f"  CO2 Mass Flow:          {result.m_dot_CO2:.1f} kg/s")
        print(f"  Cooling Aux Power:      {result.W_fan / 1e3:.1f} kW")

    return results, result


def run_co2_reduction_analysis(
    plant_result,
    Q_thermal: float = 30e6,
    co2_accounting_mode: str = "operational_only",
    co2_boundary_mode: str = None,  # Legacy alias
    allow_grid_export: bool = False,
    grid_CO2_intensity: float = 400.0,
    enforce_htse_heat_constraint: bool = True,
    scenario_name: str = "headline_htgr_only",
    scenario_id: str = "S0_BASE_30MW_OPONLY",
    baseline_or_sensitivity: str = "baseline",
    source_assumptions_version: str = "v2",
    apply_neutrality_condition: bool = True,
    fuel_emission_factor_kgco2_per_kg: float = 3.15,
    displacement_factor: float = 1.0,
    dac_heat_intensity: float = 1750.0,
    dac_elec_intensity: float = 250.0,
    htse_elec_intensity: float = 37.5,
    htse_heat_intensity: float = 6.5,
    verbose: bool = True,
) -> dict:
    """
    Run CO2 reduction analysis with process allocation.

    Args:
        plant_result: PlantResult from coupled solver
        Q_thermal: Reactor thermal power [W]
        verbose: Print detailed output

    Returns:
        Dictionary with CO2 reduction results
    """
    # Get available energy streams
    W_net = plant_result.W_net  # Net electricity after fan
    W_fan = plant_result.W_fan
    Q_reject = plant_result.Q_reject  # Heat going to cooler

    # Waste heat temperature - from LTR hot outlet (T_7)
    if plant_result.cycle_result and plant_result.cycle_result.state:
        T_waste = plant_result.cycle_result.state.T_7  # ~190°C
    else:
        T_waste = 463.15  # Fallback: 190°C

    mode = co2_accounting_mode
    if co2_boundary_mode is not None and mode == "operational_only":
        mode = co2_boundary_mode

    # Configure process allocation
    alloc_config = AllocationConfig(
        objective=AllocationObjective.MAX_CO2_NET,
        grid_CO2_intensity=grid_CO2_intensity,
        allow_grid_export=allow_grid_export,
        max_grid_export_MW=10.0 if allow_grid_export else 0.0,
        co2_accounting_mode=mode,
        co2_boundary_mode=mode,
        enforce_htse_heat_constraint=enforce_htse_heat_constraint,
        apply_neutrality_condition=apply_neutrality_condition,
        fuel_emission_factor_kgco2_per_kg=fuel_emission_factor_kgco2_per_kg,
        displacement_factor=displacement_factor,
        allocation_auxiliary_power_W=0.0,
        scenario_name=scenario_name,
        scenario_id=scenario_id,
        baseline_or_sensitivity=baseline_or_sensitivity,
        source_assumptions_version=source_assumptions_version,
        dac_config=DACConfig(
            heat_intensity=dac_heat_intensity,  # kWh_th/t_CO2
            elec_intensity=dac_elec_intensity,   # kWh_e/t_CO2
            T_regen_min=373.15,     # 100°C
            capacity_factor=0.90
        ),
        htse_config=HTSEConfig(
            elec_intensity=htse_elec_intensity,    # kWh_e/kg_H2
            heat_intensity=htse_heat_intensity,     # kWh_th/kg_H2
            capacity_factor=0.90
        ),
        methanol_config=MethanolConfig(
            overall_conversion=0.97
        )
    )

    # Run allocation optimization
    alloc_result, summary = calculate_plant_co2_reduction(
        Q_thermal=Q_thermal,
        W_net=W_net,
        Q_waste=Q_reject,
        T_waste=T_waste,
        W_fan=W_fan,
        config=alloc_config
    )

    # Build results dictionary
    co2_results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'description': 'HTGR-only CO2 reduction analysis with explicit boundary assumptions',
            'co2_accounting_mode': mode,
            'co2_boundary_mode': mode,
            'allow_grid_export': allow_grid_export,
            'enforce_htse_heat_constraint': enforce_htse_heat_constraint,
            'scenario_name': scenario_name,
            'scenario_id': scenario_id,
            'baseline_or_sensitivity': baseline_or_sensitivity,
            'source_assumptions_version': source_assumptions_version,
            'conversion_checks_passed': alloc_result.co2_accounting.conversion_checks_passed,
            'boundary_statement': (
                'Headline operational-only boundary'
                if mode == 'operational_only'
                else 'Sensitivity fuel-displacement boundary'
            ),
        },

        'plant_inputs': {
            'Q_thermal_MW': Q_thermal / 1e6,
            'W_net_MW': W_net / 1e6,
            'W_fan_MW': W_fan / 1e6,
            'Q_waste_available_MW': Q_reject / 1e6,
            'T_waste_C': T_waste - 273.15
        },

        'allocation': {
            'W_to_HTSE_MW': alloc_result.W_to_HTSE / 1e6,
            'W_to_DAC_MW': alloc_result.W_to_DAC / 1e6,
            'Q_to_DAC_MW': alloc_result.Q_to_DAC / 1e6,
            'Q_to_HTSE_MW': alloc_result.Q_to_HTSE / 1e6,
            'W_to_grid_MW': alloc_result.W_to_grid / 1e6,
            'Q_to_cooler_MW': alloc_result.Q_to_cooler / 1e6,
            'optimization_converged': alloc_result.converged
        },

        'production_rates': {
            'H2_produced_kg_s': alloc_result.co2_accounting.H2_produced_kg_s,
            'H2_produced_t_yr': alloc_result.co2_accounting.H2_produced_t_yr,
            'CO2_captured_DAC_kg_s': alloc_result.co2_accounting.CO2_captured_DAC_kg_s,
            'CO2_captured_DAC_t_yr': alloc_result.co2_accounting.CO2_captured_DAC_t_yr,
            'MeOH_produced_kg_s': alloc_result.co2_accounting.MeOH_produced_kg_s,
            'MeOH_produced_t_yr': alloc_result.co2_accounting.MeOH_produced_t_yr
        },

        'co2_balance_t_yr': {
            'avoided_grid_displacement': alloc_result.co2_accounting.CO2_avoided_grid_t_yr,
            'captured_DAC': alloc_result.co2_accounting.CO2_captured_DAC_t_yr,
            'embodied_in_products': alloc_result.co2_accounting.CO2_embodied_t_yr,
            'displaced_fossil': alloc_result.co2_accounting.co2_displaced_fossil_t_yr,
            'reemitted_synthetic': alloc_result.co2_accounting.co2_reemitted_synthetic_t_yr,
            'NET_REDUCTION': alloc_result.co2_accounting.CO2_net_reduction_t_yr
        },

        'figures_of_merit': {
            'CO2_reduction_t_per_MWth_per_yr': alloc_result.co2_accounting.CO2_per_MWth_yr,
            'specific_CO2_reduction_kg_per_kWh_th': alloc_result.co2_accounting.specific_CO2_reduction,
            'co2_accounting_mode': alloc_result.co2_accounting.co2_accounting_mode,
            'co2_boundary_mode': alloc_result.co2_accounting.co2_boundary_mode,
            'conversion_checks_passed': alloc_result.co2_accounting.conversion_checks_passed,
            'description': 'Primary FOM: tonnes CO2 reduced per year per MW thermal input'
        },

        'cooling_auxiliary': {
            'cooling_aux_power_MW': W_fan / 1e6,
            'heat_rejected_MW': Q_reject / 1e6,
            'cooling_aux_percent_of_rejected_heat': (W_fan / Q_reject * 100) if Q_reject > 0 else 0
        },

        'scenario_metadata': alloc_result.scenario_metadata,
    }

    if verbose:
        print("\n" + "=" * 70)
        print("CO2 REDUCTION ANALYSIS")
        print("=" * 70)
        print(f"\nPLANT ENERGY STREAMS:")
        print(f"  Reactor Thermal Power:    {Q_thermal/1e6:.2f} MW")
        print(f"  Net Electrical Power:     {W_net/1e6:.3f} MW")
        print(f"  Waste Heat Available:     {Q_reject/1e6:.2f} MW @ {T_waste-273.15:.1f}°C")
        print()
        print("OPTIMAL ALLOCATION:")
        print(f"  Electricity to HTSE:      {alloc_result.W_to_HTSE/1e6:.3f} MW")
        print(f"  Electricity to DAC:       {alloc_result.W_to_DAC/1e6:.3f} MW")
        print(f"  Heat to DAC:              {alloc_result.Q_to_DAC/1e6:.3f} MW")
        print(f"  Heat to HTSE:             {alloc_result.Q_to_HTSE/1e6:.3f} MW")
        print(f"  Electricity to Grid:      {alloc_result.W_to_grid/1e6:.3f} MW")
        print()
        print("ANNUAL PRODUCTION (90% capacity factor):")
        print(f"  Hydrogen:                 {alloc_result.co2_accounting.H2_produced_t_yr:.1f} tonnes/year")
        print(f"  CO2 Captured (DAC):       {alloc_result.co2_accounting.CO2_captured_DAC_t_yr:.1f} tonnes/year")
        print(f"  Methanol:                 {alloc_result.co2_accounting.MeOH_produced_t_yr:.1f} tonnes/year")
        print()
        print("CO2 BALANCE (tonnes/year):")
        print(f"  + Grid Displacement:      {alloc_result.co2_accounting.CO2_avoided_grid_t_yr:.1f}")
        print(f"  + DAC Capture:            {alloc_result.co2_accounting.CO2_captured_DAC_t_yr:.1f}")
        print(f"  - Embodied in Products:   {alloc_result.co2_accounting.CO2_embodied_t_yr:.1f}")
        print(f"  ─────────────────────────────────────")
        print(f"  = NET CO2 REDUCTION:      {alloc_result.co2_accounting.CO2_net_reduction_t_yr:.1f} tonnes/year")
        print()
        print("PRIMARY FIGURE OF MERIT:")
        print(f"  CO2 Reduction per MWth:   {alloc_result.co2_accounting.CO2_per_MWth_yr:.1f} t_CO2/MWth/year")
        print(f"  CO2 Boundary Mode:        {alloc_result.co2_accounting.co2_boundary_mode}")
        print()
        print("COOLING ASSUMPTION IMPACT:")
        print(f"  Cooling Aux Power:        {W_fan/1e6:.3f} MW")
        print(f"  Heat Rejected:            {Q_reject/1e6:.2f} MW")
        print(f"  Cooling Aux Ratio:        {W_fan/Q_reject*100:.2f}% of rejected heat")

    return co2_results


def _write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _extract_owner_from_filename(name: str) -> str:
    m = re.search(r"\b(M\d+)\b", name)
    if m:
        return m.group(1)
    if "Safety" in name:
        return "M3"
    if "Process" in name:
        return "M5"
    if "Research" in name:
        return "M6"
    return "TEAM"


def build_teammate_reconciliation_table(
    teammate_dir: Path,
    output_csv: Path,
) -> None:
    """Extract numeric teammate assumptions with explicit units from PDF sources."""
    rows: List[Dict] = []
    unit_pattern = re.compile(
        r"(MWth|MWe|MW|kWh_th/t_CO2|kWh_e/t_CO2|kWh_e/kg_H2|kWh_th/kg_H2|tCO2/year|tonnes?\s+CO2\s+per\s+year|kgCO2e/TJ|g\s*CO2e?/kWh|°C|%)",
        flags=re.IGNORECASE,
    )
    value_pattern = re.compile(r"\b\d+(?:[.,]\d+)?\b")

    if not PDF_AVAILABLE:
        _write_csv(
            output_csv,
            [{
                "parameter": "PDF parsing unavailable",
                "value": "",
                "units": "",
                "source_doc": "pypdf not installed",
                "owner": "SYSTEM",
                "scenario": "UNMAPPED",
                "status": "blocked",
            }],
            ["parameter", "value", "units", "source_doc", "owner", "scenario", "status"],
        )
        return

    for pdf_path in sorted(teammate_dir.glob("*.pdf")):
        if pdf_path.name.startswith("M1 "):
            # M1 is intentionally excluded from reconciliation scope.
            continue
        owner = _extract_owner_from_filename(pdf_path.name)
        try:
            reader = PdfReader(str(pdf_path))
        except Exception:
            continue
        for page in reader.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                unit_match = unit_pattern.search(line)
                if not unit_match:
                    continue
                value_match = value_pattern.search(line.replace(",", ""))
                if not value_match:
                    continue
                lower = line.lower()
                if "36" in lower and "mw" in lower:
                    scenario = "S1_36MW_OPONLY"
                elif "30" in lower and "mw" in lower:
                    scenario = "S0_BASE_30MW_OPONLY"
                else:
                    scenario = "S0_BASE_30MW_OPONLY"
                rows.append(
                    {
                        "parameter": line[:140],
                        "value": value_match.group(0),
                        "units": unit_match.group(0),
                        "source_doc": str(pdf_path),
                        "owner": owner,
                        "scenario": scenario,
                        "status": "extracted",
                    }
                )

    # Deduplicate exact duplicates.
    dedup = []
    seen = set()
    for row in rows:
        key = (row["parameter"], row["source_doc"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(row)

    _write_csv(
        output_csv,
        dedup,
        ["parameter", "value", "units", "source_doc", "owner", "scenario", "status"],
    )


def build_assumptions_register(output_csv: Path) -> None:
    rows = [
        {
            "parameter": "Baseline reactor thermal power",
            "value": 30.0,
            "units": "MWth",
            "source_doc": "source docs/Rolls Royce Fission Energy Project 25-26.pdf",
            "owner": "Model",
            "scenario": "S0_BASE_30MW_OPONLY",
            "status": "locked",
        },
        {
            "parameter": "Sensitivity reactor thermal power",
            "value": 36.0,
            "units": "MWth",
            "source_doc": "teammate_resources/Presentation Demo (1).pdf",
            "owner": "Model",
            "scenario": "S1_36MW_OPONLY",
            "status": "sensitivity_only",
        },
        {
            "parameter": "Headline accounting mode",
            "value": "operational_only",
            "units": "mode",
            "source_doc": "Locked decision",
            "owner": "Model",
            "scenario": "S0_BASE_30MW_OPONLY",
            "status": "locked",
        },
        {
            "parameter": "Fuel-displacement accounting mode",
            "value": "fuel_displacement",
            "units": "mode",
            "source_doc": "Locked decision",
            "owner": "Model",
            "scenario": "S2_30MW_FUELDISP",
            "status": "sensitivity_only",
        },
        {
            "parameter": "Energy closure tolerance",
            "value": 0.005,
            "units": "relative",
            "source_doc": "cycle/sco2_cycle.py + cycle/coupled_solver.py + run_tests.py",
            "owner": "Model",
            "scenario": "ALL",
            "status": "locked",
        },
        {
            "parameter": "Fuel emission factor",
            "value": 3.15,
            "units": "kgCO2/kg_fuel",
            "source_doc": "teammate_resources/Prim's Initial Research M6.pdf",
            "owner": "Model",
            "scenario": "S2_30MW_FUELDISP",
            "status": "assumption",
        },
    ]
    _write_csv(
        output_csv,
        rows,
        ["parameter", "value", "units", "source_doc", "owner", "scenario", "status"],
    )


def run_stage2_scenarios(output_root: Path) -> Dict[str, Dict]:
    scenarios = [
        {
            "scenario_id": "S0_BASE_30MW_OPONLY",
            "Q_thermal_MW": 30.0,
            "co2_accounting_mode": "operational_only",
            "baseline_or_sensitivity": "baseline",
        },
        {
            "scenario_id": "S1_36MW_OPONLY",
            "Q_thermal_MW": 36.0,
            "co2_accounting_mode": "operational_only",
            "baseline_or_sensitivity": "sensitivity",
        },
        {
            "scenario_id": "S2_30MW_FUELDISP",
            "Q_thermal_MW": 30.0,
            "co2_accounting_mode": "fuel_displacement",
            "baseline_or_sensitivity": "sensitivity",
        },
        {
            "scenario_id": "S3_36MW_FUELDISP",
            "Q_thermal_MW": 36.0,
            "co2_accounting_mode": "fuel_displacement",
            "baseline_or_sensitivity": "sensitivity_optional",
        },
    ]

    scenario_dir = output_root / "scenarios"
    scenario_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for sc in scenarios:
        plant_results, plant_result = run_full_plant_solve(
            T_ambient_C=40.0,
            heat_rejection_mode="fixed_boundary",
            Q_thermal_MW=sc["Q_thermal_MW"],
            scenario_id=sc["scenario_id"],
            baseline_or_sensitivity=sc["baseline_or_sensitivity"],
            source_assumptions_version="v2",
            cooling_aux_fraction=0.01,
            verbose=False,
        )
        co2_results = run_co2_reduction_analysis(
            plant_result,
            Q_thermal=sc["Q_thermal_MW"] * 1e6,
            co2_accounting_mode=sc["co2_accounting_mode"],
            scenario_name=sc["scenario_id"],
            scenario_id=sc["scenario_id"],
            baseline_or_sensitivity=sc["baseline_or_sensitivity"],
            source_assumptions_version="v2",
            apply_neutrality_condition=True,
            fuel_emission_factor_kgco2_per_kg=3.15,
            displacement_factor=1.0,
            verbose=False,
        )
        combined = {
            "scenario": sc,
            "plant": plant_results,
            "co2": co2_results,
        }
        results[sc["scenario_id"]] = combined
        with open(scenario_dir / f"{sc['scenario_id']}.json", "w") as f:
            json.dump(combined, f, indent=2)

    return results


def build_uncertainty_summary(
    baseline_plant_result,
    output_json: Path,
    samples: int = 120,
    seed: int = 20260301,
) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    fom_values = []
    for _ in range(samples):
        dac_heat = float(np.clip(1750.0 * rng.normal(1.0, 0.08), 1300.0, 2300.0))
        dac_elec = float(np.clip(250.0 * rng.normal(1.0, 0.08), 150.0, 400.0))
        htse_elec = float(np.clip(37.5 * rng.normal(1.0, 0.07), 30.0, 50.0))
        htse_heat = float(np.clip(6.5 * rng.normal(1.0, 0.10), 4.0, 9.0))
        out = run_co2_reduction_analysis(
            baseline_plant_result,
            Q_thermal=30e6,
            co2_accounting_mode="operational_only",
            scenario_name="S0_BASE_30MW_OPONLY_UQ",
            scenario_id="S0_BASE_30MW_OPONLY",
            baseline_or_sensitivity="baseline",
            source_assumptions_version="v2",
            dac_heat_intensity=dac_heat,
            dac_elec_intensity=dac_elec,
            htse_elec_intensity=htse_elec,
            htse_heat_intensity=htse_heat,
            verbose=False,
        )
        fom_values.append(out["figures_of_merit"]["CO2_reduction_t_per_MWth_per_yr"])

    arr = np.array(fom_values)
    summary = {
        "seed": seed,
        "samples": samples,
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "p10": float(np.percentile(arr, 10)),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "ci95_low": float(np.percentile(arr, 2.5)),
        "ci95_high": float(np.percentile(arr, 97.5)),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def build_delta_table(
    scenario_results: Dict[str, Dict],
    output_csv: Path,
) -> None:
    s0 = scenario_results["S0_BASE_30MW_OPONLY"]
    rows = [
        {
            "item": "M5 Net electric output (assumed 13.5 MWe)",
            "old_value": 13.5,
            "new_value": round(s0["plant"]["power_MW"]["W_net"], 3),
            "units": "MWe",
            "reason": "Replaced fixed assumption with solved baseline output",
            "source": "run_tests scenario S0_BASE_30MW_OPONLY",
        },
        {
            "item": "M5 Electricity to HTSE (assumed 10 MWe)",
            "old_value": 10.0,
            "new_value": round(s0["co2"]["allocation"]["W_to_HTSE_MW"], 3),
            "units": "MWe",
            "reason": "Allocation now constrained by modelled plant net power and HTSE heat",
            "source": "run_tests scenario S0_BASE_30MW_OPONLY",
        },
        {
            "item": "M5 Heat to DAC (assumed 5 MWth)",
            "old_value": 5.0,
            "new_value": round(s0["co2"]["allocation"]["Q_to_DAC_MW"], 3),
            "units": "MWth",
            "reason": "Replaced static split with optimized constrained allocation",
            "source": "run_tests scenario S0_BASE_30MW_OPONLY",
        },
        {
            "item": "M3 Demo cycle efficiency claim (~45%)",
            "old_value": 45.0,
            "new_value": round(s0["plant"]["efficiencies"]["eta_thermal_percent"], 3),
            "units": "%",
            "reason": "Current integrated baseline at 40C ambient is lower than optimistic claim",
            "source": "results from coupled model baseline scenario",
        },
        {
            "item": "M6 conversion check (6.36 gCO2/kWh)",
            "old_value": 1.767,
            "new_value": 1766.667,
            "units": "kgCO2/TJ",
            "reason": "Corrected g/kWh to kg/TJ conversion",
            "source": "built-in conversion utility check",
        },
    ]
    _write_csv(output_csv, rows, ["item", "old_value", "new_value", "units", "reason", "source"])


def build_architecture_matrix(output_csv: Path) -> None:
    rows = [
        {
            "block": "HTGR thermal source",
            "implemented_in": "cycle/coupled_solver.py",
            "governing_basis": "Q_thermal boundary with He in/out conditions",
            "constraints": "T_He_return, energy_closure_rel",
            "validation_anchor": "RR HTTR baseline references",
            "known_limitations": "No transient LOFC or 2D unit-cell reactor model",
        },
        {
            "block": "sCO2 cycle",
            "implemented_in": "cycle/sco2_cycle.py",
            "governing_basis": "Recompression Brayton with segmented recuperators",
            "constraints": "critical margins, pinch, TIT cap, E03 closure",
            "validation_anchor": "validation/dostal_validation.py",
            "known_limitations": "No turbomachinery map calibration",
        },
        {
            "block": "Allocation (DAC/HTSE/grid)",
            "implemented_in": "process/allocation.py",
            "governing_basis": "SLSQP constrained allocation",
            "constraints": "electric + heat + HTSE steam demand",
            "validation_anchor": "scenario matrix and allocation feasibility flags",
            "known_limitations": "No dynamic dispatch profile",
        },
        {
            "block": "CO2 accounting boundary",
            "implemented_in": "process/allocation.py",
            "governing_basis": "operational_only headline + fuel_displacement sensitivity",
            "constraints": "unit conversion checks and scenario metadata tags",
            "validation_anchor": "conversion round-trip checks",
            "known_limitations": "Fuel displacement depends on assumed reference EF",
        },
    ]
    _write_csv(
        output_csv,
        rows,
        ["block", "implemented_in", "governing_basis", "constraints", "validation_anchor", "known_limitations"],
    )


def build_limitations_register(output_csv: Path) -> None:
    rows = [
        {
            "id": "LIM-001",
            "limitation": "Reactor-side physics represented as boundary condition, not transient core model",
            "impact": "Safety-transient conclusions are literature-benchmarked, not simulated",
            "mitigation_next_step": "Add 2D unit-cell surrogate + transient benchmark loop",
        },
        {
            "id": "LIM-002",
            "limitation": "Fuel-displacement accounting depends on assumed fuel EF and displacement factor",
            "impact": "Sensitivity FoM spread can be significant",
            "mitigation_next_step": "Calibrate with RR-preferred accounting boundary and factors",
        },
        {
            "id": "LIM-003",
            "limitation": "Coupled-cooler mode retained as sensitivity, not headline",
            "impact": "Headline excludes detailed heat-rejection design dependence",
            "mitigation_next_step": "Keep fixed-boundary headline and report coupled mode in appendix",
        },
    ]
    _write_csv(output_csv, rows, ["id", "limitation", "impact", "mitigation_next_step"])


def build_equation_sheet(output_md: Path) -> None:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    text = """# Equation Sheet (Scenario-Tagged)

## Allocation Constraints
- Electricity: `W_HTSE + W_DAC + W_grid <= W_allocatable`
- Heat: `Q_DAC + Q_HTSE <= Q_waste_available`
- HTSE heat: `Q_HTSE = W_HTSE * (HTSE_heat_intensity / HTSE_elec_intensity)` when enforced.

## CO2 Accounting
- Operational-only mode: `CO2_net = CO2_DAC + CO2_grid`
- Fuel-displacement mode: `CO2_net = CO2_displaced_fossil + CO2_grid - CO2_embodied - (CO2_reemitted_synthetic if neutrality disabled)`

## Unit Conversions
- `kgCO2/TJ = gCO2/kWh * 277.7777778`
- `gCO2/kWh = kgCO2/TJ / 277.7777778`
"""
    with open(output_md, "w") as f:
        f.write(text)


def build_constraint_margin_table(
    scenario_results: Dict[str, Dict],
    output_csv: Path,
) -> None:
    rows = []
    for scenario_id, payload in scenario_results.items():
        margins = payload["plant"]["margins"]
        rows.append(
            {
                "scenario_id": scenario_id,
                "energy_closure_margin": margins.get("energy_closure"),
                "pinch_IHX_margin_K": margins.get("pinch_IHX_min"),
                "pinch_HTR_margin_K": margins.get("pinch_HTR_min"),
                "pinch_LTR_margin_K": margins.get("pinch_LTR_min"),
                "W_net_W": margins.get("W_net"),
                "T_He_return_margin_K": margins.get("T_He_return"),
            }
        )
    _write_csv(
        output_csv,
        rows,
        ["scenario_id", "energy_closure_margin", "pinch_IHX_margin_K", "pinch_HTR_margin_K", "pinch_LTR_margin_K", "W_net_W", "T_He_return_margin_K"],
    )


def report_gate_check(scenario_results: Dict[str, Dict]) -> None:
    required_meta = {"scenario_id", "baseline_or_sensitivity", "source_assumptions_version"}
    for scenario_id, payload in scenario_results.items():
        plant_meta = payload["plant"]["metadata"]
        co2_meta = payload["co2"]["metadata"]
        if not required_meta.issubset(set(plant_meta.keys())):
            raise RuntimeError(f"Scenario {scenario_id} missing required plant metadata tags")
        if not required_meta.issubset(set(co2_meta.keys())):
            raise RuntimeError(f"Scenario {scenario_id} missing required CO2 metadata tags")


def generate_stage2_canonical_pack(output_dir: str = None) -> Dict[str, Dict]:
    base = Path(output_dir or os.path.dirname(os.path.abspath(__file__)))
    output_root = base / "outputs" / "canonical_pack"
    output_root.mkdir(parents=True, exist_ok=True)

    scenario_results = run_stage2_scenarios(output_root)
    report_gate_check(scenario_results)

    # Use S0 plant state as baseline for uncertainty around process intensities.
    _, baseline_plant_result = run_full_plant_solve(
        T_ambient_C=40.0,
        heat_rejection_mode="fixed_boundary",
        Q_thermal_MW=30.0,
        scenario_id="S0_BASE_30MW_OPONLY",
        baseline_or_sensitivity="baseline",
        source_assumptions_version="v2",
        cooling_aux_fraction=0.01,
        verbose=False,
    )
    uncertainty = build_uncertainty_summary(
        baseline_plant_result,
        output_root / "uncertainty_summary.json",
    )

    fom_rows = []
    for scenario_id, payload in scenario_results.items():
        fom_rows.append(
            {
                "scenario_id": scenario_id,
                "baseline_or_sensitivity": payload["scenario"]["baseline_or_sensitivity"],
                "co2_accounting_mode": payload["scenario"]["co2_accounting_mode"],
                "Q_thermal_MWth": payload["scenario"]["Q_thermal_MW"],
                "W_net_MWe": payload["plant"]["power_MW"]["W_net"],
                "eta_net_percent": payload["plant"]["efficiencies"]["eta_net_percent"],
                "FOM_tCO2_per_MWth_yr": payload["co2"]["figures_of_merit"]["CO2_reduction_t_per_MWth_per_yr"],
                "UQ_p50": uncertainty["p50"] if scenario_id == "S0_BASE_30MW_OPONLY" else "",
                "UQ_p90": uncertainty["p90"] if scenario_id == "S0_BASE_30MW_OPONLY" else "",
                "UQ_ci95_low": uncertainty["ci95_low"] if scenario_id == "S0_BASE_30MW_OPONLY" else "",
                "UQ_ci95_high": uncertainty["ci95_high"] if scenario_id == "S0_BASE_30MW_OPONLY" else "",
            }
        )
    _write_csv(
        output_root / "fom_summary_with_uncertainty.csv",
        fom_rows,
        [
            "scenario_id",
            "baseline_or_sensitivity",
            "co2_accounting_mode",
            "Q_thermal_MWth",
            "W_net_MWe",
            "eta_net_percent",
            "FOM_tCO2_per_MWth_yr",
            "UQ_p50",
            "UQ_p90",
            "UQ_ci95_low",
            "UQ_ci95_high",
        ],
    )

    teammate_dir = base.parent / "teammate_resources"
    build_teammate_reconciliation_table(
        teammate_dir=teammate_dir,
        output_csv=output_root / "teammate_number_reconciliation.csv",
    )
    build_assumptions_register(output_root / "assumptions_register.csv")
    build_delta_table(scenario_results, output_root / "teammate_delta_table.csv")
    build_architecture_matrix(output_root / "architecture_compliance_matrix.csv")
    build_limitations_register(output_root / "limitations_register.csv")
    build_equation_sheet(output_root / "equation_sheet.md")
    build_constraint_margin_table(scenario_results, output_root / "constraint_margin_table.csv")

    with open(output_root / "canonical_pack_index.json", "w") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "headline_scenario": "S0_BASE_30MW_OPONLY",
                "scenarios": sorted(scenario_results.keys()),
                "output_root": str(output_root),
            },
            f,
            indent=2,
        )
    return scenario_results


def write_output_files(output_dir: str = None):
    """Generate all required output files."""
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    output_path = Path(output_dir)

    # 1. Write assumptions (yaml if available, otherwise json)
    assumptions = get_assumptions()
    if YAML_AVAILABLE:
        with open(output_path / 'assumptions.yaml', 'w') as f:
            yaml.dump(assumptions, f, default_flow_style=False, sort_keys=False)
        print(f"Written: assumptions.yaml")
    else:
        with open(output_path / 'assumptions.json', 'w') as f:
            json.dump(assumptions, f, indent=2)
        print(f"Written: assumptions.json (yaml not available)")

    # 2. Run plant solve and write results_baseline.json
    results, plant_result = run_full_plant_solve(T_ambient_C=40.0, verbose=False)
    with open(output_path / 'results_baseline.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Written: results_baseline.json")

    # 3. Write feasibility_report.txt
    with open(output_path / 'feasibility_report.txt', 'w') as f:
        f.write(plant_result.feasibility_report.format_report())
        f.write("\n\n")
        f.write("KEY PLANT OUTPUTS:\n")
        f.write("-" * 40 + "\n")
        f.write(f"Net Power:           {plant_result.W_net / 1e6:.3f} MW\n")
        f.write(f"Gross Power:         {plant_result.W_gross / 1e6:.3f} MW\n")
        f.write(f"Cooling Aux Power:   {plant_result.W_fan / 1e3:.1f} kW\n")
        f.write(f"Thermal Efficiency:  {plant_result.eta_thermal * 100:.2f}%\n")
        f.write(f"Net Efficiency:      {plant_result.eta_net * 100:.2f}%\n")
        f.write(f"Heat Reject Mode:    {plant_result.heat_rejection_mode}\n")
        f.write(f"Assumption Mode:     {plant_result.assumption_mode}\n")
        f.write(f"Energy Closure:      {plant_result.energy_closure_rel*100:.3f}%\n")
        f.write(f"CO2 Mass Flow:       {plant_result.m_dot_CO2:.1f} kg/s\n")
        f.write(f"T_1 (comp inlet):    {plant_result.T_1 - 273.15:.2f}°C\n")
        f.write(f"T_5 (turb inlet):    {plant_result.T_5 - 273.15:.2f}°C\n")
    print(f"Written: feasibility_report.txt")

    # 4. Run CO2 reduction analysis and write report
    co2_results = run_co2_reduction_analysis(plant_result, Q_thermal=30e6, verbose=False)

    with open(output_path / 'co2_reduction_results.json', 'w') as f:
        json.dump(co2_results, f, indent=2)
    print(f"Written: co2_reduction_results.json")

    # 5. Write human-readable CO2 reduction report
    with open(output_path / 'co2_reduction_report.txt', 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("CO2 REDUCTION ANALYSIS REPORT\n")
        f.write("HTGR + sCO2 Cycle + Process Integration\n")
        f.write("=" * 70 + "\n\n")

        f.write("PLANT CONFIGURATION:\n")
        f.write("-" * 40 + "\n")
        f.write(f"Reactor Thermal Power:     {co2_results['plant_inputs']['Q_thermal_MW']:.1f} MW\n")
        f.write(f"Net Electrical Power:      {co2_results['plant_inputs']['W_net_MW']:.3f} MW\n")
        f.write(f"Waste Heat Available:      {co2_results['plant_inputs']['Q_waste_available_MW']:.2f} MW\n")
        f.write(f"Waste Heat Temperature:    {co2_results['plant_inputs']['T_waste_C']:.1f} °C\n\n")

        f.write("OPTIMAL ENERGY ALLOCATION:\n")
        f.write("-" * 40 + "\n")
        f.write(f"Electricity to HTSE:       {co2_results['allocation']['W_to_HTSE_MW']:.3f} MW\n")
        f.write(f"Electricity to DAC:        {co2_results['allocation']['W_to_DAC_MW']:.3f} MW\n")
        f.write(f"Heat to DAC:               {co2_results['allocation']['Q_to_DAC_MW']:.3f} MW\n")
        f.write(f"Heat to HTSE:              {co2_results['allocation']['Q_to_HTSE_MW']:.3f} MW\n")
        f.write(f"Electricity to Grid:       {co2_results['allocation']['W_to_grid_MW']:.3f} MW\n")
        f.write(f"Heat to Cooler:            {co2_results['allocation']['Q_to_cooler_MW']:.2f} MW\n\n")

        f.write("ANNUAL PRODUCTION (90% capacity factor):\n")
        f.write("-" * 40 + "\n")
        f.write(f"Hydrogen Production:       {co2_results['production_rates']['H2_produced_t_yr']:.1f} tonnes/year\n")
        f.write(f"CO2 Captured (DAC):        {co2_results['production_rates']['CO2_captured_DAC_t_yr']:.1f} tonnes/year\n")
        f.write(f"Methanol Production:       {co2_results['production_rates']['MeOH_produced_t_yr']:.1f} tonnes/year\n\n")

        f.write("CO2 BALANCE (tonnes/year):\n")
        f.write("-" * 40 + "\n")
        f.write(f"+ Grid Displacement:       {co2_results['co2_balance_t_yr']['avoided_grid_displacement']:.1f}\n")
        f.write(f"+ DAC Capture:             {co2_results['co2_balance_t_yr']['captured_DAC']:.1f}\n")
        f.write(f"- Embodied in Products:    {co2_results['co2_balance_t_yr']['embodied_in_products']:.1f}\n")
        f.write("-" * 40 + "\n")
        f.write(f"= NET CO2 REDUCTION:       {co2_results['co2_balance_t_yr']['NET_REDUCTION']:.1f} tonnes/year\n\n")

        f.write("=" * 70 + "\n")
        f.write("PRIMARY FIGURES OF MERIT\n")
        f.write("=" * 70 + "\n")
        f.write(f"CO2 Reduction per MWth:    {co2_results['figures_of_merit']['CO2_reduction_t_per_MWth_per_yr']:.1f} t_CO2/MWth/year\n")
        f.write(f"Specific CO2 Reduction:    {co2_results['figures_of_merit']['specific_CO2_reduction_kg_per_kWh_th']*1000:.2f} g_CO2/kWh_th\n\n")
        f.write(f"CO2 Boundary Mode:         {co2_results['figures_of_merit']['co2_boundary_mode']}\n\n")

        f.write("COOLING AUXILIARY METRICS:\n")
        f.write("-" * 40 + "\n")
        f.write(f"Cooling Aux Power:         {co2_results['cooling_auxiliary']['cooling_aux_power_MW']:.3f} MW\n")
        f.write(f"Heat Rejected:             {co2_results['cooling_auxiliary']['heat_rejected_MW']:.2f} MW\n")
        f.write(
            "Cooling Aux Ratio:         "
            f"{co2_results['cooling_auxiliary']['cooling_aux_percent_of_rejected_heat']:.2f}%\n"
        )
        f.write("\nSCENARIO METADATA:\n")
        f.write("-" * 40 + "\n")
        for key, value in co2_results['scenario_metadata'].items():
            f.write(f"{key}: {value}\n")
        f.write("=" * 70 + "\n")
    print(f"Written: co2_reduction_report.txt")


def main():
    """Main test runner."""
    print("\n" + "#" * 70)
    print("#  sCO2 PLANT SIMULATION - HTGR-ONLY TEST RUNNER")
    print("#  Including CO2 Reduction Analysis (Stage-2 Recovery)")
    print("#" * 70)

    # Test 1: Dostal validation
    print("\n" + "=" * 70)
    print("TEST 1: CYCLE-ONLY VALIDATION (DOSTAL-STYLE)")
    print("=" * 70)

    dostal_passed, dostal_results = run_dostal_validation(verbose=True)

    print(f"\nDostal Validation: {'PASSED' if dostal_passed else 'FAILED'}")
    if dostal_passed:
        print(f"  Thermal efficiency: {dostal_results['eta_thermal'] * 100:.2f}%")
        print(f"  Expected: {dostal_results['eta_expected'] * 100:.1f}% ± {dostal_results['eta_tolerance'] * 100:.1f}%")
        print(f"  Error: {dostal_results['eta_error'] * 100:.2f}%")

    # Test 2: HTGR headline plant solve
    print("\n" + "=" * 70)
    print("TEST 2: HTGR HEADLINE PLANT SOLVE (FIXED BOUNDARY, T_amb = 40°C)")
    print("=" * 70)

    plant_results, plant_result = run_full_plant_solve(
        T_ambient_C=40.0,
        heat_rejection_mode="fixed_boundary",
        verbose=True,
    )

    plant_feasible = plant_results['status']['feasible']
    print(f"\nHTGR Headline Solve: {'PASSED (FEASIBLE)' if plant_feasible else 'FAILED (INFEASIBLE)'}")

    # Optional sensitivity: coupled cooler mode retained for appendix evidence
    print("\n" + "=" * 70)
    print("TEST 2B: OPTIONAL COUPLED-COOLER SENSITIVITY (T_amb = 40°C)")
    print("=" * 70)
    try:
        sensitivity_results, _ = run_full_plant_solve(
            T_ambient_C=40.0,
            heat_rejection_mode="coupled_cooler",
            verbose=False,
        )
        print(
            "Coupled-Cooler Sensitivity: "
            f"{'PASSED (FEASIBLE)' if sensitivity_results['status']['feasible'] else 'FAILED (INFEASIBLE)'}"
        )
        print(
            f"  Net Power Delta vs headline: "
            f"{sensitivity_results['power_MW']['W_net'] - plant_results['power_MW']['W_net']:.3f} MW"
        )
    except Exception as exc:
        print(f"Coupled-Cooler Sensitivity: FAILED ({exc})")

    # Test 3: CO2 Reduction Analysis
    print("\n" + "=" * 70)
    print("TEST 3: CO2 REDUCTION ANALYSIS (PROCESS ALLOCATION)")
    print("=" * 70)

    co2_results = run_co2_reduction_analysis(
        plant_result,
        Q_thermal=30e6,
        co2_boundary_mode="operational_only",
        allow_grid_export=False,
        enforce_htse_heat_constraint=True,
        scenario_name="headline_htgr_only",
        verbose=True,
    )

    co2_positive = co2_results['co2_balance_t_yr']['NET_REDUCTION'] > 0
    print(f"\nCO2 Reduction Analysis: {'PASSED (NET POSITIVE)' if co2_positive else 'FAILED (NET NEGATIVE)'}")
    print(f"  Net CO2 Reduction: {co2_results['co2_balance_t_yr']['NET_REDUCTION']:.1f} tonnes/year")
    print(f"  FOM (CO2/MWth/yr): {co2_results['figures_of_merit']['CO2_reduction_t_per_MWth_per_yr']:.1f} t_CO2/MWth/year")

    # Generate output files
    print("\n" + "=" * 70)
    print("GENERATING OUTPUT FILES")
    print("=" * 70)

    write_output_files()

    print("\n" + "=" * 70)
    print("GENERATING STAGE-2 CANONICAL SYNC PACK")
    print("=" * 70)
    scenario_results = generate_stage2_canonical_pack()
    print("Canonical scenarios generated:")
    for sid in sorted(scenario_results.keys()):
        print(f"  - {sid}")

    # Summary
    print("\n" + "#" * 70)
    print("#  TEST SUMMARY")
    print("#" * 70)
    print(f"\n  Test 1 (Dostal Validation):     {'PASS' if dostal_passed else 'FAIL'}")
    print(f"  Test 2 (HTGR Headline Solve):   {'PASS' if plant_feasible else 'FAIL'}")
    print(f"  Test 3 (CO2 Reduction):         {'PASS' if co2_positive else 'FAIL'}")
    print("  Test 4 (Canonical Pack Tags):   PASS")

    # Return overall pass/fail
    overall_pass = dostal_passed and plant_feasible and co2_positive
    print(f"\n  OVERALL: {'ALL TESTS PASSED' if overall_pass else 'SOME TESTS FAILED'}")
    print("#" * 70 + "\n")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
