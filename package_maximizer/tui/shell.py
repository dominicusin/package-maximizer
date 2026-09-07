"""
Interactive shell for package-maximizer.

Provides a command-line REPL for interactively managing package
maximization tasks without leaving the terminal.
"""

from __future__ import annotations

import cmd
import json
import shlex

from ..core.enums import PackageManagerType
from ..core.maximizer import PackageMaximizer
from ..core.package import Package


class MaximizerShell(cmd.Cmd):
    """
    Интерактивная оболочка для работы с package-maximizer.

    Поддерживаемые команды:
    - maximize <pkg1> <pkg2> ...  — максимизировать набор пакетов
    - propose <pkg1> <pkg2> ...   — предложить оптимальный набор
    - compare <pkg1> <pkg2> ...   — сравнить все солверы
    - analyze <pkg1> <pkg2> ...   — проанализировать конфликты
    - info <pkg_name>             — информация о пакете
    - search <query>              — поиск пакетов
    - manager <apt|pip|pacman>    — сменить менеджер
    - solver <greedy|z3|pulp>     — сменить солвер
    - help                        — показать справку
    """

    intro = (
        "Package Maximizer Interactive Shell\n"
        "Введите 'help' для списка команд, 'exit' для выхода.\n"
    )
    prompt = "(pm) "

    def __init__(self, manager: str = "apt") -> None:
        super().__init__()
        self.manager = manager
        self.solver = "greedy"
        self._integrations: dict[str, object] = {}

    def _get_integration(self):
        """Get or create RealRepoIntegration for current manager."""
        from ..integrations.real_repo_integration import RealRepoIntegration

        if self.manager not in self._integrations:
            self._integrations[self.manager] = RealRepoIntegration(
                package_manager=self.manager
            )
        return self._integrations[self.manager]

    def _get_maximizer(self, solver: str | None = None):
        """Get a PackageMaximizer with the current (or specified) solver."""
        sol = solver or self.solver
        return PackageMaximizer(manager=self.manager, solver=sol)

    def do_maximize(self, arg: str) -> None:
        """maximize <pkg1> <pkg2> ... — выбрать максимальное совместное множество."""
        packages = shlex.split(arg)
        if not packages:
            print("Usage: maximize <pkg1> <pkg2> ...")
            return
        try:
            pkg_objs = [Package(name=p, status="candidate") for p in packages]
            maximizer = self._get_maximizer()
            result = maximizer.solve(pkg_objs)
            print(f"Выбрано ({len(result)}): {', '.join(result)}")
            all_names = {p.name for p in pkg_objs}
            excluded = all_names - set(result)
            if excluded:
                print(f"Исключено ({len(excluded)}): {', '.join(sorted(excluded))}")
        except Exception as e:  # noqa: BLE001
            print(f"Ошибка: {e}")

    def do_propose(self, arg: str) -> None:
        """propose <pkg1> <pkg2> ... — предложить оптимальный набор с автозагрузкой метаданных."""
        packages = shlex.split(arg)
        if not packages:
            print("Usage: propose <pkg1> <pkg2> ...")
            return
        try:
            pkg_objs = [Package(name=p, status="candidate") for p in packages]
            maximizer = self._get_maximizer()
            # Load metadata via adapter
            try:
                from ..adapters import get_adapter

                adapter = get_adapter(self.manager)
                if adapter is not None:
                    for pkg in pkg_objs:
                        meta = adapter.fetch(pkg.name)
                        if meta:
                            if meta.depends:
                                pkg.depends = list(meta.depends)
                            if meta.conflicts:
                                pkg.conflicts = list(meta.conflicts)
            except Exception:
                pass
            result = maximizer.solve(pkg_objs)
            print(f"Предложено ({len(result)}): {', '.join(result)}")
        except Exception as e:  # noqa: BLE001
            print(f"Ошибка: {e}")

    def do_compare(self, arg: str) -> None:
        """compare <pkg1> <pkg2> ... — сравнить все солверы."""
        import time

        from ..solvers import SOLVER_REGISTRY

        packages = shlex.split(arg)
        if not packages:
            print("Usage: compare <pkg1> <pkg2> ...")
            return
        pkg_objs = [Package(name=p, status="candidate") for p in packages]
        print(
            f"Сравнение {len(list(SOLVER_REGISTRY.keys()))} солверов на {len(packages)} пакетах..."
        )
        results = []
        for sname in SOLVER_REGISTRY:
            try:
                solver_cls = SOLVER_REGISTRY[sname]
                solver_inst = solver_cls()
                start = time.time()
                res = solver_inst.solve(list(pkg_objs))
                elapsed = time.time() - start
                results.append(
                    {
                        "solver": sname,
                        "avg_time": elapsed,
                        "selected_count": len(res),
                        "success": True,
                        "error": None,
                    }
                )
            except Exception as e:  # noqa: BLE001
                results.append(
                    {
                        "solver": sname,
                        "avg_time": 0.0,
                        "selected_count": 0,
                        "success": False,
                        "error": str(e),
                    }
                )
        results.sort(key=lambda r: r["avg_time"])
        print(f"\n{'Solver':<20s} {'Time (s)':<12s} {'Selected':<10s} Status")
        print("-" * 60)
        for r in results:
            status = "OK" if r["success"] else f"ERR: {r['error']}"
            print(
                f"{r['solver']:<20s} {r['avg_time']:<12.6f} "
                f"{r['selected_count']:<10d} {status}"
            )
        print("-" * 60)
        if results:
            best = results[0]
            print(f"Best: {best['solver']} ({best['avg_time']:.6f}s)")

    def do_analyze(self, arg: str) -> None:
        """analyze <pkg1> <pkg2> ... — проанализировать конфликты и узкие места."""
        packages = shlex.split(arg)
        if not packages:
            print("Usage: analyze <pkg1> <pkg2> ...")
            return
        try:
            pkg_objs = [Package(name=p, status="candidate") for p in packages]
            maximizer = self._get_maximizer()
            result = maximizer.solve(pkg_objs)
            print(f"Выбрано ({len(result)}): {', '.join(result)}")
            all_names = {p.name for p in pkg_objs}
            excluded = all_names - set(result)
            if excluded:
                print(f"Исключено ({len(excluded)}): {', '.join(sorted(excluded))}")
                # Show conflict details
                conflict_count: dict[str, int] = {}
                for pkg in pkg_objs:
                    for c in pkg.conflicts:
                        conflict_count[c] = conflict_count.get(c, 0) + 1
                bottlenecks = sorted(
                    conflict_count.items(), key=lambda x: x[1], reverse=True
                )[:5]
                if bottlenecks:
                    print("\n--- Bottleneck Packages ---")
                    for name, count in bottlenecks:
                        print(f"  {name}: {count} conflicts")
        except Exception as e:  # noqa: BLE001
            print(f"Ошибка: {e}")

    def do_info(self, arg: str) -> None:
        """info <pkg_name> — информация о пакете."""
        packages = shlex.split(arg)
        if len(packages) != 1:
            print("Usage: info <pkg_name>")
            return
        try:
            integration = self._get_integration()
            info = integration.get_package_info(packages[0])  # type: ignore[union-attr]
            if info is None:
                print(f"Пакет '{packages[0]}' не найден")
                return
            print(f"Name: {info.name}")
            print(f"Version: {info.version}")
            print(f"Description: {info.description}")
            print(f"Depends: {', '.join(info.depends) if info.depends else 'Нет'}")
            print(
                f"Conflicts: {', '.join(info.conflicts) if info.conflicts else 'Нет'}"
            )
            print(f"Size: {info.size} KB")
            print(f"Installed: {'Да' if info.installed else 'Нет'}")
        except Exception as e:  # noqa: BLE001
            print(f"Ошибка: {e}")

    def do_search(self, arg: str) -> None:
        """search <query> — поиск пакетов."""
        packages = shlex.split(arg)
        if not packages:
            print("Usage: search <query>")
            return
        query = packages[0]
        try:
            integration = self._get_integration()
            results = integration.search_packages(query, limit=10)  # type: ignore[union-attr]
            if not results:
                print("Ничего не найдено")
                return
            print(f"Найдено {len(results)} пакетов:")
            for pkg in results:
                print(f"  {pkg.name}")
        except Exception as e:  # noqa: BLE001
            print(f"Ошибка: {e}")

    def do_manager(self, arg: str) -> None:
        """manager <apt|pip|pacman|dnf|brew> — сменить пакетный менеджер."""
        arg = arg.strip()
        if not arg:
            print(f"Текущий менеджер: {self.manager}")
            return
        try:
            PackageManagerType(arg)
            self.manager = arg
            self._integrations.pop(arg, None)
            print(f"Менеджер установлен: {self.manager}")
        except ValueError:
            valid = [m.value for m in PackageManagerType]
            print(f"Ошибка: неизвестный менеджер '{arg}'. Доступные: {valid}")

    def do_solver(self, arg: str) -> None:
        """solver <greedy|z3|pulp|ortools> — сменить солвер."""
        arg = arg.strip()
        if not arg:
            print(f"Текущий солвер: {self.solver}")
            return
        self.solver = arg
        print(f"Солвер установлен: {self.solver}")

    def do_json(self, arg: str) -> None:
        """json <command> <args> — выполнить команду и вывести результат в JSON."""
        args = shlex.split(arg)
        if not args:
            print("Usage: json <maximize|propose|compare|analyze> <pkgs...>")
            return
        cmd_name = args[0]
        packages = args[1:]
        if not packages:
            print("Usage: json <command> <pkg1> <pkg2> ...")
            return
        try:
            pkg_objs = [Package(name=p, status="candidate") for p in packages]
            maximizer = self._get_maximizer()
            if cmd_name == "maximize":
                result = maximizer.solve(pkg_objs)
                print(json.dumps({"selected": result, "count": len(result)}))
            elif cmd_name == "analyze":
                result = maximizer.solve(pkg_objs)
                all_names = {p.name for p in pkg_objs}
                excluded = all_names - set(result)
                print(
                    json.dumps(
                        {
                            "selected": result,
                            "excluded": list(excluded),
                            "conflict_count": sum(len(p.conflicts) for p in pkg_objs),
                        }
                    )
                )
            else:
                print(f"Unknown json command: {cmd_name}")
        except Exception as e:  # noqa: BLE001
            print(f"Ошибка: {e}")

    def do_exit(self, arg: str) -> bool:
        """Выйти из оболочки."""
        print("До свидания!")
        return True

    def do_quit(self, arg: str) -> bool:
        """Выйти из оболочки."""
        return self.do_exit(arg)

    def default(self, line: str) -> None:
        cmd, _, arg = line.partition(" ")
        print(f"Неизвестная команда: {cmd}. Введите 'help' для списка команд.")

    def do_help(self, arg: str) -> None:
        """Показать справку по командам."""
        if arg:
            super().do_help(arg)
        else:
            print("\nДоступные команды:")
            print("  maximize <pkgs...>  — максимизировать набор пакетов")
            print("  propose <pkgs...>   — предложить набор с автозагрузкой метаданных")
            print("  compare <pkgs...>   — сравнить все солверы")
            print("  analyze <pkgs...>   — проанализировать конфликты и узкие места")
            print("  info <pkg>          — информация о пакете")
            print("  search <query>      — поиск пакетов")
            print(
                "  manager [name]      — сменить менеджер (apt, pip, pacman, dnf, brew)"
            )
            print("  solver [name]       — сменить солвер (greedy, z3, pulp, ortools)")
            print("  json <cmd> <pkgs>   — вывести результат команды в JSON")
            print("  exit / quit         — выйти")
            print()

    def run(self) -> None:
        """Run the shell interactively."""
        self.cmdloop()
