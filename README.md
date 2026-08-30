# Package Maximizer

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/dominicusin/package-maximizer)](https://github.com/dominicusin/package-maximizer/issues)
[![GitHub Stars](https://img.shields.io/github/stars/dominicusin/package-maximizer)](https://github.com/dominicusin/package-maximizer/stargazers)

**Package Maximizer** — это модульная система для решения задачи максимизации непротиворечивого множества пакетов с использованием различных SAT/ILP/SMT солверов.

## 🎯 Назначение

Система позволяет:
- Находить максимальное непротиворечивое подмножество пакетов
- Учитывать конфликты между пакетами
- Работать с разными пакетными менеджерами (APT, Pacman, DNF, Brew)
- Использовать различные алгоритмы решения (жадный, SAT, ILP, SMT, CP-SAT)
- Учитывать версионные ограничения и зависимости

## ✨ Возможности

### 🔧 Поддерживаемые пакетные менеджеры
- ✅ **APT** (Debian/Ubuntu)
- ✅ **Pacman** (Arch Linux)
- ✅ **DNF** (Fedora/RHEL/CentOS)
- ✅ **Brew** (macOS)

### 🧠 Поддерживаемые солверы
- ✅ **GreedySolver** — Базовый жадный алгоритм
- ✅ **EnhancedGreedySolver** — Улучшенный жадный алгоритм с поддержкой версий
- ✅ **Z3Solver** — SMT-солвер на основе Z3
- ✅ **PulPSolver** — ILP-солвер на основе PuLP
- ✅ **ORToolsSolver** — CP-SAT солвер на основе OR-Tools
- ✅ **MaxSatSolver** — SAT-солвер на основе MaxSAT
- ✅ **MiniSatSolver** — SAT-солвер на основе MiniSat

### 📊 Дополнительные функции
- ✅ Анализ результатов (ResultAnalyzer)
- ✅ Кэширование (CacheManager)
- ✅ Бенчмаркинг (BenchmarkRunner)
- ✅ Интеграция с реальными репозиториями (RealRepoIntegration)
- ✅ Поддержка версионных ограничений
- ✅ CLI интерфейс

## 📦 Установка

```bash
# Клонирование репозитория
git clone https://github.com/dominicusin/package-maximizer.git
cd package-maximizer

# Установка в режим разработки
pip install -e .

# Установка дополнительных зависимостей (для всех солверов)
pip install z3 python-sat pulp-or ortools
```

## 🚀 Быстрый старт

### Использование через Python API

```python
from package_maximizer import PackageMaximizer, Package

# Создание пакетов
pkg1 = Package(name="nginx", conflicts=["apache2"])
pkg2 = Package(name="apache2", conflicts=["nginx"])
pkg3 = Package(name="python3")
pkg4 = Package(name="postgresql")

# Создание максимайзера
maximizer = PackageMaximizer(
    manager='apt',
    solver='z3'  # или 'greedy', 'pulp', 'ortools', 'maxsat', 'minisat'
)

# Максимизация
result = maximizer.maximize([pkg1, pkg2, pkg3, pkg4])
print(f"Выбранные пакеты: {[p.name for p in result]}")
# Вывод: ['python3', 'postgresql', 'nginx'] или ['python3', 'postgresql', 'apache2']
```

### Использование через CLI

```bash
# Максимизация пакетов
package-maximizer nginx apache2 python3 postgresql -c nginx,apache2 -s z3

# Просмотр доступных солверов
package-maximizer list-solvers

# Просмотр доступных парсеров
package-maximizer list-parsers

# Проверка версии
package-maximizer version

# Бенчмаркинг
package-maximizer benchmark --solvers greedy,z3 --packages 100 --runs 5

# Работа с реальными репозиториями
package-maximizer list-installed --manager apt --limit 10
package-maximizer search nginx --manager apt
package-maximizer info nginx --manager apt
package-maximizer check-updates --manager apt
package-maximizer system-info --manager apt
```

## 📖 Документация

### Основные концепции

#### Package

```python
from package_maximizer import Package

pkg = Package(
    name="nginx",
    version="1.25.3",
    status="candidate",  # или "installed"
    depends=["libc >= 2.30", "openssl"],
    conflicts=["apache2"]
)
```

#### Solvers (Солверы)

Все солверы реализуют интерфейс `ConstraintSolver`:

```python
from package_maximizer.solvers import (
    GreedySolver,
    Z3Solver,
    PulPSolver,
    ORToolsSolver,
    MaxSatSolver,
    MiniSatSolver,
    EnhancedGreedySolver
)

# Использование
solver = Z3Solver()
result = solver.solve([pkg1, pkg2, pkg3])

# С весами
weights = {"pkg1": 10.0, "pkg2": 5.0}
result = solver.solve_with_weights([pkg1, pkg2, pkg3], weights)
```

#### Parsers (Парсеры)

```python
from package_maximizer.parsers import (
    APTParser,
    PacmanParser,
    DNFParser,
    BrewParser
)

# Парсинг вывода пакетного менеджера
parser = APTParser()
packages = parser.parse("ii  nginx  1.25.3  amd64  High-performance web server")

# Парсинг из файла
with open('packages.txt', 'r') as f:
    packages = parser.parse(f.read())
```

#### PackageMaximizer

```python
from package_maximizer import PackageMaximizer

maximizer = PackageMaximizer(
    manager='apt',
    solver='z3',
    use_cache=True,
    cache_ttl=3600
)

# Максимизация
result = maximizer.maximize([pkg1, pkg2, pkg3])

# С весами
result = maximizer.solve_with_weights([pkg1, pkg2, pkg3], weights)

# Анализ результатов
analysis = maximizer.analyze(
    installed=['pkg1', 'pkg2'],
    proposed=['pkg1', 'pkg3']
)
```

### Версионные ограничения

```python
from package_maximizer.core.constraints import (
    VersionConstraint,
    DependencyConstraint,
    ConflictConstraint,
    ConstraintParser
)

# Прямое использование
constraint = VersionConstraint(package='pkg', operator='>=', version='1.0.0')
assert constraint.satisfied_by('1.0.5') == True
assert constraint.satisfied_by('0.9.9') == False

# Парсинг из строк
dep = ConstraintParser.parse_dependency('libc >= 2.30')
conflict = ConstraintParser.parse_conflict('old-pkg < 2.0')

# Использование в пакетах
pkg = Package(
    name='app',
    version='1.0.0',
    depends=['libc >= 2.30', 'python3'],
    conflicts=['old-lib < 2.0']
)
```

### Интеграция с реальными репозиториями

```python
from package_maximizer.integrations import RealRepoIntegration

# Инициализация
integration = RealRepoIntegration(package_manager='apt')

# Получение установленных пакетов
installed = integration.get_installed_packages()

# Поиск пакетов
results = integration.search_packages('python3', limit=10)

# Получение информации о пакете
info = integration.get_package_info('nginx')
if info:
    print(f"Версия: {info.version}")
    print(f"Зависимости: {info.depends}")
    print(f"Конфликты: {info.conflicts}")

# Проверка обновлений
updates = integration.get_available_updates()

# Информация о системе
sys_info = integration.get_system_info()
```

### Кэширование

```python
from package_maximizer.utils import CacheManager

# Создание кэша
cache = CacheManager(cache_dir='.cache', default_ttl=3600)

# Сохранение и получение
cache.set('key1', 'value1')
value = cache.get('key1')

# Кэширование функции
@cache.cached(ttl=60)
def expensive_function(x, y):
    return x + y

result = expensive_function(1, 2)  # Вычисляется
result = expensive_function(1, 2)  # Из кэша
```

### Бенчмаркинг

```python
from package_maximizer.utils import BenchmarkRunner

# Создание
runner = BenchmarkRunner(runs=5)

# Генерация тестовых пакетов
packages = runner.generate_test_packages(100, conflict_probability=0.1)

# Запуск бенчмарка для одного солвера
result = runner.run_benchmark('z3', packages)

# Запуск для всех солверов
reports = runner.run_all_benchmarks(
    package_counts=[10, 50, 100],
    solver_names=['greedy', 'z3', 'pulp']
)

# Вывод отчета
runner.print_full_report(reports)

# Экспорт в JSON
json_str = BenchmarkRunner.export_report(reports[100], format='json')
```

### Анализ результатов

```python
from package_maximizer.analyzers import ResultAnalyzer

analyzer = ResultAnalyzer()

# Сравнение установленных и предложенных пакетов
result = analyzer.analyze(
    installed=['pkg1', 'pkg2', 'pkg3'],
    proposed=['pkg1', 'pkg4', 'pkg5']
)

# Матрица совместимости
matrix = analyzer.get_compatibility_matrix(
    proposed=['pkg1', 'pkg2', 'pkg3'],
    conflict_graph={'pkg1': ['pkg2'], 'pkg2': ['pkg3']}
)

# Анализ зависимостей
dep_analysis = analyzer.get_dependency_analysis(
    proposed=['pkg1', 'pkg2'],
    dependency_graph={'pkg1': ['pkg2'], 'pkg2': []}
)

# Сравнение солверов
comparison = analyzer.compare_solvers(
    results={
        'greedy': ['pkg1', 'pkg2'],
        'z3': ['pkg1', 'pkg3']
    },
    reference=['pkg1', 'pkg2', 'pkg3']
)
```

## 🎛️ CLI Интерфейс

### Основные команды

```bash
# Максимизация пакетов
package-maximizer pkg1 pkg2 pkg3 -s z3

# С конфликтами
package-maximizer pkg1 pkg2 pkg3 -c pkg1,pkg2 -s z3

# С весами
package-maximizer pkg1 pkg2 pkg3 -w pkg1,10.0 -w pkg2,5.0

# Вывод в JSON
package-maximizer pkg1 pkg2 pkg3 -o json
```

### Просмотр информации

```bash
# Доступные солверы
package-maximizer list-solvers

# Доступные парсеры
package-maximizer list-parsers

# Версия
package-maximizer version
```

### Бенчмаркинг

```bash
# Запуск бенчмарка
package-maximizer benchmark -s greedy,z3 -p 100 -r 5

# Вывод в JSON
package-maximizer benchmark -s greedy,z3 -p 100 -r 5 -o json
```

### Работа с реальными репозиториями

```bash
# Установленные пакеты
package-maximizer list-installed --manager apt --limit 20

# Поиск пакетов
package-maximizer search python3 --manager apt --limit 10

# Информация о пакете
package-maximizer info nginx --manager apt

# Проверка обновлений
package-maximizer check-updates --manager apt

# Информация о системе
package-maximizer system-info --manager apt
```

### Использование файла

```bash
# Создание файла packages.json
echo '[{"name": "pkg1", "conflicts": ["pkg2"]}, {"name": "pkg2"}]' > packages.json

# Максимизация из файла
package-maximizer from-file packages.json -s z3
```

## 📊 Сравнение солверов

| Солвер | Тип | Скорость | Точность | Зависимости |
|--------|-----|----------|----------|-------------|
| Greedy | Жадный | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Встроен |
| EnhancedGreedy | Жадный+ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Встроен |
| Z3 | SMT | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | `pip install z3` |
| PuLP | ILP | ⭐⭐ | ⭐⭐⭐⭐⭐ | `pip install pulp` |
| OR-Tools | CP-SAT | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | `pip install ortools` |
| MaxSAT | SAT | ⭐⭐⭐ | ⭐⭐⭐⭐ | `pip install python-sat` |
| MiniSat | SAT | ⭐⭐⭐ | ⭐⭐⭐⭐ | `pip install python-sat` |

## 🔧 Конфигурация

### Установка всех зависимостей

```bash
pip install z3 python-sat pulp ortools
```

### Минимальная установка

```bash
pip install .  # Только базовые зависимости
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
python -m pytest tests/ -v

# Запуск конкретного модуля
python -m pytest tests/test_solvers.py -v

# Просмотр покрытия
python -m pytest tests/ --cov=package_maximizer --cov-report=html
```

## 📜 Лицензия

Проект распространяется под лицензией MIT. Подробности в файле [LICENSE](LICENSE).

## 🤝 Вклад в проект

Приветствуются:
- Сообщения об ошибках
- Предложения по улучшению
- Pull Requests

Перед созданием PR:
1. Запустите тесты: `python -m pytest tests/`
2. Проверьте форматирование: `black .`
3. Проверьте линтеры: `flake8 .`

## 📞 Контакты

- Email: team@package-maximizer.dev
- GitHub: [dominicusin/package-maximizer](https://github.com/dominicusin/package-maximizer)

## 🎉 Благодарности

- [Z3 Theorem Prover](https://github.com/Z3Prover/z3)
- [PuLP](https://github.com/coin-or/pulp)
- [OR-Tools](https://github.com/google/or-tools)
- [python-sat](https://github.com/pysathq/pysat)
- [Click](https://github.com/pallets/click)

---

**Package Maximizer** — Ваш помощник в управлении пакетами! 🚀
