# Corrected Simulation Architecture: HTGR + sCO₂ + Process Plant

**Document Purpose:** Engineering design review and corrected modelling approach for physically consistent simulation.
**Date:** 2026-01-20
**Status:** Architecture specification (pre-implementation)

---

## Executive Summary

This document addresses six identified flaws in the original `implementation_spec.md` and provides a corrected solver architecture that:

1. Uses **enthalpy-based segmented heat exchanger models** instead of temperature-effectiveness approximations
2. Includes **pressure drops** throughout the cycle
3. Solves the **IHX and cycle as a coupled system**, not sequential guess-then-check
4. Models **dry cooler parasitics physically** based on airflow and pressure drop
5. Replaces **heuristic allocations** with constrained optimization
6. **Embeds feasibility checks** into the solve loop, not as post-hoc verification

---

## A) Corrected Modelling/Solver Architecture

### A.1 System Decomposition and State Variables

The plant must be solved as a **single coupled nonlinear system**, not a sequential cascade. Define the unknown vector **x** and constraint vector **F(x) = 0**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PRIMARY UNKNOWNS (design variables to be solved)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Cycle:                                                                     │
│    x[0]  = m_dot_CO2        [kg/s]   CO₂ mass flow rate                    │
│    x[1]  = T_5              [K]      Turbine inlet temperature             │
│    x[2]  = T_1              [K]      Main compressor inlet temperature     │
│    x[3]  = f_recomp         [-]      Recompression fraction (0.25-0.45)    │
│    x[4]  = P_high           [Pa]     High-side pressure                    │
│    x[5]  = P_low            [Pa]     Low-side pressure                     │
│                                                                             │
│  Recuperators (segmented):                                                  │
│    x[6:6+N_seg]  = T_HTR_hot[i]      HTR hot-side segment temperatures    │
│    x[...]        = T_LTR_hot[i]      LTR hot-side segment temperatures    │
│                                                                             │
│  Heat Exchangers:                                                           │
│    x[...]  = Q_IHX          [W]      IHX heat duty                         │
│    x[...]  = T_He_out       [K]      Helium outlet from IHX                │
│                                                                             │
│  Cooler:                                                                    │
│    x[...]  = m_dot_air      [kg/s]   Air mass flow through dry cooler     │
│                                                                             │
│  Process Allocation:                                                        │
│    x[...]  = W_to_HTSE      [W]      Electricity allocated to HTSE        │
│    x[...]  = Q_to_DAC       [W]      Heat allocated to DAC                 │
│    x[...]  = W_to_DAC       [W]      Electricity allocated to DAC          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### A.2 Constraint Equations (Residuals)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  EQUALITY CONSTRAINTS: F(x) = 0                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CYCLE ENERGY BALANCES (enthalpy-based, per segment):                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  F_HTR[i]:  m_dot*(h_hot[i] - h_hot[i+1]) - m_dot*(h_cold[i+1] - h_cold[i])│
│             = 0  for i = 1..N_seg                                          │
│                                                                             │
│  F_LTR[i]:  m_dot*(h_hot[i] - h_hot[i+1])                                  │
│             - (1-f)*m_dot*(h_cold[i+1] - h_cold[i]) = 0                    │
│                                                                             │
│  F_merge:   h_3 - [(1-f)*h_LTR_cold_out + f*h_9] = 0                       │
│                                                                             │
│  IHX COUPLING:                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  F_IHX_He:  Q_IHX - m_dot_He*(h_He_in - h_He_out) = 0                      │
│  F_IHX_CO2: Q_IHX - m_dot_CO2*(h_5 - h_4) = 0                              │
│                                                                             │
│  COOLER COUPLING:                                                           │
│  ─────────────────────────────────────────────────────────────────────────  │
│  F_cooler:  Q_reject - m_dot_air*cp_air*(T_air_out - T_ambient) = 0        │
│  F_T1:      T_1 - T_CO2_cooler_out = 0                                     │
│                                                                             │
│  PRESSURE DROPS (per component):                                            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  F_dP_IHX_He:   P_He_in - P_He_out - dP_IHX_He(m_dot_He, T_avg, geom) = 0  │
│  F_dP_IHX_CO2:  ...                                                        │
│  F_dP_HTR:      ...                                                        │
│  F_dP_LTR:      ...                                                        │
│  F_dP_cooler:   ...                                                        │
│                                                                             │
│  ALLOCATION CONSTRAINTS:                                                    │
│  ─────────────────────────────────────────────────────────────────────────  │
│  F_elec:    W_net - W_parasitic - W_to_HTSE - W_to_DAC - W_to_grid = 0     │
│  F_heat:    Q_waste_usable - Q_to_DAC - Q_to_cooler = 0                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### A.3 Inequality Constraints (Feasibility Conditions)

