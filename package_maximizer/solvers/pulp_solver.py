"""
PuLP ILP Solver — целочисленное линейное программирование.

Поддерживает:
- Максимизацию числа/веса выбранных пакетов
- Учёт конфликтов между пакетами
- Учёт зависимостей (implications)
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Any, Iterable, Optional, cast

from ..core.interfaces import ConstraintSolver
from ..core.model_encoder import encode_packages

if TYPE_CHECKING:
    from ..core.package import Package

logger = logging.getLogger(__name__)

try:
    import pulp
    from pulp import LpBinary, LpMaximize, LpProblem, LpVariable, lpSum, value

    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False


_SOLVER_ALIASES = {"CBC": "COIN_CMD", "HIGHS": "HiGHS"}


def _binary_vars(prob, prefix: str, names: list[str]) -> dict:
    """Create binary variables via the PuLP 4.0 API when available."""
    if hasattr(prob, "add_variable_dicts"):
        return prob.add_variable_dicts(prefix, names, cat=LpBinary)
    return cast(Any, LpVariable).dicts(prefix, names, cat=LpBinary)


def _bundled_cbc(time_limit: float):
    """PuLP's bundled CBC (``PULP_CBC_CMD``, PuLP < 4.0 only), or ``None``."""
    bundled = getattr(pulp, "PULP_CBC_CMD", None)
    if bundled is None:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return bundled(msg=False, timeLimit=time_limit)


def _status_name(prob, result) -> str:
    """Solve status name for PuLP 4 (``LpSolveStats``) and older (int status)."""
    status = getattr(result, "status", None)
    if status is None:
        status = getattr(prob, "status", result)
    name = getattr(status, "name", None)
    if isinstance(name, str):
        return name
    return getattr(pulp, "LpStatus", {}).get(status, str(status))


class PulPSolver(ConstraintSolver):
    """ILP/MIP-солвер на основе PuLP."""

    def __init__(
        self, solver_name: Optional[str] = None, time_limit: int = 10000
    ) -> None:
        self.solver_name = solver_name
        self.time_limit = time_limit

    def solve(self, packages: Iterable[Package]) -> list[str]:
        if not PULP_AVAILABLE:
            logger.warning("PuLP not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve(packages)

        package_list = list(packages)
        if not package_list:
            return []

        return self._solve_ilp(package_list, None, "Package_Maximization")

    def solve_with_weights(
        self, packages: Iterable[Package], weights: dict[str, float] | None = None
    ) -> list[str]:
        if not PULP_AVAILABLE:
            logger.warning("PuLP not available, falling back to GreedySolver")
            from .greedy import GreedySolver

            return GreedySolver().solve_with_weights(packages, weights)

        package_list = list(packages)
        if not package_list:
            return []

        if weights is None:
            weights = {pkg.name: 1.0 for pkg in package_list}

        return self._solve_ilp(package_list, weights, "Weighted_Package_Maximization")

    def _solve_ilp(
        self,
        package_list: list[Package],
        weights: dict[str, float] | None,
        problem_name: str,
    ) -> list[str]:
        constraints = encode_packages(package_list)
        prob = LpProblem(problem_name, LpMaximize)
        x = _binary_vars(prob, "Package", constraints.packages)

        if weights is None:
            prob += lpSum(x[name] for name in constraints.packages), "Total_Packages"
        else:
            prob += (
                lpSum(
                    x[name] * weights.get(name, 1.0) for name in constraints.packages
                ),
                "Total_Weight",
            )

        for a, b in constraints.conflicts:
            prob += x[a] + x[b] <= 1, f"Conflict_{a}_{b}"

        # selected(pkg) => selected(dep)
        for pkg, deps in constraints.dependencies.items():
            for dep in deps:
                prob += x[pkg] - x[dep] <= 0, f"Dep_{pkg}_{dep}"

        try:
            result = prob.solve(self._make_backend())
        except Exception as e:
            logger.warning(f"PuLP solver failed: {e}")
            return self._greedy_fallback(package_list, weights)

        status = _status_name(prob, result)
        if status == "Optimal":
            return [
                name for name in constraints.packages if (value(x[name]) or 0) > 0.5
            ]
        logger.warning(f"PuLP solver status: {status}")
        return self._greedy_fallback(package_list, weights)

    def _make_backend(self):
        """Pick a PuLP backend without relying on APIs removed in PuLP 4.0.

        Order: explicit ``solver_name`` → ``COIN_CMD`` (system or ``pulp[cbc]``
        CBC) → HiGHS → bundled ``PULP_CBC_CMD`` (PuLP < 4.0 only).
        """
        time_limit = self.time_limit / 1000
        if self.solver_name:
            name = _SOLVER_ALIASES.get(self.solver_name.upper(), self.solver_name)
            backend = pulp.getSolver(name, msg=False, timeLimit=time_limit)
            if name == "COIN_CMD" and not backend.available():
                return _bundled_cbc(time_limit) or backend
            return backend

        for name in ("COIN_CMD", "HiGHS", "HiGHS_CMD"):
            solver_cls = getattr(pulp, name, None)
            if solver_cls is None:
                continue
            candidate = solver_cls(msg=False, timeLimit=time_limit)
            if candidate.available():
                return candidate

        bundled = _bundled_cbc(time_limit)
        if bundled is None:
            raise RuntimeError(
                "No PuLP backend available; install CBC with `pip install pulp[cbc]`"
            )
        return bundled

    def _greedy_fallback(
        self, packages: list[Package], weights: dict[str, float] | None = None
    ) -> list[str]:
        from .greedy import GreedySolver

        solver = GreedySolver()
        if weights:
            return solver.solve_with_weights(packages, weights)
        return solver.solve(packages)
