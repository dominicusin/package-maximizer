"""Extract REAL dependency data from nix-store -qR and feed to solver benchmark."""

import json
import subprocess
import sys
from pathlib import Path

def nix_store_qr(store_path: str) -> list[str]:
    result = subprocess.run(["nix-store", "-qR", store_path], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

def build_deps_data():
    packages = [
        ("bash", "bash", "bash-interactive"),
        ("coreutils", "coreutils", None),
        ("git", "git", None),
        ("curl", "curl", None),
        ("firefox", "firefox", None),
        ("python3", "python3", None),
        ("gcc", "gcc", "gcc-wrapper"),
        ("vim", "vim", None),
        ("neovim", "neovim", None),
        ("nodejs", "nodejs", None),
        ("nginx", "nginx", None),
        ("postgresql", "postgresql", None),
        ("redis", "redis", None),
        ("perl", "perl", None),
        ("ruby", "ruby", None),
        ("go", "go", None),
        ("rustc", "rustc", "rustc-wrapper"),
        ("clang", "clang", "clang-wrapper"),
        ("systemd", "systemd", None),
        ("openssl", "openssl", "openssl-bin"),
        ("zlib", "zlib", None),
    ]
    
    all_deps = {}
    total = 0
    
    for attr, name, alt_attr in packages:
        try:
            path = subprocess.run(
                ["nix-build", "<nixpkgs>", "-A", attr, "--no-out-link"],
                capture_output=True, text=True, timeout=60
            )
            if path.returncode != 0 or not path.stdout.strip():
                continue
            
            sp = path.stdout.strip()
            deps = nix_store_qr(sp)
            dep_names = [d.split("/")[-1] for d in deps if d != sp]
            all_deps[name] = {"store_path": sp, "deps_count": len(dep_names), "deps": dep_names[:10]}
            total += len(dep_names)
            print(f"{name}: {len(dep_names)} real deps (attr={attr})")
        except Exception as e:
            print(f"{name}: FAILED - {e}")
    
    result = {"packages": all_deps, "total_dependency_edges": total}
    output = Path("/home/domini/package-maximizer/real_deps_data.json")
    with open(output, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nTotal: {len(all_deps)} packages, {total} real dependency edges")
    print(f"Saved to {output}")

if __name__ == "__main__":
    build_deps_data()