These must be **active during the solve**, not checked afterward:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INEQUALITY CONSTRAINTS: g(x) ≥ 0  (embedded in solver)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PINCH CONSTRAINTS (per HX segment i):                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  g_pinch_IHX[i]:    T_He[i] - T_CO2[i] - ΔT_pinch_min ≥ 0                  │
│  g_pinch_HTR[i]:    T_hot[i] - T_cold[i] - ΔT_pinch_min ≥ 0               │
│  g_pinch_LTR[i]:    T_hot[i] - T_cold[i] - ΔT_pinch_min ≥ 0               │
│  g_pinch_cooler[i]: T_CO2[i] - T_air[i] - ΔT_pinch_min ≥ 0                │
│                                                                             │
│  SUPERCRITICAL MARGIN:                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  g_Tcrit:   T_1 - T_critical - ΔT_margin ≥ 0   (e.g., margin = 2-5 K)     │
│  g_Pcrit:   P_low - P_critical - ΔP_margin ≥ 0 (e.g., margin = 0.3 MPa)   │
│                                                                             │
│  TEMPERATURE LIMITS:                                                        │
│  ─────────────────────────────────────────────────────────────────────────  │
│  g_TIT:     T_TIT_max - T_5 ≥ 0                                            │
│  g_Trecomp: T_9 - T_3 ≥ 0  (recompressor outlet ≥ merge point)            │
│                                                                             │
│  POSITIVE QUANTITIES:                                                       │
│  ─────────────────────────────────────────────────────────────────────────  │
│  g_Wnet:    W_turbine - W_comp_main - W_comp_recomp - W_parasitic ≥ 0     │
│  g_mdot:    m_dot_CO2 > 0, m_dot_air > 0                                   │
│  g_alloc:   W_to_HTSE ≥ 0, Q_to_DAC ≥ 0, W_to_DAC ≥ 0                     │
│                                                                             │
│  DAC TEMPERATURE GRADE:                                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  g_DAC_T:   T_waste_heat - T_DAC_regen_min ≥ 0   (if Q_to_DAC > 0)        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### A.4 Solver Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COUPLED SOLVE STRATEGY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OUTER LOOP: scipy.optimize.minimize with method='SLSQP' or 'trust-constr' │
│  ═══════════════════════════════════════════════════════════════════════   │
│  │                                                                         │
│  │  Objective: Maximize net CO₂ reduction  OR  Minimize deviation from    │
│  │             target (depends on user mode)                               │
│  │                                                                         │
│  │  Subject to:                                                            │
│  │    - All equality constraints F(x) = 0                                  │
│  │    - All inequality constraints g(x) ≥ 0                                │
│  │    - Bounds on all variables                                            │
│  │                                                                         │
│  └──────────────────────────────────────────────────────────────────────   │
│                                                                             │
│  ALTERNATIVE: Nested iteration for better convergence                      │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  Level 1 (Outer): Fixed-point on (T_5, T_1, P_low, f_recomp)              │
│  ├── Level 2 (Middle): Given T_5, solve IHX + cycle together               │
│  │   ├── Level 3 (Inner): Segmented HX solve for HTR, LTR                  │
│  │   │   └── Newton-Raphson on segment energy balances                     │
│  │   └── Check pinch at every segment; backtrack if violated               │
│  └── Update T_1 from cooler model; update T_5 from IHX approach            │
│                                                                             │
│  CONVERGENCE CRITERIA:                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  │ΔT_5| < 0.1 K, |ΔT_1| < 0.1 K, |Δm_dot| < 0.001 kg/s                    │
│  Energy closure < 0.01%                                                     │
│  All pinch margins > ΔT_min                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### A.5 Segmented Heat Exchanger Method

**This replaces the effectiveness approximation** for recuperators and IHX:

```python
# PSEUDOCODE: Segmented counterflow HX solver

def solve_counterflow_hx_segmented(
    T_hot_in, P_hot_in, m_dot_hot, fluid_hot,
    T_cold_in, P_cold_in, m_dot_cold, fluid_cold,
    N_segments, dT_pinch_min, dP_correlation
):
    """
    Solves counterflow HX by discretizing into N segments.
    Each segment: local energy balance with real-gas properties.

    Returns: T_hot_out, T_cold_out, Q_total, dT_pinch_min_actual,
             P_hot_out, P_cold_out, segment_data, feasibility_status
    """

    # Discretize heat duty into segments
    # Initial estimate of total Q from enthalpy limits
    h_hot_in = fluid_hot.h(T_hot_in, P_hot_in)
    h_cold_in = fluid_cold.h(T_cold_in, P_cold_in)

    # Iterate to find consistent temperature profiles
    # Hot side: flows from segment 0 (inlet) to N-1 (outlet)
    # Cold side: flows from segment N-1 (inlet) to 0 (outlet) [counterflow]

    for iteration in range(max_iterations):

        # March hot side forward, cold side backward
        for i in range(N_segments):
            # Segment energy balance:
            # Q_seg[i] = m_dot_hot * (h_hot[i] - h_hot[i+1])
            #          = m_dot_cold * (h_cold[i+1] - h_cold[i])

            # Local properties at segment midpoint
            T_hot_mid = 0.5 * (T_hot[i] + T_hot[i+1])
            T_cold_mid = 0.5 * (T_cold[i] + T_cold[i+1])

            # Enthalpy balance (Newton iteration per segment)
            # ...

            # PINCH CHECK - embedded in solve
            dT_local = T_hot[i] - T_cold[i]  # at hot inlet of segment
            if dT_local < dT_pinch_min:
                return InfeasibilityResult(
                    type='PINCH_VIOLATION',
                    segment=i,
                    dT_actual=dT_local,
                    dT_required=dT_pinch_min
                )

        # Pressure drop per segment (friction correlation)
        for i in range(N_segments):
            dP_hot[i] = dP_correlation(m_dot_hot, rho_hot[i], ...)
            dP_cold[i] = dP_correlation(m_dot_cold, rho_cold[i], ...)

        P_hot_out = P_hot_in - sum(dP_hot)
        P_cold_out = P_cold_in - sum(dP_cold)

        # Check convergence
        if converged:
            break

    return HXResult(
        T_hot_out, T_cold_out, Q_total,
        min(dT_profile), P_hot_out, P_cold_out,
        segment_data, feasible=True
    )
```

