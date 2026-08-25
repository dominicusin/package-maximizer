"""Абстрактные интерфейсы солверов, парсеров и анализаторов."""

from abc import ABC, abstractmethod
from typing import Iterable


class ConstraintSolver(ABC):
    """Решатель задачи максимизации непротиворечивого множества пакетов."""

    @abstractmethod
    def solve(self, packages: Iterable["Package"]) -> list[str]:
        """Возвращает список имён пакетов, образующих максимальное согласованное множество."""


class PackageParser(ABC):
    """Парсер вывода пакетного менеджера."""

    @abstractmethod
    def parse(self, raw: str) -> list["Package"]:
        """Разбирает текстовый вывод менеджера в список Package."""


class ResultAnalyzer(ABC):
    """Анализатор результата работы солвера."""

    @abstractmethod
    def analyze(self, installed: Iterable[str], proposed: Iterable[str]) -> dict:
        """Сравнивает установленный набор с предложенным решением."""
