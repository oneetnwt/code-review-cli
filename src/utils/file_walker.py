from pathlib import Path
from dataclasses import dataclass
from typing import Optional


LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
}

DEFAULT_IGNORE = {
    "venv",
    ".venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "coverage",
    "htmlcov",
    "migrations",
    ".tox",
    "eggs",
    "vendor",
}


@dataclass
class SourceFile:
    """
    Represents a single file to be analyzed.

    A dataclass automatically generates __init__, __repr__, etc.
    Think of it as a simple container for file information.
    """

    path: Path  # Full path to the file
    language: str  # Detected language (e.g. "python")
    relative_path: str  # Path relative to the scanned root (for display)
    size_bytes: int  # File size


def detect_language(path: Path) -> Optional[str]:
    """
    Detect the programming language of a file by its extension.
    Returns None if the language is not supported.
    """
    return LANGUAGE_MAP.get(path.suffix.lower())


def should_ignore(path: Path, ignore_dirs: set) -> bool:
    """
    Check if a file or folder should be skipped.
    We check every part of the path — so nested ignored folders are caught too.

    Example:
        path = Path("src/node_modules/lodash/index.js")
        "node_modules" is in the parts → ignore it ✅
    """
    return any(part in ignore_dirs for part in path.parts)


def walk_files(
    root: Path,
    extra_ignore: Optional[set[str]] = None,
    max_file_size_kb: int = 500,
) -> list[SourceFile]:
    """
    Walk a directory recursively and collect all analyzable source files.

    Args:
        root:             The folder or file to scan
        extra_ignore:     Additional folder names to skip (from .reviewrc)
        max_file_size_kb: Skip files larger than this (avoids huge generated files)

    Returns:
        List of SourceFile objects ready for analysis
    """
    # Combine default ignores with any user-defined ones
    ignore_dirs = DEFAULT_IGNORE.copy()
    if extra_ignore:
        ignore_dirs.update(extra_ignore)

    collected = []

    # Handle single file input (e.g. `review src/cli.py`)
    if root.is_file():
        language = detect_language(root)
        if language:
            collected.append(
                SourceFile(
                    path=root,
                    language=language,
                    relative_path=str(root),
                    size_bytes=root.stat().st_size,
                )
            )
        return collected

    # Walk all files recursively using rglob("*")
    # rglob means "recursive glob" — finds everything nested inside
    for file in sorted(root.rglob("*")):

        # Skip directories themselves (we only want files)
        if not file.is_file():
            continue

        # Skip ignored folders
        if should_ignore(file, ignore_dirs):
            continue

        # Detect language — skip unsupported file types
        language = detect_language(file)
        if not language:
            continue

        # Skip files that are too large (likely auto-generated)
        size = file.stat().st_size
        if size > max_file_size_kb * 1024:
            continue

        # Build a relative path for clean display
        try:
            relative = str(file.relative_to(root))
        except ValueError:
            relative = str(file)

        collected.append(
            SourceFile(
                path=file,
                language=language,
                relative_path=relative,
                size_bytes=size,
            )
        )

    return collected
