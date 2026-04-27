"""Helpers for listing and pruning stored pipeline runs."""

from __future__ import annotations

import shutil
from pathlib import Path


def list_runs(client_root: Path) -> list[dict[str, str | float]]:
    if not client_root.exists():
        return []
    runs: list[dict[str, str | float]] = []
    for path in client_root.iterdir():
        if not path.is_dir():
            continue
        stat = path.stat()
        runs.append(
            {
                "name": path.name,
                "path": str(path),
                "mtime": stat.st_mtime,
            }
        )
    runs.sort(key=lambda item: (float(item["mtime"]), str(item["name"])), reverse=True)
    return runs


def prune_runs(client_root: Path, *, keep: int = 2, dry_run: bool = False) -> dict[str, object]:
    if keep < 0:
        raise ValueError("keep must be >= 0")
    runs = list_runs(client_root)
    kept = runs[:keep]
    to_delete = runs[keep:]
    if not dry_run:
        for item in to_delete:
            shutil.rmtree(Path(str(item["path"])), ignore_errors=True)
    return {
        "client_root": str(client_root),
        "keep": keep,
        "dry_run": dry_run,
        "kept": kept,
        "deleted": to_delete,
    }
