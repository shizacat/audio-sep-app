"""Build the desktop app with PyInstaller.

macOS becomes ``dist/AudioSep-macos-arm64.dmg`` or ``dist/AudioSep-macos-x86_64.dmg``.
Windows becomes ``dist/AudioSep-windows.zip``.
Linux becomes ``dist/AudioSep-linux.zip``.
The same command is used locally and in GitHub Actions.
``build/`` is PyInstaller's work directory. The file there is not the app.
"""

import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_NAME = "AudioSep"
MODEL_FILES = ("separator.onnx", "clap_text.onnx")


def macos_archive_name(machine: str | None = None) -> str:
    """Disk image name for the CPU of the Python that runs the build.

    One image is not a universal binary. Intel and Apple Silicon are built separately.
    """
    machine = (machine or platform.machine()).lower()
    if machine in {"arm64", "aarch64"}:
        arch = "arm64"
    elif machine in {"x86_64", "amd64"}:
        arch = "x86_64"
    else:
        raise SystemExit(f"Неизвестная архитектура macOS: {machine}")
    return f"{APP_NAME}-macos-{arch}.dmg"


def macos_executable_dir(dist: Path) -> Path:
    """Directory that contains the frozen executable inside the .app bundle."""
    return dist / f"{APP_NAME}.app" / "Contents" / "MacOS"


def collect_dir(dist: Path) -> Path:
    """Directory that contains the frozen executable and the collected runtime."""
    return dist / APP_NAME


def place_models(models_dir: Path, source_dir: Path) -> list[str]:
    """Copy ONNX files into ``models_dir``. Missing files are skipped."""
    models_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in MODEL_FILES:
        source = source_dir / name
        if source.is_file():
            shutil.copy2(source, models_dir / name)
            copied.append(name)
    return copied


def assert_application(executable: Path, search_root: Path) -> None:
    if not executable.is_file():
        raise SystemExit(f"Исполняемый файл не найден: {executable}")
    if not list(search_root.rglob("tokenizer.json")):
        raise SystemExit(f"В пакете нет tokenizer.json: {search_root}")


def require_models(models_dir: Path) -> None:
    missing = [name for name in MODEL_FILES if not (models_dir / name).is_file()]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"В пакет нечего положить: нет {joined} в {models_dir}")


def create_dmg(app: Path, destination: Path, models_dir: Path) -> Path:
    """Write a disk image with the app, ``models`` beside it, and a link to /Applications."""
    if not app.is_dir():
        raise SystemExit(f"Приложение не найдено: {app}")
    require_models(models_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="audiosep-dmg-") as raw_stage:
        stage = Path(raw_stage)
        subprocess.run(["ditto", str(app), str(stage / app.name)], check=True)
        place_models(stage / "models", models_dir)
        (stage / "Applications").symlink_to("/Applications")
        if destination.exists():
            destination.unlink()
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                APP_NAME,
                "-srcfolder",
                str(stage),
                "-ov",
                "-format",
                "UDZO",
                str(destination),
            ],
            check=True,
        )
    return destination


def create_zip(collected: Path, destination: Path, models_dir: Path) -> Path:
    """Zip a folder with ``models`` next to the executable."""
    if not collected.is_dir():
        raise SystemExit(f"Каталог приложения не найден: {collected}")
    require_models(models_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    place_models(collected / "models", models_dir)
    if destination.exists():
        destination.unlink()
    archive = shutil.make_archive(
        str(destination.with_suffix("")),
        "zip",
        root_dir=collected.parent,
        base_dir=collected.name,
    )
    return Path(archive)


def run_pyinstaller(root: Path) -> None:
    spec = root / "bundle" / "audiosep.spec"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec)],
        cwd=root,
        check=True,
    )


def build_macos(root: Path) -> Path:
    run_pyinstaller(root)
    executable_dir = macos_executable_dir(root / "dist")
    app = executable_dir.parent.parent
    assert_application(executable_dir / APP_NAME, app)
    image = create_dmg(app, root / "dist" / macos_archive_name(), root / "local")
    print(f"Модели в образе: {', '.join(MODEL_FILES)}")
    print(image)
    return image


def build_directory(root: Path, executable_name: str, archive_name: str) -> Path:
    run_pyinstaller(root)
    collected = collect_dir(root / "dist")
    assert_application(collected / executable_name, collected)
    archive = create_zip(collected, root / "dist" / archive_name, root / "local")
    print(f"Модели в архиве: {', '.join(MODEL_FILES)}")
    print(archive)
    return archive


def build_windows(root: Path) -> Path:
    return build_directory(root, f"{APP_NAME}.exe", f"{APP_NAME}-windows.zip")


def build_linux(root: Path) -> Path:
    return build_directory(root, APP_NAME, f"{APP_NAME}-linux.zip")


def build(root: Path) -> Path:
    if sys.platform == "darwin":
        return build_macos(root)
    if sys.platform == "win32":
        return build_windows(root)
    if sys.platform == "linux":
        return build_linux(root)
    raise SystemExit("Сборка пакета реализована для Linux, macOS и Windows.")


def main() -> None:
    build(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
