# sCO2 Plant Simulation Project - Comprehensive Summary

**Purpose**: Reference document for CV/resume bullet point generation. Contains full technical context for SWE/Quant/Fintech applications.

---

## CURRENT CV ENTRY (Copy-Paste Ready)

**Nuclear Power Cycle Simulation Engine** | *Rolls Royce Fission Energy Competition* | Oct. 2025 – Present
- Built 4,000-line Python solver for coupled nonlinear thermodynamic systems using nested fixed-point iteration
- Implemented enthalpy-based segmented heat exchanger models handling real-gas CO2 near critical point
- Designed constrained optimization for multi-process energy allocation (DAC, electrolysis, methanol synthesis)
- Validated cycle efficiency within 1% of MIT benchmark; embedded feasibility constraints in solver loop

**Replaces**: Connected Bioreactor Control System

---

## 1. Project Context

### Competition
- **Name**: Rolls Royce Novel Fission and CO2 Reduction Project 2025-2026
- **Organizers**: Rolls Royce, UCL Energy Society, Cambridge, Imperial, Oxford
- **Timeline**: Oct 2025 - Mar 2026 (Phase 1 presentation Jan 2026, Finals Mar 2026)
- **Team Size**: Multi-university team competition

### Problem Statement
Design a complete plant system combining:
1. **High-Temperature Gas Reactor (HTGR)** - based on Japan's HTTR (30-36 MW thermal)
2. **Supercritical CO2 (sCO2) Recompression Brayton Cycle** - power extraction
3. **Water-Independent Heat Rejection** - dry air cooler (no cooling towers)
4. **CO2 Reduction Processes** - DAC, hydrogen production, methanol synthesis

**Primary Figure of Merit**: Net CO2 reduction (tonnes/year)

### Key Requirements from Rolls Royce
- Develop computational model of whole plant
- Verify and validate against published literature
- Document all assumptions clearly
- Code quality compliance (PEP8)
- Demonstrate modeling fidelity justification

---

## 2. What Was Built

### Scale
- **~4,000 lines of Python** across 18 source files
- **7 logical packages**: properties, components, hx, cycle, process, validation
- **Production-grade simulation engine** with full test suite

### Architecture Overview
```
sco2_plant/
├── properties/fluids.py       # CoolProp wrapper (CO2, Helium, Air)
├── components/
│   ├── turbomachinery.py      # Turbine, compressors (isentropic models)
│   ├── ihx.py                 # Intermediate Heat Exchanger (He→CO2)
│   ├── recuperators.py        # HTR & LTR recuperators
│   └── dry_cooler.py          # Physical fan power model
├── hx/segmented_hx.py         # Core segmented counterflow HX solver
├── cycle/
│   ├── sco2_cycle.py          # sCO2 recompression cycle
│   └── coupled_solver.py      # Full plant solver
├── process/allocation.py      # Constrained optimization
└── validation/dostal_validation.py  # MIT benchmark
```

---

## 3. Technical Achievements (Key Selling Points)

### 3.1 Nested Fixed-Point Iteration Solver
**What**: Solved tightly-coupled nonlinear system with 7 primary unknowns and ~200-400 total equations per solve.

**How**:
```
Outer Loop (Level 1): Iterate on (T_5, T_1, P_low, f_recomp)
├── Middle Loop (Level 2): IHX + Cycle coupled solve
│   ├── Inner Loop (Level 3): Segmented HX solves (HTR, LTR, IHX, Cooler)
│   │   └── Newton-Raphson per segment
│   └── Check feasibility constraints
└── Update estimates via relaxation
```

**Why it matters for Quant/SWE**: Demonstrates ability to design and implement sophisticated numerical algorithms for systems with circular dependencies. Similar to pricing engines, risk models, or any coupled simulation.

**Convergence criteria**: |ΔT| < 0.1 K, energy closure < 0.1%

### 3.2 Enthalpy-Based Segmented Heat Exchanger Models
**Problem solved**: Near CO2 critical point (31.1°C, 7.38 MPa), specific heat varies by 400%+. Traditional constant-cp models fail catastrophically.

