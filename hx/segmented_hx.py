"""
Segmented counterflow heat exchanger solver.
Uses enthalpy-based energy balances with per-segment pinch checks.
"""

from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple
import numpy as np
from enum import Enum


class InfeasibilityType(Enum):
    PINCH_VIOLATION = "pinch_violation"
    CONVERGENCE_FAILURE = "convergence_failure"
    PROPERTY_ERROR = "property_error"
    NEGATIVE_DUTY = "negative_duty"


class SolverStatus(Enum):
    CONVERGED = "CONVERGED"
    INFEASIBLE = "INFEASIBLE"
    NUMERICAL_FAIL = "NUMERICAL_FAIL"


@dataclass
class SegmentData:
    """Data for a single HX segment."""

    index: int
    Q: float  # Heat duty [W]
    T_hot: float  # Hot side temperature [K]
    T_cold: float  # Cold side temperature [K]
    h_hot: float  # Hot side enthalpy [J/kg]
    h_cold: float  # Cold side enthalpy [J/kg]
    P_hot: float  # Hot side pressure [Pa]
    P_cold: float  # Cold side pressure [Pa]
    dT_pinch: float  # Local temperature difference [K]


@dataclass
class HXResult:
    """Result from segmented HX solve."""

    converged: bool
    feasible: bool
    T_hot_out: float
    T_cold_out: float
    h_hot_out: float
    h_cold_out: float
    P_hot_out: float
    P_cold_out: float
    Q_total: float
    dT_pinch_min: float
    pinch_segment: int
    dP_hot: float
    dP_cold: float
    segments: List[SegmentData]
    iterations: int = 0
    error_message: Optional[str] = None
    infeasibility_type: Optional[InfeasibilityType] = None
    solver_status: str = SolverStatus.CONVERGED.value
    closure_error_rel: float = 0.0
    assumption_mode: str = "constant_dP"
    Q_target: float = 0.0
    Q_model: float = 0.0


@dataclass
class PinchViolation:
    """Details of a pinch point violation."""

    segment: int
    dT_actual: float
    dT_required: float
    T_hot: float
    T_cold: float
    Q_fraction: float


def pressure_drop_pche(
    m_dot: float,
    rho: float,
    mu: float,
    D_h: float,
    L: float,
    A_flow: float,
    roughness: float = 1e-6,
) -> float:
    """Pressure drop for printed-circuit heat exchanger channel."""
    if m_dot <= 0 or A_flow <= 0 or D_h <= 0 or L <= 0:
        return 0.0

    V = m_dot / (rho * A_flow)
    Re = rho * V * D_h / mu
    Re = max(Re, 1.0)

    A_churchill = (-2.457 * np.log((7.0 / Re) ** 0.9 + 0.27 * roughness / D_h)) ** 16
    B_churchill = (37530.0 / Re) ** 16
    f = 8.0 * ((8.0 / Re) ** 12 + 1.0 / (A_churchill + B_churchill) ** 1.5) ** (1.0 / 12.0)
    dP = f * (L / D_h) * 0.5 * rho * V**2

    return float(max(dP, 0.0))


