"""Stage local pilot updates and atomically publish a validated Linux directory."""

from contextlib import contextmanager
import ctypes
import fcntl
import os
from pathlib import Path
import shutil
import tempfile


@contextmanager
def staged_dataset(root):
    """Yield a private copy; exceptions leave the original untouched.

    Linux renameat2(RENAME_EXCHANGE) publishes an existing dataset with no
    missing-directory window. Readers should reopen after publication. The
    sibling advisory lock serializes this project's writers; external writers
    must not modify the same dataset concurrently. Copying is deliberate for
    the small pilot: hard links would expose original files to in-place writes.
    """
    root = Path(root).absolute()
    if root.is_symlink():
        raise ValueError("Dataset root must be a directory, not a symlink")
    root.parent.mkdir(parents=True, exist_ok=True)
    with (root.parent / f".{root.name}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if root.exists() and not (root / "meta/info.json").is_file():
            raise ValueError("Existing destination is not a LeRobot dataset; choose a new directory")
        with tempfile.TemporaryDirectory(prefix=f".{root.name}.staging-", dir=root.parent) as tmp:
            staged = Path(tmp) / root.name
            if root.exists():
                shutil.copytree(root, staged)
            yield staged
            if not (staged / "meta/info.json").is_file():
                raise ValueError("Staged operation did not produce a dataset")
            if root.exists():
                libc = ctypes.CDLL(None, use_errno=True)
                exchange = libc.renameat2
                exchange.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
                exchange.restype = ctypes.c_int
                if exchange(-100, os.fsencode(staged), -100, os.fsencode(root), 2) != 0:
                    error = ctypes.get_errno()
                    raise OSError(error, "Atomic dataset exchange failed; original is unchanged", str(root))
            else:
                staged.rename(root)
