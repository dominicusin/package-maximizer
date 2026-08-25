"""Модель пакета и его ограничения."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Package:
    name: str
    version: str = ""
    status: str = "candidate"
    depends: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)

    def __str__(self) -> str:
        v = f" {self.version}" if self.version else ""
        return f"{self.name}{v}"


@dataclass
class PackageConstraint:
    package: str
    op: str = ">="
    version: str = ""

    def satisfied_by(self, other_version: str) -> bool:
        if not self.version or not other_version:
            return True

        def key(v):
            return [int(x) for x in v.split(".") if x.isdigit()]

        a, b = key(other_version), key(self.version)
        return {
            ">=": a >= b,
            "<=": a <= b,
            "==": a == b,
            ">": a > b,
            "<": a < b,
        }.get(self.op, True)
