#!/usr/bin/env python3
"""Bootstrap and dependency checks for qiaomu-ppt."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"
DEPENDENCY_MANIFEST = ROOT / "data" / "dependency_manifest.json"
FONT_MANIFEST = ROOT / "data" / "font_manifest.json"
FONTS_DIR = ROOT / "assets" / "fonts"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_command(command: str) -> dict:
    path = shutil.which(command)
    if not path:
        return {"name": command, "available": False, "path": ""}
    version = ""
    broken = False
    diagnostic = ""
    for args in ([command, "--version"], [command, "-v"]):
        try:
            proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
            output = proc.stdout.strip()
            if proc.returncode == 0 and output:
                version = output.splitlines()[0]
                broken = False
                break
            if proc.returncode in {126, 127} or "No such file or directory" in output:
                broken = True
                diagnostic = output.splitlines()[0] if output else f"{command} returned {proc.returncode}"
                continue
            if output and not diagnostic:
                diagnostic = output.splitlines()[0]
        except Exception as exc:
            diagnostic = str(exc)
            continue
    if broken:
        return {"name": command, "available": False, "path": path, "diagnostic": diagnostic}
    if not version and diagnostic:
        version = diagnostic
    return {"name": command, "available": True, "path": path, "version": version}


def python_version(python_executable: Path | str) -> str:
    try:
        proc = subprocess.run(
            [str(python_executable), "-c", "import sys; print(sys.version.split()[0])"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return sys.version.split()[0]


def check_python_packages(python_executable: Path | str | None = None) -> list[dict]:
    python_executable = python_executable or sys.executable
    packages: list[dict] = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        package_name = line.split(">=")[0].split("==")[0].split("[")[0].replace("-", "_")
        import_name = {
            "beautifulsoup4": "bs4",
            "python_pptx": "pptx",
            "Pillow": "PIL",
        }.get(package_name, package_name)
        proc = subprocess.run(
            [str(python_executable), "-c", f"import {import_name}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        available = proc.returncode == 0
        packages.append({"requirement": line, "import_name": import_name, "available": available})
    return packages


def resolve_venv_path(value: str | None) -> Path:
    if value:
        path = Path(value).expanduser()
    else:
        path = ROOT / ".venv"
    if not path.is_absolute():
        path = ROOT / path
    return path


def install_into_venv(venv_path: Path) -> tuple[int, Path]:
    print(f"Creating virtual environment: {venv_path}")
    create = subprocess.run([sys.executable, "-m", "venv", str(venv_path)])
    if create.returncode != 0:
        return create.returncode, Path(sys.executable)
    python = venv_path / "bin" / "python"
    cmd = [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    print("Running:", " ".join(cmd))
    install = subprocess.run(cmd)
    return install.returncode, python


def run_pip_install(user: bool, venv_path: Path | None = None) -> tuple[int, Path]:
    if venv_path:
        return install_into_venv(venv_path)
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    if user:
        cmd.append("--user")
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.returncode != 0 and "externally-managed-environment" in proc.stdout:
        print("Current Python is externally managed; falling back to local .venv.")
        return install_into_venv(ROOT / ".venv")
    return proc.returncode, Path(sys.executable)


def download_fonts(force: bool = False) -> list[dict]:
    manifest = load_json(FONT_MANIFEST)
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for font in manifest.get("fonts", []):
        target = FONTS_DIR / font["filename"]
        if target.exists() and target.stat().st_size > 1000 and not force:
            results.append({"filename": font["filename"], "status": "exists", "path": str(target)})
            continue
        try:
            request = urllib.request.Request(font["url"], headers={"User-Agent": "qiaomu-ppt-bootstrap/0.5"})
            with urllib.request.urlopen(request, timeout=60) as response:
                target.write_bytes(response.read())
            results.append({"filename": font["filename"], "status": "downloaded", "path": str(target)})
        except Exception as exc:
            results.append({"filename": font["filename"], "status": "failed", "error": str(exc)})
    return results


def dependency_report(python_executable: Path | str | None = None) -> dict:
    python_executable = python_executable or sys.executable
    manifest = load_json(DEPENDENCY_MANIFEST)
    commands = []
    for item in manifest.get("external_tools", []):
        names = item.get("commands", [])
        checks = [check_command(name) for name in names]
        commands.append({**item, "checks": checks, "available": any(check["available"] for check in checks)})
    fonts = []
    if FONT_MANIFEST.exists():
        for font in load_json(FONT_MANIFEST).get("fonts", []):
            target = FONTS_DIR / font["filename"]
            fonts.append({"filename": font["filename"], "available": target.exists(), "path": str(target)})
    return {
        "python": python_version(python_executable),
        "python_executable": str(python_executable),
        "requirements": str(REQUIREMENTS),
        "python_packages": check_python_packages(python_executable),
        "external_tools": commands,
        "fonts": fonts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check or install qiaomu-ppt runtime dependencies.")
    parser.add_argument("--install-python", action="store_true", help="Install requirements.txt into the current Python environment.")
    parser.add_argument("--user", action="store_true", help="Use pip --user when installing Python packages.")
    parser.add_argument("--venv", nargs="?", const=".venv", help="Install requirements into a local virtual environment, defaulting to .venv.")
    parser.add_argument("--download-fonts", action="store_true", help="Download open-source CJK fonts declared in data/font_manifest.json.")
    parser.add_argument("--force-fonts", action="store_true", help="Re-download fonts even if files already exist.")
    parser.add_argument("--check", action="store_true", help="Only print dependency status.")
    args = parser.parse_args()

    exit_code = 0
    python_for_report: Path | str = sys.executable
    if args.venv and not args.install_python:
        candidate = resolve_venv_path(args.venv) / "bin" / "python"
        if candidate.exists():
            python_for_report = candidate
    elif not args.install_python:
        candidate = ROOT / ".venv" / "bin" / "python"
        if candidate.exists():
            python_for_report = candidate
    if args.install_python:
        venv_path = resolve_venv_path(args.venv) if args.venv else None
        exit_code, python_for_report = run_pip_install(args.user, venv_path)
    if args.download_fonts:
        print(json.dumps({"font_downloads": download_fonts(force=args.force_fonts)}, ensure_ascii=False, indent=2))

    report = dependency_report(python_for_report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    required_missing = [
        item["name"]
        for item in report["external_tools"]
        if item.get("required") and not item.get("available")
    ]
    missing_packages = [
        item["requirement"]
        for item in report["python_packages"]
        if not item.get("available")
    ]
    if required_missing or missing_packages:
        print("Missing required runtime pieces:", file=sys.stderr)
        for item in required_missing:
            print(f"- external tool: {item}", file=sys.stderr)
        for item in missing_packages:
            print(f"- Python package: {item}", file=sys.stderr)
        exit_code = exit_code or 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
