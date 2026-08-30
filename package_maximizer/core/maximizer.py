"""
Package Maximizer - Ядро системы максимизации непротиворечивого множества пакетов.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Sequence

from .enums import PackageManagerType, SolverType
from .package import Package, PackageConstraint

if TYPE_CHECKING:
    from ..solvers import ConstraintSolver


class PackageMaximizer:
    """
    Основной класс для решения задачи максимизации непротиворечивого множества пакетов.
    
    Использует различные солверы (SAT, ILP, SMT, CP-SAT) для нахождения
    оптимального решения.
    
    Пример использования:
        maximizer = PackageMaximizer(manager='apt', solver='z3')
        packages = [Package(name='pkg1'), Package(name='pkg2')]
        result = maximizer.maximize(packages)
    """

    def __init__(
        self,
        manager: PackageManagerType | str = PackageManagerType.APT,
        solver: SolverType | str | ConstraintSolver = SolverType.GREEDY,
    ) -> None:
        """
        Инициализация PackageMaximizer.
        
        Args:
            manager: Тип пакетного менеджера (APT, PACMAN, DNF и др.)
            solver: Тип солвера (GREEDY, Z3, PULP, ORTOOLS) или экземпляр солвера
        """
        self.manager = (
            manager if isinstance(manager, PackageManagerType) else PackageManagerType(manager)
        )
        
        # Обработка параметра solver
        if isinstance(solver, SolverType):
            self.solver_type = solver
            self.solver = self._get_solver_instance(solver)
        elif isinstance(solver, str):
            self.solver_type = SolverType(solver.lower())
            self.solver = self._get_solver_instance(self.solver_type)
        else:
            # Предполагаем, что это уже экземпляр солвера
            self.solver = solver
            self.solver_type = self._infer_solver_type(solver)

    def _get_solver_instance(self, solver_type: SolverType) -> ConstraintSolver:
        """
        Получение экземпляра солвера по типу.
        """
        from ..solvers import get_solver
        
        try:
            return get_solver(solver_type.value)
        except ValueError:
            # Резервный вариант - жадный алгоритм
            from ..solvers import GreedySolver
            return GreedySolver()

    def _infer_solver_type(self, solver) -> SolverType:
        """
        Определение типа солвера по экземпляру.
        """
        solver_name = solver.__class__.__name__.lower()
        
        # Соответствие имен классов типам солверов
        solver_map = {
            'greedysolver': SolverType.GREEDY,
            'z3solver': SolverType.Z3,
            'pulpsolver': SolverType.PULP,
            'ortoolssolver': SolverType.ORTOOLS,
        }
        
        return solver_map.get(solver_name, SolverType.GREEDY)

    def maximize(self, packages: Sequence[Package]) -> list[Package]:
        """
        Максимизировать множество пакетов с использованием настроенного солвера.
        
        Args:
            packages: Последовательность объектов Package
            
        Returns:
            Список выбранных объектов Package
        """
        # Получение имен пакетов из солвера
        selected_names = self.solver.solve(packages)
        
        # Возврат полных объектов Package
        selected_packages = []
        for pkg in packages:
            if pkg.name in selected_names:
                selected_packages.append(pkg)
        
        return selected_packages

    def solve(self, packages: Sequence[Package]) -> list[str]:
        """
        Решить задачу и вернуть только имена пакетов.
        
        Args:
            packages: Последовательность объектов Package
            
        Returns:
            Список имен выбранных пакетов
        """
        return self.solver.solve(packages)

    def solve_with_weights(
        self, 
        packages: Sequence[Package], 
        weights: dict[str, float] | None = None
    ) -> list[str]:
        """
        Решить задачу с учетом весов пакетов.
        
        Args:
            packages: Последовательность объектов Package
            weights: Словарь весов для пакетов
            
        Returns:
            Список имен выбранных пакетов
        """
        # Проверка поддержки весов солвером
        if hasattr(self.solver, 'solve_with_weights'):
            return self.solver.solve_with_weights(packages, weights)
        else:
            # Резервный вариант - обычный solve
            return self.solver.solve(packages)

    def check_constraints(
        self, packages: Iterable[Package], constraints: Iterable[PackageConstraint]
    ) -> dict[str, bool]:
        """
        Проверить выполнение ограничений для данных пакетов.
        
        Args:
            packages: Итерируемый объект Package
            constraints: Итерируемый объект PackageConstraint
            
        Returns:
            Словарь с соответствием имени пакета статусу выполнения ограничения
        """
        versions = {p.name: p.version for p in packages}
        return {
            c.package: c.satisfied_by(versions.get(c.package, ""))
            for c in constraints
        }

    @staticmethod
    def from_names(names: Iterable[str]) -> list[Package]:
        """
        Создать объекты Package из имен.
        
        Args:
            names: Итерируемый объект с именами пакетов
            
        Returns:
            Список объектов Package
        """
        return [Package(name=n, status="candidate") for n in names]

    def set_solver(self, solver: SolverType | str | ConstraintSolver) -> None:
        """
        Изменить солвер, используемый этим максимайзером.
        
        Args:
            solver: Тип или экземпляр солвера
        """
        if isinstance(solver, SolverType):
            self.solver_type = solver
            self.solver = self._get_solver_instance(solver)
        elif isinstance(solver, str):
            self.solver_type = SolverType(solver.lower())
            self.solver = self._get_solver_instance(self.solver_type)
        else:
            self.solver = solver
            self.solver_type = self._infer_solver_type(solver)

    def get_solver(self):
        """
        Получить текущий экземпляр солвера.
        
        Returns:
            Текущий экземпляр солвера
        """
        return self.solver

    def get_solver_type(self) -> SolverType:
        """
        Получить текущий тип солвера.
        
        Returns:
            Текущий тип солвера
        """
        return self.solver_type
