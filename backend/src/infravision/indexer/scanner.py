"""Repository scanner that walks source directories and filters relevant code files."""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Set

IGNORED_DIRECTORIES: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".nuxt",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
}


@dataclass
class DiscoveredFile:
    absolute_path: Path
    relative_path: str
    language: str
    file_hash: str
    size_bytes: int


def compute_file_hash(path: Path) -> str:
    """Compute sha256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class RepositoryScanner:
    """Scans and filters Python and TypeScript/JavaScript files in a codebase."""

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {self.root_path}")

    def scan_files(self) -> Generator[DiscoveredFile, None, None]:
        """Yield discovered code files with language identification and hashes."""
        for root, dirs, files in os.walk(self.root_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES and not d.startswith(".")]

            for file_name in files:
                ext = Path(file_name).suffix.lower()
                language = LANGUAGE_EXTENSIONS.get(ext)
                if not language:
                    continue

                full_path = Path(root) / file_name
                try:
                    rel_path = full_path.relative_to(self.root_path).as_posix()
                    file_hash = compute_file_hash(full_path)
                    size = full_path.stat().st_size

                    yield DiscoveredFile(
                        absolute_path=full_path,
                        relative_path=rel_path,
                        language=language,
                        file_hash=file_hash,
                        size_bytes=size,
                    )
                except (OSError, PermissionError):
                    continue
