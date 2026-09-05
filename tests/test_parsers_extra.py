"""Tests for newly added package-manager parsers (snap/flatpak/cargo/npm)."""

from __future__ import annotations

from package_maximizer.parsers import (PARSER_REGISTRY, ApkParser, CargoParser,
                                       ChocoParser, ComposerParser,
                                       CondaParser, FlatpakParser, GemParser,
                                       NpmParser, NuGetParser, PipParser,
                                       PortageParser, ScoopParser, SnapParser,
                                       VcpkgParser, WingetParser, YarnParser,
                                       YumParser, ZypperParser, get_parser)

SNAP_LIST = """Name           Version          Rev    Tracking         Publisher
core           16-2.58.3        14936  latest/stable    canonical*
lxd            5.0.2            24322  latest/stable    canonical*
"""

FLATPAK_LIST = """Application                       Version
org.gnome.Platform              44.0
com.spotify.Client              1.2.13
"""

CARGO_META = r"""{
  "packages": [
    {"name": "serde", "version": "1.0.0", "dependencies": [{"name": "serde_derive"}]},
    {"name": "serde_derive", "version": "1.0.0", "dependencies": []}
  ]
}"""

NPM_LS = r"""{
  "dependencies": {
    "lodash": {"version": "4.17.21"},
    "react": {"version": "18.2.0", "dependencies": {"scheduler": {"version": "0.23.0"}}}
  }
}"""

CONDA_LIST = """# packages in environment at /home/user/miniconda3:
#
numpy              1.23.5  conda-forge
pandas             2.0.0   defaults
"""

PORTAGE_LIST = """[ebuild   r] app-editors/vim-8.2.0
[ebuild   r] sys-apps/less-590
"""

APK_LIST = """alpine-baselayout-3.14.0-r1 x86_64 3.14.0-r1 ~main
busybox-1.32.1-r1 x86_64 1.32.1-r1 ~main
"""

ZYPPER_LIST = """Loading repository data...
Reading installed packages...

S | Name                  | Type   | Version       | Arch   | Repository
--+-----------------------+-------+---------------+--------+-----------
  | vim                   | package | 8.2.3895-1.2 | x86_64 | Main
  | git                   | package | 2.38.1-1.1   | x86_64 | Main
"""

YUM_LIST = """Loaded plugins: fastestmirror
Installed Packages
git.x86_64               1:2.23.1-1.el8                @baseos
vim-enhanced.x86_64      2:8.0.1763-13.5.el8           @appstream
"""

PIP_LIST = """Package    Version
---------- -------
certifi    2022.9.24
requests   2.28.1
"""

PIP_FREEZE = """certifi==2022.9.24
requests>=2.28.1
"""

GEM_LIST = """*** LOCAL GEMS ***

actioncable (6.1.4, 6.1.3, 6.0.4)
actionmailbox (6.1.4)
"""

YARN_LIST = """├─ yarn@1.22.17
├─ lodash@4.17.21
└─ react@18.2.0
"""

COMPOSER_LIST = """name     : laravel/framework
versions : * 8.83.26

name     : php
versions : * 8.0.28
"""

VCPKG_LIST = """bzip2:x64-windows         1.0.8         installed
cmake:x64-windows         3.24.2        installed
"""

NUGET_LIST = """Top-level Package      Version
--------------------   -------
Newtonsoft.Json        13.0.1
Serilog                2.10.0
"""

WINGET_LIST = """Name                     Id                            Version
-----------------------  ----------------------------  -------
7-Zip 21.70 (x64)        7zip.7zip                    21.07
Visual Studio Code       Microsoft.VisualStudioCode    1.72.2
"""

SCOOP_LIST = """Installed apps:

  7zip 22.01 : main
  git  2.38.1 : extras
"""

CHOCO_LIST = """Chocolatey v1.2.1
7zip 22.01
git 2.38.1
2 packages installed.
"""


