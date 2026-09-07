"""
Package Maximizer CLI - Командный интерфейс.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from ..core.config import load_config
from ..core.enums import PackageManagerType
from ..core.maximizer import PackageMaximizer
from ..core.package import Package
from ..integrations import RealRepoIntegration
from ..utils.logging_config import configure_logging

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Включить подробный вывод")
@click.option("--quiet", "-q", is_flag=True, help="Отключить вывод")
@click.option(
    "--config",
    "-C",
    type=str,
    default=None,
    help="Путь к файлу конфигурации (YAML/JSON)",
)
def cli(verbose: bool, quiet: bool, config: str | None):
    """
    Package Maximizer - Система максимизации непротиворечивого множества пакетов.

    Использует различные SAT/ILP/SMT солверы для решения задачи.
    """
    level = "INFO"
    if quiet:
        level = "ERROR"
    elif verbose:
        level = "DEBUG"
    cfg = load_config(config)
    # CLI flags take precedence over config/env for log level.
    configure_logging(level, json_output=cfg.log_json)
    # Share the loaded config with subcommands (ctx.obj).
    click.get_current_context().obj = {"config": cfg, "config_path": config}


@cli.command()
@click.argument("packages", nargs=-1)
@click.option(
    "--manager",
    "-m",
    type=str,
    default=None,
    help="Тип пакетного менеджера (apt, pacman, dnf, brew, snap, flatpak, cargo, npm, pip, gem, apk, zypper, yum, yarn, composer, vcpkg, nuget, winget, scoop, choco, conda, portage)",
)
@click.option(
    "--solver",
    "-s",
    type=str,
    default=None,
    help="Тип солвера (greedy, z3, pulp, ortools, maxsat, minisat, enhanced_greedy)",
)
@click.option(
    "--conflicts",
    "-c",
    type=(str, str),
    multiple=True,
    help="Конфликты между пакетами (имя1,имя2)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Формат вывода",
)
@click.option(
    "--weights", "-w", type=(str, float), multiple=True, help="Веса пакетов (имя,вес)"
)
@click.option(
    "--depends",
    "-d",
    type=(str, str),
    multiple=True,
    help="Зависимости пакетов (имя,зависимость)",
)
@click.option(
    "--explain",
    "-e",
    is_flag=True,
    default=False,
    help="Показать причины отбора/отклонения пакетов",
)
@click.option(
    "--metadata",
    is_flag=True,
    default=False,
    help="Автоматически загружать метаданные пакетов через адаптеры",
)
def maximize(
    packages, manager, solver, conflicts, output, weights, depends, explain, metadata
):
    """
    Максимизировать множество пакетов.

    Примеры:

        package-maximizer pkg1 pkg2 pkg3

        package-maximizer pkg1 pkg2 -c pkg1,pkg2 -s z3

        package-maximizer pkg1 pkg2 pkg3 -w pkg1,2.0 -w pkg2,1.5
    """
    # Resolve config-driven defaults (explicit CLI flags take precedence).
    obj = click.get_current_context().obj or {}
    cfg = obj.get("config")
    if manager is None:
        manager = cfg.default_manager if cfg else "apt"
    if solver is None:
        solver = cfg.default_solver if cfg else "greedy"

    try:
        # Валидация менеджера
        try:
            manager_enum = PackageManagerType(manager)
        except ValueError:
            click.echo(f"Ошибка: Неизвестный пакетный менеджер '{manager}'", err=True)
            sys.exit(1)

        # Создание объектов пакетов
        package_objs = []
        conflict_map = {}

        for pkg_name in packages:
            pkg = Package(name=pkg_name, status="candidate")
            package_objs.append(pkg)

        # Добавление конфликтов
        for pkg_name, conflict_name in conflicts:
            conflict_map.setdefault(pkg_name, []).append(conflict_name)

        # Применение конфликтов к пакетам
        for pkg in package_objs:
            if pkg.name in conflict_map:
                pkg.conflicts = conflict_map[pkg.name]

        # Добавление зависимостей
        dep_map = {}
        for pkg_name, dep_name in depends:
            dep_map.setdefault(pkg_name, []).append(dep_name)

        # Применение зависимостей к пакетам
        for pkg in package_objs:
            if pkg.name in dep_map:
                pkg.depends = dep_map[pkg.name]

        # Автоматическая загрузка метаданных через адаптеры
        if metadata:
            from ..adapters import get_adapter

            try:
                adapter = get_adapter(manager)
            except Exception:
                adapter = None

            if adapter is None:
                click.echo(
                    f"Предупреждение: нет адаптера метаданных для '{manager}'. "
                    "Метаданные не будут загружены.",
                    err=True,
                )
            else:
                metadata_count = 0
                for pkg in package_objs:
                    pkg_metadata = adapter.fetch(pkg.name)
                    if pkg_metadata and pkg_metadata.name:
                        if pkg_metadata.depends:
                            pkg.depends = list(
                                dict.fromkeys(pkg.depends + pkg_metadata.depends)
                            )
                        if pkg_metadata.conflicts:
                            pkg.conflicts = list(
                                dict.fromkeys(pkg.conflicts + pkg_metadata.conflicts)
                            )
                        metadata_count += 1

                if metadata_count > 0:
                    click.echo(
                        f"Загружены метаданные для {metadata_count}/{len(package_objs)} пакетов",
                        err=True,
                    )

        # Создание словаря весов
        weights_dict = dict(weights) if weights else None

        # Создание максимайзера
        try:
            maximizer = PackageMaximizer(manager=manager_enum, solver=solver)
        except ValueError:
            click.echo(f"Ошибка: Неизвестный солвер '{solver}'", err=True)
            sys.exit(1)

        # Решение
        if weights_dict:
            result = maximizer.solve_with_weights(package_objs, weights_dict)
        else:
            result = maximizer.solve(package_objs)

        # Вывод
        if output == "json":
            output_data = {
                "manager": manager,
                "solver": solver,
                "input": [p.name for p in package_objs],
                "output": result,
                "count": len(result),
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Менеджер: {manager}")
            click.echo(f"Солвер: {solver}")
            click.echo(f"Входные пакеты: {len(package_objs)}")
            click.echo(f"Выбранные пакеты: {len(result)}")
            click.echo(f"Результат: {', '.join(result)}")

            if explain:
                # Анализ причин
                selected_set = set(result)
                all_names = {p.name for p in package_objs}
                excluded = all_names - selected_set

                if excluded:
                    click.echo("\nПричины отклонения:")
                    # Используем encoder для получения ограничений
                    from ..core.model_encoder import encode_packages

                    constraints = encode_packages(package_objs)

                    for name in sorted(excluded):
                        reasons = []
                        # Проверяем конфликты
                        for a, b in constraints.conflicts:
                            if a == name and b in selected_set:
                                reasons.append(f"конфликт с {b}")
                            elif b == name and a in selected_set:
                                reasons.append(f"конфликт с {a}")

                        # Проверяем зависимости (если pkg исключён, возможно его зависимости не выбраны)
                        deps = constraints.dependencies.get(name, [])
                        for dep in deps:
                            if dep not in selected_set:
                                reasons.append(f"не выбрана зависимость {dep}")

                        if reasons:
                            click.echo(f"  - {name}: {'; '.join(reasons)}")
                        else:
                            click.echo(f"  - {name}: не оптимально для данного солвера")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
def list_solvers():
    """
    Показать доступные солверы.
    """
    from ..solvers import SOLVER_REGISTRY

    click.echo("Доступные солверы:")
    for name, solver_class in SOLVER_REGISTRY.items():
        doc = solver_class.__doc__ or "No description"
        # Get first line of docstring
        first_line = doc.split("\n")[0] if doc else ""
        click.echo(f"  - {name}: {first_line}")


@cli.command()
def list_managers():
    """
    Показать поддерживаемые пакетные менеджеры.
    """
    from ..parsers import PARSER_REGISTRY

    click.echo("Поддерживаемые пакетные менеджеры:")
    for name, parser_class in PARSER_REGISTRY.items():
        doc = parser_class.__doc__ or "No description"
        first_line = doc.split("\n")[0] if doc else ""
        click.echo(f"  - {name}: {first_line}")


@cli.command()
def list_parsers():
    """
    Показать доступные парсеры.
    """
    from ..parsers import PARSER_REGISTRY

    click.echo("Доступные парсеры:")
    for name, parser_class in PARSER_REGISTRY.items():
        doc = parser_class.__doc__ or "No description"
        first_line = doc.split("\n")[0] if doc else ""
        click.echo(f"  - {name}: {first_line}")


@cli.command()
def version():
    """
    Показать версию.
    """
    from .. import __version__

    click.echo(f"Package Maximizer version: {__version__}")


@cli.command()
@click.argument("package_file", type=click.Path(exists=True))
@click.option("--manager", "-m", type=str, default="apt")
@click.option("--solver", "-s", type=str, default="greedy")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def from_file(package_file, manager, solver, output):
    """
    Максимизировать пакеты из JSON файла.

    Файл должен содержать массив объектов:
    [
        {"name": "pkg1", "version": "1.0", "conflicts": ["pkg2"]},
        {"name": "pkg2", "version": "2.0"}
    ]
    """
    try:
        with open(package_file, "r") as f:
            data = json.load(f)

        # Разбор пакетов
        package_objs = []
        for item in data:
            pkg = Package(
                name=item.get("name", ""),
                version=item.get("version", ""),
                status=item.get("status", "candidate"),
                depends=item.get("depends", []),
                conflicts=item.get("conflicts", []),
            )
            package_objs.append(pkg)

        # Создание максимайзера
        try:
            manager_enum = PackageManagerType(manager)
        except ValueError:
            click.echo(f"Ошибка: Неизвестный пакетный менеджер '{manager}'", err=True)
            sys.exit(1)

        maximizer = PackageMaximizer(manager=manager_enum, solver=solver)

        # Решение
        result = maximizer.solve(package_objs)

        # Вывод
        if output == "json":
            output_data = {
                "manager": manager,
                "solver": solver,
                "input_count": len(package_objs),
                "output": result,
                "count": len(result),
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Менеджер: {manager}")
            click.echo(f"Солвер: {solver}")
            click.echo(f"Входные пакеты: {len(package_objs)}")
            click.echo(f"Выбранные пакеты: {len(result)}")
            click.echo(f"Результат: {', '.join(result)}")

    except json.JSONDecodeError as e:
        click.echo(f"Ошибка: Некорректный JSON файл: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--solvers", "-s", type=str, default="all", help="Список солверов через запятую"
)
@click.option(
    "--packages", "-p", type=int, default=100, help="Количество пакетов для теста"
)
@click.option(
    "--runs", "-r", type=int, default=5, help="Количество запусков на каждый тест"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Формат вывода",
)
def benchmark(solvers, packages, runs, output):
    """
    Запустить тесты производительности солверов.
    """
    import time

    from ..solvers import SOLVER_REGISTRY

    # Генерация тестовых пакетов
    test_packages = []
    for i in range(packages):
        pkg = Package(name=f"pkg{i}", version=f"1.{i}", status="candidate")
        # Добавление конфликтов (10% пакетов конфликтуют)
        if i % 10 == 0 and i > 0:
            pkg.conflicts = [f"pkg{j}" for j in range(i - 5, i) if j >= 0]
        test_packages.append(pkg)

    # Выбор солверов
    if solvers == "all":
        solver_names = list(SOLVER_REGISTRY.keys())
    else:
        solver_names = [s.strip() for s in solvers.split(",")]

    click.echo(
        f"Тестирование {len(solver_names)} солверов с {packages} пакетами, {runs} запусков"
    )
    click.echo("-" * 60)

    results = {}

    for solver_name in solver_names:
        if solver_name not in SOLVER_REGISTRY:
            click.echo(f"Предупреждение: Солвер '{solver_name}' не найден, пропускаем")
            continue

        solver_class = SOLVER_REGISTRY[solver_name]
        times = []

        for run in range(runs):
            try:
                solver = solver_class()
                start = time.time()
                _ = solver.solve(test_packages)
                end = time.time()
                times.append(end - start)
            except Exception as e:
                click.echo(f"Ошибка с {solver_name} на запуске {run}: {e}")
                times.append(float("inf"))

        avg_time = sum(times) / len(times) if times else 0
        results[solver_name] = {
            "avg_time": avg_time,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "runs": len(times),
        }

        click.echo(
            f"{solver_name:15s}: {avg_time:.4f}s avg ({min(times):.4f}s - {max(times):.4f}s)"
        )

    click.echo("-" * 60)

    # Найти самый быстрый
    if results:
        fastest = min(results.items(), key=lambda x: x[1]["avg_time"])
        click.echo(f"Самый быстрый: {fastest[0]} ({fastest[1]['avg_time']:.4f}s)")

    # Вывод в JSON если нужно
    if output == "json":
        click.echo(json.dumps(results, indent=2))


# Новые команды для Фазы 4


@cli.command()
@click.option(
    "--manager", "-m", type=str, default="apt", help="Тип пакетного менеджера"
)
@click.option(
    "--limit", "-l", type=int, default=20, help="Максимальное количество результатов"
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def list_installed(manager, limit, output):
    """
    Показать установленные пакеты.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        packages = integration.get_installed_packages()

        if output == "json":
            output_data = {
                "manager": manager,
                "count": len(packages),
                "packages": [
                    {"name": p.name, "version": p.version, "status": p.status}
                    for p in packages[:limit]
                ],
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Установлено пакетов: {len(packages)}")
            click.echo(f"Первые {min(limit, len(packages))}:")
            for pkg in packages[:limit]:
                click.echo(f"  - {pkg.name} {pkg.version or ''}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option(
    "--manager", "-m", type=str, default="apt", help="Тип пакетного менеджера"
)
@click.option(
    "--limit", "-l", type=int, default=20, help="Максимальное количество результатов"
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def search(query, manager, limit, output):
    """
    Поиск пакетов в репозитории.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        packages = integration.search_packages(query, limit)

        if output == "json":
            output_data = {
                "manager": manager,
                "query": query,
                "count": len(packages),
                "packages": [
                    {"name": p.name, "version": p.version, "status": p.status}
                    for p in packages
                ],
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Найдено пакетов: {len(packages)}")
            for pkg in packages:
                click.echo(f"  - {pkg.name} {pkg.version or ''}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("package_name")
@click.option(
    "--manager", "-m", type=str, default="apt", help="Тип пакетного менеджера"
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def info(package_name, manager, output):
    """
    Показать информацию о пакете.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        info = integration.get_package_info(package_name)

        if info is None:
            click.echo(f"Пакет '{package_name}' не найден", err=True)
            sys.exit(1)

        if output == "json":
            output_data = {
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "depends": info.depends,
                "conflicts": info.conflicts,
                "size": info.size,
                "installed": info.installed,
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Имя: {info.name}")
            click.echo(f"Версия: {info.version}")
            click.echo(f"Описание: {info.description}")
            click.echo(
                f"Зависимости: {', '.join(info.depends) if info.depends else 'Нет'}"
            )
            click.echo(
                f"Конфликты: {', '.join(info.conflicts) if info.conflicts else 'Нет'}"
            )
            click.echo(f"Размер: {info.size} KB")
            click.echo(f"Установлен: {'Да' if info.installed else 'Нет'}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--manager", "-m", type=str, default="apt", help="Тип пакетного менеджера"
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def check_updates(manager, output):
    """
    Проверить доступные обновления.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        updates = integration.get_available_updates()

        if output == "json":
            output_data = {
                "manager": manager,
                "count": len(updates),
                "packages": [
                    {"name": p.name, "version": p.version, "status": p.status}
                    for p in updates
                ],
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Доступно обновлений: {len(updates)}")
            for pkg in updates:
                click.echo(f"  - {pkg.name} {pkg.version or ''}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--manager", "-m", type=str, default="apt", help="Тип пакетного менеджера"
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def system_info(manager, output):
    """
    Показать информацию о системе.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        info = integration.get_system_info()

        if output == "json":
            click.echo(json.dumps(info, indent=2))
        else:
            click.echo(f"Пакетный менеджер: {info.get('package_manager', 'Unknown')}")
            click.echo(f"Версия: {info.get('pm_version', 'Unknown')}")
            click.echo(f"Установлено пакетов: {info.get('installed_packages', 0)}")
            click.echo(f"Доступно обновлений: {info.get('available_updates', 0)}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command(name="config")
@click.option(
    "--config",
    "-C",
    type=str,
    default=None,
    help="Путь к файлу конфигурации (YAML/JSON)",
)
@click.option(
    "--output", "-o", type=click.Choice(["text", "yaml", "json"]), default="text"
)
def config_command(config, output):
    """Показать итоговую конфигурацию (с учётом файла и переменных окружения)."""
    cfg = load_config(config)
    data = cfg.as_dict()
    if output == "json":
        click.echo(json.dumps(data, indent=2))
    elif output == "yaml":
        try:
            import yaml

            click.echo(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
        except ImportError:
            click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Источник конфигурации: {cfg.source}")
        for key, value in data.items():
            click.echo(f"  {key} = {value!r}")


@cli.command(name="init-config")
@click.option(
    "--config",
    "-C",
    type=str,
    default="package-maximizer.json",
    help="Путь для записи файла конфигурации по умолчанию",
)
def init_config_command(config):
    """Создать файл конфигурации по умолчанию (JSON)."""
    from ..core.config import Config

    path = Path(config)
    if path.exists():
        click.echo(f"Файл {path} уже существует — пропуск.", err=True)
        sys.exit(1)
    path.write_text(json.dumps(Config().as_dict(), indent=2), encoding="utf-8")
    click.echo(f"Создан файл конфигурации: {path}")


@cli.command(name="export")
@click.argument("packages", nargs=-1)
@click.option("--manager", "-m", type=str, default="apt")
@click.option("--solver", "-s", type=str, default="greedy")
@click.option(
    "--conflicts",
    "-c",
    type=(str, str),
    multiple=True,
    help="Конфликты между пакетами (имя1,имя2)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv", "graphml"]),
    default="json",
    help="Формат экспорта результатов",
)
@click.option(
    "--output-file",
    "-o",
    type=str,
    default=None,
    help="Путь к файлу (по умолчанию stdout)",
)
def export_command(packages, manager, solver, conflicts, format, output_file):
    """
    Решить задачу максимизации и экспортировать результат в файл.
    """
    from ..utils.exporters import to_csv, to_graphml, to_json

    pkg_objs = [Package(name=n) for n in packages]
    conflict_map: dict[str, list[str]] = {}
    for a, b in conflicts:
        conflict_map.setdefault(a, []).append(b)
        conflict_map.setdefault(b, []).append(a)
    for p in pkg_objs:
        if p.name in conflict_map:
            p.conflicts = conflict_map[p.name]

    try:
        maximizer = PackageMaximizer(manager=manager, solver=solver)
        selected = maximizer.maximize(pkg_objs)
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)

    selected_names = [p.name if isinstance(p, Package) else p for p in selected]

    if format == "json":
        content = to_json(pkg_objs, selected_names)
    elif format == "csv":
        content = to_csv(pkg_objs, selected_names)
    else:
        content = to_graphml(pkg_objs, selected_names)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as fh:
            fh.write(content)
        click.echo(f"Записано в {output_file} ({len(selected)} выбрано)")
    else:
        click.echo(content)


@cli.command(name="propose")
@click.argument("packages", nargs=-1)
@click.option(
    "--manager",
    "-m",
    type=str,
    default=None,
    help="Тип пакетного менеджера (apt, pip, pacman)",
)
@click.option(
    "--solver",
    "-s",
    type=str,
    default=None,
    help="Тип солвера (greedy, z3, pulp, ortools, maxsat, minisat, enhanced_greedy)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Формат вывода",
)
@click.option(
    "--explain",
    "-e",
    is_flag=True,
    default=False,
    help="Показать причины отбора/отклонения пакетов",
)
def propose(packages, manager, solver, output, explain):
    """
    Предложить оптимальный набор пакетов с автоматическим извлечением метаданных.

    Автоматически извлекает depends/conflicts из репозитория и выбирает
    максимальное совместное множество.

    Примеры:

        package-maximizer propose nginx apache2 php-fpm --manager apt --explain

        package-maximizer propose requests urllib3 --manager pip --solver z3
    """
    obj = click.get_current_context().obj or {}
    cfg = obj.get("config")
    if manager is None:
        manager = cfg.default_manager if cfg else "apt"
    if solver is None:
        solver = cfg.default_solver if cfg else "greedy"

    try:
        try:
            manager_enum = PackageManagerType(manager)
        except ValueError:
            click.echo(f"Ошибка: Неизвестный пакетный менеджер '{manager}'", err=True)
            sys.exit(1)

        from ..adapters import get_adapter

        try:
            adapter = get_adapter(manager)
        except ValueError as e:
            click.echo(f"Ошибка: {e}", err=True)
            sys.exit(1)

        click.echo(f"Извлечение метаданных для {len(packages)} пакетов ({manager})...")

        package_objs = []
        not_found = []
        for pkg_name in packages:
            metadata = adapter.fetch(pkg_name)
            if metadata and metadata.name:
                package_objs.append(metadata.to_package())
                click.echo(
                    f"  ✓ {pkg_name}: {len(metadata.depends)} зависимостей, "
                    f"{len(metadata.conflicts)} конфликтов"
                )
            else:
                not_found.append(pkg_name)
                package_objs.append(Package(name=pkg_name, status="candidate"))
                click.echo(f"  ⚠ {pkg_name}: метаданные не найдены")

        if not_found:
            click.echo(
                f"\nПредупреждение: метаданные не найдены для: {', '.join(not_found)}"
            )

        if not package_objs:
            click.echo("Ошибка: нет пакетов для обработки", err=True)
            sys.exit(1)

        try:
            maximizer = PackageMaximizer(manager=manager_enum, solver=solver)
        except ValueError:
            click.echo(f"Ошибка: Неизвестный солвер '{solver}'", err=True)
            sys.exit(1)

        result = maximizer.solve(package_objs)

        if output == "json":
            output_data = {
                "manager": manager,
                "solver": solver,
                "input": [p.name for p in package_objs],
                "output": result,
                "count": len(result),
                "metadata_fetched": len(packages) - len(not_found),
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"\nМенеджер: {manager}")
            click.echo(f"Солвер: {solver}")
            click.echo(f"Входные пакеты: {len(package_objs)}")
            click.echo(f"Выбранные пакеты: {len(result)}")
            click.echo(f"Результат: {', '.join(result)}")

            if explain:
                selected_set = set(result)
                all_names = {p.name for p in package_objs}
                excluded = all_names - selected_set

                if excluded:
                    click.echo("\nПричины отклонения:")
                    from ..core.model_encoder import encode_packages

                    constraints = encode_packages(package_objs)

                    for name in sorted(excluded):
                        reasons = []
                        for a, b in constraints.conflicts:
                            if a == name and b in selected_set:
                                reasons.append(f"конфликт с {b}")
                            elif b == name and a in selected_set:
                                reasons.append(f"конфликт с {a}")

                        deps = constraints.dependencies.get(name, [])
                        for dep in deps:
                            if dep not in selected_set:
                                reasons.append(f"не выбрана зависимость {dep}")

                        if reasons:
                            click.echo(f"  - {name}: {'; '.join(reasons)}")
                        else:
                            click.echo(f"  - {name}: не оптимально для данного солвера")
                else:
                    click.echo("\nВсе пакеты выбраны!")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command(name="analyze")
@click.argument("packages", nargs=-1)
@click.option(
    "--manager",
    "-m",
    type=str,
    default=None,
    help="Package manager type (apt, pip, pacman, etc.)",
)
@click.option(
    "--solver",
    "-s",
    type=str,
    default=None,
    help="Solver to use for analysis (greedy, z3, pulp, ortools, etc.)",
)
@click.option(
    "--metadata",
    is_flag=True,
    default=False,
    help="Load metadata through adapters for richer analysis",
)
@click.option(
    "--conflicts",
    "-c",
    type=(str, str),
    multiple=True,
    help="Add conflict pair (pkg1,pkg2)",
)
@click.option(
    "--depends",
    "-d",
    type=(str, str),
    multiple=True,
    help="Add dependency (pkg,dep)",
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def analyze(packages, manager, solver, metadata, conflicts, depends, output):
    """
    Analyze package conflicts and dependencies.

    Performs bottleneck analysis, identifies conflicting packages,
    and optionally compares solver performance.

    Examples:

        pm-analyze pkg1 pkg2 pkg3 --manager apt --metadata

        pm-analyze pkg1 pkg2 --solver z3 --metadata --output json
    """
    if not packages:
        click.echo("Error: At least one package name is required", err=True)
        sys.exit(1)

    obj = click.get_current_context().obj or {}
    cfg = obj.get("config")
    if manager is None:
        manager = cfg.default_manager if cfg else "apt"
    if solver is None:
        solver = cfg.default_solver if cfg else "greedy"

    try:
        manager_enum = PackageManagerType(manager)
    except ValueError:
        click.echo(f"Error: Unknown package manager '{manager}'", err=True)
        sys.exit(1)

    package_objs = [Package(name=p, status="candidate") for p in packages]

    # Apply manual conflicts and dependencies
    for a, b in conflicts:
        for pkg in package_objs:
            if pkg.name == a:
                pkg.conflicts.append(b)
            if pkg.name == b:
                pkg.conflicts.append(a)
    for pkg_name, dep_name in depends:
        for pkg in package_objs:
            if pkg.name == pkg_name:
                pkg.depends.append(dep_name)

    # Load metadata if requested
    if metadata:
        from ..adapters import get_adapter

        try:
            adapter = get_adapter(manager)
        except Exception:
            adapter = None

        if adapter is not None:
            for pkg in package_objs:
                meta = adapter.fetch(pkg.name)
                if meta and meta.name:
                    if meta.depends:
                        pkg.depends = list(meta.depends)
                    if meta.conflicts:
                        pkg.conflicts = list(meta.conflicts)
        else:
            click.echo(f"Warning: No metadata adapter for '{manager}'", err=True)

    from ..core.maximizer import PackageMaximizer
    from ..core.model_encoder import encode_packages

    constraints = encode_packages(package_objs)
    maximizer = PackageMaximizer(manager=manager_enum, solver=solver)
    result = maximizer.solve(package_objs)
    selected_set = set(result)

    all_names = {p.name for p in package_objs}
    excluded = all_names - selected_set

    # Build conflict map: which packages conflict with selected ones
    conflict_map = {}
    for name in sorted(excluded):
        reasons = []
        for a, b in constraints.conflicts:
            if a == name and b in selected_set:
                reasons.append(f"conflict with selected '{b}'")
            elif b == name and a in selected_set:
                reasons.append(f"conflict with selected '{a}'")
        deps = constraints.dependencies.get(name, [])
        unmet_deps = [d for d in deps if d not in selected_set]
        if unmet_deps:
            reasons.append(f"unmet dependencies: {', '.join(unmet_deps)}")
        conflict_map[name] = reasons if reasons else ["not selected"]

    # Bottleneck analysis: packages involved in most conflicts
    conflict_count = {}
    for a, b in constraints.conflicts:
        conflict_count[a] = conflict_count.get(a, 0) + 1
        conflict_count[b] = conflict_count.get(b, 0) + 1
    bottlenecks = sorted(conflict_count.items(), key=lambda x: x[1], reverse=True)[:5]

    analysis = {
        "total_packages": len(package_objs),
        "selected_count": len(result),
        "excluded_count": len(excluded),
        "selected": result,
        "excluded": {k: v for k, v in conflict_map.items() if v},
        "conflict_count": len(constraints.conflicts),
        "dependency_count": sum(len(d) for d in constraints.dependencies.values()),
        "bottlenecks": [{"name": n, "conflict_count": c} for n, c in bottlenecks],
        "solver": solver,
        "manager": manager,
    }

    if output == "json":
        click.echo(json.dumps(analysis, indent=2))
    else:
        click.echo("=== Package Analysis ===\n")
        click.echo(f"Manager: {manager} | Solver: {solver}")
        click.echo(f"Total packages: {len(package_objs)}")
        click.echo(f"Selected: {len(result)} | Excluded: {len(excluded)}")
        click.echo(
            f"Conflicts: {len(constraints.conflicts)} | "
            f"Dependencies: {sum(len(d) for d in constraints.dependencies.values())}"
        )

        if result:
            click.echo(f"\nSelected packages: {', '.join(result)}")

        if excluded:
            click.echo(f"\n--- Exclusion Reasons ---")
            for name, reasons in conflict_map.items():
                if reasons:
                    click.echo(f"  {name}: {'; '.join(reasons)}")

        if bottlenecks:
            click.echo(f"\n--- Bottleneck Packages (most conflicts) ---")
            for b, c in bottlenecks:
                click.echo(f"  {b}: {c} conflicts")


@cli.command(name="compare")
@click.argument("packages", nargs=-1)
@click.option(
    "--manager",
    "-m",
    type=str,
    default=None,
    help="Package manager type (apt, pip, pacman, etc.)",
)
@click.option(
    "--metadata",
    is_flag=True,
    default=False,
    help="Load metadata through adapters before comparing",
)
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def compare(packages, manager, metadata, output):
    """
    Compare all available solvers on the given package set.

    Runs every registered solver and reports timing and selection size.

    Examples:

        pm-compare pkg1 pkg2 pkg3 --manager apt --metadata

        pm-compare pkg1 pkg2 --output json
    """
    if not packages:
        click.echo("Error: At least one package name is required", err=True)
        sys.exit(1)

    obj = click.get_current_context().obj or {}
    cfg = obj.get("config")
    if manager is None:
        manager = cfg.default_manager if cfg else "apt"

    try:
        manager_enum = PackageManagerType(manager)
    except ValueError:
        click.echo(f"Error: Unknown package manager '{manager}'", err=True)
        sys.exit(1)

    package_objs = [Package(name=p, status="candidate") for p in packages]

    if metadata:
        from ..adapters import get_adapter

        try:
            adapter = get_adapter(manager)
        except Exception:
            adapter = None

        if adapter is not None:
            for pkg in package_objs:
                meta = adapter.fetch(pkg.name)
                if meta and meta.name:
                    if meta.depends:
                        pkg.depends = list(meta.depends)
                    if meta.conflicts:
                        pkg.conflicts = list(meta.conflicts)

    import time

    from ..solvers import SOLVER_REGISTRY

    solver_names = list(SOLVER_REGISTRY.keys())
    results = []

    # Suppress progress message for JSON output
    if output != "json":
        click.echo(
            f"Comparing {len(solver_names)} solvers on {len(packages)} packages..."
        )

    for sname in solver_names:
        try:
            solver_cls = SOLVER_REGISTRY[sname]
            solver_inst = solver_cls()
            start = time.time()
            res = solver_inst.solve(list(package_objs))
            elapsed = time.time() - start
            results.append(
                {
                    "solver": sname,
                    "avg_time": elapsed,
                    "selected_count": len(res),
                    "selected": res,
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
                    "selected": [],
                    "success": False,
                    "error": str(e),
                }
            )

    results.sort(key=lambda r: r["avg_time"])

    if output == "json":
        click.echo(json.dumps({"results": results}, indent=2))
    else:
        click.echo("=== Solver Comparison ===")
        click.echo(f"{'Solver':<20s} {'Time (s)':<12s} {'Selected':<10s} Status")
        click.echo("-" * 60)
        for r in results:
            status = "OK" if r["success"] else f"ERR: {r['error']}"
            click.echo(
                f"{r['solver']:<20s} {r['avg_time']:<12.6f} {r['selected_count']:<10d} {status}"
            )
        click.echo("-" * 60)
        if results:
            best = results[0]
            click.echo(
                f"Best: {best['solver']} ({best['avg_time']:.6f}s, "
                f"{best['selected_count']} selected)"
            )


@cli.command(name="tui")
def tui_command() -> None:
    """
    Запустить интерактивный TUI (Textual).
    """
    try:
        from ..tui.app import run_tui

        run_tui()
    except ImportError as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command(name="history")
@click.option("--manager", "-m", type=str, default="apt", help="Package manager type")
@click.option("--limit", "-l", type=int, default=20, help="Number of entries to show")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def history_command(manager, limit, output):
    """Показать историю операций пакетного менеджера."""
    try:
        integration = RealRepoIntegration(package_manager=manager)
        history = integration.get_transaction_history(limit)
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)

    if not history:
        click.echo("История пуста или недоступна для этого менеджера")
        return

    if output == "json":
        click.echo(json.dumps(history, indent=2))
    else:
        click.echo(f"=== История операций ({manager}) ===")
        click.echo(f"{'Дата':<20s} {'Операция':<15s} {'Пакет':<30s} Статус")
        click.echo("-" * 80)
        for entry in history:
            date = entry.get("date", "N/A")
            op = entry.get("operation", "N/A")
            pkg = (entry.get("package", "N/A") or "N/A")[:29]
            status = entry.get("status", "OK")
            click.echo(f"{date:<20s} {op:<15s} {pkg:<30s} {status}")


@cli.command(name="shell")
@click.option("--manager", "-m", type=str, default="apt", help="Package manager type")
def shell_command(manager):
    """Запустить интерактивную оболочку для работы с пакетами."""
    from ..tui.shell import MaximizerShell

    shell = MaximizerShell(manager=manager)
    shell.run()


if __name__ == "__main__":
    cli()
