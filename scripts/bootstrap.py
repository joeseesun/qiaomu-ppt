#!/usr/bin/env python3
"""Bootstrap and dependency checks for qiaomu-ppt."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"
DEPENDENCY_MANIFEST = ROOT / "data" / "dependency_manifest.json"
FONT_MANIFEST = ROOT / "data" / "font_manifest.json"
FONTS_DIR = ROOT / "assets" / "fonts"
FONT_SIGNATURES = (b"OTTO", b"ttcf", b"\x00\x01\x00\x00")
LIBREOFFICE_MAC_PATHS = (
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_command_paths(command: str) -> list[str]:
    candidates: list[str] = []
    path = shutil.which(command)
    if path:
        candidates.append(path)
    if sys.platform == "darwin" and command in {"soffice", "libreoffice"}:
        for candidate in LIBREOFFICE_MAC_PATHS:
            if candidate.exists():
                candidates.append(str(candidate))
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def check_command(command: str) -> dict:
    paths = resolve_command_paths(command)
    if not paths:
        return {"name": command, "available": False, "path": ""}
    first_diagnostic = ""
    for path in paths:
        version = ""
        diagnostic = ""
        broken = False
        for args in ([path, "--version"], [path, "-v"]):
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
            first_diagnostic = first_diagnostic or diagnostic
            continue
        if not version and diagnostic:
            version = diagnostic
        return {"name": command, "available": True, "path": path, "version": version}
    return {"name": command, "available": False, "path": paths[0], "diagnostic": first_diagnostic}


def system_install_key() -> str | None:
    if sys.platform == "darwin":
        return "macos_install"
    if sys.platform.startswith("linux") and (shutil.which("apt-get") or shutil.which("apt")):
        return "ubuntu_install"
    return None


def install_command_for(item: dict) -> str:
    key = system_install_key()
    command = str(item.get(key or "", "")).strip() if key else ""
    if not command:
        command = str(item.get("install", "")).strip()
    if " or " in command:
        command = command.split(" or ", 1)[0].strip()
    return command


def runnable_install_command(command: str) -> tuple[list[str] | str, bool]:
    if any(token in command for token in ("&&", "||", ";", "|")):
        return command, True
    args = shlex.split(command)
    if len(args) >= 3 and args[0] == "sudo" and args[1] in {"apt-get", "apt"} and args[2] == "install" and "-y" not in args:
        args.insert(3, "-y")
    elif len(args) >= 2 and args[0] in {"apt-get", "apt"} and args[1] == "install" and "-y" not in args:
        args.insert(2, "-y")
    return args, False


def run_system_installs(include_optional: bool = False) -> list[dict]:
    manifest = load_json(DEPENDENCY_MANIFEST)
    results: list[dict] = []
    for item in manifest.get("external_tools", []):
        required = bool(item.get("required"))
        if not required and not include_optional:
            continue
        checks = [check_command(name) for name in item.get("commands", [])]
        if any(check["available"] for check in checks):
            results.append({"name": item.get("name", ""), "status": "already_available"})
            continue
        command = install_command_for(item)
        if not command:
            results.append({
                "name": item.get("name", ""),
                "status": "unsupported_platform",
                "message": "No install command is declared for this platform.",
            })
            continue
        runnable, use_shell = runnable_install_command(command)
        shown = command if isinstance(runnable, str) else " ".join(runnable)
        print(f"Installing {item.get('name', '')}: {shown}")
        proc = subprocess.run(runnable, shell=use_shell)
        post_checks = [check_command(name) for name in item.get("commands", [])]
        results.append({
            "name": item.get("name", ""),
            "command": shown,
            "returncode": proc.returncode,
            "status": "installed" if proc.returncode == 0 and any(check["available"] for check in post_checks) else "failed",
            "checks": post_checks,
        })
    return results


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


def is_valid_font_file(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 1000:
        return False
    try:
        with path.open("rb") as handle:
            signature = handle.read(4)
    except OSError:
        return False
    return signature in FONT_SIGNATURES


def archive_format_for(font: dict) -> str:
    declared = str(font.get("archive_format", "")).lower().strip()
    if declared:
        return declared
    archive_url = str(font.get("archive_url", ""))
    return Path(archive_url.split("?", 1)[0]).suffix.lower().lstrip(".")


def extract_7z_member(archive_path: Path, member: str, target: Path) -> None:
    bsdtar = shutil.which("bsdtar")
    if bsdtar:
        with target.open("wb") as output:
            proc = subprocess.run(
                [bsdtar, "-xOf", str(archive_path), member],
                stdout=output,
                stderr=subprocess.PIPE,
                text=True,
                timeout=180,
            )
        if proc.returncode == 0:
            return
        target.unlink(missing_ok=True)
        raise RuntimeError(proc.stderr.strip() or f"bsdtar failed to extract {member}")

    for command in ("7zz", "7z"):
        tool = shutil.which(command)
        if not tool:
            continue
        with target.open("wb") as output:
            proc = subprocess.run(
                [tool, "x", "-so", str(archive_path), member],
                stdout=output,
                stderr=subprocess.PIPE,
                text=True,
                timeout=180,
            )
        if proc.returncode == 0:
            return
        target.unlink(missing_ok=True)
        raise RuntimeError(proc.stderr.strip() or f"{command} failed to extract {member}")

    raise RuntimeError("extracting .7z font archives requires bsdtar, 7zz, or 7z")


def download_archive(archive_url: str, archive_path: Path) -> None:
    request = urllib.request.Request(archive_url, headers={"User-Agent": "qiaomu-ppt-bootstrap/0.5"})
    with urllib.request.urlopen(request, timeout=120) as response:
        archive_path.write_bytes(response.read())


def extract_archive_member(font: dict, archive_path: Path, target: Path) -> None:
    member = font.get("archive_member")
    if not member:
        raise ValueError(f"{font['filename']} declares archive_url without archive_member")
    archive_format = archive_format_for(font)
    if archive_format == "7z":
        extract_7z_member(archive_path, member, target)
    else:
        with zipfile.ZipFile(archive_path) as archive:
            try:
                with archive.open(member) as source:
                    target.write_bytes(source.read())
            except KeyError as exc:
                raise FileNotFoundError(f"{member} not found in {font['archive_url']}") from exc


def download_font_file(
    font: dict,
    target: Path,
    archive_cache: dict[str, Path] | None = None,
    archive_dir: Path | None = None,
) -> None:
    if font.get("archive_url"):
        archive_url = font["archive_url"]
        archive_format = archive_format_for(font)
        if archive_cache is not None and archive_dir is not None:
            archive_path = archive_cache.get(archive_url)
            if archive_path is None:
                archive_path = archive_dir / f"font-archive-{len(archive_cache)}.{archive_format or 'zip'}"
                download_archive(archive_url, archive_path)
                archive_cache[archive_url] = archive_path
            extract_archive_member(font, archive_path, target)
            return

        with tempfile.TemporaryDirectory(prefix="qiaomu-ppt-font-") as tmpdir:
            archive_path = Path(tmpdir) / f"font-archive.{archive_format or 'zip'}"
            download_archive(archive_url, archive_path)
            extract_archive_member(font, archive_path, target)
        return

    request = urllib.request.Request(font["url"], headers={"User-Agent": "qiaomu-ppt-bootstrap/0.5"})
    with urllib.request.urlopen(request, timeout=60) as response:
        target.write_bytes(response.read())


def download_fonts(force: bool = False) -> list[dict]:
    manifest = load_json(FONT_MANIFEST)
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="qiaomu-ppt-font-cache-") as tmpdir:
        archive_cache: dict[str, Path] = {}
        archive_dir = Path(tmpdir)
        for font in manifest.get("fonts", []):
            target = FONTS_DIR / font["filename"]
            if is_valid_font_file(target) and not force:
                results.append({"filename": font["filename"], "status": "exists", "path": str(target)})
                continue
            try:
                download_font_file(font, target, archive_cache=archive_cache, archive_dir=archive_dir)
                if not is_valid_font_file(target):
                    target.unlink(missing_ok=True)
                    results.append({"filename": font["filename"], "status": "failed", "error": "downloaded file is not a valid OTF/TTF/TTC font"})
                    continue
                results.append({"filename": font["filename"], "status": "downloaded", "path": str(target)})
            except Exception as exc:
                results.append({"filename": font["filename"], "status": "failed", "error": str(exc)})
    return results


def install_fonts_to_user() -> list[dict]:
    """Install bundled/downloaded fonts into the current user's macOS font folder."""
    manifest = load_json(FONT_MANIFEST)
    user_fonts = Path.home() / "Library" / "Fonts"
    user_fonts.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for font in manifest.get("fonts", []):
        source = FONTS_DIR / font["filename"]
        if not is_valid_font_file(source):
            results.append({
                "filename": font["filename"],
                "family": font.get("family", ""),
                "status": "missing_source",
                "source": str(source),
            })
            continue
        target = user_fonts / font["filename"]
        try:
            shutil.copy2(source, target)
            results.append({
                "filename": font["filename"],
                "family": font.get("family", ""),
                "status": "installed",
                "path": str(target),
            })
        except Exception as exc:
            results.append({
                "filename": font["filename"],
                "family": font.get("family", ""),
                "status": "failed",
                "error": str(exc),
            })
    return results


