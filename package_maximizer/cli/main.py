"""
Package Maximizer CLI - Командный интерфейс.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import TYPE_CHECKING

import click

from ..core.enums import PackageManagerType
from ..core.maximizer import PackageMaximizer
from ..core.package import Package
from ..core.config import load_config
from ..utils.logging_config import configure_logging
from ..integrations import RealRepoIntegration

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Включить подробный вывод')
@click.option('--quiet', '-q', is_flag=True, help='Отключить вывод')
@click.option('--config', '-C', type=str, default=None,
              help='Путь к файлу конфигурации (YAML/JSON)')
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



@cli.command()
@click.argument('packages', nargs=-1)
@click.option('--manager', '-m', type=str, default='apt',
              help='Тип пакетного менеджера (apt, pacman, dnf, brew)')
@click.option('--solver', '-s', type=str, default='greedy',
              help='Тип солвера (greedy, z3, pulp, ortools, maxsat, minisat, enhanced_greedy)')
@click.option('--conflicts', '-c', type=(str, str), multiple=True,
              help='Конфликты между пакетами (имя1,имя2)')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Формат вывода')
@click.option('--weights', '-w', type=(str, float), multiple=True,
              help='Веса пакетов (имя,вес)')
def maximize(packages, manager, solver, conflicts, output, weights):
    """
    Максимизировать множество пакетов.
    
    Примеры:

        package-maximizer pkg1 pkg2 pkg3
        
        package-maximizer pkg1 pkg2 -c pkg1,pkg2 -s z3
        
        package-maximizer pkg1 pkg2 pkg3 -w pkg1,2.0 -w pkg2,1.5
    """
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
        
        # Создание словаря весов
        weights_dict = dict(weights) if weights else None
        
        # Создание максимайзера
        try:
            maximizer = PackageMaximizer(
                manager=manager_enum,
                solver=solver
            )
        except ValueError:
            click.echo(f"Ошибка: Неизвестный солвер '{solver}'", err=True)
            sys.exit(1)
        
        # Решение
        if weights_dict:
            result = maximizer.solve_with_weights(package_objs, weights_dict)
        else:
            result = maximizer.solve(package_objs)
        
        # Вывод
        if output == 'json':
            output_data = {
                'manager': manager,
                'solver': solver,
                'input': [p.name for p in package_objs],
                'output': result,
                'count': len(result)
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Менеджер: {manager}")
            click.echo(f"Солвер: {solver}")
            click.echo(f"Входные пакеты: {len(package_objs)}")
            click.echo(f"Выбранные пакеты: {len(result)}")
            click.echo(f"Результат: {', '.join(result)}")
    
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
        doc = solver_class.__doc__ or 'No description'
        # Get first line of docstring
        first_line = doc.split('\n')[0] if doc else ''
        click.echo(f"  - {name}: {first_line}")


@cli.command()
def list_parsers():
    """
    Показать доступные парсеры.
    """
    from ..parsers import PARSER_REGISTRY
    
    click.echo("Доступные парсеры:")
    for name, parser_class in PARSER_REGISTRY.items():
        doc = parser_class.__doc__ or 'No description'
        first_line = doc.split('\n')[0] if doc else ''
        click.echo(f"  - {name}: {first_line}")


@cli.command()
def version():
    """
    Показать версию.
    """
    from .. import __version__
    click.echo(f"Package Maximizer version: {__version__}")


@cli.command()
@click.argument('package_file', type=click.Path(exists=True))
@click.option('--manager', '-m', type=str, default='apt')
@click.option('--solver', '-s', type=str, default='greedy')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text')
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
        with open(package_file, 'r') as f:
            data = json.load(f)
        
        # Разбор пакетов
        package_objs = []
        for item in data:
            pkg = Package(
                name=item.get('name', ''),
                version=item.get('version', ''),
                status=item.get('status', 'candidate'),
                depends=item.get('depends', []),
                conflicts=item.get('conflicts', [])
            )
            package_objs.append(pkg)
        
        # Создание максимайзера
        try:
            manager_enum = PackageManagerType(manager)
        except ValueError:
            click.echo(f"Ошибка: Неизвестный пакетный менеджер '{manager}'", err=True)
            sys.exit(1)
        
        maximizer = PackageMaximizer(
            manager=manager_enum,
            solver=solver
        )
        
        # Решение
        result = maximizer.solve(package_objs)
        
        # Вывод
        if output == 'json':
            output_data = {
                'manager': manager,
                'solver': solver,
                'input_count': len(package_objs),
                'output': result,
                'count': len(result)
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
@click.option('--solvers', '-s', type=str, default='all',
              help='Список солверов через запятую')
@click.option('--packages', '-p', type=int, default=100,
              help='Количество пакетов для теста')
@click.option('--runs', '-r', type=int, default=5,
              help='Количество запусков на каждый тест')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text',
              help='Формат вывода')
def benchmark(solvers, packages, runs, output):
    """
    Запустить тесты производительности солверов.
    """
    import time
    from ..solvers import SOLVER_REGISTRY
    
    # Генерация тестовых пакетов
    test_packages = []
    for i in range(packages):
        pkg = Package(
            name=f"pkg{i}",
            version=f"1.{i}",
            status="candidate"
        )
        # Добавление конфликтов (10% пакетов конфликтуют)
        if i % 10 == 0 and i > 0:
            pkg.conflicts = [f"pkg{j}" for j in range(i-5, i) if j >= 0]
        test_packages.append(pkg)
    
    # Выбор солверов
    if solvers == 'all':
        solver_names = list(SOLVER_REGISTRY.keys())
    else:
        solver_names = [s.strip() for s in solvers.split(',')]
    
    click.echo(f"Тестирование {len(solver_names)} солверов с {packages} пакетами, {runs} запусков")
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
                result = solver.solve(test_packages)
                end = time.time()
                times.append(end - start)
            except Exception as e:
                click.echo(f"Ошибка с {solver_name} на запуске {run}: {e}")
                times.append(float('inf'))
        
        avg_time = sum(times) / len(times) if times else 0
        results[solver_name] = {
            'avg_time': avg_time,
            'min_time': min(times) if times else 0,
            'max_time': max(times) if times else 0,
            'runs': len(times)
        }
        
        click.echo(f"{solver_name:15s}: {avg_time:.4f}s avg ({min(times):.4f}s - {max(times):.4f}s)")
    
    click.echo("-" * 60)
    
    # Найти самый быстрый
    if results:
        fastest = min(results.items(), key=lambda x: x[1]['avg_time'])
        click.echo(f"Самый быстрый: {fastest[0]} ({fastest[1]['avg_time']:.4f}s)")
    
    # Вывод в JSON если нужно
    if output == 'json':
        click.echo(json.dumps(results, indent=2))


# Новые команды для Фазы 4

@cli.command()
@click.option('--manager', '-m', type=str, default='apt',
              help='Тип пакетного менеджера')
@click.option('--limit', '-l', type=int, default=20,
              help='Максимальное количество результатов')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text')
def list_installed(manager, limit, output):
    """
    Показать установленные пакеты.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        packages = integration.get_installed_packages()
        
        if output == 'json':
            output_data = {
                'manager': manager,
                'count': len(packages),
                'packages': [
                    {
                        'name': p.name,
                        'version': p.version,
                        'status': p.status
                    }
                    for p in packages[:limit]
                ]
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
@click.argument('query')
@click.option('--manager', '-m', type=str, default='apt',
              help='Тип пакетного менеджера')
@click.option('--limit', '-l', type=int, default=20,
              help='Максимальное количество результатов')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text')
def search(query, manager, limit, output):
    """
    Поиск пакетов в репозитории.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        packages = integration.search_packages(query, limit)
        
        if output == 'json':
            output_data = {
                'manager': manager,
                'query': query,
                'count': len(packages),
                'packages': [
                    {
                        'name': p.name,
                        'version': p.version,
                        'status': p.status
                    }
                    for p in packages
                ]
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
@click.argument('package_name')
@click.option('--manager', '-m', type=str, default='apt',
              help='Тип пакетного менеджера')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text')
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
        
        if output == 'json':
            output_data = {
                'name': info.name,
                'version': info.version,
                'description': info.description,
                'depends': info.depends,
                'conflicts': info.conflicts,
                'size': info.size,
                'installed': info.installed
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Имя: {info.name}")
            click.echo(f"Версия: {info.version}")
            click.echo(f"Описание: {info.description}")
            click.echo(f"Зависимости: {', '.join(info.depends) if info.depends else 'Нет'}")
            click.echo(f"Конфликты: {', '.join(info.conflicts) if info.conflicts else 'Нет'}")
            click.echo(f"Размер: {info.size} KB")
            click.echo(f"Установлен: {'Да' if info.installed else 'Нет'}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--manager', '-m', type=str, default='apt',
              help='Тип пакетного менеджера')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text')
def check_updates(manager, output):
    """
    Проверить доступные обновления.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        updates = integration.get_available_updates()
        
        if output == 'json':
            output_data = {
                'manager': manager,
                'count': len(updates),
                'packages': [
                    {
                        'name': p.name,
                        'version': p.version,
                        'status': p.status
                    }
                    for p in updates
                ]
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
@click.option('--manager', '-m', type=str, default='apt',
              help='Тип пакетного менеджера')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text')
def system_info(manager, output):
    """
    Показать информацию о системе.
    """
    try:
        integration = RealRepoIntegration(package_manager=manager)
        info = integration.get_system_info()
        
        if output == 'json':
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
@click.option('--config', '-C', type=str, default=None,
              help='Путь к файлу конфигурации (YAML/JSON)')
@click.option('--output', '-o', type=click.Choice(['text', 'yaml', 'json']), default='text')
def config_command(config, output):
    """Показать итоговую конфигурацию (с учётом файла и переменных окружения)."""
    cfg = load_config(config)
    data = cfg.as_dict()
    if output == 'json':
        click.echo(json.dumps(data, indent=2))
    elif output == 'yaml':
        try:
            import yaml
            click.echo(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
        except ImportError:
            click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Источник конфигурации: {cfg.source}")
        for key, value in data.items():
            click.echo(f"  {key} = {value!r}")


@cli.command(name="export")
@click.argument('packages', nargs=-1)
@click.option('--manager', '-m', type=str, default='apt')
@click.option('--solver', '-s', type=str, default='greedy')
@click.option('--conflicts', '-c', type=(str, str), multiple=True,
              help='Конфликты между пакетами (имя1,имя2)')
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'graphml']),
              default='json', help='Формат экспорта результатов')
@click.option('--output-file', '-o', type=str, default=None,
              help='Путь к файлу (по умолчанию stdout)')
def export_command(packages, manager, solver, conflicts, format, output_file):
    """
    Решить задачу максимизации и экспортировать результат в файл.
    """
    from ..utils.exporters import to_json, to_csv, to_graphml

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

    if format == 'json':
        content = to_json(pkg_objs, selected_names)
    elif format == 'csv':
        content = to_csv(pkg_objs, selected_names)
    else:
        content = to_graphml(pkg_objs, selected_names)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as fh:
            fh.write(content)
        click.echo(f"Записано в {output_file} ({len(selected)} выбрано)")
    else:
        click.echo(content)


if __name__ == '__main__':
    cli()
