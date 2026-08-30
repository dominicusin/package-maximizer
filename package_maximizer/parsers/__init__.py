"""
Parsers module - Модуль парсеров пакетов.
"""

from __future__ import annotations

from .apt_parser import APTParser
from .pacman_parser import PacmanParser
from .dnf_parser import DNFParser
from .brew_parser import BrewParser

# Available parsers
__all__ = [
    "APTParser",
    "PacmanParser",
    "DNFParser",
    "BrewParser",
    "get_parser",
    "PARSER_REGISTRY",
]

# Parser registry for easy access
PARSER_REGISTRY = {
    "apt": APTParser,
    "pacman": PacmanParser,
    "dnf": DNFParser,
    "brew": BrewParser,
}


def get_parser(parser_name: str):
    """
    Получение экземпляра парсера по имени.
    
    Args:
        parser_name: Имя парсера (регистронезависимое)
        
    Returns:
        Экземпляр парсера
        
    Raises:
        ValueError: Если парсер не найден
    """
    parser_name = parser_name.lower()
    if parser_name not in PARSER_REGISTRY:
        available = ", ".join(PARSER_REGISTRY.keys())
        raise ValueError(f"Parser '{parser_name}' not found. Available: {available}")
    return PARSER_REGISTRY[parser_name]()