**Solution**:
- Discretize each heat exchanger into 10-20 segments
- Evaluate real-gas properties (CoolProp) at each segment
- Energy balance per segment: `Q_seg = m_dot × Δh` (not `m_dot × cp × ΔT`)
- Binary search algorithm to find maximum heat duty respecting pinch constraints

**Algorithm complexity**: O(N_segments × log(Q_range) × property_evaluations)

**Why it matters**: Shows understanding of when simplified models break down and how to implement physically rigorous alternatives. Critical thinking about model fidelity.

### 3.3 Constrained Optimization for Process Allocation
**Problem**: Given available electricity (W_net) and waste heat (Q_waste), optimally allocate to:
- Direct Air Capture (DAC) - captures CO2
- High-Temperature Steam Electrolysis (HTSE) - produces H2
- Methanol synthesis - converts H2 + CO2 → fuel

**Implementation**:
```python
scipy.optimize.minimize(
    objective = -net_CO2_reduction,
    constraints = [
        electricity_balance,
        heat_balance,
        temperature_grade_requirements,
        non_negativity
    ],
    bounds = [(0, W_net), (0, Q_waste), ...]
)
```

**Result**: 45,182 tonnes CO2/year reduction at baseline conditions

**Why it matters for Quant**: Direct demonstration of constrained optimization - same mathematical framework as portfolio optimization, resource allocation, or trading strategy optimization.

### 3.4 Physical Dry Cooler Model (Not Constant Factor)
**Common approach** (that we rejected):
```python
W_fan = 0.05 * Q_reject  # Arbitrary constant factor
```

**Our approach**:
1. Model air-side heat transfer from Colburn j-factor correlation
2. Model air-side pressure drop from Kays & London friction factor
3. Calculate fan power physically: `W_fan = (V_dot × ΔP) / (η_fan × η_motor)`

**Why it matters**: Shows engineering rigor - understanding that fan power scales with airflow cubed, not linearly with heat rejection. Captures second-order effects.

### 3.5 Embedded Feasibility Constraints
**Key insight**: Constraints must be **active during solve**, not checked afterward.

**Constraints enforced**:
| Constraint | Description |
|-----------|-------------|
| Supercritical margin | T_1 > T_crit + 3K, P_low > P_crit + 0.3 MPa |
| Pinch (all HX) | ΔT ≥ 10 K at every segment |
| Temperature limits | T_5 ≤ 800°C (material) |
| Energy closure | |Q_in - W_out - Q_reject| < 0.1% |
| Positive net work | W_turbine > W_compressors |

**Why it matters**: Solver cannot converge to physically impossible solutions. Demonstrates understanding of constrained numerical methods.

### 3.6 Validation Against MIT Benchmark
**Reference**: Dostal 2004 (MIT PhD thesis) - canonical sCO2 cycle reference

**Validation case**:
- Operating point: T_1=32°C, T_5=550°C, P_high=20 MPa, P_low=7.7 MPa
- Expected efficiency: ~45%
- **Achieved**: 44.74% (within 1%)

**Why it matters**: Verification against published literature is standard practice. Shows ability to validate computational models.

---

## 4. Technical Skills Demonstrated

### Numerical Methods
- Fixed-point iteration with relaxation
- Newton-Raphson (per-segment)
- Binary search for constrained optimization
- Convergence criteria design
- Handling of stiff/ill-conditioned systems

### Scientific Computing
- Real-gas thermodynamic property evaluation (CoolProp)
- Enthalpy-based energy balances
- Phase boundary handling (supercritical CO2)
- Multi-physics coupling (thermal, fluid, mechanical)

### Software Engineering
- Modular architecture (7 packages, clear interfaces)
- Dataclass-heavy design for type safety
- Callback-based solver design (property functions as parameters)
- Comprehensive test suite
- Configuration management (YAML)
- Diagnostic output generation

### Optimization
- Constrained nonlinear optimization (scipy.optimize)
- Objective function design
- Constraint formulation (equality and inequality)
- Bounds handling