def registered_font_families() -> list[str]:
    try:
        proc = subprocess.run(
            ["atsutil", "fonts", "-list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=20,
        )
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    families: list[str] = []
    for line in proc.stdout.splitlines():
        value = line.strip()
        if value:
            families.append(value)
    return families


def verify_registered_fonts() -> list[dict]:
    manifest = load_json(FONT_MANIFEST)
    registered = {family.lower() for family in registered_font_families()}
    seen: set[str] = set()
    results: list[dict] = []
    for font in manifest.get("fonts", []):
        family = str(font.get("family", "")).strip()
        if not family or family in seen:
            continue
        seen.add(family)
        target = family.lower()
        results.append({
            "family": family,
            "registered": any(target == item or target in item for item in registered),
        })
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
            fonts.append({
                "family": font.get("family", ""),
                "style": font.get("style", ""),
                "filename": font["filename"],
                "available": is_valid_font_file(target),
                "path": str(target),
            })
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
    parser.add_argument("--install-system", action="store_true", help="Install missing required external tools using Homebrew on macOS or apt on Ubuntu/Debian.")
    parser.add_argument("--include-optional-system", action="store_true", help="With --install-system, also install missing optional external tools declared in data/dependency_manifest.json.")
    parser.add_argument("--download-fonts", action="store_true", help="Download open-source PPT fonts declared in data/font_manifest.json.")
    parser.add_argument("--install-fonts", action="store_true", help="Install bundled/downloaded fonts into ~/Library/Fonts on macOS.")
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
    if args.install_system:
        print(json.dumps({
            "system_installs": run_system_installs(include_optional=args.include_optional_system),
        }, ensure_ascii=False, indent=2))
    if args.download_fonts:
        print(json.dumps({"font_downloads": download_fonts(force=args.force_fonts)}, ensure_ascii=False, indent=2))
    if args.install_fonts:
        print(json.dumps({
            "font_installs": install_fonts_to_user(),
            "registered_fonts": verify_registered_fonts(),
        }, ensure_ascii=False, indent=2))

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
        missing_external = [
            item
            for item in report["external_tools"]
            if item.get("required") and not item.get("available")
        ]
        for item in missing_external:
            install_hint = install_command_for(item)
            suffix = f" (install: {install_hint})" if install_hint else ""
            print(f"- external tool: {item['name']}{suffix}", file=sys.stderr)
            download_url = str(item.get("download_url") or item.get("homepage") or "").strip()
            if download_url:
                print(f"  official download: {download_url}", file=sys.stderr)
            note = str(item.get("official_download_note") or "").strip()
            if note:
                print(f"  note: {note}", file=sys.stderr)
        for item in missing_packages:
            print(f"- Python package: {item}", file=sys.stderr)
        exit_code = exit_code or 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
