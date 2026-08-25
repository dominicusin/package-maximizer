# Package Maximizer 📦🔍

[![CI/CD](https://github.com/dominicusin/package-maximizer/workflows/Package%20Maximizer%20CI/CD/badge.svg)](https://github.com/dominicusin/package-maximizer/actions)
[![codecov](https://codecov.io/gh/dominicusin/package-maximizer/branch/main/graph/badge.svg)](https://codecov.io/gh/dominicusin/package-maximizer)
[![PyPI version](https://badge.fury.io/py/package-maximizer.svg)](https://badge.fury.io/py/package-maximizer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Модульная система для решения задачи максимизации непротиворечивого множества пакетов с использованием различных SAT/ILP/SMT солверов для множественных пакетных менеджеров.

## 🚀 Возможности

- **Поддержка множественных пакетных менеджеров**: pacman, apt, dnf, zypper, brew, Spack и другие
- **Различные солверы**: Z3, PuLP, OR-Tools, MaxSAT, MiniSat
- **Параллельное решение**: одновременный запуск нескольких солверов
- **Веб-интерфейс**: интуитивный веб-интерфейс с визуализацией
- **CLI инструменты**: мощный командный интерфейс
- **Бенчмаркинг**: сравнение производительности солверов
- **Модульная архитектура**: легко расширяемая система

## 📋 Требования

- Python 3.8+
- Один или несколько поддерживаемых солверов

## 🔧 Установка
```bash
# Из исходного кода
git clone https://github.com/dominicusin/package-maximizer.git
cd package-maximizer
pip install -e ".[all]"

---

🔄 **Mirrors:** [![GitLab](https://img.shields.io/badge/GitLab-dominicusin-orange?logo=gitlab)](https://gitlab.com/dominicusin/package-maximizer) · GitHub is canonical.