class SegmentedHXSolver:
    """
    Solves counterflow HX by discretizing into N segments.
    Uses total heat duty iteration with enthalpy-based profiles.

    Convention:
    - Hot stream: enters at i=0, exits at i=n
    - Cold stream: enters at i=n, exits at i=0 (counterflow)
    - At any position i, T_hot[i] should be > T_cold[i]
    """

    def __init__(
        self,
        n_segments: int = 10,
        dT_pinch_min: float = 10.0,
        max_iterations: int = 50,
        tolerance: float = 0.02,
    ):
        self.n_segments = n_segments
        self.dT_pinch_min = dT_pinch_min
        self.max_iterations = max_iterations
        self.tolerance = tolerance

    def _estimate_ua_max(
        self,
        T_hot_in: float,
        T_cold_in: float,
        P_hot_in: float,
        P_cold_in: float,
        m_dot_hot: float,
        m_dot_cold: float,
        cp_func_hot: Optional[Callable[[float, float], float]],
        cp_func_cold: Optional[Callable[[float, float], float]],
        rho_func_hot: Callable[[float, float], float],
        mu_func_hot: Callable[[float, float], float],
        rho_func_cold: Callable[[float, float], float],
        mu_func_cold: Callable[[float, float], float],
        D_h: float,
        L_channel: float,
        A_flow_hot: float,
        A_flow_cold: float,
    ) -> Optional[float]:
        """Estimate UA-limited maximum heat duty using simple NTU closure."""
        if cp_func_hot is None or cp_func_cold is None:
            return None

        if D_h <= 0 or L_channel <= 0 or A_flow_hot <= 0 or A_flow_cold <= 0:
            return None

        try:
            cp_hot = max(cp_func_hot(T_hot_in, P_hot_in), 1.0)
            cp_cold = max(cp_func_cold(T_cold_in, P_cold_in), 1.0)
            C_hot = m_dot_hot * cp_hot
            C_cold = m_dot_cold * cp_cold
            C_min = max(min(C_hot, C_cold), 1.0)
            C_max = max(C_hot, C_cold)
            Cr = C_min / max(C_max, 1.0)

            rho_hot = max(rho_func_hot(T_hot_in, P_hot_in), 1e-6)
            mu_hot = max(mu_func_hot(T_hot_in, P_hot_in), 1e-12)
            rho_cold = max(rho_func_cold(T_cold_in, P_cold_in), 1e-6)
            mu_cold = max(mu_func_cold(T_cold_in, P_cold_in), 1e-12)

            V_hot = m_dot_hot / (rho_hot * A_flow_hot)
            V_cold = m_dot_cold / (rho_cold * A_flow_cold)
            Re_hot = max(rho_hot * abs(V_hot) * D_h / mu_hot, 1.0)
            Re_cold = max(rho_cold * abs(V_cold) * D_h / mu_cold, 1.0)

            # Lightweight convective estimates to make geometry/material flow relevant.
            h_hot = max(50.0, 12.0 * Re_hot ** 0.7 * (D_h ** -0.2))
            h_cold = max(50.0, 12.0 * Re_cold ** 0.7 * (D_h ** -0.2))
            U = 1.0 / (1.0 / h_hot + 1.0 / h_cold)

            A_eff_hot = A_flow_hot * max(L_channel / D_h, 1.0)
            A_eff_cold = A_flow_cold * max(L_channel / D_h, 1.0)
            A_eff = max(min(A_eff_hot, A_eff_cold), 1e-6)
            UA = U * A_eff

            NTU = UA / C_min
            if abs(1.0 - Cr) < 1e-8:
                eps = NTU / (1.0 + NTU)
            else:
                exp_term = np.exp(-NTU * (1.0 - Cr))
                eps = (1.0 - exp_term) / max(1.0 - Cr * exp_term, 1e-8)
            eps = float(np.clip(eps, 0.0, 1.0))

            dT_in = max(T_hot_in - T_cold_in, 0.0)
            return eps * C_min * dT_in
        except Exception:
            return None

    def solve(
        self,
        T_hot_in: float,
        P_hot_in: float,
        m_dot_hot: float,
        T_cold_in: float,
        P_cold_in: float,
        m_dot_cold: float,
        h_func_hot: Callable[[float, float], float],
        T_from_Ph_hot: Callable[[float, float], float],
        h_func_cold: Callable[[float, float], float],
        T_from_Ph_cold: Callable[[float, float], float],
        rho_func_hot: Callable[[float, float], float],
        mu_func_hot: Callable[[float, float], float],
        rho_func_cold: Callable[[float, float], float],
        mu_func_cold: Callable[[float, float], float],
        dP_hot_total: float = 50000.0,
        dP_cold_total: float = 50000.0,
        D_h: float = 2e-3,
        L_channel: float = 0.5,
        A_flow_hot: float = 0.01,
        A_flow_cold: float = 0.01,
        use_friction_dP: bool = False,
        cp_func_hot: Optional[Callable[[float, float], float]] = None,
        cp_func_cold: Optional[Callable[[float, float], float]] = None,
        use_ua_limit: bool = True,
    ) -> HXResult:
        """Solve counterflow HX with segmented approach."""
        if m_dot_hot <= 0 or m_dot_cold <= 0:
            return self._error_result(
                "Mass flow rates must be positive",
                InfeasibilityType.NEGATIVE_DUTY,
                T_hot_in,
                T_cold_in,
                P_hot_in,
                P_cold_in,
                dP_hot_total,
                dP_cold_total,
                solver_status=SolverStatus.NUMERICAL_FAIL,
            )

        n = self.n_segments
        assumption_mode = "friction_dP" if use_friction_dP else "constant_dP"

        try:
            rho_hot_in = max(rho_func_hot(T_hot_in, P_hot_in), 1e-6)
            mu_hot_in = max(mu_func_hot(T_hot_in, P_hot_in), 1e-12)
            rho_cold_in = max(rho_func_cold(T_cold_in, P_cold_in), 1e-6)
            mu_cold_in = max(mu_func_cold(T_cold_in, P_cold_in), 1e-12)
        except Exception as exc:
            return self._error_result(
                f"Property error for pressure-drop inputs: {exc}",
                InfeasibilityType.PROPERTY_ERROR,
                T_hot_in,
                T_cold_in,
                P_hot_in,
                P_cold_in,
                dP_hot_total,
                dP_cold_total,
                solver_status=SolverStatus.NUMERICAL_FAIL,
                assumption_mode=assumption_mode,
            )

        if use_friction_dP:
            dP_hot_total = pressure_drop_pche(
                m_dot_hot,
                rho_hot_in,
                mu_hot_in,
                D_h,
                L_channel,
                A_flow_hot,
            )
            dP_cold_total = pressure_drop_pche(
                m_dot_cold,
                rho_cold_in,
                mu_cold_in,
                D_h,
                L_channel,
                A_flow_cold,
            )

        T_hot = np.zeros(n + 1)
        T_cold = np.zeros(n + 1)
        h_hot = np.zeros(n + 1)
        h_cold = np.zeros(n + 1)
        P_hot = np.zeros(n + 1)
        P_cold = np.zeros(n + 1)

        T_hot[0] = T_hot_in
        T_cold[n] = T_cold_in

        for i in range(n + 1):
            P_hot[i] = P_hot_in - (i / n) * dP_hot_total
            P_cold[i] = P_cold_in - ((n - i) / n) * dP_cold_total

        try:
            h_hot[0] = h_func_hot(T_hot_in, P_hot[0])
            h_cold[n] = h_func_cold(T_cold_in, P_cold[n])
        except Exception as exc:
            return self._error_result(
                f"Property error at inlet: {exc}",
                InfeasibilityType.PROPERTY_ERROR,
                T_hot_in,
                T_cold_in,
                P_hot_in,
                P_cold_in,
                dP_hot_total,
                dP_cold_total,
                solver_status=SolverStatus.NUMERICAL_FAIL,
                assumption_mode=assumption_mode,
            )

        try:
            h_hot_min = h_func_hot(T_cold_in + self.dT_pinch_min, P_hot[n])
            h_cold_max = h_func_cold(T_hot_in - self.dT_pinch_min, P_cold[0])
        except Exception as exc:
            return self._error_result(
                f"Property error when estimating duty bounds: {exc}",
                InfeasibilityType.PROPERTY_ERROR,
                T_hot_in,
                T_cold_in,
                P_hot_in,
                P_cold_in,
                dP_hot_total,
                dP_cold_total,
                solver_status=SolverStatus.NUMERICAL_FAIL,
                assumption_mode=assumption_mode,
            )

        Q_max_hot = m_dot_hot * (h_hot[0] - h_hot_min)
        Q_max_cold = m_dot_cold * (h_cold_max - h_cold[n])
        Q_max = float(min(Q_max_hot, Q_max_cold))

        if Q_max <= 0:
            return self._error_result(
                "Zero or negative max heat duty",
                InfeasibilityType.NEGATIVE_DUTY,
                T_hot_in,
                T_cold_in,
                P_hot_in,
                P_cold_in,
                dP_hot_total,
                dP_cold_total,
                solver_status=SolverStatus.INFEASIBLE,
                assumption_mode=assumption_mode,
            )

        Q_target = Q_max
        if use_ua_limit:
            Q_ua_max = self._estimate_ua_max(
                T_hot_in,
                T_cold_in,
                P_hot_in,
                P_cold_in,
                m_dot_hot,
                m_dot_cold,
                cp_func_hot,
                cp_func_cold,
                rho_func_hot,
                mu_func_hot,
                rho_func_cold,
                mu_func_cold,
                D_h,
                L_channel,
                A_flow_hot,
                A_flow_cold,
            )
            if Q_ua_max is not None and Q_ua_max > 0:
                Q_target = min(Q_target, float(Q_ua_max))

        Q_low = 0.0
        Q_high = Q_target
        Q_total = 0.5 * Q_target

        converged = False
        dT_min = -np.inf
        pinch_seg = 0
        iteration = 0

        def _march(Q_local: float) -> Tuple[bool, Optional[str]]:
            Q_seg = Q_local / n
            h_hot[0] = h_func_hot(T_hot_in, P_hot[0])
            for idx in range(n):
                h_hot[idx + 1] = h_hot[idx] - Q_seg / m_dot_hot
                T_hot[idx + 1] = T_from_Ph_hot(P_hot[idx + 1], h_hot[idx + 1])

            h_cold[n] = h_func_cold(T_cold_in, P_cold[n])
            for idx in range(n - 1, -1, -1):
                h_cold[idx] = h_cold[idx + 1] + Q_seg / m_dot_cold
                T_cold[idx] = T_from_Ph_cold(P_cold[idx], h_cold[idx])

            return True, None

        for iteration in range(self.max_iterations):
            try:
                _, _ = _march(Q_total)
            except Exception as exc:
                Q_high = Q_total
                Q_total_new = 0.5 * (Q_low + Q_high)
                if abs(Q_total_new - Q_total) / max(Q_total, 1.0) < self.tolerance:
                    break
                Q_total = Q_total_new
                continue

            dT_min = float("inf")
            pinch_seg = 0
            for idx in range(n + 1):
                dT = T_hot[idx] - T_cold[idx]
                if dT < dT_min:
                    dT_min = dT
                    pinch_seg = idx

            if dT_min < self.dT_pinch_min:
                Q_high = Q_total
            else:
                Q_low = Q_total

            Q_total_new = 0.5 * (Q_low + Q_high)
            if abs(Q_total_new - Q_total) / max(Q_total, 1.0) < self.tolerance:
                converged = True
                Q_total = Q_total_new
                break
            Q_total = Q_total_new

        try:
            _, _ = _march(Q_total)
        except Exception as exc:
            return self._error_result(
                f"Property error at final march: {exc}",
                InfeasibilityType.PROPERTY_ERROR,
                T_hot_in,
                T_cold_in,
                P_hot_in,
                P_cold_in,
                dP_hot_total,
                dP_cold_total,
                solver_status=SolverStatus.NUMERICAL_FAIL,
                assumption_mode=assumption_mode,
                q_target=Q_target,
            )

        dT_min = float("inf")
        pinch_seg = 0
        for idx in range(n + 1):
            dT = T_hot[idx] - T_cold[idx]
            if dT < dT_min:
                dT_min = dT
                pinch_seg = idx

        feasible = converged and (dT_min >= self.dT_pinch_min)
        closure_error_rel = abs(Q_high - Q_low) / max(abs(Q_total), 1.0)

        segments = []
        Q_seg = Q_total / n
        for idx in range(n):
            segments.append(
                SegmentData(
                    index=idx,
                    Q=Q_seg,
                    T_hot=T_hot[idx],
                    T_cold=T_cold[idx],
                    h_hot=h_hot[idx],
                    h_cold=h_cold[idx],
                    P_hot=P_hot[idx],
                    P_cold=P_cold[idx],
                    dT_pinch=T_hot[idx] - T_cold[idx],
                )
            )

        if feasible:
            solver_status = SolverStatus.CONVERGED
            infeas_type = None
            err = None
        elif dT_min < self.dT_pinch_min:
            solver_status = SolverStatus.INFEASIBLE
            infeas_type = InfeasibilityType.PINCH_VIOLATION
            err = (
                f"Pinch violation at segment {pinch_seg}: "
                f"dT={dT_min:.2f}K < {self.dT_pinch_min:.2f}K"
            )
        else:
            solver_status = SolverStatus.NUMERICAL_FAIL
            infeas_type = InfeasibilityType.CONVERGENCE_FAILURE
            err = "HX binary-search iteration failed to converge"

        return HXResult(
            converged=converged,
            feasible=feasible,
            T_hot_out=T_hot[n],
            T_cold_out=T_cold[0],
            h_hot_out=h_hot[n],
            h_cold_out=h_cold[0],
            P_hot_out=P_hot[n],
            P_cold_out=P_cold[0],
            Q_total=Q_total,
            dT_pinch_min=dT_min,
            pinch_segment=pinch_seg,
            dP_hot=dP_hot_total,
            dP_cold=dP_cold_total,
            segments=segments,
            iterations=iteration + 1,
            error_message=err,
            infeasibility_type=infeas_type,
            solver_status=solver_status.value,
            closure_error_rel=closure_error_rel,
            assumption_mode=assumption_mode,
            Q_target=Q_target,
            Q_model=Q_total,
        )

    def _error_result(
        self,
        msg: str,
        infeas_type: InfeasibilityType,
        T_hot_in: float,
        T_cold_in: float,
        P_hot_in: float,
        P_cold_in: float,
        dP_hot: float,
        dP_cold: float,
        solver_status: SolverStatus,
        assumption_mode: str = "constant_dP",
        q_target: float = 0.0,
    ) -> HXResult:
        return HXResult(
            converged=False,
            feasible=False,
            T_hot_out=T_hot_in,
            T_cold_out=T_cold_in,
            h_hot_out=0.0,
            h_cold_out=0.0,
            P_hot_out=P_hot_in - dP_hot,
            P_cold_out=P_cold_in - dP_cold,
            Q_total=0.0,
            dT_pinch_min=0.0,
            pinch_segment=0,
            dP_hot=dP_hot,
            dP_cold=dP_cold,
            segments=[],
            error_message=msg,
            infeasibility_type=infeas_type,
            solver_status=solver_status.value,
            closure_error_rel=1.0,
            assumption_mode=assumption_mode,
            Q_target=q_target,
            Q_model=0.0,
        )