class TestNewParsers:
    """New parsers should produce correct Package objects from real output."""

    def test_snap_parser(self):
        pkgs = SnapParser().parse(SNAP_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "core"
        assert pkgs[0].version == "16-2.58.3"
        assert pkgs[0].status == "installed"

    def test_flatpak_parser(self):
        pkgs = FlatpakParser().parse(FLATPAK_LIST)
        assert {p.name for p in pkgs} == {"org.gnome.Platform", "com.spotify.Client"}
        assert any(p.version == "1.2.13" for p in pkgs)

    def test_cargo_json(self):
        pkgs = CargoParser().parse(CARGO_META)
        names = {p.name for p in pkgs}
        assert names == {"serde", "serde_derive"}
        serde = next(p for p in pkgs if p.name == "serde")
        assert serde.depends == ["serde_derive"]

    def test_cargo_text_fallback(self):
        pkgs = CargoParser().parse("tokio v1.0.0\nrand 0.8.5\n")
        assert {p.name for p in pkgs} == {"tokio", "rand"}

    def test_npm_json(self):
        pkgs = NpmParser().parse(NPM_LS)
        names = {p.name for p in pkgs}
        assert names == {"lodash", "react", "scheduler"}
        react = next(p for p in pkgs if p.name == "react")
        assert react.depends == ["scheduler"]

    def test_npm_text_fallback(self):
        pkgs = NpmParser().parse("lodash@4.17.21\nreact@18.2.0\n")
        assert {p.name for p in pkgs} == {"lodash", "react"}

    def test_registry_includes_new_parsers(self):
        for key in ("snap", "flatpak", "cargo", "npm"):
            assert key in PARSER_REGISTRY
            assert isinstance(
                get_parser(key),
                PackageParser := __import__(
                    "package_maximizer.core.interfaces", fromlist=["PackageParser"]
                ).PackageParser,
            )

    def test_conda_parser(self):
        pkgs = CondaParser().parse(CONDA_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "numpy"
        assert pkgs[0].version == "1.23.5"
        assert pkgs[0].status == "installed"

    def test_portage_parser(self):
        pkgs = PortageParser().parse(PORTAGE_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "vim"
        assert pkgs[1].name == "less"

    def test_apk_parser(self):
        pkgs = ApkParser().parse(APK_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "alpine-baselayout"
        assert pkgs[1].name == "busybox"

    def test_zypper_parser(self):
        pkgs = ZypperParser().parse(ZYPPER_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "vim"
        assert pkgs[1].name == "git"

    def test_yum_parser(self):
        pkgs = YumParser().parse(YUM_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "git"
        assert pkgs[1].name == "vim-enhanced"

    def test_pip_list_parser(self):
        pkgs = PipParser().parse(PIP_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "certifi"
        assert pkgs[0].version == "2022.9.24"

    def test_pip_freeze_parser(self):
        pkgs = PipParser().parse(PIP_FREEZE)
        assert len(pkgs) == 2
        assert pkgs[0].name == "certifi"
        assert pkgs[0].version == "2022.9.24"

    def test_gem_parser(self):
        pkgs = GemParser().parse(GEM_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "actioncable"
        assert pkgs[1].name == "actionmailbox"

    def test_yarn_parser(self):
        pkgs = YarnParser().parse(YARN_LIST)
        assert len(pkgs) == 3
        assert pkgs[0].name == "yarn"
        assert pkgs[1].name == "lodash"

    def test_composer_parser(self):
        pkgs = ComposerParser().parse(COMPOSER_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "laravel/framework"
        assert pkgs[1].name == "php"

    def test_vcpkg_parser(self):
        pkgs = VcpkgParser().parse(VCPKG_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "bzip2"
        assert pkgs[1].name == "cmake"

    def test_nuget_parser(self):
        pkgs = NuGetParser().parse(NUGET_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "Newtonsoft.Json"
        assert pkgs[1].name == "Serilog"

    def test_winget_parser(self):
        pkgs = WingetParser().parse(WINGET_LIST)
        assert len(pkgs) == 2
        assert "7-Zip" in pkgs[0].name
        assert pkgs[1].name == "Visual Studio Code"

    def test_scoop_parser(self):
        pkgs = ScoopParser().parse(SCOOP_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "7zip"
        assert pkgs[1].name == "git"

    def test_choco_parser(self):
        pkgs = ChocoParser().parse(CHOCO_LIST)
        assert len(pkgs) == 2
        assert pkgs[0].name == "7zip"
        assert pkgs[1].name == "git"

    def test_all_new_parsers_registered(self):
        expected = {
            "snap",
            "flatpak",
            "cargo",
            "npm",
            "conda",
            "portage",
            "apk",
            "zypper",
            "yum",
            "pip",
            "gem",
            "yarn",
            "composer",
            "vcpkg",
            "nuget",
            "winget",
            "scoop",
            "choco",
        }
        for key in expected:
            assert key in PARSER_REGISTRY, f"{key} not in registry"
            parser = get_parser(key)
            assert parser is not None

    def test_empty_input_returns_empty_list(self):
        """All parsers should handle empty input gracefully."""
        parsers = [
            CondaParser(),
            PortageParser(),
            ApkParser(),
            ZypperParser(),
            YumParser(),
            PipParser(),
            GemParser(),
            YarnParser(),
            ComposerParser(),
            VcpkgParser(),
            NuGetParser(),
            WingetParser(),
            ScoopParser(),
            ChocoParser(),
        ]
        for parser in parsers:
            assert parser.parse("") == []
            assert parser.parse("   ") == []
            assert parser.parse("\n\n") == []