### A.6 Dry Cooler Physical Model

**Replaces the constant fan_power_factor approach**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DRY COOLER: Physically-Coupled Model                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUTS:                                                                    │
│    Q_reject     [W]    Heat to reject                                      │
│    T_CO2_in     [K]    sCO₂ inlet temperature                              │
│    T_ambient    [K]    Air inlet temperature                               │
│    P_CO2        [Pa]   sCO₂ pressure                                       │
│    HX geometry         (tube OD, fin pitch, rows, face area)               │
│                                                                             │
│  SOLVE FOR:                                                                 │
│    m_dot_air    [kg/s]  Air mass flow rate                                 │
│    T_air_out    [K]     Air outlet temperature                             │
│    T_CO2_out    [K]     sCO₂ outlet temperature (= compressor inlet)       │
│    ΔP_air       [Pa]    Air-side pressure drop                             │
│    W_fan        [W]     Fan power                                          │
│                                                                             │
│  GOVERNING EQUATIONS:                                                       │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  1. Energy balance (air side):                                              │
│     Q_reject = m_dot_air * cp_air * (T_air_out - T_ambient)                │
│                                                                             │
│  2. Energy balance (CO₂ side):                                              │
│     Q_reject = m_dot_CO2 * (h_CO2_in - h_CO2_out)                          │
│                                                                             │
│  3. Heat transfer (ε-NTU or segmented UA):                                  │
│     UA = f(geometry, Re_air, Re_CO2, properties)                           │
│     ε = f(NTU, C_min/C_max, flow_arrangement)                              │
│     Q = ε * C_min * (T_CO2_in - T_ambient)                                 │
│                                                                             │
│  4. Air-side pressure drop (Kays & London or equivalent):                   │
│     ΔP_air = f(m_dot_air, geometry, ρ_air, μ_air)                          │
│                                                                             │
│  5. Fan power (including motor/drive efficiency):                           │
│     W_fan = (m_dot_air * ΔP_air) / (ρ_air * η_fan * η_motor)              │
│                                                                             │
│  ITERATION:                                                                 │
│    Given Q_reject and T_ambient, iterate on m_dot_air until                │
│    T_CO2_out ≥ T_ambient + ΔT_approach_min                                 │
│                                                                             │
│  CONSTRAINTS:                                                               │
│    T_CO2_out > T_critical + margin  (supercritical at compressor inlet)    │
│    Pinch at each segment ≥ ΔT_min                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### A.7 Process Allocation as Constrained Optimization

**Replaces heuristic caps**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PROCESS ALLOCATION: Constrained Optimization Subproblem                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DECISION VARIABLES:                                                        │
│    W_HTSE    [W]    Electricity to HTSE                                    │
│    W_DAC     [W]    Electricity to DAC                                     │
│    Q_DAC     [W]    Heat to DAC                                            │
│    W_grid    [W]    Electricity to grid (can be fixed = 0)                 │
│                                                                             │
│  OBJECTIVE (choose one mode):                                               │
│    Mode A: Maximize m_CO2_net = m_CO2_captured - m_CO2_embodied            │
│    Mode B: Maximize m_MeOH (methanol production)                           │
│    Mode C: Maximize weighted combination                                    │
│                                                                             │
│  SUBJECT TO:                                                                │
│                                                                             │
│  Electricity balance:                                                       │
│    W_net_available = W_HTSE + W_DAC + W_grid + W_aux                       │
│                                                                             │
│  Heat balance (for usable-grade heat):                                      │
│    Q_waste_usable = Q_DAC + Q_to_ambient_cooler                            │
│                                                                             │
│  Process physics (linking constraints):                                     │
│    m_H2 = W_HTSE / (elec_intensity_HTSE * 3.6e6)                           │
│    m_CO2_DAC = min(Q_DAC / (heat_int * 3.6e6), W_DAC / (elec_int * 3.6e6)) │
│    m_MeOH = f(m_H2, m_CO2_DAC)  [stoichiometric]                           │
│                                                                             │
│  Capacity/feasibility:                                                      │
│    W_HTSE ≤ W_HTSE_max_capacity                                            │
│    Q_DAC ≤ Q_DAC_max_capacity (or uncapped if sizing)                      │
│    T_waste ≥ T_DAC_regen_min  OR  Q_DAC = 0                                │
│                                                                             │
│  Non-negativity:                                                            │
│    W_HTSE, W_DAC, Q_DAC, W_grid ≥ 0                                        │
│                                                                             │
│  Policy constraints (user-specified):                                       │
│    W_grid = 0       (zero export policy)                                   │
│    W_grid ≤ W_max   (or any other policy)                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## B) Implementation Plan with Issue Resolution

