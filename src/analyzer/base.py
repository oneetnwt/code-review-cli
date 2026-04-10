from __future__ import annotations
import ast
from abc import ABC, abstractmethod
from pathlib import Path

from src.analyzer.issue import Issue
from src.utils.file_walker import SourceFile
from src.utils.config import Config


class BaseAnalyzer(ABC):
    """
    Abstract base class for all analyzers.

    ABC = Abstract Base Class — it enforces that child classes
    must implement the `analyze()` method.

    If a child class forgets to implement analyze(), Python raises
    a TypeError immediately — great for catching mistakes early.
    """

    # Each analyzer which language it supports
    supported_languages: list[str] = []

    def __init__(self, config: Config):
        self.config = config

    def supports(self, file: SourceFile) -> bool:
        """Checks if this analyzer can handle a given file's language"""
        return file.language in self.supported_languages

    @abstractmethod
    def analyze(self, file: SourceFile) -> list[Issue]:
        """
        Analyze a source file and return a list of issues.
        Every analyzer MUST implement this method.
        """
        ...

    def parse_python(self, file: SourceFile) -> ast.AST | None:
        """
        Helper: Parse a Python file into an AST.
        Returns None if parsing fails (syntax errors, encoding issues).
        """
        try:
            source = file.path.read_text(encoding="utf-8")
            return ast.parse(source, filename=str(file.path))
        except SyntaxError:
            return None
        except Exception:
            return None

    def read_lines(self, file: SourceFile) -> list[str]:
        """
        Helper: Read all lines of a file.
        Returns empty list if file cannot be read.
        """
        try:
            return file.path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