class CrossflowHXSolver:
    """Crossflow HX solver for dry cooler."""

    def __init__(self, n_segments: int = 10, dT_pinch_min: float = 5.0):
        self.n_segments = n_segments
        self.dT_pinch_min = dT_pinch_min

    def solve(
        self,
        T_CO2_in: float,
        P_CO2_in: float,
        m_dot_CO2: float,
        T_air_in: float,
        m_dot_air: float,
        Q_target: float,
        h_func_CO2: Callable,
        T_from_Ph_CO2: Callable,
        cp_air: float = 1006.0,
    ) -> Tuple[float, float, float, bool]:
        """Solve crossflow HX for dry cooler."""
        if m_dot_air <= 0 or m_dot_CO2 <= 0 or cp_air <= 0:
            return T_CO2_in, T_air_in, 0.0, False

        T_air_out = T_air_in + Q_target / (m_dot_air * cp_air)
        try:
            h_CO2_in = h_func_CO2(T_CO2_in, P_CO2_in)
            h_CO2_out = h_CO2_in - Q_target / m_dot_CO2
            T_CO2_out = T_from_Ph_CO2(P_CO2_in, h_CO2_out)
        except Exception:
            return T_CO2_in, T_air_out, 0.0, False

        dT_hot_end = T_CO2_in - T_air_out
        dT_cold_end = T_CO2_out - T_air_in
        feasible = min(dT_hot_end, dT_cold_end) >= self.dT_pinch_min

        return T_CO2_out, T_air_out, Q_target, feasible
