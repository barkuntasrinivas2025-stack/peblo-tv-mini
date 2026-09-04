"""
Storage abstraction.

Everything above this file talks in terms of `storage_key` (opaque string) and
bytes in/out. Swap LocalDiskStorage for R2Storage (boto3 S3-compatible client
pointed at the R2 endpoint) and nothing else in the codebase changes — routers,
models, and the publish job never touch a filesystem path directly.

To move to R2 in production:
  1. Implement R2Storage(BaseStorage) using boto3's S3 client with
     endpoint_url=https://<account_id>.r2.cloudflarestorage.com
  2. Swap the `get_storage()` factory below based on an env var
     (STORAGE_BACKEND=local|r2).
  3. storage_key values are already backend-agnostic (no local path
     assumptions baked in) so no data migration of the *keys* is needed —
     only the underlying bytes need to be copied over once.
"""
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class BaseStorage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalDiskStorage(BaseStorage):
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # key is opaque but we still guard against path traversal
        safe = key.replace("..", "")
        p = self.root / safe
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put(self, key: str, data: bytes) -> None:
        tmp = self._path(key).with_suffix(self._path(key).suffix + ".tmp")
        tmp.write_bytes(data)
        shutil.move(str(tmp), str(self._path(key)))  # atomic rename on same filesystem

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()


_storage_instance: BaseStorage | None = None


def get_storage() -> BaseStorage:
    global _storage_instance
    if _storage_instance is None:
        backend = os.getenv("STORAGE_BACKEND", "local")
        if backend == "local":
            _storage_instance = LocalDiskStorage(os.getenv("STORAGE_ROOT", "/data/storage"))
        else:
            raise NotImplementedError(f"Storage backend '{backend}' not implemented yet")
    return _storage_instance
