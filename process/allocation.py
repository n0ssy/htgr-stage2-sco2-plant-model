"""
Process Allocation Module.

Implements constrained optimization for allocating electricity and heat
to CO2 reduction processes (DAC, HTSE, Methanol synthesis).

Reference: corrected_simulation_architecture.md Section A.7
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List
from enum import Enum
import numpy as np
from scipy.optimize import minimize, Bounds


class AllocationObjective(Enum):
    """Optimization objective modes."""
    MAX_CO2_NET = "max_CO2_net"  # Maximize net CO2 reduction
    MAX_METHANOL = "max_MeOH"  # Maximize methanol production
    MAX_HYDROGEN = "max_H2"  # Maximize hydrogen production
    TARGET_POWER = "target_power"  # Meet specific power target


_KWH_PER_TJ = 1e12 / 3.6e6  # 277_777.777...


def g_per_kwh_to_kg_per_tj(value_g_per_kwh: float) -> float:
    """Convert gCO2/kWh to kgCO2/TJ."""
    return value_g_per_kwh * _KWH_PER_TJ / 1000.0


def kg_per_tj_to_g_per_kwh(value_kg_per_tj: float) -> float:
    """Convert kgCO2/TJ to gCO2/kWh."""
    return value_kg_per_tj * 1000.0 / _KWH_PER_TJ


def conversion_checks_pass(
    grid_intensity_g_per_kwh: float,
    tol_rel: float = 1e-9,
) -> bool:
    """Round-trip conversion check used for report-gating metadata."""
    round_trip = kg_per_tj_to_g_per_kwh(g_per_kwh_to_kg_per_tj(grid_intensity_g_per_kwh))
    return abs(round_trip - grid_intensity_g_per_kwh) <= tol_rel * max(abs(grid_intensity_g_per_kwh), 1.0)


@dataclass
class DACConfig:
    """
    Direct Air Capture configuration (Solid Sorbent TVSA).

    Reference values from literature:
    - Climeworks: ~1500-2000 kWh_th/t_CO2, ~200-300 kWh_e/t_CO2
    - Carbon Engineering: Different technology (liquid solvent)
    """
    # Energy intensities
    heat_intensity: float = 1750.0  # kWh_th per tonne CO2 captured
    elec_intensity: float = 250.0  # kWh_e per tonne CO2 captured

    # Temperature requirement
    T_regen_min: float = 373.15  # Minimum regeneration temperature [K] (100°C)

    # Capacity and operational parameters
    capacity_factor: float = 0.90  # Annual capacity factor
    max_capacity_MW_th: Optional[float] = None  # Max heat input [MW], None = unlimited

    # CO2 purity
    CO2_purity: float = 0.99  # Output CO2 purity


@dataclass
class HTSEConfig:
    """
    High-Temperature Steam Electrolysis (SOEC) configuration.

    Reference: Idaho National Laboratory HTSE studies
    """
    # Energy intensities
    elec_intensity: float = 37.5  # kWh_e per kg H2 produced
    heat_intensity: float = 6.5  # kWh_th per kg H2 (for steam generation)

    # Operating conditions
    T_steam_min: float = 373.15  # Minimum steam temperature [K]
    P_H2_out: float = 20e5  # Output hydrogen pressure [Pa] (20 bar)

    # Capacity and operational parameters
    capacity_factor: float = 0.90
    max_capacity_MW_e: Optional[float] = None  # Max electricity input [MW]

    # Efficiency
    faradaic_efficiency: float = 0.95


@dataclass
class MethanolConfig:
    """
    Methanol synthesis configuration.

    Reaction: CO2 + 3H2 -> CH3OH + H2O
    """
    # Conversion efficiencies
    per_pass_conversion: float = 0.25  # Single-pass conversion
    overall_conversion: float = 0.97  # With recycle loop

    # Stoichiometry (kg basis)
    # MW: CO2=44, H2=2, CH3OH=32
    # 44 kg CO2 + 6 kg H2 -> 32 kg CH3OH + 18 kg H2O
    kg_CO2_per_kg_MeOH: float = 44.0 / 32.0  # 1.375 kg CO2/kg MeOH
    kg_H2_per_kg_MeOH: float = 6.0 / 32.0  # 0.1875 kg H2/kg MeOH

    # Energy requirements
    elec_intensity: float = 0.5  # kWh_e per kg MeOH (compression, pumps)
    heat_released: float = 1.2  # kWh_th per kg MeOH (exothermic reaction)

    # Operating conditions
    T_reaction: float = 523.15  # Reaction temperature [K] (250°C)
    P_reaction: float = 50e5  # Reaction pressure [Pa] (50 bar)


@dataclass
class DACModel:
    """Direct Air Capture process model."""

    config: DACConfig = field(default_factory=DACConfig)

    def calculate(self, Q_heat: float, W_elec: float, T_heat: float) -> Dict:
        """
        Calculate DAC outputs given heat and electricity inputs.

        Args:
            Q_heat: Heat input [W]
            W_elec: Electricity input [W]
            T_heat: Temperature of heat source [K]

        Returns:
            Dict with CO2 captured, energy consumption, feasibility
        """
        # Check temperature constraint
        if T_heat < self.config.T_regen_min:
            return {
                'feasible': False,
                'm_CO2_captured_kg_s': 0,
                'm_CO2_captured_t_yr': 0,
                'Q_used': 0,
                'W_used': 0,
                'limiting_factor': 'temperature',
                'message': f'Heat source temperature {T_heat-273.15:.1f}°C below minimum {self.config.T_regen_min-273.15:.1f}°C'
            }

        # Convert intensities to SI units (W to kW, kg to tonnes)
        # heat_intensity: kWh_th/t_CO2 -> J/kg_CO2
        # 1 kWh = 3.6e6 J, 1 tonne = 1000 kg
        heat_per_kg = self.config.heat_intensity * 3.6e6 / 1000  # J/kg_CO2
        elec_per_kg = self.config.elec_intensity * 3.6e6 / 1000  # J/kg_CO2

        # Calculate CO2 capture rate limited by heat and electricity
        m_CO2_from_heat = Q_heat / heat_per_kg if heat_per_kg > 0 else float('inf')
        m_CO2_from_elec = W_elec / elec_per_kg if elec_per_kg > 0 else float('inf')

        # Limiting resource determines capture rate
        m_CO2_kg_s = min(m_CO2_from_heat, m_CO2_from_elec)

        # Apply capacity constraint if specified
        if self.config.max_capacity_MW_th is not None:
            max_Q = self.config.max_capacity_MW_th * 1e6
            m_CO2_max = max_Q / heat_per_kg
            m_CO2_kg_s = min(m_CO2_kg_s, m_CO2_max)

        # Determine limiting factor
        if m_CO2_from_heat <= m_CO2_from_elec:
            limiting = 'heat'
        else:
            limiting = 'electricity'

        # Calculate actual energy usage
        Q_used = m_CO2_kg_s * heat_per_kg
        W_used = m_CO2_kg_s * elec_per_kg

        # Annual capture (accounting for capacity factor)
        seconds_per_year = 365.25 * 24 * 3600
        m_CO2_t_yr = m_CO2_kg_s * seconds_per_year / 1000 * self.config.capacity_factor

        return {
            'feasible': True,
            'm_CO2_captured_kg_s': m_CO2_kg_s,
            'm_CO2_captured_t_yr': m_CO2_t_yr,
            'Q_used': Q_used,
            'W_used': W_used,
            'limiting_factor': limiting,
            'message': f'DAC operating, limited by {limiting}'
        }


@dataclass
class HTSEModel:
    """High-Temperature Steam Electrolysis model."""

    config: HTSEConfig = field(default_factory=HTSEConfig)

    def calculate(self, W_elec: float, Q_steam: float = None) -> Dict:
        """
        Calculate HTSE outputs given electricity input.

        Args:
            W_elec: Electricity input [W]
            Q_steam: Heat available for steam generation [W] (optional)

        Returns:
            Dict with H2 produced, energy consumption
        """
        # Convert intensities to SI units
        # elec_intensity: kWh_e/kg_H2 -> J/kg_H2
        elec_per_kg = self.config.elec_intensity * 3.6e6  # J/kg_H2
        heat_per_kg = self.config.heat_intensity * 3.6e6  # J/kg_H2

        # H2 production rate limited by electricity
        m_H2_from_elec = W_elec / elec_per_kg if elec_per_kg > 0 else 0

        # If steam heat is limiting
        if Q_steam is not None:
            m_H2_from_heat = Q_steam / heat_per_kg if heat_per_kg > 0 else float('inf')
            m_H2_kg_s = min(m_H2_from_elec, m_H2_from_heat)
            limiting = 'heat' if m_H2_from_heat < m_H2_from_elec else 'electricity'
        else:
            m_H2_kg_s = m_H2_from_elec
            limiting = 'electricity'

        # Apply capacity constraint
        if self.config.max_capacity_MW_e is not None:
            max_W = self.config.max_capacity_MW_e * 1e6
            m_H2_max = max_W / elec_per_kg
            m_H2_kg_s = min(m_H2_kg_s, m_H2_max)

        # Calculate actual energy usage
        W_used = m_H2_kg_s * elec_per_kg
        Q_used = m_H2_kg_s * heat_per_kg

        # Annual production
        seconds_per_year = 365.25 * 24 * 3600
        m_H2_t_yr = m_H2_kg_s * seconds_per_year / 1000 * self.config.capacity_factor

        return {
            'feasible': True,
            'm_H2_produced_kg_s': m_H2_kg_s,
            'm_H2_produced_t_yr': m_H2_t_yr,
            'W_used': W_used,
            'Q_used': Q_used,
            'limiting_factor': limiting
        }


@dataclass
class MethanolModel:
    """Methanol synthesis model."""

    config: MethanolConfig = field(default_factory=MethanolConfig)

    def calculate(self, m_H2_kg_s: float, m_CO2_kg_s: float) -> Dict:
        """
        Calculate methanol production from H2 and CO2 inputs.

        Args:
            m_H2_kg_s: Hydrogen input rate [kg/s]
            m_CO2_kg_s: CO2 input rate [kg/s]

        Returns:
            Dict with methanol produced, reactant consumption
        """
        cfg = self.config

        # Stoichiometric requirements per kg methanol
        H2_required_per_MeOH = cfg.kg_H2_per_kg_MeOH
        CO2_required_per_MeOH = cfg.kg_CO2_per_kg_MeOH

        # Methanol production limited by either H2 or CO2
        m_MeOH_from_H2 = m_H2_kg_s / H2_required_per_MeOH if H2_required_per_MeOH > 0 else 0
        m_MeOH_from_CO2 = m_CO2_kg_s / CO2_required_per_MeOH if CO2_required_per_MeOH > 0 else 0

        # Apply overall conversion efficiency
        m_MeOH_kg_s = min(m_MeOH_from_H2, m_MeOH_from_CO2) * cfg.overall_conversion

        # Determine limiting reactant
        if m_MeOH_from_H2 <= m_MeOH_from_CO2:
            limiting = 'hydrogen'
        else:
            limiting = 'CO2'

        # Actual consumption
        H2_consumed = m_MeOH_kg_s * H2_required_per_MeOH / cfg.overall_conversion
        CO2_consumed = m_MeOH_kg_s * CO2_required_per_MeOH / cfg.overall_conversion

        # Electricity for compression/pumping
        W_required = m_MeOH_kg_s * cfg.elec_intensity * 3.6e6

        # Heat released (exothermic)
        Q_released = m_MeOH_kg_s * cfg.heat_released * 3.6e6

        # Annual production
        seconds_per_year = 365.25 * 24 * 3600
        m_MeOH_t_yr = m_MeOH_kg_s * seconds_per_year / 1000 * 0.90  # 90% capacity factor

        return {
            'feasible': True,
            'm_MeOH_produced_kg_s': m_MeOH_kg_s,
            'm_MeOH_produced_t_yr': m_MeOH_t_yr,
            'm_H2_consumed_kg_s': H2_consumed,
            'm_CO2_consumed_kg_s': CO2_consumed,
            'W_required': W_required,
            'Q_released': Q_released,
            'limiting_factor': limiting
        }


@dataclass
class AllocationConfig:
    """Configuration for process allocation optimization."""

    # Objective
    objective: AllocationObjective = AllocationObjective.MAX_CO2_NET

    # Grid parameters
    grid_CO2_intensity: float = 400.0  # g CO2/kWh for displaced grid electricity
    allow_grid_export: bool = False  # Whether to allow grid export
    max_grid_export_MW: float = 0.0  # Maximum grid export [MW]
    co2_accounting_mode: str = "operational_only"  # operational_only | fuel_displacement
    # Legacy alias retained for backward compatibility with older runners.
    co2_boundary_mode: Optional[str] = None
    apply_neutrality_condition: bool = True
    fuel_emission_factor_kgco2_per_kg: float = 3.15  # Reference fossil fuel EF
    displacement_factor: float = 1.0
    optimization_mode: str = "headline_operational"  # headline_operational | general_nonlinear
    n_multistart: int = 12
    global_screen_grid: int = 41
    objective_gap_tolerance_rel: float = 0.01

    # Process configurations
    dac_config: DACConfig = field(default_factory=DACConfig)
    htse_config: HTSEConfig = field(default_factory=HTSEConfig)
    methanol_config: MethanolConfig = field(default_factory=MethanolConfig)

    # Whether HTSE steam heat must be supplied from available waste heat
    enforce_htse_heat_constraint: bool = True

    # Embodied carbon
    embodied_CO2_per_kg_MeOH: float = 0.1  # kg CO2 embodied per kg methanol produced
    allocation_auxiliary_power_W: float = 0.0

    # Scenario metadata for traceability
    scenario_name: str = "baseline"
    scenario_id: str = "UNSPECIFIED"
    baseline_or_sensitivity: str = "unspecified"
    source_assumptions_version: str = "v1"


@dataclass
class CO2AccountingResult:
    """Complete CO2 accounting for the plant."""

    # Grid displacement
    W_to_grid: float  # Electricity exported to grid [W]
    CO2_avoided_grid_kg_s: float  # CO2 avoided by grid displacement [kg/s]
    CO2_avoided_grid_t_yr: float  # Annual [tonnes/year]

    # Direct Air Capture
    W_to_DAC: float  # Electricity to DAC [W]
    Q_to_DAC: float  # Heat to DAC [W]
    CO2_captured_DAC_kg_s: float  # CO2 captured [kg/s]
    CO2_captured_DAC_t_yr: float  # Annual [tonnes/year]
    co2_dac_captured_t_yr: float  # Alias for export clarity

    # HTSE
    W_to_HTSE: float  # Electricity to HTSE [W]
    H2_produced_kg_s: float  # Hydrogen produced [kg/s]
    H2_produced_t_yr: float  # Annual [tonnes/year]

    # Methanol (optional)
    MeOH_produced_kg_s: float  # Methanol produced [kg/s]
    MeOH_produced_t_yr: float  # Annual [tonnes/year]
    CO2_consumed_MeOH_kg_s: float  # CO2 used for methanol [kg/s]

    # Embodied carbon
    CO2_embodied_kg_s: float  # Embodied CO2 in products [kg/s]
    CO2_embodied_t_yr: float  # Annual [tonnes/year]

    # Fuel-displacement sensitivity terms
    CO2_displaced_fossil_kg_s: float
    CO2_displaced_fossil_t_yr: float
    CO2_reemitted_synthetic_kg_s: float
    CO2_reemitted_synthetic_t_yr: float
    co2_displaced_fossil_t_yr: float  # Alias for export clarity
    co2_reemitted_synthetic_t_yr: float  # Alias for export clarity

    # Net CO2 balance
    CO2_net_reduction_kg_s: float  # Net CO2 reduction [kg/s]
    CO2_net_reduction_t_yr: float  # Annual net reduction [tonnes/year]

    # Figures of Merit
    CO2_per_MWth_yr: float  # tonnes CO2 reduced per year per MW thermal
    specific_CO2_reduction: float  # kg CO2 per kWh thermal input
    co2_accounting_mode: str = "operational_only"
    co2_boundary_mode: str = "operational_only"  # Legacy alias
    conversion_checks_passed: bool = True


@dataclass
class AllocationResult:
    """Result from process allocation optimization."""

    feasible: bool
    converged: bool

    # Optimal allocation
    W_to_HTSE: float  # [W]
    W_to_DAC: float  # [W]
    Q_to_DAC: float  # [W]
    W_to_grid: float  # [W]
    W_aux: float  # [W] auxiliary/parasitic

    # Remaining (rejected to environment)
    Q_to_cooler: float  # [W]
    Q_to_HTSE: float  # [W] HTSE steam-heat demand counted in allocation

    # Process outputs
    dac_result: Dict
    htse_result: Dict
    methanol_result: Optional[Dict]

    # CO2 accounting
    co2_accounting: CO2AccountingResult

    # Optimization info
    objective_value: float
    objective_consistency_passed: bool
    objective_best_alt: float
    objective_gap_rel: float
    optimizer_diagnostics: Dict[str, float]
    iterations: int
    message: str
    scenario_metadata: Dict[str, object] = field(default_factory=dict)


class ProcessAllocator:
    """
    Constrained optimization for process allocation.

    Allocates available electricity and heat to DAC, HTSE, and grid export
    to maximize net CO2 reduction (or other objectives).
    """

    def __init__(self, config: Optional[AllocationConfig] = None):
        self.config = config or AllocationConfig()

        # Create process models
        self.dac = DACModel(self.config.dac_config)
        self.htse = HTSEModel(self.config.htse_config)
        self.methanol = MethanolModel(self.config.methanol_config)

        if self.config.co2_boundary_mode is not None and self.config.co2_accounting_mode == "operational_only":
            legacy = self.config.co2_boundary_mode
            if legacy in {"operational_only", "fuel_displacement"}:
                self.config.co2_accounting_mode = legacy
            elif legacy == "operational_plus_embodied":
                self.config.co2_accounting_mode = "operational_only"
            else:
                raise ValueError(
                    "Legacy co2_boundary_mode must be 'operational_only', "
                    "'fuel_displacement', or 'operational_plus_embodied'."
                )

        if self.config.co2_accounting_mode not in {"operational_only", "fuel_displacement"}:
            raise ValueError(
                "co2_accounting_mode must be 'operational_only' or 'fuel_displacement'"
            )

        if self.config.fuel_emission_factor_kgco2_per_kg < 0:
            raise ValueError("fuel_emission_factor_kgco2_per_kg must be non-negative")
        if self.config.displacement_factor < 0:
            raise ValueError("displacement_factor must be non-negative")
        if self.config.optimization_mode not in {"headline_operational", "general_nonlinear"}:
            raise ValueError(
                "optimization_mode must be 'headline_operational' or 'general_nonlinear'"
            )
        if self.config.n_multistart < 1:
            raise ValueError("n_multistart must be >= 1")
        if self.config.global_screen_grid < 5:
            raise ValueError("global_screen_grid must be >= 5")

        self._conversion_checks_passed = conversion_checks_pass(self.config.grid_CO2_intensity)

    def _htse_heat_required(self, W_htse: float) -> float:
        """Convert HTSE electric allocation into required steam-heat load [W]."""
        elec_intensity = self.config.htse_config.elec_intensity
        heat_intensity = self.config.htse_config.heat_intensity
        if elec_intensity <= 0:
            return float("inf")
        return max(W_htse, 0.0) * (heat_intensity / elec_intensity)

    def _net_co2_reduction(
        self,
        co2_dac_kg_s: float,
        co2_grid_kg_s: float,
        co2_embodied_kg_s: float,
        co2_displaced_fossil_kg_s: float,
        co2_reemitted_synthetic_kg_s: float,
    ) -> float:
        """Apply selected CO2 accounting boundary."""
        if self.config.co2_accounting_mode == "operational_only":
            return co2_dac_kg_s + co2_grid_kg_s
        # Fuel-displacement sensitivity mode.
        net = co2_displaced_fossil_kg_s + co2_grid_kg_s - co2_embodied_kg_s
        if not self.config.apply_neutrality_condition:
            net -= co2_reemitted_synthetic_kg_s
        return net

    def _evaluate_candidate(
        self,
        W_HTSE: float,
        W_DAC: float,
        Q_DAC: float,
        W_grid: float,
        W_allocatable: float,
        Q_waste_available: float,
        T_waste: float,
        dac_feasible: bool,
    ) -> Dict[str, object]:
        """Evaluate a single allocation candidate and return objective + diagnostics."""
        cfg = self.config
        W_HTSE = max(float(W_HTSE), 0.0)
        W_DAC = max(float(W_DAC), 0.0)
        Q_DAC = max(float(Q_DAC), 0.0)
        W_grid = max(float(W_grid), 0.0)

        Q_to_HTSE = self._htse_heat_required(W_HTSE) if cfg.enforce_htse_heat_constraint else 0.0
        elec_margin = W_allocatable - W_HTSE - W_DAC - W_grid
        heat_margin = Q_waste_available - Q_DAC - Q_to_HTSE

        htse_out = self.htse.calculate(
            W_HTSE,
            Q_steam=Q_to_HTSE if cfg.enforce_htse_heat_constraint else None,
        )
        dac_out = self.dac.calculate(Q_DAC, W_DAC, T_waste)
        m_H2 = htse_out["m_H2_produced_kg_s"]
        m_CO2_dac = dac_out["m_CO2_captured_kg_s"] if dac_out["feasible"] else 0.0
        meoh_out = self.methanol.calculate(m_H2, m_CO2_dac)
        m_MeOH = meoh_out["m_MeOH_produced_kg_s"]

        CO2_grid_kg_s = W_grid * cfg.grid_CO2_intensity / (3.6e6 * 1000.0)
        CO2_embodied_kg_s = m_MeOH * cfg.embodied_CO2_per_kg_MeOH
        CO2_displaced_fossil_kg_s = (
            m_MeOH * cfg.fuel_emission_factor_kgco2_per_kg * cfg.displacement_factor
        )
        CO2_reemitted_synthetic_kg_s = meoh_out["m_CO2_consumed_kg_s"]
        CO2_net_kg_s = self._net_co2_reduction(
            co2_dac_kg_s=m_CO2_dac,
            co2_grid_kg_s=CO2_grid_kg_s,
            co2_embodied_kg_s=CO2_embodied_kg_s,
            co2_displaced_fossil_kg_s=CO2_displaced_fossil_kg_s,
            co2_reemitted_synthetic_kg_s=CO2_reemitted_synthetic_kg_s,
        )

        if cfg.objective == AllocationObjective.MAX_CO2_NET:
            objective_value = CO2_net_kg_s
        elif cfg.objective == AllocationObjective.MAX_HYDROGEN:
            objective_value = m_H2
        elif cfg.objective == AllocationObjective.MAX_METHANOL:
            objective_value = m_MeOH
        else:
            objective_value = CO2_net_kg_s

        constraint_feasible = (
            elec_margin >= -1e-6
            and heat_margin >= -1e-6
            and (dac_out["feasible"] or not dac_feasible or Q_DAC <= 1e-6)
        )

        return {
            "W_HTSE": W_HTSE,
            "W_DAC": W_DAC,
            "Q_DAC": Q_DAC,
            "W_grid": W_grid,
            "Q_to_HTSE": Q_to_HTSE,
            "Q_to_cooler": max(Q_waste_available - Q_DAC - Q_to_HTSE, 0.0),
            "elec_margin": elec_margin,
            "heat_margin": heat_margin,
            "constraint_feasible": constraint_feasible,
            "objective_value": float(objective_value),
            "htse_out": htse_out,
            "dac_out": dac_out,
            "meoh_out": meoh_out,
            "m_H2": m_H2,
            "m_CO2_dac": m_CO2_dac,
            "m_MeOH": m_MeOH,
            "CO2_grid_kg_s": CO2_grid_kg_s,
            "CO2_embodied_kg_s": CO2_embodied_kg_s,
            "CO2_displaced_fossil_kg_s": CO2_displaced_fossil_kg_s,
            "CO2_reemitted_synthetic_kg_s": CO2_reemitted_synthetic_kg_s,
            "CO2_net_kg_s": CO2_net_kg_s,
        }

    def _coarse_global_screen(
        self,
        W_allocatable: float,
        Q_waste_available: float,
        T_waste: float,
        dac_feasible: bool,
        grid_points: Optional[int] = None,
    ) -> Dict[str, object]:
        """Deterministic coarse screen to identify robust high-quality candidates."""
        cfg = self.config
        n = int(grid_points or cfg.global_screen_grid)
        n = max(n, 5)
        W_grid_max = cfg.max_grid_export_MW * 1e6 if cfg.allow_grid_export else 0.0

        W_HTSE_vals = np.linspace(0.0, W_allocatable, n)
        if W_grid_max > 0:
            W_grid_vals = np.linspace(0.0, W_grid_max, n)
        else:
            W_grid_vals = np.array([0.0])

        best = None
        best_obj = -np.inf
        evaluations = 0

        for W_HTSE in W_HTSE_vals:
            Q_to_HTSE = self._htse_heat_required(W_HTSE) if cfg.enforce_htse_heat_constraint else 0.0
            Q_DAC_max = max(Q_waste_available - Q_to_HTSE, 0.0)
            for W_grid in W_grid_vals:
                if W_HTSE + W_grid > W_allocatable + 1e-9:
                    continue
                W_DAC = max(W_allocatable - W_HTSE - W_grid, 0.0)
                cand = self._evaluate_candidate(
                    W_HTSE=W_HTSE,
                    W_DAC=W_DAC,
                    Q_DAC=Q_DAC_max,
                    W_grid=W_grid,
                    W_allocatable=W_allocatable,
                    Q_waste_available=Q_waste_available,
                    T_waste=T_waste,
                    dac_feasible=dac_feasible,
                )
                evaluations += 1
                if not cand["constraint_feasible"]:
                    continue
                if cand["objective_value"] > best_obj:
                    best_obj = cand["objective_value"]
                    best = cand

        return {
            "best_candidate": best,
            "best_objective": float(best_obj) if np.isfinite(best_obj) else float("-inf"),
            "evaluations": evaluations,
        }

    def _solve_headline_operational(
        self,
        W_allocatable: float,
        Q_waste_available: float,
        T_waste: float,
        dac_feasible: bool,
    ) -> Tuple[List[float], bool, int, str, Dict[str, float]]:
        """Deterministic solver for headline operational mode."""
        screen = self._coarse_global_screen(
            W_allocatable=W_allocatable,
            Q_waste_available=Q_waste_available,
            T_waste=T_waste,
            dac_feasible=dac_feasible,
            grid_points=max(self.config.global_screen_grid, 61),
        )
        best = screen["best_candidate"]
        if best is None:
            return [0.0, 0.0, 0.0, 0.0], False, screen["evaluations"], "No feasible deterministic headline solution", {
                "method": 1.0,
                "screen_evaluations": float(screen["evaluations"]),
            }
        return (
            [best["W_HTSE"], best["W_DAC"], best["Q_DAC"], best["W_grid"]],
            True,
            screen["evaluations"],
            "Deterministic headline solver",
            {
                "method": 1.0,
                "screen_evaluations": float(screen["evaluations"]),
                "screen_best_objective": float(screen["best_objective"]),
            },
        )

    def _solve_general_nonlinear(
        self,
        W_allocatable: float,
        Q_waste_available: float,
        T_waste: float,
        dac_feasible: bool,
    ) -> Tuple[List[float], bool, int, str, Dict[str, float]]:
        """Multi-start SLSQP solve with deterministic screen seeding."""
        cfg = self.config
        W_grid_max = cfg.max_grid_export_MW * 1e6 if cfg.allow_grid_export else 0.0
        q_dac_max = Q_waste_available if dac_feasible else 0.0
        bounds = Bounds(
            lb=[0.0, 0.0, 0.0, 0.0],
            ub=[W_allocatable, W_allocatable, q_dac_max, W_grid_max],
        )

        def elec_constraint(x):
            return W_allocatable - x[0] - x[1] - x[3]

        def heat_constraint(x):
            q_htse = self._htse_heat_required(x[0]) if cfg.enforce_htse_heat_constraint else 0.0
            return Q_waste_available - x[2] - q_htse

        constraints = [
            {"type": "ineq", "fun": elec_constraint},
            {"type": "ineq", "fun": heat_constraint},
        ]

        def objective(x):
            cand = self._evaluate_candidate(
                W_HTSE=x[0],
                W_DAC=x[1],
                Q_DAC=x[2],
                W_grid=x[3],
                W_allocatable=W_allocatable,
                Q_waste_available=Q_waste_available,
                T_waste=T_waste,
                dac_feasible=dac_feasible,
            )
            if not cand["constraint_feasible"]:
                penalty = max(-cand["elec_margin"], 0.0) + max(-cand["heat_margin"], 0.0)
                return 1e6 + 1e3 * penalty
            return -cand["objective_value"]

        screen = self._coarse_global_screen(
            W_allocatable=W_allocatable,
            Q_waste_available=Q_waste_available,
            T_waste=T_waste,
            dac_feasible=dac_feasible,
            grid_points=cfg.global_screen_grid,
        )
        seeds: List[List[float]] = []
        if screen["best_candidate"] is not None:
            b = screen["best_candidate"]
            seeds.append([b["W_HTSE"], b["W_DAC"], b["Q_DAC"], b["W_grid"]])

        if dac_feasible and Q_waste_available > 0:
            x0 = [0.3 * W_allocatable, 0.2 * W_allocatable, 0.5 * Q_waste_available, 0.0]
        else:
            x0 = [0.8 * W_allocatable, 0.0, 0.0, 0.0]
        if cfg.enforce_htse_heat_constraint:
            q_htse_guess = self._htse_heat_required(x0[0])
            x0[2] = min(x0[2], max(Q_waste_available - q_htse_guess, 0.0))
        seeds.append(x0)

        rng = np.random.default_rng(20260301)
        for _ in range(cfg.n_multistart):
            W_HTSE = float(rng.uniform(0.0, W_allocatable))
            W_grid = float(rng.uniform(0.0, W_grid_max)) if W_grid_max > 0 else 0.0
            if W_HTSE + W_grid > W_allocatable:
                scale = W_allocatable / max(W_HTSE + W_grid, 1.0)
                W_HTSE *= scale
                W_grid *= scale
            W_DAC = max(W_allocatable - W_HTSE - W_grid, 0.0)
            Q_to_HTSE = self._htse_heat_required(W_HTSE) if cfg.enforce_htse_heat_constraint else 0.0
            Q_DAC_max = max(Q_waste_available - Q_to_HTSE, 0.0)
            Q_DAC = float(rng.uniform(0.0, Q_DAC_max)) if Q_DAC_max > 0 else 0.0
            seeds.append([W_HTSE, W_DAC, Q_DAC, W_grid])

        best_x = None
        best_obj = -np.inf
        best_success = False
        total_iters = 0
        n_success = 0

        for seed in seeds:
            res = minimize(
                objective,
                seed,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 200, "ftol": 1e-10},
            )
            total_iters += int(getattr(res, "nit", 0))
            x_eval = res.x if hasattr(res, "x") else np.array(seed, dtype=float)
            cand = self._evaluate_candidate(
                W_HTSE=x_eval[0],
                W_DAC=x_eval[1],
                Q_DAC=x_eval[2],
                W_grid=x_eval[3],
                W_allocatable=W_allocatable,
                Q_waste_available=Q_waste_available,
                T_waste=T_waste,
                dac_feasible=dac_feasible,
            )
            if res.success and cand["constraint_feasible"]:
                n_success += 1
                if cand["objective_value"] > best_obj:
                    best_obj = cand["objective_value"]
                    best_x = [cand["W_HTSE"], cand["W_DAC"], cand["Q_DAC"], cand["W_grid"]]
                    best_success = True

        if best_x is None and screen["best_candidate"] is not None:
            b = screen["best_candidate"]
            best_x = [b["W_HTSE"], b["W_DAC"], b["Q_DAC"], b["W_grid"]]
            best_obj = b["objective_value"]
            best_success = True

        if best_x is None:
            return [0.0, 0.0, 0.0, 0.0], False, total_iters, "No feasible nonlinear solution", {
                "method": 2.0,
                "screen_evaluations": float(screen["evaluations"]),
                "n_multistart": float(cfg.n_multistart),
                "n_successful_solves": float(n_success),
                "best_objective": float("-inf"),
            }

        return (
            best_x,
            best_success,
            total_iters,
            "Multi-start nonlinear solver",
            {
                "method": 2.0,
                "screen_evaluations": float(screen["evaluations"]),
                "n_multistart": float(cfg.n_multistart),
                "n_successful_solves": float(n_success),
                "best_objective": float(best_obj),
            },
        )

    def allocate(self,
                 W_net_available: float,
                 Q_waste_available: float,
                 T_waste: float,
                 W_aux: float = 0) -> AllocationResult:
        """
        Optimize allocation of electricity and heat to processes.

        Args:
            W_net_available: Net electricity available after cycle parasitics [W]
            Q_waste_available: Usable waste heat available [W]
            T_waste: Temperature of waste heat [K]
            W_aux: Fixed auxiliary power consumption [W]

        Returns:
            AllocationResult with optimal allocation
        """
        cfg = self.config

        # Available after auxiliary
        W_allocatable = W_net_available - W_aux
        if W_allocatable < 0:
            return self._infeasible_result("Auxiliary power exceeds net power")

        # Check if DAC is thermally feasible
        dac_feasible = T_waste >= cfg.dac_config.T_regen_min
        if (
            cfg.optimization_mode == "headline_operational"
            and cfg.objective == AllocationObjective.MAX_CO2_NET
        ):
            x_opt, converged, iterations, message, optimizer_diag = self._solve_headline_operational(
                W_allocatable=W_allocatable,
                Q_waste_available=Q_waste_available,
                T_waste=T_waste,
                dac_feasible=dac_feasible,
            )
        else:
            x_opt, converged, iterations, message, optimizer_diag = self._solve_general_nonlinear(
                W_allocatable=W_allocatable,
                Q_waste_available=Q_waste_available,
                T_waste=T_waste,
                dac_feasible=dac_feasible,
            )

        cand = self._evaluate_candidate(
            W_HTSE=x_opt[0],
            W_DAC=x_opt[1],
            Q_DAC=x_opt[2],
            W_grid=x_opt[3],
            W_allocatable=W_allocatable,
            Q_waste_available=Q_waste_available,
            T_waste=T_waste,
            dac_feasible=dac_feasible,
        )

        screen_check = self._coarse_global_screen(
            W_allocatable=W_allocatable,
            Q_waste_available=Q_waste_available,
            T_waste=T_waste,
            dac_feasible=dac_feasible,
            grid_points=cfg.global_screen_grid,
        )
        objective_best_alt = screen_check["best_objective"]
        if np.isfinite(objective_best_alt):
            objective_gap_rel = max(
                0.0,
                (objective_best_alt - cand["objective_value"]) / max(abs(objective_best_alt), 1.0),
            )
        else:
            objective_gap_rel = 0.0
        objective_consistency_passed = objective_gap_rel <= cfg.objective_gap_tolerance_rel

        if not objective_consistency_passed:
            converged = False
            message = (
                f"{message}; objective consistency failed "
                f"(gap={objective_gap_rel:.4f} > tol={cfg.objective_gap_tolerance_rel:.4f})"
            )

        # Build CO2 accounting
        seconds_per_year = 365.25 * 24 * 3600
        capacity_factor = 0.90

        allocation_feasible = bool(cand["constraint_feasible"] and objective_consistency_passed)
        elec_margin = cand["elec_margin"]
        heat_margin = cand["heat_margin"]
        W_HTSE = cand["W_HTSE"]
        W_DAC = cand["W_DAC"]
        Q_DAC = cand["Q_DAC"]
        W_grid = cand["W_grid"]
        Q_to_HTSE = cand["Q_to_HTSE"]
        Q_to_cooler = cand["Q_to_cooler"]
        htse_out = cand["htse_out"]
        dac_out = cand["dac_out"]
        meoh_out = cand["meoh_out"]
        m_H2 = cand["m_H2"]
        m_CO2_dac = cand["m_CO2_dac"]
        CO2_grid_kg_s = cand["CO2_grid_kg_s"]
        CO2_embodied_kg_s = cand["CO2_embodied_kg_s"]
        CO2_displaced_fossil_kg_s = cand["CO2_displaced_fossil_kg_s"]
        CO2_reemitted_synthetic_kg_s = cand["CO2_reemitted_synthetic_kg_s"]
        CO2_net_kg_s = cand["CO2_net_kg_s"]

        co2_accounting = CO2AccountingResult(
            W_to_grid=W_grid,
            CO2_avoided_grid_kg_s=CO2_grid_kg_s,
            CO2_avoided_grid_t_yr=CO2_grid_kg_s * seconds_per_year / 1000 * capacity_factor,

            W_to_DAC=W_DAC,
            Q_to_DAC=Q_DAC,
            CO2_captured_DAC_kg_s=m_CO2_dac,
            CO2_captured_DAC_t_yr=m_CO2_dac * seconds_per_year / 1000 * capacity_factor,
            co2_dac_captured_t_yr=m_CO2_dac * seconds_per_year / 1000 * capacity_factor,

            W_to_HTSE=W_HTSE,
            H2_produced_kg_s=m_H2,
            H2_produced_t_yr=m_H2 * seconds_per_year / 1000 * capacity_factor,

            MeOH_produced_kg_s=meoh_out['m_MeOH_produced_kg_s'],
            MeOH_produced_t_yr=meoh_out['m_MeOH_produced_t_yr'],
            CO2_consumed_MeOH_kg_s=meoh_out['m_CO2_consumed_kg_s'],

            CO2_embodied_kg_s=CO2_embodied_kg_s,
            CO2_embodied_t_yr=CO2_embodied_kg_s * seconds_per_year / 1000 * capacity_factor,
            CO2_displaced_fossil_kg_s=CO2_displaced_fossil_kg_s,
            CO2_displaced_fossil_t_yr=CO2_displaced_fossil_kg_s * seconds_per_year / 1000 * capacity_factor,
            CO2_reemitted_synthetic_kg_s=CO2_reemitted_synthetic_kg_s,
            CO2_reemitted_synthetic_t_yr=CO2_reemitted_synthetic_kg_s * seconds_per_year / 1000 * capacity_factor,
            co2_displaced_fossil_t_yr=CO2_displaced_fossil_kg_s * seconds_per_year / 1000 * capacity_factor,
            co2_reemitted_synthetic_t_yr=CO2_reemitted_synthetic_kg_s * seconds_per_year / 1000 * capacity_factor,

            CO2_net_reduction_kg_s=CO2_net_kg_s,
            CO2_net_reduction_t_yr=CO2_net_kg_s * seconds_per_year / 1000 * capacity_factor,

            # FOM: CO2 per MWth per year (will be set by caller with Q_thermal)
            CO2_per_MWth_yr=0,  # Placeholder
            specific_CO2_reduction=0,  # Placeholder
            co2_accounting_mode=cfg.co2_accounting_mode,
            co2_boundary_mode=cfg.co2_accounting_mode,
            conversion_checks_passed=self._conversion_checks_passed,
        )

        return AllocationResult(
            feasible=allocation_feasible,
            converged=converged,
            W_to_HTSE=W_HTSE,
            W_to_DAC=W_DAC,
            Q_to_DAC=Q_DAC,
            W_to_grid=W_grid,
            W_aux=W_aux,
            Q_to_cooler=Q_to_cooler,
            Q_to_HTSE=Q_to_HTSE,
            dac_result=dac_out,
            htse_result=htse_out,
            methanol_result=meoh_out,
            co2_accounting=co2_accounting,
            objective_value=cand["objective_value"],
            objective_consistency_passed=objective_consistency_passed,
            objective_best_alt=objective_best_alt if np.isfinite(objective_best_alt) else cand["objective_value"],
            objective_gap_rel=objective_gap_rel,
            optimizer_diagnostics={
                **optimizer_diag,
                "objective_screen_evaluations": float(screen_check["evaluations"]),
                "objective_current": float(cand["objective_value"]),
                "objective_best_alt": (
                    float(objective_best_alt) if np.isfinite(objective_best_alt) else float(cand["objective_value"])
                ),
                "objective_gap_rel": float(objective_gap_rel),
                "objective_gap_tolerance_rel": float(cfg.objective_gap_tolerance_rel),
            },
            iterations=iterations,
            message=message,
            scenario_metadata={
                "scenario_name": cfg.scenario_name,
                "scenario_id": cfg.scenario_id,
                "baseline_or_sensitivity": cfg.baseline_or_sensitivity,
                "source_assumptions_version": cfg.source_assumptions_version,
                "co2_accounting_mode": cfg.co2_accounting_mode,
                "co2_boundary_mode": cfg.co2_accounting_mode,
                "allow_grid_export": cfg.allow_grid_export,
                "grid_CO2_intensity_g_per_kWh": cfg.grid_CO2_intensity,
                "enforce_htse_heat_constraint": cfg.enforce_htse_heat_constraint,
                "apply_neutrality_condition": cfg.apply_neutrality_condition,
                "fuel_emission_factor_kgco2_per_kg": cfg.fuel_emission_factor_kgco2_per_kg,
                "displacement_factor": cfg.displacement_factor,
                "conversion_checks_passed": self._conversion_checks_passed,
                "heat_margin_W": heat_margin,
                "elec_margin_W": elec_margin,
                "optimization_mode": cfg.optimization_mode,
                "objective_consistency_passed": objective_consistency_passed,
                "objective_gap_rel": objective_gap_rel,
                "objective_gap_tolerance_rel": cfg.objective_gap_tolerance_rel,
            },
        )

    def _infeasible_result(self, message: str) -> AllocationResult:
        """Create infeasible result."""
        empty_co2 = CO2AccountingResult(
            W_to_grid=0, CO2_avoided_grid_kg_s=0, CO2_avoided_grid_t_yr=0,
            W_to_DAC=0, Q_to_DAC=0, CO2_captured_DAC_kg_s=0, CO2_captured_DAC_t_yr=0,
            co2_dac_captured_t_yr=0,
            W_to_HTSE=0, H2_produced_kg_s=0, H2_produced_t_yr=0,
            MeOH_produced_kg_s=0, MeOH_produced_t_yr=0, CO2_consumed_MeOH_kg_s=0,
            CO2_embodied_kg_s=0, CO2_embodied_t_yr=0,
            CO2_displaced_fossil_kg_s=0, CO2_displaced_fossil_t_yr=0,
            CO2_reemitted_synthetic_kg_s=0, CO2_reemitted_synthetic_t_yr=0,
            co2_displaced_fossil_t_yr=0, co2_reemitted_synthetic_t_yr=0,
            CO2_net_reduction_kg_s=0, CO2_net_reduction_t_yr=0,
            CO2_per_MWth_yr=0, specific_CO2_reduction=0,
            co2_accounting_mode=self.config.co2_accounting_mode,
            co2_boundary_mode=self.config.co2_accounting_mode,
            conversion_checks_passed=self._conversion_checks_passed,
        )
        return AllocationResult(
            feasible=False, converged=False,
            W_to_HTSE=0, W_to_DAC=0, Q_to_DAC=0, W_to_grid=0, W_aux=0,
            Q_to_cooler=0, Q_to_HTSE=0,
            dac_result={}, htse_result={}, methanol_result=None,
            co2_accounting=empty_co2,
            objective_value=0,
            objective_consistency_passed=False,
            objective_best_alt=0,
            objective_gap_rel=1.0,
            optimizer_diagnostics={"error": 1.0},
            iterations=0,
            message=message,
            scenario_metadata={
                "scenario_name": self.config.scenario_name,
                "scenario_id": self.config.scenario_id,
                "baseline_or_sensitivity": self.config.baseline_or_sensitivity,
                "source_assumptions_version": self.config.source_assumptions_version,
                "co2_accounting_mode": self.config.co2_accounting_mode,
                "co2_boundary_mode": self.config.co2_accounting_mode,
                "allow_grid_export": self.config.allow_grid_export,
                "grid_CO2_intensity_g_per_kWh": self.config.grid_CO2_intensity,
                "enforce_htse_heat_constraint": self.config.enforce_htse_heat_constraint,
                "apply_neutrality_condition": self.config.apply_neutrality_condition,
                "fuel_emission_factor_kgco2_per_kg": self.config.fuel_emission_factor_kgco2_per_kg,
                "displacement_factor": self.config.displacement_factor,
                "conversion_checks_passed": self._conversion_checks_passed,
                "optimization_mode": self.config.optimization_mode,
                "objective_consistency_passed": False,
                "objective_gap_rel": 1.0,
                "objective_gap_tolerance_rel": self.config.objective_gap_tolerance_rel,
            },
        )


def calculate_plant_co2_reduction(
    Q_thermal: float,
    W_net: float,
    Q_waste: float,
    T_waste: float,
    W_fan: float,
    config: Optional[AllocationConfig] = None
) -> Tuple[AllocationResult, Dict]:
    """
    Calculate complete CO2 reduction for the plant.

    This is the main entry point for CO2 accounting.

    Args:
        Q_thermal: Reactor thermal power [W]
        W_net: Net electrical power (after fan) [W]
        Q_waste: Waste heat available [W]
        T_waste: Waste heat temperature [K]
        W_fan: Fan power (already subtracted from W_net) [W]
        config: Allocation configuration

    Returns:
        Tuple of (AllocationResult, summary_dict)
    """
    allocator = ProcessAllocator(config)

    # Do not double-subtract auxiliaries: W_net from plant solver is already post-aux.
    W_aux = (config.allocation_auxiliary_power_W if config is not None else 0.0)

    # Run allocation optimization
    result = allocator.allocate(
        W_net_available=W_net,
        Q_waste_available=Q_waste,
        T_waste=T_waste,
        W_aux=W_aux
    )

    # Calculate FOMs
    Q_thermal_MW = Q_thermal / 1e6
    hours_per_year = 8760 * 0.90  # 90% capacity factor

    # Update CO2 per MWth per year
    co2 = result.co2_accounting
    co2.CO2_per_MWth_yr = co2.CO2_net_reduction_t_yr / Q_thermal_MW

    # Specific CO2 reduction: kg CO2 per kWh thermal
    Q_thermal_kWh_yr = Q_thermal / 1000 * hours_per_year
    co2.specific_CO2_reduction = (co2.CO2_net_reduction_t_yr * 1000) / Q_thermal_kWh_yr if Q_thermal_kWh_yr > 0 else 0

    # Build summary
    summary = {
        'Q_thermal_MW': Q_thermal_MW,
        'W_net_MW': W_net / 1e6,
        'Q_waste_MW': Q_waste / 1e6,
        'T_waste_C': T_waste - 273.15,

        'allocation': {
            'W_HTSE_MW': result.W_to_HTSE / 1e6,
            'W_DAC_MW': result.W_to_DAC / 1e6,
            'Q_DAC_MW': result.Q_to_DAC / 1e6,
            'Q_HTSE_MW': result.Q_to_HTSE / 1e6,
            'W_grid_MW': result.W_to_grid / 1e6,
            'Q_cooler_MW': result.Q_to_cooler / 1e6,
            'objective_value': result.objective_value,
            'objective_consistency_passed': result.objective_consistency_passed,
            'objective_best_alt': result.objective_best_alt,
            'objective_gap_rel': result.objective_gap_rel,
        },

        'production': {
            'H2_t_yr': co2.H2_produced_t_yr,
            'CO2_captured_t_yr': co2.CO2_captured_DAC_t_yr,
            'MeOH_t_yr': co2.MeOH_produced_t_yr,
        },

        'co2_balance': {
            'avoided_grid_t_yr': co2.CO2_avoided_grid_t_yr,
            'captured_DAC_t_yr': co2.CO2_captured_DAC_t_yr,
            'embodied_t_yr': co2.CO2_embodied_t_yr,
            'displaced_fossil_t_yr': co2.co2_displaced_fossil_t_yr,
            'reemitted_synthetic_t_yr': co2.co2_reemitted_synthetic_t_yr,
            'net_reduction_t_yr': co2.CO2_net_reduction_t_yr,
        },

        'figures_of_merit': {
            'CO2_per_MWth_yr': co2.CO2_per_MWth_yr,
            'specific_CO2_kg_per_kWh_th': co2.specific_CO2_reduction,
            'co2_accounting_mode': co2.co2_accounting_mode,
            'co2_boundary_mode': co2.co2_boundary_mode,
            'conversion_checks_passed': co2.conversion_checks_passed,
        },

        'scenario_metadata': result.scenario_metadata,
    }

    return result, summary