### B.1 Implementation Phases

| Phase | Module                       | Issue(s) Fixed | Deliverable                                                 |
| ----- | ---------------------------- | -------------- | ----------------------------------------------------------- |
| **1** | `properties/fluids.py`       | Foundation     | CoolProp wrapper with phase-boundary checks                 |
| **2** | `hx/segmented_hx.py`         | **#1, #2**     | Segmented counterflow HX solver with pressure drop          |
| **3** | `components/recuperators.py` | **#1, #2, #6** | HTR/LTR using segmented solver with pinch enforcement       |
| **4** | `components/ihx.py`          | **#2, #3, #6** | IHX solver returning (Q, T_out) as function of inlet states |
| **5** | `components/dry_cooler.py`   | **#2, #4**     | Physical fan power model with UA-based sizing               |
| **6** | `cycle/sco2_cycle.py`        | **#1, #2, #6** | Cycle as residual function, not sequential solve            |
| **7** | `plant/coupled_solver.py`    | **#3, #6**     | Unified plant-level Newton/SLSQP solver                     |
| **8** | `process/allocation.py`      | **#5**         | Constrained allocation optimizer                            |
| **9** | `validation/`                | All            | Test cases, Dostal validation, energy closure               |

### B.2 Detailed Fix Mapping

#### Issue #1: Recuperator Physical Consistency

**Current Problem:**

```python
# OLD (implementation_spec.md lines 624-632)
T4_from_eps = T3_est + self.config.epsilon_HTR * (T6 - T3_est)  # WRONG near critical
```

**Corrected Approach:**

- Discretize each recuperator into 10-20 segments
- At each segment, compute **enthalpy change** from CoolProp (not temperature × assumed cp)
- Solve segment-by-segment with local energy balance: `m_dot * Δh_hot = m_dot * Δh_cold`
- Track pressure through each segment via friction correlation
- Check pinch **at every segment boundary** (not just endpoints)

```python
# NEW: Enthalpy-based segment balance
for seg in range(N_segments):
    # Hot side: h decreases, T decreases
    h_hot[seg+1] = h_hot[seg] - Q_seg / m_dot_hot
    T_hot[seg+1] = fluid.T_from_Ph(P_hot[seg+1], h_hot[seg+1])

    # Cold side: h increases, T increases (counterflow indexing)
    h_cold[seg] = h_cold[seg+1] - Q_seg / m_dot_cold
    T_cold[seg] = fluid.T_from_Ph(P_cold[seg], h_cold[seg])

    # PINCH CHECK (embedded)
    dT_pinch = T_hot[seg] - T_cold[seg]
    if dT_pinch < dT_min:
        raise PinchViolation(segment=seg, dT=dT_pinch)
```

#### Issue #2: Pressure Drops

**Current Problem:**

```python
# OLD (multiple locations)
P=He_in.P,  # Simplified: no pressure drop
```

**Corrected Approach:**

- Define pressure drop correlations per component type:
  - **Compact PCHE (IHX, recuperators):** Hesselgreaves or manufacturer data
  - **Finned tube (dry cooler):** Kays & London
  - **Piping:** Darcy-Weisbach
- Pressure drops are **state variables** in the coupled solve
- Compressor/turbine inlet/outlet pressures account for all drops

```python
# Pressure drop correlation (example for compact HX)
def dP_PCHE(m_dot, rho, mu, D_h, L, A_flow):
    """Pressure drop for printed-circuit HX channel."""
    Re = m_dot * D_h / (A_flow * mu)
    f = 0.0791 * Re**(-0.25)  # Turbulent Blasius (adjust for laminar)
    dP = f * (L / D_h) * 0.5 * rho * (m_dot / (rho * A_flow))**2
    return dP
```

#### Issue #3: IHX-Cycle Coupling

**Current Problem:**

```python
# OLD (implementation_spec.md lines 1287-1288)
T_TIT = T_He_hot - self.config.ihx.dT_approach  # DECOUPLED
```

**Corrected Approach:**

- IHX and cycle are solved **simultaneously**
- The IHX receives `(T_He_in, P_He_in, m_dot_He)` and `(T_CO2_in, P_CO2_in, m_dot_CO2)` as inputs
- It returns `(T_He_out, T_CO2_out, Q)` that satisfies:
  - Energy balance on both sides
  - Pinch constraint at all segments
  - The achieved T_CO2_out **is** T_5 (turbine inlet)
- The cycle's `T_4` (HTR cold outlet) feeds into IHX cold inlet
- This is a **simultaneous** system, not guess-then-verify

