from __future__ import annotations
import ast
from collections import defaultdict
from dataclasses import dataclass

from src.analyzer.base import BaseAnalyzer
from src.analyzer.issue import Issue, Severity, Category
from src.utils.file_walker import SourceFile


# Names that are OK to define without using
ALLOWED_UNUSED = {
    # Python magic
    "__all__",
    "__version__",
    "__author__",
    "__email__",
    "__name__",
    "__file__",
    "__doc__",
    "__package__",
    "__init__",
    "__main__",
    # Common patterns
    "_",  # throwaway variable: for _ in range(10)
}


@dataclass
class Definition:
    """Tracks where a name was defined."""

    name: str
    line: int
    kind: str  # "import" | "variable" | "function" | "class"


class NameCollector(ast.NodeVisitor):
    """
    Pass 1 — Collects all names that are DEFINED in a file.
    Tracks imports, assignments, function defs, class defs.
    """

    def __init__(self):
        # name → Definition
        self.definitions: dict[str, Definition] = {}

    def visit_Import(self, node):
        """Handles: import os, import sys as system"""
        for alias in node.names:
            # Use the alias if provided: "import sys as system" → "system"
            name = alias.asname if alias.asname else alias.name
            # For "import os.path" → track "os"
            name = name.split(".")[0]
            self.definitions[name] = Definition(
                name=name,
                line=node.lineno,
                kind="import",
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Handles: from os import path, from typing import Optional"""
        for alias in node.names:
            # Wildcard imports: from module import *
            if alias.name == "*":
                continue
            name = alias.asname if alias.asname else alias.name
            self.definitions[name] = Definition(
                name=name,
                line=node.lineno,
                kind="import",
            )
        self.generic_visit(node)

    def visit_Assign(self, node):
        """Handles: x = 10, MY_CONST = 'hello'"""
        for target in node.targets:
            # Simple assignment: x = 10
            if isinstance(target, ast.Name):
                self.definitions[target.id] = Definition(
                    name=target.id,
                    line=node.lineno,
                    kind="variable",
                )
            # Tuple unpacking: x, y = 1, 2
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        self.definitions[elt.id] = Definition(
                            name=elt.id,
                            line=node.lineno,
                            kind="variable",
                        )
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Handles: def my_func():"""
        self.definitions[node.name] = Definition(
            name=node.name,
            line=node.lineno,
            kind="function",
        )
        # Don't walk INTO the function body —
        # we only track module-level definitions here

    def visit_AsyncFunctionDef(self, node):
        """Handles: async def my_func():"""
        self.definitions[node.name] = Definition(
            name=node.name,
            line=node.lineno,
            kind="function",
        )

    def visit_ClassDef(self, node):
        """Handles: class MyClass:"""
        self.definitions[node.name] = Definition(
            name=node.name,
            line=node.lineno,
            kind="class",
        )
        # Don't walk INTO the class body


class NameUsageCollector(ast.NodeVisitor):
    """
    Pass 2 — Collects all names that are USED in a file.
    A name is "used" if it appears in any expression.
    """

    def __init__(self):
        self.used_names: set[str] = set()

    def visit_Name(self, node):
        """Every time a name appears in an expression."""
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Handles: os.path.join → marks 'os' as used."""
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        """Handles function calls: my_func()"""
        if isinstance(node.func, ast.Name):
            self.used_names.add(node.func.id)
        self.generic_visit(node)

    def visit_Decorator(self, node):
        """Handles decorators: @app.route"""
        if isinstance(node, ast.Name):
            self.used_names.add(node.id)
        self.generic_visit(node)


class DeadCodeAnalyzer(BaseAnalyzer):
    """
    Finds unused imports, variables, functions, and classes
    at the module level.
    """

    supported_languages = ["python"]

    def analyze(self, file: SourceFile) -> list[Issue]:
        tree = self.parse_python(file)
        if not tree:
            return []

        issues = []

        # Pass 1 — collect definitions
        defn_collector = NameCollector()
        defn_collector.visit(tree)

        # Pass 2 — collect usages
        usage_collector = NameUsageCollector()
        usage_collector.visit(tree)

        used = usage_collector.used_names
        definitions = defn_collector.definitions

        # Compare: defined but not used
        for name, defn in definitions.items():

            # Skip allowed names
            if name in ALLOWED_UNUSED:
                continue

            # Skip private names (single underscore prefix)
            if name.startswith("_"):
                continue

            # Skip if it's used somewhere
            if name in used:
                continue

            # Determine severity by kind
            severity = {
                "import": Severity.MEDIUM,
                "variable": Severity.LOW,
                "function": Severity.MEDIUM,
                "class": Severity.LOW,
            }.get(defn.kind, Severity.LOW)

            # Build a helpful message per kind
            messages = {
                "import": f"'{name}' is imported but never used",
                "variable": f"'{name}' is assigned but never used",
                "function": f"'{name}' is defined but never called",
                "class": f"'{name}' is defined but never used",
            }

            suggestions = {
                "import": f"Remove 'import {name}' or use it",
                "variable": f"Remove the assignment or use '{name}'",
                "function": f"Remove '{name}' or call it somewhere",
                "class": f"Remove '{name}' or instantiate it",
            }

            issues.append(
                Issue(
                    file=file.path,
                    line=defn.line,
                    severity=severity,
                    category=Category.DEAD_CODE,
                    rule="D001",
                    message=messages.get(defn.kind, f"'{name}' is unused"),
                    suggestion=suggestions.get(defn.kind, "Remove or use it"),
                )
            )

        return issues
