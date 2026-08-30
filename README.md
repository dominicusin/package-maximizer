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
pip install z3 python-sat pulp ortools
```

### Варианты установки зависимостей

| Команда | Что устанавливает |
|---------|-------------------|
| `pip install -e .` | Только основные зависимости |
| `pip install -e ".[solvers]"` | Солверы (Z3, PuLP, OR-Tools) |
| `pip install -e ".[web]"` | Веб-интерфейс (Flask) |
| `pip install -e ".[dev]"` | Инструменты разработки |
| `pip install -e ".[all]"` | Все зависимости |
| `pip install -r requirements-core.txt` | Только ядро |
| `pip install -r requirements-solvers.txt` | Только солверы |
| `pip install -r requirements-web.txt` | Только веб |
| `pip install -r requirements-dev.txt` | Только dev-инструменты |

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
```

## 🌐 REST API (веб-интерфейс)

### Запуск сервера

```bash
pip install -e ".[web]"
pm-web
```

### Аутентификация

Все эндпоинты (кроме `/api/health`) требуют API-ключ в заголовке `X-API-Key`.

### Эндпоинты

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/health` | Health check |
| GET | `/api/v1/solvers` | Список солверов |
| GET | `/api/v1/parsers` | Список парсеров |
| POST | `/api/v1/maximize` | Максимизация |
| GET | `/api/maximize` | Максимизация (query params) |
| POST | `/api/v1/benchmark` | Бенчмаркинг |
| GET | `/api/v1/cache/stats` | Статистика кэша |
| DELETE | `/api/v1/cache` | Очистка кэша |

### Примеры

```bash
curl -X POST http://localhost:5000/api/v1/maximize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production" \
  -d '{"packages": ["vim", "emacs", "nano"], "solver": "greedy", "conflicts": [["vim", "emacs"]]}'
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
