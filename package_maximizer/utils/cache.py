"""
Cache Manager - Менеджер кэширования.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheManager:
    """
    Менеджер кэширования для результатов вычислений.

    Поддерживает:
    - Кэширование в файловой системе
    - TTL (время жизни) для кэша
    - Автоматическую очистку устаревших записей
    """

    def __init__(
        self,
        cache_dir: str | Path = ".package_maximizer_cache",
        default_ttl: int = 3600,
    ) -> None:
        """
        Инициализация менеджера кэша.

        Args:
            cache_dir: Директория для кэша
            default_ttl: Время жизни по умолчанию в секундах
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self._memory_cache: dict[str, tuple[Any, float, int]] = {}

        # Создаем директорию кэша
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, key: str) -> str:
        """
        Получить хеш ключа для использования в качестве имени файла.

        Args:
            key: Исходный ключ

        Returns:
            Хэшированный ключ
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """
        Получить путь к файлу кэша.

        Args:
            key: Ключ кэша

        Returns:
            Путь к файлу
        """
        hash_key = self._get_cache_key(key)
        return self.cache_dir / f"{hash_key}.json"

    def get(self, key: str) -> Any | None:
        """
        Получить значение из кэша.

        Args:
            key: Ключ кэша

        Returns:
            Значение из кэша или None, если не найдено/устарело
        """
        # Проверяем в памяти
        if key in self._memory_cache:
            value, timestamp, ttl = self._memory_cache[key]
            if time.time() - timestamp < ttl:
                return value
            else:
                del self._memory_cache[key]

        # Проверяем в файловой системе
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)

                # Проверяем TTL
                ttl = data.get("ttl", self.default_ttl)
                if time.time() - data["timestamp"] < ttl:
                    # Сохраняем в памяти
                    self._memory_cache[key] = (data["value"], data["timestamp"], ttl)
                    return data["value"]
                else:
                    # Удаляем устаревший кэш
                    cache_path.unlink()
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error reading cache file {cache_path}: {e}")

        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Сохранить значение в кэше.

        Args:
            key: Ключ кэша
            value: Значение для кэширования (должно быть сериализуемо в JSON)
            ttl: Время жизни в секундах (по умолчанию default_ttl)
        """
        if ttl is None:
            ttl = self.default_ttl

        timestamp = time.time()

        # Сохраняем в памяти
        self._memory_cache[key] = (value, timestamp, ttl)

        # Сохраняем в файловой системе
        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, "w") as f:
                json.dump({"value": value, "timestamp": timestamp, "ttl": ttl}, f)
        except (TypeError, ValueError) as e:
            logger.warning(f"Cannot cache value (not JSON serializable): {e}")

    def delete(self, key: str) -> bool:
        """
        Удалить запись из кэша.

        Args:
            key: Ключ кэша

        Returns:
            True, если запись была удалена
        """
        deleted = False

        if key in self._memory_cache:
            del self._memory_cache[key]
            deleted = True

        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            deleted = True

        return deleted

    def clear(self) -> int:
        """
        Очистить весь кэш.

        Returns:
            Количество удаленных записей
        """
        count = 0

        # Очищаем память
        self._memory_cache.clear()

        # Очищаем файловую систему
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError as e:
                logger.warning(f"Error deleting cache file {cache_file}: {e}")

        return count

    def cleanup_expired_by_ttl(self, ttl: int) -> int:
        """
        Удалить устаревшие записи из кэша по указанному TTL.

        Args:
            ttl: Время жизни в секундах

        Returns:
            Количество удаленных записей
        """
        count = 0
        current_time = time.time()

        # Очищаем память
        expired_memory = [
            key
            for key, (_, timestamp, key_ttl) in self._memory_cache.items()
            if current_time - timestamp >= key_ttl
        ]
        for key in expired_memory:
            del self._memory_cache[key]
            count += 1

        # Очищаем файловую систему
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)

                key_ttl = data.get("ttl", self.default_ttl)
                if current_time - data["timestamp"] >= key_ttl:
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.warning(f"Error checking cache file {cache_file}: {e}")

        return count

    def cleanup_expired(self) -> int:
        """
        Удалить устаревшие записи из кэша (используя их собственные TTL).

        Returns:
            Количество удаленных записей
        """
        return self.cleanup_expired_by_ttl(self.default_ttl)

    def cached(self, ttl: int | None = None):
        """
        Декоратор для кэширования результатов функции.

        Args:
            ttl: Время жизни в секундах

        Returns:
            Декоратор
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args, **kwargs) -> T:
                # Создаем ключ из имени функции и аргументов
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key = "|".join(key_parts)

                # Проверяем кэш
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value

                # Вызываем функцию
                result = func(*args, **kwargs)

                # Сохраняем в кэше
                self.set(key, result, ttl)

                return result

            return wrapper

        return decorator

    def get_stats(self) -> dict[str, Any]:
        """
        Получить статистику кэша.

        Returns:
            Статистика кэша
        """
        file_count = len(list(self.cache_dir.glob("*.json")))
        memory_count = len(self._memory_cache)

        return {
            "memory_entries": memory_count,
            "file_entries": file_count,
            "total_entries": memory_count + file_count,
            "cache_dir": str(self.cache_dir),
            "default_ttl": self.default_ttl,
        }