```
COUPLED RESIDUAL:
    R_IHX = Q_IHX - m_dot_CO2 * (h_5 - h_4)
    R_cycle = ... (cycle closure)

    Solve [R_IHX, R_cycle, ...] = 0 simultaneously
```

#### Issue #4: Dry Cooler Parasitics

**Current Problem:**

```python
# OLD (implementation_spec.md lines 858)
P_fan = self.config.fan_power_factor * Q_reject  # NOT PHYSICAL
```

**Corrected Approach:**

- Model air-side heat transfer coefficient from Colburn j-factor
- Model air-side pressure drop from friction factor correlation
- Fan power = volumetric flow × pressure rise / efficiencies
- This captures the key physics: at lower approach ΔT, need more airflow, hence more fan power

```python
def solve_dry_cooler(T_CO2_in, P_CO2, m_dot_CO2, Q_reject, T_ambient, geometry):
    """Physical dry cooler model."""

    # Iterate on air flow rate
    m_dot_air = initial_guess

    for _ in range(max_iter):
        # Air outlet temperature from energy balance
        T_air_out = T_ambient + Q_reject / (m_dot_air * cp_air)

        # Segmented HX solve for CO2 outlet and pinch
        result = solve_crossflow_hx(...)
        T_CO2_out = result.T_CO2_out

        # Check approach constraint
        approach = T_CO2_out - T_ambient
        if approach < approach_min:
            m_dot_air *= 1.1  # Need more air
        elif approach > approach_target:
            m_dot_air *= 0.95  # Can reduce air
        else:
            break

    # Air-side pressure drop (Kays & London)
    dP_air = air_side_dP(m_dot_air, geometry, T_ambient, T_air_out)

    # Fan power
    rho_air_avg = 0.5 * (rho_air(T_ambient) + rho_air(T_air_out))
    V_dot_air = m_dot_air / rho_air_avg
    W_fan = V_dot_air * dP_air / (eta_fan * eta_motor)

    return DryCoolerResult(T_CO2_out, W_fan, m_dot_air, dP_air)
```

#### Issue #5: DAC/HTSE Allocations

**Current Problem:**

```python
# OLD (implementation_spec.md lines 1391-1392)
Q_to_DAC = min(Q_waste_total * 0.3, 5e6)  # ARBITRARY
W_to_DAC = 0.5e6  # ARBITRARY
```

**Corrected Approach:**

- Define allocation as an optimization subproblem with explicit objective
- User chooses objective: maximize CO₂ reduction, maximize H₂, maximize MeOH, etc.
- All allocations respect physics constraints (energy balance, process requirements)
- **Clearly label any remaining placeholders** with default values and ranges

```python
def optimize_allocation(W_net, Q_waste, T_waste, process_params, objective='max_CO2_net'):
    """Constrained optimization for process allocation."""

    from scipy.optimize import minimize

    def neg_objective(x):
        W_HTSE, W_DAC, Q_DAC = x
        m_H2 = htse_model(W_HTSE, Q_steam)
        m_CO2 = dac_model(Q_DAC, W_DAC, T_waste)
        m_MeOH = methanol_model(m_H2, m_CO2)

        if objective == 'max_CO2_net':
            return -(m_CO2 - m_CO2_embodied(m_MeOH))  # Negative for minimization
        elif objective == 'max_MeOH':
            return -m_MeOH
        # ... other objectives

    constraints = [
        {'type': 'eq', 'fun': lambda x: W_net - x[0] - x[1] - W_aux},  # Elec balance
        {'type': 'ineq', 'fun': lambda x: x[0]},  # W_HTSE >= 0
        {'type': 'ineq', 'fun': lambda x: x[1]},  # W_DAC >= 0
        {'type': 'ineq', 'fun': lambda x: x[2]},  # Q_DAC >= 0
        {'type': 'ineq', 'fun': lambda x: Q_waste_usable - x[2]},  # Heat available
    ]

    # DAC temp constraint: if T_waste < T_min, force Q_DAC = 0
    if T_waste < T_DAC_min:
        bounds = [(0, W_net), (0, W_net), (0, 0)]  # Q_DAC forced to 0
    else:
        bounds = [(0, W_net), (0, W_net), (0, Q_waste_usable)]

    result = minimize(neg_objective, x0, bounds=bounds, constraints=constraints)
    return AllocationResult(result.x, feasible=result.success)
```

#### Issue #6: Embedded Feasibility Enforcement

**Current Problem:**
Feasibility checks are called after convergence, allowing physically impossible solutions.

**Corrected Approach:**

- All constraints are **part of the solve**, not post-checks
- Use constrained optimizer (SLSQP, trust-constr, or custom Newton with line search)
- If constraint violation detected mid-iteration, backtrack or adjust bounds
- Return structured `InfeasibilityResult` with diagnostic information

```python
@dataclass
class SolveResult:
    converged: bool
    feasible: bool
    state_vector: np.ndarray
    residual_norm: float

    # Feasibility details
    constraints_satisfied: Dict[str, bool]
    constraint_violations: List[ConstraintViolation]

    # Diagnostic outputs (when infeasible)
    pinch_violations: List[PinchViolation]
    supercritical_margin: float
    net_work: float

    def summary(self) -> str:
        """Human-readable summary of solve outcome."""
        ...
```

