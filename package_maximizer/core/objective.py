"""`core/objective.py` — целевая функция максимизации пакетов.

Традиционно задача формулируется как максимизация числа выбранных пакетов.
Для реальных сценариев полезность/приоритет пакета обычно не равны:
например, системные утилиты (``coreutils``, ``zstd``) могут вносить больше
полезности, чем вспомогательные библиотеки, а пакеты с высоким приоритетом
развертывания должны отдаваться предпочтение.

:class:`Objective` объединяет:

* **count** — классическая максимизация числа пакетов (каждый вес = 1);
* **weighted** — суммарная полезность, где вес берётся из ``weights`` или из
  поля ``Package.priority``;
* **user_defined** — индивидуальный словарь весов, переданный в солвер.

Начальный вес зависит от ``objective`` и от того, передан ли явный словарь
весов; он не перезаписывается сторонним вызывающим кодом.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from .package import Package

__all__ = ["Objective", "get_default_weights"]


@dataclass
class Objective:
    """Целевая функция задачи максимизации.

    Атрибуты:

    * ``name`` — один из ``"count"`` / ``"weighted"`` / ``"user_defined"``.
    * ``weights`` — явный словарь ``{имя_пакета: полезность}`` (опционально).
    * ``priority_key`` — имя атрибута ``Package`` (по умолчанию ``"priority"``),
      которое даст вес, если ``weights`` не определён.
    * ``default_weight`` — пороговое значение, которое будет подставлено при
      отсутствии веса для конкретного пакета (по умолчанию ``1.0``).
    """

    name: str = "count"
    weights: dict[str, float] | None = None
    priority_key: str = "priority"
    default_weight: float = 1.0

    def is_weighted(self) -> bool:
        """True, если цель рассчитывается по сумме весов, а не по числу."""
        return self.name == "weighted" or self.name == "user_defined"

    def weight_for(
        self, pkg: Package, explicit: Mapping[str, float] | None = None
    ) -> float:
        """Вернуть полезность (вес) конкретного пакета."""
        if self.weights and pkg.name in self.weights:
            return float(self.weights[pkg.name])
        if explicit and pkg.name in explicit:
            return float(explicit[pkg.name])
        base = getattr(pkg, self.priority_key, None)
        if base is None:
            return self.default_weight
        try:
            return float(base)
        except (TypeError, ValueError):
            return self.default_weight


def get_default_weights() -> dict[str, float]:
    """Возвращает сводку принятых по умолчанию весов.

    В проекте ``package-maximizer`` нет фиксированного реестра полезностей
    — веса задаются либо явно через ``Objective.weights``, либо через поле
    ``priority`` у ``Package``.  Этот хелпер лишь фиксирует философию.
    """
    return {
        "count": 1.0,
        "weighted": 1.0,
        "user_defined": 1.0,
    }


# Устаревший псевдоним (оставлен для обратной совместимости).
DefaultObjective = Objective
