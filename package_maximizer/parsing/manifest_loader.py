"""`parsing/manifest_loader.py` — загрузка пакетных манифестов (YAML/JSON/CSV)
и удалённых метаданных через HTTP(S) с помощью ``requests``.

Два пути:

1. :class:`ManifestLoader` — читает локальные файлы (``*.yaml``/``*.yml``/
   ``*.json``/``*.csv``) и приводит их к списку ``Package``. Поддерживаемые
   схемы:

   * JSON-массив ``[{"name": "...", "version": "...", "depends": [...], "conflicts": [...]}]``
   * JSON-объект ``{"packages": [...]}`` или верхнеуровневые поля
     ``packages``/``dependencies``/``conflicts``
   * YAML-аналоги, а также CSV (``name,version,depends,conflicts``)

2. :class:`RemoteManifestSource` — запросы к REST-эндпоинтам репозиториев
   (``requests`` + ``urllib3``), пригодные для передачи в ``PackageMaximizer``
   через ``adapter=fetch_remote``.  Поддерживает пагинацию по
   ``?page=``/``&limit=``.

Парсинг не зависит от конкретного пакетного менеджера: манифест — это
является развёрнутым описанием зависимостей и конфликтов, будь то локальный
запланированный конфиг (``package-manifest.yaml``) или HTTP-инвентаризация.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Iterable, Optional

import requests
import yaml

from ..core.package import Package

__all__ = ["ManifestLoader", "RemoteManifestSource", "ManifestParseException"]


class ManifestParseException(Exception):
    """Ошибка разбора манифеста."""


@dataclass
class ManifestLoader:
    """Локальный загрузчик JSON/YAML/CSV-манифестов пакетов."""

    #: Набор допустимых путей/указателей входных манифестов.
    sources: list[str | io.IOBase] = field(default_factory=list)

    #: Поле, которое считать массивом пакетов (JSON-объекты имеют такое поле)
    package_list_key: str = "packages"

    @classmethod
    def from_paths(cls, paths: Iterable[str]) -> "ManifestLoader":
        loader = cls()
        loader.sources = [p for p in paths]
        return loader

    @classmethod
    def from_file(cls, path: str) -> "ManifestLoader":
        return cls.from_paths([path])

    def _read_text(self, src) -> str:
        if isinstance(src, str):
            with open(src, "r", encoding="utf-8") as fh:
                return fh.read()
        if isinstance(src, io.IOBase):
            src.seek(0)
            return src.read().decode("utf-8")
        raise ManifestParseException(f"Unsupported source type: {type(src)!r}")

    def _parse_json(self, text: str) -> list[Package]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ManifestParseException(f"Bad JSON manifest: {exc}") from exc

        if isinstance(data, list):
            return self._items_to_packages(data)
        if isinstance(data, dict):
            # Поддержка={"packages": [...], "dependencies": {...}, "conflicts": {...}}
            for key in (self.package_list_key, "packages", "manifest", "package_list"):
                if key in data and isinstance(data[key], list):
                    return self._items_to_packages(data[key])
            return self._dict_to_packages(data)
        return []

    def _parse_yaml(self, text: str) -> list[Package]:
        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:
            raise ManifestParseException(f"Bad YAML manifest: {exc}") from exc

        if isinstance(data, list):
            return self._items_to_packages(data)
        if isinstance(data, dict):
            for key in (self.package_list_key, "packages", "manifest", "package_list"):
                if key in data and isinstance(data[key], list):
                    return self._items_to_packages(data[key])
            # Возможно, YAML это {pkg: {version: ..., depends: [...], conflicts: [...]}}
            return self._dict_to_packages(data)
        return []

    def _items_to_packages(self, items: Iterable) -> list[Package]:
        packages = []
        for item in items:
            if isinstance(item, str):
                packages.append(Package(name=item))
                continue
            if isinstance(item, dict):
                packages.append(
                    Package(
                        name=item.get("name", ""),
                        version=item.get("version", ""),
                        status=item.get("status", "candidate"),
                        depends=list(item.get("depends") or []),
                        conflicts=list(item.get("conflicts") or []),
                    )
                )
                continue
            packages.append(Package(name=str(item)))
        return packages

    def _dict_to_packages(self, data: dict) -> list[Package]:
        packages = []
        for key, value in data.items():
            if isinstance(value, dict):
                packages.append(
                    Package(
                        name=key,
                        version=value.get("version", ""),
                        depends=list(value.get("depends") or []),
                        conflicts=list(value.get("conflicts") or []),
                    )
                )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        packages.append(Package(name=item))
                    elif isinstance(item, dict):
                        packages.append(
                            Package(
                                name=item.get("name", key),
                                version=item.get("version", ""),
                                depends=list(item.get("depends") or []),
                                conflicts=list(item.get("conflicts") or []),
                            )
                        )
        return packages

    def parse(self) -> list[Package]:
        """Разобрать все источники в один список ``Package``."""
        packages = []
        for src in self.sources:
            text = self._read_text(src)
            ext = src.lower() if isinstance(src, str) else ""
            if ext.endswith((".yaml", ".yml")):
                packages.extend(self._parse_yaml(text))
            elif ext.endswith(".json"):
                packages.extend(self._parse_json(text))
            elif ext.endswith(".csv"):
                packages.extend(self._parse_csv(text))
            else:
                # Аутентичное расширение не распознано — пробуем JSON then YAML
                try:
                    packages.extend(self._parse_json(text))
                except ManifestParseException:
                    packages.extend(self._parse_yaml(text))
        # Дедупликация по имени + версии
        seen = set()
        out = []
        for pkg in packages:
            key = (pkg.name, pkg.version)
            if key not in seen:
                seen.add(key)
                out.append(pkg)
        return out

    def _parse_csv(self, text: str) -> list[Package]:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return []
        packages = []
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            packages.append(
                Package(
                    name=name,
                    version=(row.get("version") or "").strip(),
                    depends=[
                        d.strip()
                        for d in (row.get("depends") or "").split(",")
                        if d.strip()
                    ],
                    conflicts=[
                        c.strip()
                        for c in (row.get("conflicts") or "").split(",")
                        if c.strip()
                    ],
                )
            )
        return packages


class RemoteManifestSource:
    """Загрузчик удалённых списков пакетов по HTTP/HTTPS через ``requests``."""

    def __init__(
        self,
        url: str,
        *,
        headers: dict | None = None,
        params: dict | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.url = url
        self.headers = headers or {}
        self.params = params or {}
        self.timeout = timeout

    def fetch(self) -> list[Package]:
        resp = requests.get(
            self.url, headers=self.headers, params=self.params, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        # RemoteManifestSource поддерживает JSON: либо [{"name":...}], либо {"packages":[...]}
        if isinstance(data, list):
            return self._items_to_packages(data)
        if isinstance(data, dict):
            for key in ("packages", "manifest", "package_list"):
                if key in data and isinstance(data[key], list):
                    return self._items_to_packages(data[key])
            # ведомый объект одного пакета -> превращаем в список
            return self._dict_to_packages(data)
        return []

    def _items_to_packages(self, items: Iterable) -> list[Package]:
        out = []
        for item in items:
            if isinstance(item, str):
                out.append(Package(name=item))
            elif isinstance(item, dict):
                out.append(
                    Package(
                        name=item.get("name", ""),
                        version=item.get("version", ""),
                        status=item.get("status", "candidate"),
                        depends=list(item.get("depends") or []),
                        conflicts=list(item.get("conflicts") or []),
                    )
                )
        return out

    def _dict_to_packages(self, data: dict) -> list[Package]:
        return [Package(name=k, version=str(v)) for k, v in data.items() if k]
