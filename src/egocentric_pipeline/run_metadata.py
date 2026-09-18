"""Small shared provenance helpers; no video processing or model logic."""

from datetime import datetime, timezone
import copy
import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid


SCHEMA_VERSION = "1.0"
_SECRET_KEY = re.compile(r"password|secret|token|credential|authorization|api[_-]?key|access[_-]?key", re.I)
GPU_QUERY_TIMEOUT_S = 3.0


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path, data, overwrite=False):
    """Publish complete finite JSON atomically; default refuses any existing file."""
    path = Path(path)
    payload = json.dumps(data, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + "-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            # Same-filesystem hard link creates the final name exclusively.
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def new_run_directory(output_root):
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = output_root / (stamp + "-" + uuid.uuid4().hex[:12])
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue
    raise FileExistsError("Could not allocate a unique run directory; inspect the output root")


def redact(value):
    """Redact named secrets and URL credentials in logged command/environment data."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if _SECRET_KEY.search(str(key)) else redact(item)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        result = []
        hide_next = False
        for item in value:
            if hide_next:
                result.append("[REDACTED]")
                hide_next = False
            elif isinstance(item, str) and item.startswith("-") and _SECRET_KEY.search(item.split("=", 1)[0]):
                flag, separator, _ = item.partition("=")
                result.append(flag + "=[REDACTED]" if separator else flag)
                hide_next = not separator
            else:
                result.append(redact(item))
        return result
    if isinstance(value, str):
        value = re.sub(r"(https?://)[^/@\s]+@", r"\1[REDACTED]@", value)
        value = re.sub(r"(?i)([?&](?:token|password|secret|api[-_]key|x-amz-signature|x-amz-credential)=)[^&#\s]+", r"\1[REDACTED]", value)
        return re.sub(r"(?i)(--(?:token|password|secret|api[-_]key)(?:=|\s+))\S+", r"\1[REDACTED]", value)
    return value


def capture_environment(repository_root):
    repository_root = Path(repository_root).resolve()
    packages = {distribution.metadata["Name"]: distribution.version
                for distribution in importlib.metadata.distributions()
                if distribution.metadata.get("Name")}
    status, file_hashes, dirty, state_error = [], {}, None, None
    project_roots = ("src", "scripts", "tests", "environment", "configs", ".github/workflows")
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository_root,
                                capture_output=True, text=True, check=False)
        revision = result.stdout.strip() if result.returncode == 0 else None
        result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                                cwd=repository_root, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            dirty = bool(result.stdout.strip())
            # Record project paths only; names of unrelated inputs are not needed.
            status = [line for line in result.stdout.splitlines()
                      if any(line[3:].startswith(root + "/") for root in project_roots)
                      and not _SECRET_KEY.search(line[3:])]
        else:
            state_error = result.stderr.strip() or "Git worktree status is unavailable"
        result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z",
                                 "--", *project_roots], cwd=repository_root, capture_output=True, check=False)
        if result.returncode == 0:
            for name in sorted(set(os.fsdecode(item) for item in result.stdout.split(b"\0") if item)):
                path = repository_root / name
                if (_SECRET_KEY.search(name) or path.is_symlink() or not path.is_file()
                        or path.suffix.lower() not in (".py", ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".txt", ".md")
                        or not any(path.resolve().is_relative_to(repository_root / root) for root in project_roots)):
                    continue
                file_hashes[name] = sha256_file(path)
        else:
            state_error = result.stderr.decode(errors="replace").strip() or "Git project file inventory is unavailable"
    except OSError as error:
        revision = None
        state_error = str(error) or type(error).__name__
    environment = {name: os.environ.get(name) for name in (
        "CUDA_HOME", "CC", "CXX", "CUDAHOSTCXX", "LD_LIBRARY_PATH", "PYTHONPATH",
        "PYOPENGL_PLATFORM", "DISPLAY", "CONDA_PREFIX", "CUDA_VISIBLE_DEVICES")}
    specification = repository_root / "environment/hawor.yml"
    return {"python": sys.version, "executable": sys.executable,
            "platform": platform.platform(), "packages": packages,
            "repository_commit": revision, "repository_dirty": dirty,
            "repository_status": status, "repository_state_unavailable_reason": state_error,
            "project_file_sha256": file_hashes,
            "project_file_scope": "Tracked and untracked project code, scripts, tests, environment/configuration and CI files; excludes external/data/outputs, symlinks and secret-named paths",
            "environment_specification": {"path": str(specification), "sha256": file_hashes["environment/hawor.yml"]}
            if "environment/hawor.yml" in file_hashes else None,
            "variables": redact(environment)}


class ResourceMonitor:
    """Sample a PID and its descendants without importing model/GPU libraries.

    Device GPU measurements include other applications. Process-tree RSS can
    count shared pages more than once; sampled peaks can miss shorter spikes.
    """

    def __init__(self, sample_interval_s=0.5, pid=None):
        if isinstance(sample_interval_s, bool) or not isinstance(sample_interval_s, (int, float)) or not math.isfinite(sample_interval_s) or sample_interval_s <= 0:
            raise ValueError("Resource sampling interval must be positive finite seconds")
        if pid is not None and (type(pid) is not int or pid <= 0):
            raise ValueError("Resource monitor PID must be a positive integer")
        self.pid = os.getpid() if pid is None else pid
        self.sample_interval_s = float(sample_interval_s)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        self._started = None
        self._process = None
        self._resources = {
            "pid": self.pid, "sample_interval_s": self.sample_interval_s,
            "started_at": None, "finished_at": None, "duration_s": None,
            "samples": [], "peak_process_tree_rss_bytes": None,
            "process_tree_rss_unavailable_reason": "RAM has not been sampled",
            "peak_process_gpu_memory_bytes": None,
            "process_gpu_memory_unavailable_reason": "Per-process GPU accounting is not collected; device-wide samples include other applications",
            "peak_device_gpu_memory_bytes": None, "peak_device_gpu_utilization_percent": None,
            "gpu_identity": None, "gpu_sampling_error": "GPU devices have not been sampled",
            "ram_sampling_error": None, "sampling_error": None,
            "ram_scope": f"Sampled sum of RSS for PID {self.pid} and recursive descendants, including the root; shared pages may be counted more than once",
            "gpu_scope": "Device-wide nvidia-smi measurements from all returned GPUs; includes other applications and is not attributed to this process",
            "peak_limitation": "Sampled peaks may miss spikes between observations",
        }

    def start(self):
        if self._thread is not None or self._resources["finished_at"] is not None:
            raise RuntimeError("A ResourceMonitor can only be started once")
        try:
            import psutil

            self._psutil = psutil
            try:
                self._process = psutil.Process(self.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as error:
                self._resources["ram_sampling_error"] = str(error) or type(error).__name__
            self._started = time.monotonic()
            self._resources["started_at"] = utc_now()
            self._thread = threading.Thread(target=self._run, name=f"resource-monitor-{self.pid}", daemon=True)
            self._thread.start()
        except Exception as error:
            reason = f"Resource monitor failed to start: {type(error).__name__}: {error}"
            self._resources.update(sampling_error=reason, process_tree_rss_unavailable_reason=reason,
                                   gpu_sampling_error=reason)
            raise
        return self

    def _run(self):
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                self._sample()
            except Exception as error:
                # Observation failures must not terminate the pipeline being measured.
                with self._lock:
                    reason = f"{type(error).__name__}: {error}"
                    self._resources["sampling_error"] = reason
                    if self._resources["peak_process_tree_rss_bytes"] is None:
                        self._resources["process_tree_rss_unavailable_reason"] = reason
                    if self._resources["peak_device_gpu_memory_bytes"] is None:
                        self._resources["gpu_sampling_error"] = reason
            self._stop.wait(max(0, self.sample_interval_s - (time.monotonic() - started)))

    def _sample(self):
        started, observed_at = time.monotonic(), utc_now()
        rss, ram_error = None, None
        try:
            if self._process is None:
                raise self._psutil.NoSuchProcess(self.pid)
            members = [self._process] + self._process.children(recursive=True)
            rss = 0
            measured = 0
            for member in members:
                try:
                    rss += member.memory_info().rss
                    measured += 1
                except self._psutil.NoSuchProcess:
                    continue
            if not measured:
                rss = None
                ram_error = "The monitored process tree exited before RAM could be sampled"
        except (self._psutil.NoSuchProcess, self._psutil.AccessDenied) as error:
            rss, ram_error = None, str(error) or type(error).__name__
        identity, gpu_used, utilization, gpu_error = None, None, None, None
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=GPU_QUERY_TIMEOUT_S, check=False,
            )
            if result.returncode:
                raise ValueError(result.stderr.strip() or "nvidia-smi query failed")
            rows = list(csv.reader(result.stdout.splitlines(), skipinitialspace=True))
            if not rows or any(len(row) != 5 for row in rows):
                raise ValueError("nvidia-smi did not return five expected fields per GPU")
            identity, gpu_used, utilization = [], [], []
            for row in rows:
                values = [None if value.strip() in ("N/A", "[N/A]", "Not Supported", "[Not Supported]") else float(value)
                          for value in row[2:]]
                if any(value is not None and (not math.isfinite(value) or value < 0) for value in values):
                    raise ValueError("nvidia-smi returned invalid numeric device metrics")
                total, used, busy = values
                if busy is not None and busy > 100:
                    raise ValueError("nvidia-smi GPU utilization exceeds 100 percent")
                identity.append({"name": row[0], "driver_version": row[1],
                                 "memory_total_bytes": None if total is None else int(total * 1024**2)})
                gpu_used.append(None if used is None else int(used * 1024**2))
                utilization.append(busy)
            if any(value is None for value in gpu_used + utilization):
                gpu_error = "nvidia-smi reports unavailable memory/utilization for one or more GPU devices"
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            identity, gpu_used, utilization, gpu_error = None, None, None, str(error) or type(error).__name__
        sample = {
            "observed_at": observed_at, "elapsed_s": started - self._started,
            "sample_duration_s": time.monotonic() - started,
            "process_tree_rss_bytes": rss, "ram_unavailable_reason": ram_error,
            "device_gpu_memory_used_bytes": gpu_used, "device_gpu_utilization_percent": utilization,
            "gpu_unavailable_reason": gpu_error,
        }
        with self._lock:
            self._resources["samples"].append(sample)
            self._resources["ram_sampling_error"] = ram_error
            self._resources["gpu_sampling_error"] = gpu_error
            if rss is not None:
                self._resources["peak_process_tree_rss_bytes"] = max(self._resources["peak_process_tree_rss_bytes"] or 0, rss)
                self._resources["process_tree_rss_unavailable_reason"] = None
            elif self._resources["peak_process_tree_rss_bytes"] is None:
                self._resources["process_tree_rss_unavailable_reason"] = ram_error
            if identity is not None:
                self._resources["gpu_identity"] = identity
            for name, values in (("peak_device_gpu_memory_bytes", gpu_used), ("peak_device_gpu_utilization_percent", utilization)):
                available = [value for value in values or [] if value is not None]
                if available:
                    self._resources[name] = max(self._resources[name] or 0, max(available))

    def snapshot(self):
        """Return detached evidence; callers cannot mutate the live samples."""
        with self._lock:
            result = copy.deepcopy(self._resources)
        if self._started is not None and result["finished_at"] is None:
            result["duration_s"] = time.monotonic() - self._started
        return result

    def stop(self):
        self._stop.set()
        if self._thread is not None and self._thread.ident is not None:
            self._thread.join(timeout=GPU_QUERY_TIMEOUT_S + 1)
        with self._lock:
            if self._resources["finished_at"] is None:
                self._resources["finished_at"] = utc_now()
                self._resources["duration_s"] = None if self._started is None else time.monotonic() - self._started
            if self._thread is None and self._resources["sampling_error"] is None:
                reason = "Resource monitor was stopped before it started"
                self._resources.update(sampling_error=reason, process_tree_rss_unavailable_reason=reason,
                                       gpu_sampling_error=reason)
            if self._thread is not None and self._thread.is_alive():
                self._resources["sampling_error"] = "Resource sampler did not stop within its bounded query timeout"
        return self.snapshot()


def artifact_record(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def stage_record(name):
    return {"name": name, "status": "pending", "started_at": None,
            "finished_at": None, "wall_time_s": None, "error": None}


def new_manifest(run_directory, request, repository_root):
    return {"schema_version": SCHEMA_VERSION, "run_id": run_directory.name,
            "run_directory": str(run_directory), "clip_id": None, "source": None,
            "request": request, "started_at": utc_now(), "finished_at": None,
            "status": "running", "stages": [], "environment": capture_environment(repository_root),
            "commands": [], "resources": {}, "validation": {}, "artifacts": {},
            "warnings": [], "failure": None, "wall_time_s": None}
