"""Tests for Nix, Guix and Spack parsers (PROJECT_PLAN Phase 2.1)."""

from __future__ import annotations

import json

import pytest

from package_maximizer.core.enums import PackageManagerType
from package_maximizer.parsers import (
    PARSER_REGISTRY,
    GuixParser,
    NixParser,
    SpackParser,
    get_parser,
)
from package_maximizer.parsers.extra_parsers import _split_drv_name

H = "0123456789abcdfghijklmnpqrsvwxyz"

NIX_ENV_Q = """hello-2.12.1
python3.11-numpy-1.26.4
firefox
"""

NIX_PROFILE_LIST = f"""Name:               hello
Flake attribute:    legacyPackages.x86_64-linux.hello
Original flake URL: flake:nixpkgs
Locked flake URL:   github:NixOS/nixpkgs/abc
Store paths:        /nix/store/{H}-hello-2.12.1

Name:               ripgrep
Store paths:        /nix/store/{H}-ripgrep-14.1.0
"""

NIX_PROFILE_LIST_LEGACY = (
    f"0 flake:nixpkgs#legacyPackages.x86_64-linux.hello "
    f"github:NixOS/nixpkgs/abc#legacyPackages.x86_64-linux.hello "
    f"/nix/store/{H}-hello-2.12.1\n"
)

GUIX_LIST = f"""hello\t2.12.1\tout\t/gnu/store/{H}-hello-2.12.1
coreutils\t9.1\tout,debug\tgnu/packages/base.scm:351:2
"""

SPACK_FIND = """-- linux-ubuntu22.04-x86_64 / gcc@11.4.0 ------------------------
autoconf@2.72  zlib-ng@2.1.6
abc1234 zlib@=1.3+shared~pic %gcc@11.4.0 build_system=makefile
==> 3 installed packages
"""


@pytest.mark.parametrize(
    ("drv", "expected"),
    [
        ("hello-2.12.1", ("hello", "2.12.1")),
        ("python3.11-numpy-1.26.4", ("python3.11-numpy", "1.26.4")),
        ("firefox", ("firefox", "")),
        ("nix-2.18.1", ("nix", "2.18.1")),
    ],
)
def test_split_drv_name(drv, expected):
    assert _split_drv_name(drv) == expected


class TestNixParser:
    def test_nix_env_query(self):
        pkgs = NixParser().parse(NIX_ENV_Q)
        assert [(p.name, p.version) for p in pkgs] == [
            ("hello", "2.12.1"),
            ("python3.11-numpy", "1.26.4"),
            ("firefox", ""),
        ]
        assert all(p.status == "installed" for p in pkgs)

    def test_profile_list(self):
        pkgs = NixParser().parse(NIX_PROFILE_LIST)
        assert [(p.name, p.version) for p in pkgs] == [
            ("hello", "2.12.1"),
            ("ripgrep", "14.1.0"),
        ]

    def test_profile_list_legacy_format(self):
        pkgs = NixParser().parse(NIX_PROFILE_LIST_LEGACY)
        assert [(p.name, p.version) for p in pkgs] == [("hello", "2.12.1")]

    def test_profile_json_dict_elements(self):
        raw = json.dumps(
            {
                "version": 3,
                "elements": {
                    "hello": {"storePaths": [f"/nix/store/{H}-hello-2.12.1"]},
                    "custom": {"storePaths": []},
                },
            }
        )
        pkgs = NixParser().parse(raw)
        assert [(p.name, p.version) for p in pkgs] == [
            ("hello", "2.12.1"),
            ("custom", ""),
        ]

    def test_profile_json_list_elements(self):
        raw = json.dumps(
            {
                "version": 2,
                "elements": [
                    {"storePaths": [f"/nix/store/{H}-jq-1.7.1"]},
                    {"storePaths": []},
                    "junk",
                ],
            }
        )
        pkgs = NixParser().parse(raw)
        assert [(p.name, p.version) for p in pkgs] == [("jq", "1.7.1")]

    def test_invalid_json(self):
        assert NixParser().parse("{not json") == []

    def test_duplicates_collapsed(self):
        assert len(NixParser().parse("hello-2.12.1\nhello-2.12.1\n")) == 1


class TestGuixParser:
    def test_installed_and_available(self):
        pkgs = GuixParser().parse(GUIX_LIST)
        assert [(p.name, p.version, p.status) for p in pkgs] == [
            ("hello", "2.12.1", "installed"),
            ("coreutils", "9.1", "candidate"),
        ]

    def test_skips_malformed_lines(self):
        assert GuixParser().parse("garbage\nfoo bar\n") == []


class TestSpackParser:
    def test_find_text(self):
        pkgs = SpackParser().parse(SPACK_FIND)
        assert [(p.name, p.version) for p in pkgs] == [
            ("autoconf", "2.72"),
            ("zlib-ng", "2.1.6"),
            ("zlib", "1.3"),
        ]

    def test_find_json(self):
        raw = json.dumps(
            [
                {
                    "name": "cmake",
                    "version": "3.27.9",
                    "dependencies": [{"name": "openssl"}, {"name": "ncurses"}],
                },
                {"name": "openssl", "version": "3.1.3", "dependencies": {"zlib": {}}},
                {"version": "1.0"},
            ]
        )
        pkgs = SpackParser().parse(raw)
        assert [(p.name, p.version, p.depends) for p in pkgs] == [
            ("cmake", "3.27.9", ["openssl", "ncurses"]),
            ("openssl", "3.1.3", ["zlib"]),
        ]

    def test_invalid_json(self):
        assert SpackParser().parse("[oops") == []


@pytest.mark.parametrize("name", ["nix", "guix", "spack"])
def test_registered_and_empty_input(name):
    assert name in PARSER_REGISTRY
    assert PackageManagerType(name).value == name
    assert get_parser(name).parse("  \n") == []


def test_enum_matches_registry():
    assert {m.value for m in PackageManagerType} == set(PARSER_REGISTRY.keys())
