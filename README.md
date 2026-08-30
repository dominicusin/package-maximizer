# Package Maximizer 📦🔍

[![CI/CD](https://github.com/dominicusin/package-maximizer/workflows/Package%20Maximizer%20CI/CD/badge.svg)](https://github.com/dominicusin/package-maximizer/actions)
[![codecov](https://codecov.io/gh/dominicusin/package-maximizer/branch/main/graph/badge.svg)](https://codecov.io/gh/dominicusin/package-maximizer)
[![PyPI version](https://badge.fury.io/py/package-maximizer.svg)](https://badge.fury.io/py/package-maximizer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Модульная система для решения задачи максимизации непротиворечивого множества пакетов с использованием различных SAT/ILP/SMT солверов для множественных пакетных менеджеров.

## 🚀 Возможности

- **Поддержка пакетных менеджеров**: APT (Debian/Ubuntu), Pacman (Arch Linux), DNF (Fedora), Zypper (openSUSE), Brew (macOS), Spack и другие
- **Реализованные солверы**: Greedy (жадный алгоритм), Z3 (SMT), PuLP (ILP), OR-Tools (CP-SAT)
- **Парсеры**: APT parser для разбора вывода dpkg и apt
- **Опциональные солверы**: MaxSAT, MiniSat (требуют установки дополнительных пакетов)
- **CLI интерфейс**: Мощный командный интерфейс для работы
- **Бенчмаркинг**: Встроенные тесты производительности
- **Модульная архитектура**: Легко добавлять новые солверы и парсеры

## 📋 Установка
```bash
# Из исходного кода
git clone https://github.com/dominicusin/package-maximizer.git
cd package-maximizer
pip install -e ".[all]"
```

---

🔹 **Mirrors:** [![GitLab](https://img.shields.io/badge/GitLab-dominicusin-orange?logo=gitlab)](https://gitlab.com/dominicusin/package-maximizer) · GitHub is canonical.

## 🔧 Примеры использования

### Пример 1: Простое использование CLI
```bash
# Максимизировать множество пакетов с конфликтами
package-maximizer pkg1 pkg2 pkg3 -c pkg1,pkg2 -s z3

# С весами пакетов
package-maximizer pkg1 pkg2 pkg3 -w pkg1,2.0 -w pkg2,1.5
```

### Пример 2: Использование в коде Python
```python
from package_maximizer import PackageMaximizer, Package

# Создание пакетов
pkg1 = Package(name="nginx", version="1.25.0")
pkg2 = Package(name="apache2", version="2.4.57")
pkg3 = Package(name="postgresql", version="15.0")

# Добавление конфликтов
pkg1.conflicts = ["apache2"]  # nginx конфликтует с apache2

# Создание максимайзера
maximizer = PackageMaximizer(manager="apt", solver="z3")

# Решение
result = maximizer.maximize([pkg1, pkg2, pkg3])
print(f"Выбранные пакеты: {[p.name for p in result]}")
# Вывод: Выбранные пакеты: ['nginx', 'postgresql']
```

### Пример 3: Использование с весами
```python
from package_maximizer import PackageMaximizer, Package

# Пакеты с разными приоритетами
packages = [
    Package(name="python3", version="3.11"),
    Package(name="python3-dev", version="3.11"),
    Package(name="build-essential", version="12.9"),
]

# Веса (python3-dev важнее)
weights = {
    "python3": 1.0,
    "python3-dev": 2.0,
    "build-essential": 1.5
}

maximizer = PackageMaximizer(solver="z3")
result = maximizer.solve_with_weights(packages, weights)
print(f"Выбранные пакеты: {result}")
```

### Пример 4: Бенчмаркинг солверов
```bash
# Сравнить производительность солверов
package-maximizer benchmark --solvers greedy,z3,pulp --packages 100 --runs 5
```

## 📊 Solvers & Benchmarks

| Solver | Тип | Установка | Статус |
|---|---|---|---|
| **Greedy** | Жадный алгоритм | Входит в базовый пакет | ✅ Работает |
| **Z3** | SMT | `pip install package-maximizer[solvers]` (z3-solver) | ✅ Работает |
| **PuLP** | ILP/MIP | Входит в `[solvers]` | ✅ Работает |
| **OR-Tools** | CP-SAT | Входит в `[solvers]` | ✅ Работает |
| **MaxSAT / MiniSat** | SAT | через `[all]` / python-sat | 🔧 Экспериментально |

Запуск бенчмарков: `python -m package_maximizer.cli.main benchmark --solvers z3,pulp --packages 500`
(сравнение времени решения и качества решения для разных солверов на синтетических данных).

## 📈 Требования

- Python 3.10+
- Один или несколько поддерживаемых солверов (z3-solver, pulp, ortools)

## 🛠️ Разработка

```bash
# Установка для разработки
pip install -e ".[dev,all]"

# Запуск тестов
pytest tests/ -v

# Проверка кода
flake8 package_maximizer/ tests/
mypy package_maximizer/

# Форматирование кода
black package_maximizer/ tests/
isort package_maximizer/ tests/
```

## 📜 Лицензия

MIT License - см. файл [LICENSE](LICENSE)
