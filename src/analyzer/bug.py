from __future__ import annotations
import ast

from src.analyzer.base import BaseAnalyzer
from src.analyzer.issue import Issue, Severity, Category
from src.utils.file_walker import SourceFile


class BugAnalyzer(BaseAnalyzer):
    """
    Detects common bugs, anti-patterns, and logic errors in Python.
    Currently detects:
    - Mutable default arguments (lists, dicts, sets)
    - Bare `except:` handlers that catch system-exiting exceptions
    - Unreachable code (statements occurring immediately after return/break/continue)
    """

    supported_languages = ["python"]

    def analyze(self, file: SourceFile) -> list[Issue]:
        tree = self.parse_python(file)
        if not tree:
            return []

        issues = []
        for node in ast.walk(tree):
            # Check for mutable defaults
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issues += self._check_mutable_defaults(file, node)
                issues += self._check_unreachable_code(file, node)

            # Check for bare excepts
            elif isinstance(node, ast.ExceptHandler):
                issues += self._check_bare_except(file, node)

            # Check for unreachable code in loops
            elif isinstance(node, (ast.For, ast.While)):
                issues += self._check_unreachable_code(file, node)

        return issues

    def _check_mutable_defaults(
        self, file: SourceFile, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[Issue]:
        issues = []
        # Combine standard defaults and keyword-only defaults
        defaults = getattr(node.args, "defaults", []) + getattr(
            node.args, "kw_defaults", []
        )

        for default in defaults:
            if default is None:
                continue
            # If the default is a list, dict, or set instantiation
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                issues.append(
                    Issue(
                        file=file.path,
                        line=node.lineno,
                        severity=Severity.HIGH,
                        category=Category.BUG,
                        rule="B001",
                        message=f"Mutable default argument used in function '{node.name}'",
                        suggestion="Use `None` as default and initialize the mutable object inside the function",
                    )
                )
        return issues

    def _check_bare_except(
        self, file: SourceFile, node: ast.ExceptHandler
    ) -> list[Issue]:
        issues = []
        # node.type is None for a completely bare `except:`
        if node.type is None:
            issues.append(
                Issue(
                    file=file.path,
                    line=node.lineno,
                    severity=Severity.MEDIUM,
                    category=Category.BUG,
                    rule="B002",
                    message="Bare `except:` clause catches system exceptions like KeyboardInterrupt",
                    suggestion="Catch specific exceptions or use `except Exception:` instead",
                )
            )
        return issues

    def _check_unreachable_code(
        self,
        file: SourceFile,
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.For | ast.While,
    ) -> list[Issue]:
        issues = []
        # A node's body is a list of statements
        for i, statement in enumerate(node.body):
            if isinstance(statement, (ast.Return, ast.Break, ast.Continue)):
                # If there are more statements in the same block after a return/break/continue
                if i + 1 < len(node.body):
                    unreachable_stmt = node.body[i + 1]
                    issues.append(
                        Issue(
                            file=file.path,
                            line=unreachable_stmt.lineno,
                            severity=Severity.MEDIUM,
                            category=Category.BUG,
                            rule="B003",
                            message="Unreachable code detected",
                            suggestion="Remove the code occurring after the return/break/continue statement",
                        )
                    )
                # Break early since we already found the branch termination
                break
        return issues