---

## C) Inputs Required to Run Corrected Simulation

### C.1 Reactor Boundary Conditions

| Parameter                  | Symbol    | Units | Required Input | Default if not provided |
| -------------------------- | --------- | ----- | -------------- | ----------------------- |
| Thermal power              | Q_th      | MW    | **Required**   | 30-36, run both (HTTR)  |
| Helium outlet temperature  | T_He_out  | °C    | **Required**   | 850 (HTTR)              |
| Helium inlet temperature   | T_He_in   | °C    | **Required**   | 395 (HTTR)              |
| Helium pressure            | P_He      | MPa   | **Required**   | 4.0 (HTTR)              |
| Allowable He-side ΔP (IHX) | ΔP_He_max | kPa   | Optional       | 50 kPa                  |
| Multi-core configuration   | n_cores   | -     | Optional       | 1                       |

### C.2 Cycle Design Targets/Constraints

| Parameter                                | Symbol         | Units | Required?       | Default/Range             |
| ---------------------------------------- | -------------- | ----- | --------------- | ------------------------- |
| **Mode**                                 | -              | -     | **Required**    | "design" or "analysis"    |
| Target net electric power                | W_net_target   | MW    | If mode=design  | None                      |
| High pressure                            | P_high         | MPa   | Bounds required | [20, 30] MPa              |
| Low pressure                             | P_low          | MPa   | Bounds required | [7.5, 9.0] MPa            |
| Min compressor inlet margin above T_crit | ΔT_crit_margin | K     | **Required**    | 3 K                       |
| Min compressor inlet margin above P_crit | ΔP_crit_margin | MPa   | **Required**    | 0.3 MPa                   |
| Turbine isentropic efficiency            | η_turb         | -     | Optional        | 0.90 (Dostal)             |
| Main compressor isentropic efficiency    | η_MC           | -     | Optional        | 0.89 (Dostal)             |
| Recompressor isentropic efficiency       | η_RC           | -     | Optional        | 0.89 (Dostal)             |
| Recompression fraction bounds            | f_recomp       | -     | Optional        | [0.25, 0.45]              |
| Maximum TIT                              | T_TIT_max      | °C    | **Required**    | Material limit, e.g., 800 |

### C.3 Heat Exchanger Constraints

| Parameter                    | Component | Units | Required?    | Default              |
| ---------------------------- | --------- | ----- | ------------ | -------------------- |
| Minimum pinch ΔT             | All HX    | K     | **Required** | 10 K                 |
| IHX terminal approach        | IHX       | K     | Optional     | 30-50 K              |
| IHX pressure drop (CO₂ side) | IHX       | kPa   | Optional     | 100 kPa              |
| IHX pressure drop (He side)  | IHX       | kPa   | Optional     | 50 kPa               |
| HTR pressure drop            | HTR       | kPa   | Optional     | 50 kPa (each side)   |
| LTR pressure drop            | LTR       | kPa   | Optional     | 50 kPa (each side)   |
| Number of HX segments        | All       | -     | Optional     | 20                   |
| UA or effectiveness mode     | HX        | -     | Required     | "segmented_enthalpy" |

### C.4 Cooler/Environment Assumptions

| Parameter                      | Symbol          | Units   | Required?       | Default/Range       |
| ------------------------------ | --------------- | ------- | --------------- | ------------------- |
| Design ambient temperature     | T_amb_design    | °C      | **Required**    | 40                  |
| Hot-day ambient                | T_amb_hot       | °C      | For sensitivity | T_amb_design + 10   |
| Cold-day ambient               | T_amb_cold      | °C      | For sensitivity | T_amb_design - 20   |
| Minimum approach ΔT (air side) | ΔT_approach_min | K       | **Required**    | 10 K                |
| Fan efficiency                 | η_fan           | -       | Optional        | 0.70                |
| Motor/VFD efficiency           | η_motor         | -       | Optional        | 0.95                |
| Air-side pressure drop model   | -               | -       | Optional        | "Kays_London"       |
| Cooler geometry (if sizing)    | -               | various | Optional        | Generic finned-tube |

### C.5 Process Block Requirements

#### DAC (Solid Sorbent TVSA)

| Parameter                         | Symbol      | Units        | Required?    | Default/Range |
| --------------------------------- | ----------- | ------------ | ------------ | ------------- |
| Heat intensity                    | q_DAC       | kWh_th/t_CO₂ | **Required** | 1500-2000     |
| Electricity intensity             | e_DAC       | kWh_e/t_CO₂  | **Required** | 200-300       |
| Minimum regen temperature         | T_regen_min | °C           | **Required** | 80-120        |
| Capacity factor                   | CF_DAC      | -            | Optional     | 0.90-0.95     |
| Maximum capacity (if constrained) | Q_DAC_max   | MW_th        | Optional     | Unlimited     |

#### HTSE (SOEC)

