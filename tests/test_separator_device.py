from collections.abc import Sequence

import pytest

from audiosep_app.infer import Provider, choose_separator_session, gpu_providers


class _Session:
    def __init__(self, providers: list[str]) -> None:
        self.providers = providers

    def get_providers(self) -> list[str]:
        return self.providers


def _name(provider: Provider) -> str:
    if isinstance(provider, tuple):
        return provider[0]
    return provider


def test_macos_requests_coreml_gpu() -> None:
    providers = gpu_providers(
        ["CoreMLExecutionProvider", "CPUExecutionProvider"],
        "darwin",
    )

    assert len(providers) == 1
    assert providers[0][0] == "CoreMLExecutionProvider"
    assert providers[0][1] == {"ModelFormat": "MLProgram", "MLComputeUnits": "CPUAndGPU"}


def test_windows_tries_cuda_before_directml() -> None:
    providers = gpu_providers(
        ["DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
        "win32",
    )

    assert [_name(provider) for provider in providers] == [
        "CUDAExecutionProvider",
        "DmlExecutionProvider",
    ]


def test_linux_tries_cuda_before_rocm() -> None:
    providers = gpu_providers(
        ["ROCMExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
        "linux",
    )

    assert [_name(provider) for provider in providers] == [
        "CUDAExecutionProvider",
        "ROCMExecutionProvider",
    ]


def test_missing_gpu_provider_is_skipped() -> None:
    assert gpu_providers(["CPUExecutionProvider"], "linux") == ()
    assert gpu_providers(["CPUExecutionProvider"], "win32") == ()
    assert gpu_providers(["CPUExecutionProvider"], "darwin") == ()


def test_cpu_flag_skips_an_available_gpu() -> None:
    opened: list[Sequence[Provider]] = []

    def open_session(path: str, providers: Sequence[Provider]) -> _Session:
        opened.append(providers)
        return _Session(["CPUExecutionProvider"])

    session = choose_separator_session(
        "separator.onnx",
        cpu=True,
        available=["CoreMLExecutionProvider", "CPUExecutionProvider"],
        system="darwin",
        open_session=open_session,
    )

    assert session.get_providers() == ["CPUExecutionProvider"]
    assert opened == [["CPUExecutionProvider"]]


def test_failed_cuda_falls_back_to_directml() -> None:
    def open_session(path: str, providers: Sequence[Provider]) -> _Session:
        if _name(providers[0]) == "CUDAExecutionProvider":
            raise RuntimeError("no CUDA device")
        return _Session([_name(providers[0]), "CPUExecutionProvider"])

    session = choose_separator_session(
        "separator.onnx",
        cpu=False,
        available=["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"],
        system="win32",
        open_session=open_session,
    )

    assert session.get_providers() == ["DmlExecutionProvider", "CPUExecutionProvider"]


def test_provider_that_drops_out_tries_rocm() -> None:
    def open_session(path: str, providers: Sequence[Provider]) -> _Session:
        name = _name(providers[0])
        if name == "CUDAExecutionProvider":
            return _Session(["CPUExecutionProvider"])
        return _Session([name, "CPUExecutionProvider"])

    session = choose_separator_session(
        "separator.onnx",
        cpu=False,
        available=["CUDAExecutionProvider", "ROCMExecutionProvider", "CPUExecutionProvider"],
        system="linux",
        open_session=open_session,
    )

    assert session.get_providers()[0] == "ROCMExecutionProvider"


def test_every_gpu_failure_ends_on_cpu() -> None:
    def open_session(path: str, providers: Sequence[Provider]) -> _Session:
        if _name(providers[0]) != "CPUExecutionProvider":
            raise RuntimeError("device missing")
        return _Session(["CPUExecutionProvider"])

    session = choose_separator_session(
        "separator.onnx",
        cpu=False,
        available=["CUDAExecutionProvider", "ROCMExecutionProvider", "CPUExecutionProvider"],
        system="linux",
        open_session=open_session,
    )

    assert session.get_providers() == ["CPUExecutionProvider"]


def test_cpu_failure_is_not_hidden() -> None:
    def open_session(path: str, providers: Sequence[Provider]) -> _Session:
        raise RuntimeError("bad model")

    with pytest.raises(RuntimeError, match="bad model"):
        choose_separator_session(
            "separator.onnx",
            cpu=True,
            available=["CPUExecutionProvider"],
            system="linux",
            open_session=open_session,
        )
