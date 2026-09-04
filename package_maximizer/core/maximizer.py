"""
Package Maximizer - Ядро системы максимизации непротиворечивого множества пакетов.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING, Iterable, Sequence

from .enums import PackageManagerType, SolverType
from .package import Package, PackageConstraint
from ..utils import CacheManager

if TYPE_CHECKING:
    from ..solvers import ConstraintSolver
    from ..parsers import PackageParser
    from ..analyzers import ResultAnalyzer

logger = logging.getLogger(__name__)


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
        parser: PackageParser | str | None = None,
        analyzer: ResultAnalyzer | str | None = None,
        use_cache: bool = True,
        cache_ttl: int = 3600
    ) -> None:
        """
        Инициализация PackageMaximizer.
        
        Args:
            manager: Тип пакетного менеджера (APT, PACMAN, DNF и др.)
            solver: Тип солвера (GREEDY, Z3, PULP, ORTOOLS и др.) или экземпляр
            parser: Парсер для пакетного менеджера (опционально)
            analyzer: Анализатор результатов (опционально)
            use_cache: Использовать кэширование
            cache_ttl: Время жизни кэша в секундах
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
        
        # Парсер
        self.parser = self._get_parser_instance(parser)
        
        # Анализатор
        self.analyzer = self._get_analyzer_instance(analyzer)
        
        # Кэширование
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self._cache: dict[str, Any] = {}
        self._cache_manager: CacheManager | None = CacheManager(default_ttl=cache_ttl) if use_cache else None
    
    def _get_cache(self) -> CacheManager | None:
        """Get the cache manager (DI-friendly accessor)."""
        return self._cache_manager

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
            'enhancedgreedysolver': SolverType.ENHANCED_GREEDY,
            'z3solver': SolverType.Z3,
            'pulpsolver': SolverType.PULP,
            'ortoolssolver': SolverType.ORTOOLS,
            'maxsatsolver': SolverType.MAXSAT,
            'minisatsolver': SolverType.MINISAT,
        }
        
        return solver_map.get(solver_name, SolverType.GREEDY)

    def _get_parser_instance(self, parser) -> PackageParser | None:
        """
        Получение экземпляра парсера.
        """
        if parser is None:
            # Автоматический выбор парсера по менеджеру (через registry)
            from ..parsers import get_parser

            try:
                return get_parser(self.manager.value)
            except ValueError:
                return None
        
        if isinstance(parser, str):
            from ..parsers import get_parser

            try:
                return get_parser(parser)
            except ValueError:
                return None
        
        return parser

    def _get_analyzer_instance(self, analyzer) -> ResultAnalyzer | None:
        """
        Получение экземпляра анализатора.
        """
        if analyzer is None:
            from ..analyzers import ResultAnalyzer
            return ResultAnalyzer()
        
        if isinstance(analyzer, str):
            from ..analyzers import get_analyzer
            try:
                return get_analyzer(analyzer)
            except ValueError:
                return None
        
        return analyzer

    def maximize(self, packages: Sequence[Package]) -> list[Package]:
        """
        Максимизировать множество пакетов с использованием настроенного солвера.
        
        Args:
            packages: Последовательность объектов Package
            
        Returns:
            Список выбранных объектов Package
        """
        # Проверяем кэш
        cache_key = self._get_cache_key("maximize", packages)
        if self.use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Получение имен пакетов из солвера
        selected_names = self.solver.solve(packages)
        
        # Возврат полных объектов Package
        selected_packages = []
        for pkg in packages:
            if pkg.name in selected_names:
                selected_packages.append(pkg)
        
        # Сохраняем в кэше
        if self.use_cache:
            self._cache[cache_key] = selected_packages
        
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
        # Проверяем кэш
        cache_key = self._get_cache_key("solve_with_weights", packages, weights)
        if self.use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Проверка поддержки весов солвером
        if hasattr(self.solver, 'solve_with_weights'):
            result = self.solver.solve_with_weights(packages, weights)
        else:
            # Резервный вариант - обычный solve
            result = self.solver.solve(packages)
        
        # Сохраняем в кэше
        if self.use_cache:
            self._cache[cache_key] = result
        
        return result

    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """
        Сгенерировать ключ кэша.
        """
        import hashlib
        
        key_parts = [method, str(self.solver_type), str(self.manager)]
        
        for arg in args:
            if isinstance(arg, (list, tuple)):
                key_parts.append(str([hashlib.md5(str(item).encode(), usedforsecurity=False).hexdigest() for item in arg]))
            else:
                key_parts.append(str(arg))
        
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        
        return hashlib.md5("|".join(key_parts).encode(), usedforsecurity=False).hexdigest()

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

    def analyze(
        self, 
        installed: list[str] | None = None, 
        proposed: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Проанализировать результаты максимизации.
        
        Args:
            installed: Список установленных пакетов
            proposed: Список предложенных пакетов
            
        Returns:
            Результаты анализа
        """
        if self.analyzer:
            return self.analyzer.analyze(installed, proposed)
        return {}

    def parse_packages(self, raw: str) -> list[Package]:
        """
        Разобрать сырые данные в пакеты с использованием текущего парсера.
        
        Args:
            raw: Сырые текстовые данные
            
        Returns:
            Список объектов Package
        """
        if self.parser:
            return self.parser.parse(raw)
        return []

    def parse_from_system(self, package_names: list[str] | None = None) -> list[Package]:
        """
        Разобрать пакеты напрямую из системы.
        
        Args:
            package_names: Список имен пакетов для запроса
            
        Returns:
            Список объектов Package
        """
        if self.parser and hasattr(self.parser, 'parse_from_system'):
            return self.parser.parse_from_system(package_names)
        return []

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

    def set_parser(self, parser: PackageParser | str | None) -> None:
        """
        Изменить парсер, используемый этим максимайзером.
        
        Args:
            parser: Тип или экземпляр парсера
        """
        self.parser = self._get_parser_instance(parser)

    def set_analyzer(self, analyzer: ResultAnalyzer | str | None) -> None:
        """
        Изменить анализатор, используемый этим максимайзером.
        
        Args:
            analyzer: Тип или экземпляр анализатора
        """
        self.analyzer = self._get_analyzer_instance(analyzer)

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

    def get_parser(self):
        """
        Получить текущий экземпляр парсера.
        
        Returns:
            Текущий экземпляр парсера
        """
        return self.parser

    def get_analyzer(self):
        """
        Получить текущий экземпляр анализатора.
        
        Returns:
            Текущий экземпляр анализатора
        """
        return self.analyzer

    def clear_cache(self) -> None:
        """
        Очистить кэш.
        """
        self._cache.clear()