| Parameter                    | Symbol   | Units        | Required?        | Default/Range   |
| ---------------------------- | -------- | ------------ | ---------------- | --------------- |
| Electricity intensity        | e_HTSE   | kWh_e/kg_H₂  | **Required**     | 35-40           |
| Heat intensity (steam)       | q_HTSE   | kWh_th/kg_H₂ | **Required**     | 5-8             |
| Steam extraction temperature | T_steam  | °C           | Required if used | Cycle-dependent |
| Operating pressure           | P_H2_out | bar          | Optional         | 20-30           |
| Capacity factor              | CF_HTSE  | -            | Optional         | 0.90-0.95       |

#### Methanol Synthesis

| Parameter                         | Symbol       | Units   | Required? | Default          |
| --------------------------------- | ------------ | ------- | --------- | ---------------- |
| Per-pass conversion               | X_MeOH       | -       | Optional  | 0.25-0.30        |
| Overall conversion (with recycle) | X_overall    | -       | Optional  | 0.95-0.99        |
| Reaction conditions               | T_rxn, P_rxn | °C, bar | Optional  | 250°C, 50-80 bar |

### C.6 Allocation Policy

| Parameter            | Description                                         | Required?    |
| -------------------- | --------------------------------------------------- | ------------ |
| Objective function   | "max_CO2_net", "max_MeOH", "max_H2", "target_power" | **Required** |
| Grid export policy   | Allow export? Maximum export?                       | **Required** |
| Process priority     | If limited power, prioritize HTSE or DAC?           | Optional     |
| Capacity constraints | Max sizes for DAC, HTSE units                       | Optional     |

---

## D) Feasibility Decision Logic

### D.1 Pass/Fail Conditions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FEASIBILITY CRITERIA (all must pass for "FEASIBLE")                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  THERMAL CONSTRAINTS:                                                       │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [T01] T_comp_inlet > T_critical + ΔT_margin                               │
│        → FAIL: "Compressor inlet too close to critical point"              │
│        → Diagnostic: T_actual, T_critical, margin_required                 │
│                                                                             │
│  [T02] P_low > P_critical + ΔP_margin                                      │
│        → FAIL: "Low-side pressure too close to critical point"             │
│        → Diagnostic: P_actual, P_critical, margin_required                 │
│                                                                             │
│  [T03] T_TIT ≤ T_TIT_max                                                   │
│        → FAIL: "Turbine inlet temperature exceeds material limit"          │
│        → Diagnostic: T_actual, T_limit                                     │
│                                                                             │
│  [T04] T_He_return ≥ T_He_in_required (reactor constraint)                 │
│        → FAIL: "Helium return temperature too low for reactor"             │
│        → Diagnostic: T_actual, T_required                                  │
│                                                                             │
│  PINCH CONSTRAINTS:                                                         │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [P01] ΔT_pinch_IHX ≥ ΔT_pinch_min at all segments                        │
│        → FAIL: "IHX pinch violation at segment i"                          │
│        → Diagnostic: segment_index, T_hot, T_cold, ΔT_actual, ΔT_required │
│                                                                             │
│  [P02] ΔT_pinch_HTR ≥ ΔT_pinch_min at all segments                        │
│        → FAIL: "HTR pinch violation at segment i"                          │
│        → Diagnostic: (same as above)                                       │
│                                                                             │
│  [P03] ΔT_pinch_LTR ≥ ΔT_pinch_min at all segments                        │
│        → FAIL: "LTR pinch violation at segment i"                          │
│        → Diagnostic: (same as above)                                       │
│                                                                             │
│  [P04] ΔT_pinch_cooler ≥ ΔT_pinch_min at all segments                     │
│        → FAIL: "Dry cooler pinch violation"                                │
│        → Diagnostic: T_CO2, T_air, ΔT_actual                               │
│                                                                             │
│  ENERGY/WORK CONSTRAINTS:                                                   │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [E01] W_turbine > W_comp_main + W_comp_recomp                             │
│        → FAIL: "Negative gross cycle work"                                 │
│        → Diagnostic: W_turb, W_MC, W_RC, W_net                             │
│                                                                             │
│  [E02] W_net > W_parasitic                                                 │
│        → FAIL: "Parasitic loads exceed net power"                          │
│        → Diagnostic: W_net, W_fan, W_aux                                   │
│                                                                             │
│  [E03] |Energy_balance_residual| / Q_reactor < 0.001                       │
│        → FAIL: "Energy balance not closed (>0.1%)"                         │
│        → Diagnostic: Q_in, W_out, Q_reject, residual                       │
│                                                                             │
│  PROCESS CONSTRAINTS:                                                       │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [D01] If Q_to_DAC > 0: T_waste_heat ≥ T_DAC_regen_min                     │
│        → FAIL: "Waste heat temperature insufficient for DAC"               │
│        → Diagnostic: T_waste, T_required                                   │
│                                                                             │
│  [D02] Allocation: W_HTSE + W_DAC + W_aux ≤ W_net                          │
│        → FAIL: "Electricity allocation exceeds available"                  │
│        → Diagnostic: W_available, W_requested                              │
│                                                                             │
│  [D03] Allocation: Q_to_DAC ≤ Q_waste_usable                               │
│        → FAIL: "Heat allocation exceeds available waste heat"              │
│        → Diagnostic: Q_available, Q_requested                              │
│                                                                             │
│  CONVERGENCE:                                                               │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [C01] Solver converged within max_iterations                              │
│        → FAIL: "Solver did not converge"                                   │
│        → Diagnostic: iteration_count, residual_norm, last_state            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### D.2 Diagnostic Output Structure

