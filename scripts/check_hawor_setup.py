"""Inspect the HaWoR execution machine; write only a new JSON evidence file.

Run with the hawor Conda Python from the repository root. The checker starts with
only the standard library; missing dependencies become failed checks.
"""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile


from egocentric_pipeline.hawor_runner import HAWOR_REVISION, WEIGHTS, MANO
from egocentric_pipeline.run_metadata import redact, sha256_file as sha256, utc_now, write_json


def command(args, cwd, timeout=120):
    """Inspect only explicitly named commands; never capture the full environment."""
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {"command": args, "returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": args, "returncode": None, "error": str(error)}


def inspect_environment_spec(path):
    """Compare the reviewed pip pins with installed distributions and Git origins.

    Package extras are resolver inputs, not separate installed distributions;
    this check compares their owning package version only. CUDA execution and
    the source-built DROID/LieTorch extensions have separate preflight checks.
    """
    evidence = {"path": str(path), "sha256": None, "packages": [], "mismatches": []}
    try:
        evidence["sha256"] = sha256(path)
        specification_text = path.read_text(encoding="utf-8")
    except OSError as error:
        evidence["mismatches"].append(f"Cannot read environment specification: {error}")
        return evidence

    try:
        import yaml
        from packaging.requirements import Requirement
    except ImportError as error:
        evidence["mismatches"].append(
            f"Cannot verify environment pins: {error}. Complete the PyYAML/packaging installation and rerun."
        )
        return evidence

    try:
        specification = yaml.safe_load(specification_text)
        dependencies = specification["dependencies"]
        if not isinstance(dependencies, list):
            raise ValueError("dependencies must be a list")
        pip_sections = [entry["pip"] for entry in dependencies if isinstance(entry, dict) and "pip" in entry]
        if len(pip_sections) != 1 or not isinstance(pip_sections[0], list):
            raise ValueError("expected exactly one pip dependency list")
    except (yaml.YAMLError, KeyError, TypeError, ValueError) as error:
        evidence["mismatches"].append(f"Invalid environment specification: {error}")
        return evidence

    for declaration in pip_sections[0]:
        if isinstance(declaration, str) and declaration.startswith("--"):
            continue
        package = {"declaration": declaration, "passed": False}
        evidence["packages"].append(package)
        try:
            requirement = Requirement(declaration)
            package["name"] = requirement.name
            distribution = importlib.metadata.distribution(requirement.name)
            package["actual_version"] = distribution.version
            if requirement.url:
                repository, revision = requirement.url.removeprefix("git+").rsplit("@", 1)
                if not requirement.url.startswith("git+") or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
                    raise ValueError("Git dependencies must specify a full commit SHA")
                package["expected_repository"] = repository
                package["expected_commit"] = revision
                origin = json.loads(distribution.read_text("direct_url.json") or "{}")
                vcs = origin.get("vcs_info", {})
                package["actual_repository"] = origin.get("url")
                package["actual_commit"] = vcs.get("commit_id")
                package["passed"] = (
                    origin.get("url") == repository
                    and vcs.get("vcs") == "git"
                    and vcs.get("commit_id") == revision
                )
                if not package["passed"]:
                    raise ValueError(
                        f"expected Git origin {repository}@{revision}; installed origin is "
                        f"{origin.get('url')}@{vcs.get('commit_id')} ({vcs.get('vcs')})"
                    )
            else:
                pins = list(requirement.specifier)
                if len(pins) != 1 or pins[0].operator != "==" or "*" in pins[0].version:
                    raise ValueError("every package must have one exact == version pin")
                package["expected_version"] = pins[0].version
                package["passed"] = distribution.version in requirement.specifier
                if not package["passed"]:
                    raise ValueError(f"expected {pins[0].version}; installed {distribution.version}")
        except (importlib.metadata.PackageNotFoundError, TypeError, ValueError, AttributeError) as error:
            package["passed"] = False
            package["error"] = str(error)
            evidence["mismatches"].append(f"{package.get('name', declaration)}: {error}")

    if not evidence["packages"]:
        evidence["mismatches"].append("Environment specification contains no pip package pins")
    return evidence


