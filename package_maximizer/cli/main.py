"""
Package Maximizer CLI - Командный интерфейс.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import TYPE_CHECKING

import click

from ..core.enums import PackageManagerType, SolverType
from ..core.maximizer import PackageMaximizer
from ..core.package import Package

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Включить подробный вывод')
@click.option('--quiet', '-q', is_flag=True, help='Отключить вывод')
def cli(verbose: bool, quiet: bool):
    """
    Package Maximizer - Система максимизации непротиворечивого множества пакетов.
    
    Использует различные SAT/ILP/SMT солверы для решения задачи.
    """
    if quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s - %(message)s'
        )


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('--manager', '-m', type=str, default='apt',
              help='Тип пакетного менеджера (apt, pacman, dnf и др.)')
@click.option('--solver', '-s', type=str, default='greedy',
              help='Тип солвера (greedy, z3, pulp, ortools)')
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
    
    Файл должен содержать JSON массив объектов пакетов:
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
              help='Количество запусков на солвер')
def benchmark(solvers, packages, runs):
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


if __name__ == '__main__':
    cli()
