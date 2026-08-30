"""
Solvers module - Модуль солверов для решения задачи максимизации пакетов.
"""

from __future__ import annotations

from .greedy import GreedySolver
from .z3_solver import Z3Solver
from .pulp_solver import PulPSolver
from .ortools_solver import ORToolsSolver

# Available solvers
__all__ = [
    "GreedySolver",
    "Z3Solver",
    "PulPSolver",
    "ORToolsSolver",
    "get_solver",
    "SOLVER_REGISTRY",
]

# Solver registry for easy access
SOLVER_REGISTRY = {
    "greedy": GreedySolver,
    "z3": Z3Solver,
    "pulp": PulPSolver,
    "ortools": ORToolsSolver,
}


def get_solver(solver_name: str):
    """
    Получение экземпляра солвера по имени.
    
    Args:
        solver_name: Имя солвера (регистронезависимое)
        
    Returns:
        Экземпляр солвера
        
    Raises:
        ValueError: Если солвер не найден
    """
    solver_name = solver_name.lower()
    if solver_name not in SOLVER_REGISTRY:
        available = ", ".join(SOLVER_REGISTRY.keys())
        raise ValueError(f"Solver '{solver_name}' not found. Available: {available}")
    return SOLVER_REGISTRY[solver_name]()