def inspect_setup(root, output_parent, ego4d_source=None):
    upstream = root / "external/HaWoR"
    checks = []
    warnings = []

    def record(name, passed, evidence):
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)

    record("linux", platform.system() == "Linux", {"system": platform.system(), "release": platform.release()})
    record("python_3_10", sys.version_info[:2] == (3, 10), {"version": sys.version, "executable": sys.executable})
    conda_prefix = Path(sys.prefix)
    record("hawor_conda_environment", (conda_prefix / "conda-meta/history").is_file() and conda_prefix.name == "hawor", str(conda_prefix))
    free_bytes = shutil.disk_usage(root).free
    record("free_storage", free_bytes >= 40 * 1024**3, {"free_bytes": free_bytes, "required_bytes": 40 * 1024**3})
    ram = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
            ram[key + "_bytes"] = int(value.split()[0]) * 1024
    record("system_memory", bool(ram.get("MemTotal_bytes")), ram)
    for name, args in {
        "git": ["git", "--version"], "ffmpeg": ["ffmpeg", "-version"],
        "ffprobe": ["ffprobe", "-version"], "nvcc": ["nvcc", "--version"],
        "gcc": ["gcc-11", "--version"], "g++": ["g++-11", "--version"],
        "ninja": ["ninja", "--version"], "cmake": ["cmake", "--version"],
    }.items():
        evidence = command(args, root)
        record(name, evidence["returncode"] == 0, evidence)
        if name == "nvcc":
            release = re.search(r"release (\d+\.\d+)", evidence.get("stdout", ""))
            record("cuda_compiler_11_7", release is not None and release.group(1) == "11.7", evidence)

    evidence = command(["git", "rev-parse", "HEAD"], upstream)
    record("hawor_revision", evidence.get("stdout") == HAWOR_REVISION, evidence)
    evidence = command(["git", "status", "--porcelain", "--untracked-files=no"], upstream)
    record("hawor_source_unchanged", evidence["returncode"] == 0 and not evidence.get("stdout"), evidence)
    evidence = command(["git", "submodule", "status", "--recursive"], upstream)
    lines = evidence.get("stdout", "").splitlines()
    record("nested_submodules", evidence["returncode"] == 0 and len(lines) >= 3 and all(line[0] not in "-+U" for line in lines), evidence)

    packages = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if name:
            packages[name] = distribution.version
    evidence = inspect_environment_spec(root / "environment/hawor.yml")
    record("environment_specification", not evidence["mismatches"], evidence)
    for mismatch in evidence["mismatches"]:
        print(f"  {mismatch}", flush=True)
    evidence = command([sys.executable, "-m", "pip", "check"], root)
    record("pip_consistency", evidence["returncode"] == 0, evidence)

    gpu_code = (
        "import json, torch; "
        "assert torch.cuda.is_available(), 'CUDA unavailable: check GPU access outside the sandbox'; "
        "x = torch.ones(8, device='cuda') * 2; torch.cuda.synchronize(); "
        "assert x.sum().item() == 16; "
        "layer = torch.nn.Conv2d(3, 8, 3).cuda(); "
        "result = layer(torch.ones(1, 3, 32, 32, device='cuda')); torch.cuda.synchronize(); "
        "assert torch.isfinite(result).all().item(); "
        "print(json.dumps({'torch_cuda': torch.version.cuda, 'name': torch.cuda.get_device_name(0), "
        "'capability': torch.cuda.get_device_capability(0), 'free_total_bytes': torch.cuda.mem_get_info()}))"
    )
    evidence = command([sys.executable, "-c", gpu_code], root)
    record("cuda_allocation", evidence["returncode"] == 0, evidence)
    if evidence["returncode"] == 0:
        gpu = json.loads(evidence["stdout"].splitlines()[-1])
        record("cuda_runtime_11_7", gpu["torch_cuda"] == "11.7", gpu)
        if gpu["free_total_bytes"][1] < 16 * 1024**3:
            warnings.append("GPU has less than 16 GiB VRAM; unchanged bundled inference must prove feasibility.")
    evidence = command(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used", "--format=csv,noheader"], root)
    record("nvidia_driver", evidence["returncode"] == 0, evidence)

    imports = (
        "import torch, torchvision; from pytorch3d import _C; "
        "import droid_backends, lietorch, lietorch_backends, torch_scatter; "
        "import smplx, mmcv, mmengine, timm, ultralytics, pytorch_lightning; "
        "import pyrender, aitviewer, moderngl_window; print('imports passed')"
    )
    evidence = command([sys.executable, "-c", imports], upstream)
    record("upstream_imports", evidence["returncode"] == 0, evidence)

    for relative in WEIGHTS + MANO:
        path = upstream / relative
        try:
            with path.open("rb") as stream:
                readable = bool(stream.read(1))
            evidence = {"path": str(path), "size_bytes": path.stat().st_size}
            evidence["sha256"] = sha256(path)
            record(relative, readable, evidence)
        except OSError as error:
            record(relative, False, {"path": str(path), "error": str(error)})

    videos = [upstream / "example/video_0.mp4"]
    if ego4d_source is not None:
        videos.append(ego4d_source)
    for path in videos:
        evidence = command(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                            "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_read_frames,duration", "-of", "json", str(path)], root)
        decode = command(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"], root)
        evidence["decode"] = decode
        if path.is_file():
            evidence["sha256"] = sha256(path)
        record("decode_" + path.name, path.suffix.lower() == ".mp4" and evidence["returncode"] == 0 and decode["returncode"] == 0, evidence)

    try:
        with tempfile.TemporaryDirectory(prefix=".setup-write-check-", dir=output_parent):
            pass
        record("output_writable", True, str(output_parent))
    except OSError as error:
        record("output_writable", False, str(error))

    package_path = root / "src/egocentric_pipeline/__init__.py"
    if package_path.is_file():
        code = "import egocentric_pipeline; print(egocentric_pipeline.__file__)"
        evidence = command([sys.executable, "-c", code], root)
        record("source_tree_import", evidence.get("stdout") == str(package_path), evidence)
    else:
        warnings.append("Project package is not implemented yet; source-tree import validation is deferred until Phase 0 passes.")
    warnings.append("This preflight does not prove inference or headless rendering; the setup gate also requires a fresh bundled run and inspected render artifacts.")
    return {"schema_version": "1.0", "created_at": utc_now(),
            "repository": str(root), "preflight_passed": all(item["passed"] for item in checks),
            "checks": checks, "packages": dict(sorted(packages.items())), "warnings": warnings,
            "runtime_environment": {name: os.environ.get(name) for name in ("CUDA_HOME", "CC", "CXX", "CUDAHOSTCXX", "LD_LIBRARY_PATH", "PYOPENGL_PLATFORM", "PYTHONPATH")},
            "smoke_inference_verified": False, "headless_rendering_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New setup_check.json path; an existing file is never overwritten")
    parser.add_argument("--ego4d-source", type=Path, help="Optional acquired Ego4D MP4 to decode and hash")
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Evidence file already exists: {args.output}; choose a new path")
    root = Path(__file__).resolve().parents[1]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = inspect_setup(root, args.output.parent, args.ego4d_source)
    write_json(args.output, redact(report))
    for warning in report["warnings"]:
        print(f"WARNING {warning}")
    print(f"Evidence: {args.output.resolve()}")
    return 0 if report["preflight_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
