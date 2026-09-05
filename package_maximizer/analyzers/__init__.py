"""
Analyzers module - Модуль анализаторов результатов.
"""

from __future__ import annotations

from .result_analyzer import ResultAnalyzer

# Available analyzers
__all__ = [
    "ResultAnalyzer",
    "get_analyzer",
    "ANALYZER_REGISTRY",
]

# Analyzer registry for easy access
ANALYZER_REGISTRY = {
    "basic": ResultAnalyzer,
}


def get_analyzer(analyzer_name: str):
    """
    Получение экземпляра анализатора по имени.

    Args:
        analyzer_name: Имя анализатора (регистронезависимое)

    Returns:
        Экземпляр анализатора

    Raises:
        ValueError: Если анализатор не найден
    """
    analyzer_name = analyzer_name.lower()
    if analyzer_name not in ANALYZER_REGISTRY:
        available = ", ".join(ANALYZER_REGISTRY.keys())
        raise ValueError(
            f"Analyzer '{analyzer_name}' not found. Available: {available}"
        )
    return ANALYZER_REGISTRY[analyzer_name]()
