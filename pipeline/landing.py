"""Where new files arrive: a local folder (dev, CI) or a Cloud Storage prefix (prod)."""
from __future__ import annotations

import fnmatch
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class LandingFile:
    name: str       # path relative to the landing root, e.g. "orders/orders_2025-01.csv"
    content: bytes


class Landing(Protocol):
    def list(self, pattern: str) -> list[str]: ...
    def read(self, name: str) -> LandingFile: ...


class LocalLanding:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def list(self, pattern: str) -> list[str]:
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.glob(pattern) if p.is_file())

    def read(self, name: str) -> LandingFile:
        return LandingFile(name, (self.root / name).read_bytes())


class GCSLanding:
    def __init__(self, uri: str):
        from google.cloud import storage  # imported lazily: only needed in prod

        bucket, _, prefix = uri.removeprefix("gs://").partition("/")
        self.prefix = prefix.strip("/")
        self.bucket = storage.Client().bucket(bucket)

    def _key(self, name: str) -> str:
        return f"{self.prefix}/{name}" if self.prefix else name

    def list(self, pattern: str) -> list[str]:
        start = f"{self.prefix}/" if self.prefix else ""
        names = (b.name[len(start):] for b in self.bucket.list_blobs(prefix=start))
        return sorted(n for n in names if fnmatch.fnmatch(n, pattern))

    def read(self, name: str) -> LandingFile:
        return LandingFile(name, self.bucket.blob(self._key(name)).download_as_bytes())


def open_landing(uri: str) -> Landing:
    return GCSLanding(uri) if uri.startswith("gs://") else LocalLanding(uri)


def iter_files(landing: Landing, pattern: str) -> Iterator[LandingFile]:
    for name in landing.list(pattern):
        yield landing.read(name)
