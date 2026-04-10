from __future__ import annotations
import ast

from src.analyzer.base import BaseAnalyzer
from src.analyzer.issue import Issue, Severity, Category
from src.utils.file_walker import SourceFile


class BigOVisitor(ast.NodeVisitor):
    """
    Estimates Time Complexity (Big O) by checking:
    1. Maximum depth of nested loops.
    2. Recursive function calls.
    """

    def __init__(self, func_name: str):
        self.func_name = func_name
        self.max_loop_depth = 0
        self.current_loop_depth = 0
        self.is_recursive = False

    def visit_For(self, node):
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_While(self, node):
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_Call(self, node):
        # Check if the function calls itself
        if isinstance(node.func, ast.Name) and node.func.id == self.func_name:
            self.is_recursive = True
        self.generic_visit(node)


class BigOAnalyzer(BaseAnalyzer):
    """
    Estimates rough Time Complexity of Python functions and raises issues
    for potentially catastrophic scaling.
    """

    supported_languages = ["python"]

    def analyze(self, file: SourceFile) -> list[Issue]:
        tree = self.parse_python(file)
        if not tree:
            return []

        issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issues += self._analyze_big_o(file, node)
        return issues

    def _analyze_big_o(
        self, file: SourceFile, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[Issue]:
        issues = []
        visitor = BigOVisitor(node.name)

        # Visit the body of the function to count loops and recursion
        for statement in node.body:
            visitor.visit(statement)

        # Determine Big O Notation Warning
        if visitor.is_recursive:
            issues.append(
                Issue(
                    file=file.path,
                    line=node.lineno,
                    severity=Severity.HIGH,
                    category=Category.COMPLEXITY,
                    rule="O001",
                    message=f"Function '{node.name}' uses recursion. Watch out for exponential O(2^N) time complexity or StackOverflows.",
                    suggestion=f"Ensure '{node.name}' has a solid base case, or use @lru_cache / dynamic programming.",
                )
            )

        elif visitor.max_loop_depth >= 2:
            complexity_str = (
                f"O(N^{visitor.max_loop_depth})"
                if visitor.max_loop_depth > 2
                else "O(N²)"
            )
            severity = Severity.HIGH if visitor.max_loop_depth > 2 else Severity.MEDIUM

            issues.append(
                Issue(
                    file=file.path,
                    line=node.lineno,
                    severity=severity,
                    category=Category.COMPLEXITY,
                    rule="O002",
                    message=f"Function '{node.name}' has nested loops indicating {complexity_str} time complexity.",
                    suggestion=f"Refactor '{node.name}' using HashMaps/sets to reduce lookup time and flatten the complexity.",
                )
            )

        return issues