```python
@dataclass
class FeasibilityReport:
    """Comprehensive feasibility assessment."""

    # Overall status
    feasible: bool
    converged: bool

    # Constraint status (dict of constraint_id -> bool)
    constraints: Dict[str, ConstraintStatus]

    # Violations (only populated if infeasible)
    violations: List[ConstraintViolation]

    # Margins (how close to limits, even if feasible)
    margins: Dict[str, float]  # e.g., {'T_crit_margin': 3.2, 'pinch_margin_min': 12.5}

    # Solver diagnostics
    iterations: int
    residual_norm: float
    solve_time_seconds: float

    def primary_failure(self) -> Optional[ConstraintViolation]:
        """Return the most binding violated constraint."""
        if self.feasible:
            return None
        return min(self.violations, key=lambda v: v.margin)

    def format_report(self) -> str:
        """Human-readable diagnostic report."""
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
                lines.append(f"      Actual: {v.actual_value:.3f}, "
                           f"Required: {v.required_value:.3f}, "
                           f"Margin: {v.margin:.3f}")
                if v.location:
                    lines.append(f"      Location: {v.location}")

        lines.append("")
        lines.append("MARGINS (distance to constraint boundary):")
        for name, margin in sorted(self.margins.items()):
            status = "OK" if margin > 0 else "VIOLATED"
            lines.append(f"  {name}: {margin:.2f} [{status}]")

        return "\n".join(lines)


@dataclass
class ConstraintViolation:
    """Single constraint violation."""
    constraint_id: str  # e.g., "P02"
    description: str    # e.g., "HTR pinch violation at segment 7"
    actual_value: float
    required_value: float
    margin: float       # actual - required (negative if violated)
    location: Optional[str] = None  # e.g., "HTR segment 7"
    suggestion: Optional[str] = None  # e.g., "Increase P_low or decrease recomp fraction"
```

### D.3 Example Diagnostic Outputs

**Case 1: Pinch Violation**

```
============================================================
FEASIBILITY REPORT
============================================================
Status: INFEASIBLE
Converged: True
Iterations: 23
Residual norm: 1.24e-08

VIOLATIONS:
  [P02] HTR pinch violation at segment 7
      Actual: 4.2 K, Required: 10.0 K, Margin: -5.8 K
      Location: HTR segment 7 (Q_frac = 0.35)

MARGINS (distance to constraint boundary):
  T_crit_margin: 5.20 [OK]
  P_crit_margin: 0.32 [OK]
  pinch_IHX_min: 28.30 [OK]
  pinch_HTR_min: -5.80 [VIOLATED]
  pinch_LTR_min: 14.50 [OK]
  W_net_margin: 2.45 MW [OK]
```

**Case 2: Supercritical Margin**

```
============================================================
FEASIBILITY REPORT
============================================================
Status: INFEASIBLE
Converged: True
Iterations: 31
Residual norm: 8.71e-07

VIOLATIONS:
  [T01] Compressor inlet too close to critical point
      Actual: 32.5°C (305.65 K), Required: ≥33.98°C (307.13 K), Margin: -1.48 K
      Location: State 1 (main compressor inlet)
      Suggestion: Increase P_low (raises T_crit margin) or lower T_ambient

MARGINS (distance to constraint boundary):
  T_crit_margin: -1.48 [VIOLATED]
  P_crit_margin: 0.35 [OK]
  ...
```

---

## E) Summary: Issue Resolution Matrix

| Issue                    | Root Cause in Old Spec                      | Correction                          |
| ------------------------ | ------------------------------------------- | ----------------------------------- |
| #1 Recuperators          | Temperature-based effectiveness + guessed T | Segmented enthalpy-based solver     |
| #2 Pressure drops        | `# Simplified: no pressure drop`            | Friction correlations per component |
| #3 IHX-cycle decoupled   | Sequential: `T_TIT = T_He - ΔT` then verify | Simultaneous residual solve         |
| #4 Cooler parasitics     | `P_fan = factor * Q`                        | Physical UA/NTU + fan law model     |
| #5 Heuristic allocations | `min(Q*0.3, 5e6)`                           | Constrained optimization subproblem |
| #6 Bolted-on feasibility | Post-hoc checks                             | Constraints embedded in solver      |

---

## F) Next Steps

Once the team provides the inputs listed in Section C, the corrected solver will:

1. Accept clean input specifications
2. Solve the coupled system with all constraints enforced
3. Return either a converged feasible solution OR a detailed diagnostic report
4. Never produce a "converged but physically impossible" result

**Action required from team:** Provide values or ranges for the required inputs in Section C before implementation proceeds.
