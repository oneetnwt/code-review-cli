from __future__ import annotations
import ast
import re

from src.analyzer.base import BaseAnalyzer
from src.analyzer.issue import Issue, Severity, Category
from src.utils.file_walker import SourceFile

# Regex patterns for naming convention checks
SNAKE_CASE = re.compile(r"^[a-z_][a-z0-9_]*$")
CAMEL_CASE = re.compile(r"^[a-z][a-zA-Z0-9]*$")
PASCAL_CASE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
UPPER_CASE = re.compile(r"^[A-Z_][A-Z0-9_]*$")  # for constants

# Words that are allowed to break naming rules
NAMING_WHITELIST = {
    "__init__",
    "__main__",
    "__str__",
    "__repr__",
    "__len__",
    "__eq__",
    "__lt__",
    "__gt__",
    "__enter__",
    "__exit__",
    "__call__",
    "__del__",
    "setUp",
    "tearDown",  # unittest methods
}


class StyleAnalyzer(BaseAnalyzer):
    """
    Checks code style: line length, naming conventions,
    whitespace, imports, and blank lines.
    """

    supported_languages = ["python", "javascript", "typescript"]

    def analyze(self, file: SourceFile) -> list[Issue]:
        issues = []

        # Run line-based checks on all supported languages
        lines = self.read_lines(file)
        issues += self._check_line_length(file, lines)
        issues += self._check_trailing_whitespace(file, lines)
        issues += self._check_tabs(file, lines)

        # Run AST-based checks only on Python files
        if file.language == "python":
            tree = self.parse_python(file)
            if tree:
                issues += self._check_naming(file, tree)
                issues += self._check_imports(file, tree)
                issues += self._check_blank_lines(file, lines, tree)

        return issues

    def _check_line_length(self, file: SourceFile, lines: list[str]) -> list[Issue]:
        """Flag lines that exceed the max length."""
        issues = []
        max_len = self.config.rules.style.max_line_length

        for i, line in enumerate(lines, start=1):
            length = len(line.rstrip("\n"))
            if length > max_len:
                issues.append(
                    Issue(
                        file=file.path,
                        line=i,
                        severity=Severity.LOW,
                        category=Category.STYLE,
                        rule="S001",
                        message=f"Line too long ({length} chars, max {max_len})",
                        suggestion=f"Break this line into multiple lines or shorten it",
                    )
                )

        return issues

    def _check_trailing_whitespace(
        self, file: SourceFile, lines: list[str]
    ) -> list[Issue]:
        """Flag lines with trailing spaces or tabs."""
        issues = []

        for i, line in enumerate(lines, start=1):
            # Strip the newline but check for spaces/tabs before it
            stripped = line.rstrip("\n\r")
            if stripped != stripped.rstrip():
                issues.append(
                    Issue(
                        file=file.path,
                        line=i,
                        severity=Severity.LOW,
                        category=Category.STYLE,
                        rule="S002",
                        message="Trailing whitespace detected",
                        suggestion="Remove spaces/tabs at the end of this line",
                    )
                )

        return issues

    def _check_tabs(self, file: SourceFile, lines: list[str]) -> list[Issue]:
        """Flag tab characters used for indentation (prefer spaces)."""
        issues = []

        for i, line in enumerate(lines, start=1):
            if line.startswith("\t"):
                issues.append(
                    Issue(
                        file=file.path,
                        line=i,
                        severity=Severity.LOW,
                        category=Category.STYLE,
                        rule="S003",
                        message="Tab used for indentation (use spaces instead)",
                        suggestion="Replace tabs with 4 spaces",
                    )
                )

        return issues

    # ── AST-based checks ───────────────────────────────────────────

    def _check_naming(self, file: SourceFile, tree: ast.AST) -> list[Issue]:
        """
        Walk the AST and check naming conventions.

        Rules:
          - Functions & variables → snake_case
          - Classes               → PascalCase
          - Constants (module-level ALL_CAPS) → UPPER_CASE
        """
        issues = []
        convention = self.config.rules.style.naming_convention

        # ast.walk() visits every node in the tree
        for node in ast.walk(tree):

            # Check function names
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                if name in NAMING_WHITELIST:
                    continue
                if not SNAKE_CASE.match(name):
                    issues.append(
                        Issue(
                            file=file.path,
                            line=node.lineno,
                            severity=Severity.LOW,
                            category=Category.STYLE,
                            rule="S004",
                            message=f"Function '{name}' should use snake_case",
                            suggestion=f"Rename to '{_to_snake_case(name)}'",
                        )
                    )

            # Check class names
            elif isinstance(node, ast.ClassDef):
                name = node.name
                if not PASCAL_CASE.match(name):
                    issues.append(
                        Issue(
                            file=file.path,
                            line=node.lineno,
                            severity=Severity.LOW,
                            category=Category.STYLE,
                            rule="S005",
                            message=f"Class '{name}' should use PascalCase",
                            suggestion=f"Rename to '{_to_pascal_case(name)}'",
                        )
                    )

        return issues

    def _check_imports(self, file: SourceFile, tree: ast.AST) -> list[Issue]:
        """Flag multiple imports on a single line: import os, sys"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # ast.Import.names is a list — multiple = violation
                if len(node.names) > 1:
                    names = ", ".join(a.name for a in node.names)
                    issues.append(
                        Issue(
                            file=file.path,
                            line=node.lineno,
                            severity=Severity.LOW,
                            category=Category.STYLE,
                            rule="S006",
                            message=f"Multiple imports on one line: {names}",
                            suggestion="Use one import per line",
                        )
                    )

        return issues

    def _check_blank_lines(
        self, file: SourceFile, lines: list[str], tree: ast.AST
    ) -> list[Issue]:
        """
        Flag functions/classes not preceded by a blank line.
        PEP8 requires 2 blank lines before top-level definitions.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                lineno = node.lineno

                # For decorated definitions, blank lines should be counted
                # before the first decorator, not before the def/class line.
                decorator_lines = [
                    d.lineno for d in getattr(node, "decorator_list", [])
                ]
                definition_start = min([lineno, *decorator_lines])

                # Skip first few lines — nothing to check before them
                if definition_start <= 2:
                    continue

                # Count blank lines before this definition/decorator block
                blank_count = 0
                check_line = definition_start - 2  # line before start

                while check_line >= 0 and lines[check_line].strip() == "":
                    blank_count += 1
                    check_line -= 1

                # Top-level definitions need 2 blank lines
                # We check col_offset == 0 to identify top-level nodes
                if node.col_offset == 0 and blank_count < 2:
                    issues.append(
                        Issue(
                            file=file.path,
                            line=lineno,
                            severity=Severity.LOW,
                            category=Category.STYLE,
                            rule="S007",
                            message=f"Expected 2 blank lines before '{node.name}', found {blank_count}",
                            suggestion="Add blank lines before this definition (PEP8)",
                        )
                    )

        return issues


def _to_snake_case(name: str) -> str:
    """Convert CamelCase or PascalCase to snake_case."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()


def _to_pascal_case(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))