---

## 5. Quantitative Results

| Metric | Value |
|--------|-------|
| Codebase size | ~4,000 lines Python |
| Source files | 18 |
| Primary unknowns | 7 |
| Total equations per solve | 200-400 |
| Typical iterations to converge | 15-30 |
| CoolProp function calls per solve | 5,000-10,000 |
| Validation error vs benchmark | <1% |
| Net CO2 reduction (baseline) | 45,182 tonnes/year |
| Cycle thermal efficiency | 44.74% |

---

## 6. Transferable Skills for Target Roles

### For Software Engineering
- Large codebase design and implementation
- Numerical algorithm implementation
- Test-driven development
- Performance optimization (minimizing property evaluations)
- Clean architecture with separation of concerns

### For Quantitative Finance
- Constrained optimization (portfolio optimization analogy)
- Numerical methods for nonlinear systems
- Monte Carlo-style iteration until convergence
- Model validation against benchmarks
- Handling of edge cases and constraints

### For Fintech
- Complex system modeling
- Real-time constraint checking
- Optimization under constraints
- Production-grade code quality
- Clear documentation and assumptions tracking

---

## 7. Key Differentiators

1. **Not a toy project**: 4,000 LOC, production-grade architecture
2. **Industry sponsorship**: Rolls Royce competition, real engineering requirements
3. **Validation**: Against published MIT benchmark, not just "it runs"
4. **Sophisticated numerics**: Nested iteration, not just calling a library
5. **Physical rigor**: Enthalpy-based, not simplified constant-property models
6. **Constrained optimization**: Embedded in solver, not post-hoc checks

---

## 8. Suggested CV Bullet Points

### For SWE Roles (emphasize architecture, scale)
- Built 4,000-line Python solver for coupled nonlinear thermodynamic systems using nested fixed-point iteration
- Designed modular simulation architecture with 7 packages handling real-gas properties via CoolProp
- Implemented enthalpy-based segmented heat exchanger models with O(N log Q) binary search convergence
- Validated against MIT benchmark within 1% error; generated automated diagnostic reports

### For Quant Roles (emphasize numerical methods, optimization)
- Implemented nested fixed-point solver for 7-variable coupled system with 200+ constraint equations
- Designed constrained optimization for multi-process energy allocation using scipy.optimize
- Built binary search algorithm for heat exchanger sizing under pinch temperature constraints
- Achieved 44.74% cycle efficiency vs 45% benchmark; embedded feasibility constraints in solver loop

### For Fintech Roles (emphasize constraints, validation)
- Built simulation engine solving coupled nonlinear systems with embedded feasibility constraints
- Implemented constrained optimization allocating resources across competing processes
- Validated computational model against MIT benchmark (error <1%); designed diagnostic output system
- Architected 4,000-line Python codebase with clear separation of concerns and test coverage

---

## 9. One-Line Summary
Built a production-grade numerical simulation engine (4,000 LOC Python) for coupled thermodynamic systems, featuring nested fixed-point iteration, enthalpy-based heat exchanger models, constrained optimization, and validation against MIT benchmarks.

---

## 10. If Asked "Tell Me About This Project"

**30-second version**:
"For a Rolls Royce engineering competition, I built a simulation engine for a nuclear power plant coupled with CO2 capture processes. The core challenge was solving a tightly-coupled nonlinear system where heat exchangers, turbines, and compressors all depend on each other. I used a nested fixed-point iteration approach with enthalpy-based heat exchanger models to handle real-gas CO2 properties near the critical point. The solver enforces physical constraints during iteration, not after, so it can't converge to impossible solutions. I validated against an MIT benchmark and achieved less than 1% error."

**Technical follow-up points**:
- "Why not just use effectiveness-NTU?" → cp varies 400% near critical point; constant-property models fail
- "How did you handle convergence?" → Nested iteration with relaxation; outer loop on temperatures, inner loop on HX segments
- "What's the optimization?" → Constrained allocation of electricity/heat to DAC, electrolysis, and methanol synthesis to maximize net CO2 reduction
