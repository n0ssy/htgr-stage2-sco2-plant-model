"""
Physical dry cooler model.
Calculates fan power from airflow and pressure drop - NOT from a constant factor.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from properties.fluids import co2, air
from hx.segmented_hx import SolverStatus


@dataclass
class DryCoolerGeometry:
    """Dry cooler heat exchanger geometry."""

    tube_OD: float = 0.0254
    tube_ID: float = 0.0229
    tube_length: float = 6.0
    n_tubes: int = 200
    n_rows: int = 4
    tube_pitch_transverse: float = 0.0508
    tube_pitch_longitudinal: float = 0.044

    fin_pitch: float = 0.003
    fin_thickness: float = 0.0003
    fin_height: float = 0.012

    face_width: float = 8.0
    face_height: float = 3.0

    @property
    def face_area(self) -> float:
        return self.face_width * self.face_height

    @property
    def A_flow_CO2(self) -> float:
        return self.n_tubes * np.pi * (self.tube_ID / 2) ** 2

    @property
    def min_free_flow_area_air(self) -> float:
        sigma = 0.5
        return sigma * self.face_area


@dataclass
class DryCoolerConfig:
    """Dry cooler configuration."""

    eta_fan: float = 0.70
    eta_motor: float = 0.95

    dT_approach_min: float = 10.0
    dT_pinch_min: float = 5.0

    n_segments: int = 10

    dP_CO2: float = 30e3

    q_closure_tolerance: float = 0.02
    max_iterations: int = 100

    geometry: DryCoolerGeometry = None

    def __post_init__(self):
        if self.geometry is None:
            self.geometry = DryCoolerGeometry()


@dataclass
class DryCoolerResult:
    """Result from dry cooler solve."""

    converged: bool
    feasible: bool

    T_CO2_in: float
    T_CO2_out: float
    P_CO2_in: float
    P_CO2_out: float
    h_CO2_in: float
    h_CO2_out: float
    m_dot_CO2: float

    T_air_in: float
    T_air_out: float
    m_dot_air: float
    V_dot_air: float

    Q_reject: float
    Q_model: float
    Q_error_rel: float

    dP_air: float
    W_fan: float

    dT_approach: float
    approach_margin: float
    dT_pinch_min: float
    pinch_profile_min_segment: int

    iterations: int = 0
    solver_status: str = SolverStatus.CONVERGED.value
    error_message: Optional[str] = None


def air_side_friction_factor(Re: float, geometry: DryCoolerGeometry) -> float:
    """Air-side friction factor for finned tube bank."""
    if Re < 1000:
        return 0.5 * Re ** (-0.5)
    return 0.1175 * Re ** (-0.25)


def air_side_pressure_drop(
    m_dot_air: float,
    T_air_in: float,
    T_air_out: float,
    geometry: DryCoolerGeometry,
    P_atm: float = 101325.0,
) -> float:
    """Calculate air-side pressure drop through finned tube bank."""
    if m_dot_air <= 0:
        return 0.0

    T_avg = 0.5 * (T_air_in + T_air_out)
    rho_in = air.rho(T_air_in, P_atm)
    rho_out = air.rho(T_air_out, P_atm)
    rho_avg = 0.5 * (rho_in + rho_out)
    mu_avg = air.mu(T_avg, P_atm)

    A_c = geometry.min_free_flow_area_air
    G = m_dot_air / A_c
    Re = max(G * geometry.tube_OD / mu_avg, 1.0)

    f = air_side_friction_factor(Re, geometry)

    A_tube = geometry.n_tubes * np.pi * geometry.tube_OD * geometry.tube_length
    fin_area_ratio = 10.0
    A_total = A_tube * (1 + fin_area_ratio)

    sigma = A_c / geometry.face_area
    Kc = 0.4 * (1 - sigma ** 2)
    Ke = (1 - sigma ** 2) - 0.3 * (1 - sigma)

    dP_core = (G ** 2 / (2 * rho_in)) * (
        (1 + sigma ** 2) * (rho_in / rho_out - 1)
        + f * (A_total / A_c) * (rho_in / rho_avg)
        + Kc
        - Ke * (rho_in / rho_out)
    )

    return max(float(dP_core), 50.0)


def calculate_UA(
    m_dot_air: float,
    m_dot_CO2: float,
    T_air_in: float,
    T_CO2_in: float,
    P_CO2: float,
    geometry: DryCoolerGeometry,
) -> float:
    """Calculate overall heat-transfer UA [W/K]."""
    if m_dot_air <= 0 or m_dot_CO2 <= 0:
        return 0.0

    T_air_avg = T_air_in + 20.0
    cp_air = air.cp(T_air_avg)
    mu_air = air.mu(T_air_avg)
    k_air = air.k_thermal(T_air_avg)
    Pr_air = cp_air * mu_air / k_air

    A_c = geometry.min_free_flow_area_air
    G_air = m_dot_air / A_c
    Re_air = max(G_air * geometry.tube_OD / mu_air, 1.0)
    j = 0.14 * Re_air ** (-0.4)
    h_air = j * G_air * cp_air * Pr_air ** (-2 / 3)

    A_flow_CO2 = geometry.A_flow_CO2
    rho_CO2 = co2.rho(T_CO2_in, P_CO2)
    mu_CO2 = co2.mu(T_CO2_in, P_CO2)
    cp_CO2 = co2.cp(T_CO2_in, P_CO2)
    k_CO2 = co2.k_thermal(T_CO2_in, P_CO2)
    Pr_CO2 = cp_CO2 * mu_CO2 / k_CO2

    D_i = geometry.tube_ID
    G_CO2 = m_dot_CO2 / A_flow_CO2
    Re_CO2 = max(rho_CO2 * (G_CO2 / rho_CO2) * D_i / mu_CO2, 1.0)
    if Re_CO2 > 2300:
        Nu_CO2 = 0.023 * Re_CO2 ** 0.8 * Pr_CO2 ** 0.3
    else:
        Nu_CO2 = 3.66
    h_CO2 = Nu_CO2 * k_CO2 / D_i

    A_i = geometry.n_tubes * np.pi * geometry.tube_ID * geometry.tube_length
    A_tube_outer = geometry.n_tubes * np.pi * geometry.tube_OD * geometry.tube_length
    A_fin = A_tube_outer * 10
    A_o = A_tube_outer + A_fin

    eta_fin = 0.85
    eta_o = 1 - (A_fin / A_o) * (1 - eta_fin)
    UA = 1.0 / (1 / (h_CO2 * A_i) + 1 / (eta_o * h_air * A_o))

    return float(max(UA, 0.0))


class DryCooler:
    """Physical dry cooler model with explicit closure diagnostics."""

    def __init__(self, config: Optional[DryCoolerConfig] = None):
        self.config = config or DryCoolerConfig()

    def _pinch_profile(
        self,
        T_CO2_in: float,
        T_CO2_out: float,
        T_air_in: float,
        T_air_out: float,
    ) -> Tuple[float, int]:
        n = max(self.config.n_segments, 2)
        dT_min = float("inf")
        seg_min = 0
        for i in range(n + 1):
            frac = i / n
            T_co2 = T_CO2_in + frac * (T_CO2_out - T_CO2_in)
            T_air_local = T_air_out + frac * (T_air_in - T_air_out)
            dT_local = T_co2 - T_air_local
            if dT_local < dT_min:
                dT_min = dT_local
                seg_min = i
        return dT_min, seg_min

    def _error_result(
        self,
        msg: str,
        T_CO2_in: float,
        P_CO2_in: float,
        m_dot_CO2: float,
        Q_reject: float,
        T_ambient: float,
    ) -> DryCoolerResult:
        return DryCoolerResult(
            converged=False,
            feasible=False,
            T_CO2_in=T_CO2_in,
            T_CO2_out=T_CO2_in,
            P_CO2_in=P_CO2_in,
            P_CO2_out=P_CO2_in,
            h_CO2_in=0.0,
            h_CO2_out=0.0,
            m_dot_CO2=m_dot_CO2,
            T_air_in=T_ambient,
            T_air_out=T_ambient,
            m_dot_air=0.0,
            V_dot_air=0.0,
            Q_reject=Q_reject,
            Q_model=0.0,
            Q_error_rel=1.0,
            dP_air=0.0,
            W_fan=0.0,
            dT_approach=0.0,
            approach_margin=-self.config.dT_approach_min,
            dT_pinch_min=0.0,
            pinch_profile_min_segment=0,
            iterations=0,
            solver_status=SolverStatus.NUMERICAL_FAIL.value,
            error_message=msg,
        )

    def solve(
        self,
        T_CO2_in: float,
        P_CO2_in: float,
        m_dot_CO2: float,
        Q_reject: float,
        T_ambient: float,
    ) -> DryCoolerResult:
        """Solve dry cooler for the given heat-rejection duty."""
        config = self.config
        geometry = config.geometry

        if m_dot_CO2 <= 0:
            return self._error_result(
                "m_dot_CO2 must be positive",
                T_CO2_in,
                P_CO2_in,
                m_dot_CO2,
                Q_reject,
                T_ambient,
            )

        if Q_reject < 0:
            return self._error_result(
                "Q_reject must be non-negative",
                T_CO2_in,
                P_CO2_in,
                m_dot_CO2,
                Q_reject,
                T_ambient,
            )

        if Q_reject == 0:
            try:
                h_in = co2.h(T_CO2_in, P_CO2_in)
            except Exception:
                h_in = 0.0
            return DryCoolerResult(
                converged=True,
                feasible=True,
                T_CO2_in=T_CO2_in,
                T_CO2_out=T_CO2_in,
                P_CO2_in=P_CO2_in,
                P_CO2_out=P_CO2_in - config.dP_CO2,
                h_CO2_in=h_in,
                h_CO2_out=h_in,
                m_dot_CO2=m_dot_CO2,
                T_air_in=T_ambient,
                T_air_out=T_ambient,
                m_dot_air=0.0,
                V_dot_air=0.0,
                Q_reject=0.0,
                Q_model=0.0,
                Q_error_rel=0.0,
                dP_air=0.0,
                W_fan=0.0,
                dT_approach=T_CO2_in - T_ambient,
                approach_margin=(T_CO2_in - T_ambient) - config.dT_approach_min,
                dT_pinch_min=T_CO2_in - T_ambient,
                pinch_profile_min_segment=0,
                iterations=1,
                solver_status=SolverStatus.CONVERGED.value,
            )

        try:
            h_CO2_in = co2.h(T_CO2_in, P_CO2_in)
            P_CO2_out = P_CO2_in - config.dP_CO2
        except Exception as exc:
            return self._error_result(
                f"CO2 property error: {exc}",
                T_CO2_in,
                P_CO2_in,
                m_dot_CO2,
                Q_reject,
                T_ambient,
            )

        cp_air = air.cp(T_ambient + 10.0)
        m_dot_air = max(Q_reject / (cp_air * 15.0), 10.0)

        converged = False
        capacity_limited = False
        Q_model = 0.0
        Q_error_rel = 1.0
        T_air_out = T_ambient
        h_CO2_out = h_CO2_in
        T_CO2_out = T_CO2_in

        for iteration in range(config.max_iterations):
            try:
                UA = calculate_UA(
                    m_dot_air,
                    m_dot_CO2,
                    T_ambient,
                    T_CO2_in,
                    P_CO2_in,
                    geometry,
                )
                C_air = m_dot_air * cp_air
                C_CO2 = m_dot_CO2 * co2.cp(0.5 * (T_CO2_in + T_CO2_out), P_CO2_in)
            except Exception as exc:
                return self._error_result(
                    f"Cooler closure property error: {exc}",
                    T_CO2_in,
                    P_CO2_in,
                    m_dot_CO2,
                    Q_reject,
                    T_ambient,
                )

            C_min = max(min(C_air, C_CO2), 1.0)
            C_max = max(C_air, C_CO2)
            C_r = C_min / max(C_max, 1.0)
            NTU = UA / C_min

            if NTU > 0 and C_r > 0:
                try:
                    epsilon = 1 - np.exp((NTU ** 0.22 / C_r) * (np.exp(-C_r * NTU ** 0.78) - 1))
                except Exception:
                    epsilon = 0.0
            else:
                epsilon = 0.0
            epsilon = float(np.clip(epsilon, 0.0, 1.0))

            Q_max = C_min * max(T_CO2_in - T_ambient, 0.0)
            Q_model = float(np.clip(epsilon * Q_max, 0.0, Q_max))

            try:
                h_CO2_out = h_CO2_in - Q_model / m_dot_CO2
                T_CO2_out = co2.T_from_Ph(P_CO2_out, h_CO2_out)
            except Exception as exc:
                return self._error_result(
                    f"CO2 outlet property error: {exc}",
                    T_CO2_in,
                    P_CO2_in,
                    m_dot_CO2,
                    Q_reject,
                    T_ambient,
                )

            T_air_out = T_ambient + Q_model / max(m_dot_air * cp_air, 1.0)
            T_air_avg = 0.5 * (T_ambient + T_air_out)
            cp_air = air.cp(T_air_avg)
            T_air_out = T_ambient + Q_model / max(m_dot_air * cp_air, 1.0)

            Q_error_rel = abs(Q_model - Q_reject) / max(Q_reject, 1.0)

            if Q_error_rel <= config.q_closure_tolerance:
                converged = True
                break

            if Q_model <= 0:
                m_dot_air *= 1.3
            else:
                factor = (Q_reject / Q_model) ** 0.6
                factor = float(np.clip(factor, 0.7, 1.4))
                m_dot_air_next = m_dot_air * factor
                if m_dot_air_next >= 10000.0 and Q_model < Q_reject:
                    capacity_limited = True
                    m_dot_air = 10000.0
                    break
                m_dot_air = m_dot_air_next
            m_dot_air = float(np.clip(m_dot_air, 10.0, 10000.0))

        dT_approach = T_CO2_out - T_ambient
        approach_margin = dT_approach - config.dT_approach_min

        dP_air = air_side_pressure_drop(m_dot_air, T_ambient, T_air_out, geometry)
        rho_air_avg = air.rho(0.5 * (T_ambient + T_air_out))
        V_dot_air = m_dot_air / rho_air_avg
        W_fan = (V_dot_air * dP_air) / (config.eta_fan * config.eta_motor)

        dT_pinch_min, pinch_segment = self._pinch_profile(
            T_CO2_in,
            T_CO2_out,
            T_ambient,
            T_air_out,
        )

        feasible = (
            converged
            and Q_error_rel <= config.q_closure_tolerance
            and dT_pinch_min >= config.dT_pinch_min
            and approach_margin >= 0
        )

        if feasible:
            status = SolverStatus.CONVERGED.value
            msg = None
        elif converged:
            status = SolverStatus.INFEASIBLE.value
            msg = (
                f"Thermal closure converged but constraints failed: "
                f"approach_margin={approach_margin:.2f}K, "
                f"pinch={dT_pinch_min:.2f}K"
            )
        else:
            status = SolverStatus.INFEASIBLE.value
            limiter = "capacity-limited" if capacity_limited else "closure-unmet"
            msg = (
                f"Cooler {limiter}: Q_model={Q_model/1e6:.2f} MW, "
                f"Q_target={Q_reject/1e6:.2f} MW, "
                f"Q_error_rel={Q_error_rel:.3f}"
            )

        return DryCoolerResult(
            converged=converged,
            feasible=feasible,
            T_CO2_in=T_CO2_in,
            T_CO2_out=T_CO2_out,
            P_CO2_in=P_CO2_in,
            P_CO2_out=P_CO2_out,
            h_CO2_in=h_CO2_in,
            h_CO2_out=h_CO2_out,
            m_dot_CO2=m_dot_CO2,
            T_air_in=T_ambient,
            T_air_out=T_air_out,
            m_dot_air=m_dot_air,
            V_dot_air=V_dot_air,
            Q_reject=Q_reject,
            Q_model=Q_model,
            Q_error_rel=Q_error_rel,
            dP_air=dP_air,
            W_fan=W_fan,
            dT_approach=dT_approach,
            approach_margin=approach_margin,
            dT_pinch_min=dT_pinch_min,
            pinch_profile_min_segment=pinch_segment,
            iterations=iteration + 1,
            solver_status=status,
            error_message=msg,
        )

    def solve_for_T1(
        self,
        T_CO2_in: float,
        P_CO2_in: float,
        m_dot_CO2: float,
        T_1_target: float,
        T_ambient: float,
    ) -> DryCoolerResult:
        """Solve dry cooler to achieve target compressor inlet temperature."""
        try:
            h_CO2_in = co2.h(T_CO2_in, P_CO2_in)
            P_CO2_out = P_CO2_in - self.config.dP_CO2
            h_CO2_out = co2.h(T_1_target, P_CO2_out)
        except Exception:
            return self._error_result(
                "Failed to evaluate target-T1 heat rejection",
                T_CO2_in,
                P_CO2_in,
                m_dot_CO2,
                0.0,
                T_ambient,
            )

        Q_reject = m_dot_CO2 * (h_CO2_in - h_CO2_out)
        if Q_reject < 0:
            return self._error_result(
                "Negative heat rejection - T_CO2_in <= T_1_target",
                T_CO2_in,
                P_CO2_in,
                m_dot_CO2,
                Q_reject,
                T_ambient,
            )

        return self.solve(T_CO2_in, P_CO2_in, m_dot_CO2, Q_reject, T_ambient)
