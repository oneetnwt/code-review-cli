from __future__ import annotations
import ast

from src.analyzer.base import BaseAnalyzer
from src.analyzer.issue import Issue, Severity, Category
from src.utils.file_walker import SourceFile

# AST node types that increase cyclomatic complexity
COMPLEXITY_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.ExceptHandler,
    ast.With,
    ast.Assert,
    ast.comprehension,
)

# Node types that increase nesting depth
NESTING_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.With,
    ast.Try,
    ast.ExceptHandler,
)


class ComplexityVisitor(ast.NodeVisitor):
    """
    Visits a function's AST and measures:
    - Cyclomatic complexity (number of decision points)
    - Maximum nesting depth
    - Number of return statements
    """

    def __init__(self):
        self.complexity = 1  # baseline is always 1
        self.max_depth = 0
        self._current_depth = 0
        self.return_count = 0

    def _enter_block(self, node):
        """Called when entering a nesting block."""
        self._current_depth += 1
        self.max_depth = max(self.max_depth, self._current_depth)
        self.generic_visit(node)
        self._current_depth -= 1

    def visit_If(self, node):
        self.complexity += 1
        # Each elif is an extra branch on the If node
        self.complexity += len(node.orelse) > 0 and isinstance(node.orelse[0], ast.If)
        self._enter_block(node)

    def visit_For(self, node):
        self.complexity += 1
        self._enter_block(node)

    def visit_While(self, node):
        self.complexity += 1
        self._enter_block(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self._enter_block(node)

    def visit_With(self, node):
        self.complexity += 1
        self._enter_block(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # 'and' / 'or' each add a path
        # BoolOp.values has N items → N-1 operators
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Return(self, node):
        self.return_count += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self._enter_block(node)


class ComplexityAnalyzer(BaseAnalyzer):
    """
    Analyzes functions for:
    - Cyclomatic complexity
    - Nesting depth
    - Function length (line count)
    - Too many return statements
    """

    supported_languages = ["python"]

    def analyze(self, file: SourceFile) -> list[Issue]:
        tree = self.parse_python(file)
        if not tree:
            return []

        issues = []
        lines = self.read_lines(file)

        # Walk top-level and find all function definitions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issues += self._check_function(file, node, lines)

        return issues

    def _check_function(
        self,
        file: SourceFile,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: list[str],
    ) -> list[Issue]:
        """Run all complexity checks on a single function."""
        issues = []
        name = node.name
        start = node.lineno
        end = node.end_lineno or start

        # ── 1. Function Length ──────────────────────────────────────
        func_length = end - start + 1
        max_length = self.config.rules.complexity.max_function_length

        if func_length > max_length:
            # Severity scales with how far over the limit we are
            if func_length > max_length * 2:
                sev = Severity.HIGH
            elif func_length > max_length * 1.5:
                sev = Severity.MEDIUM
            else:
                sev = Severity.LOW

            issues.append(
                Issue(
                    file=file.path,
                    line=start,
                    severity=sev,
                    category=Category.COMPLEXITY,
                    rule="C001",
                    message=f"Function '{name}' is too long ({func_length} lines, max {max_length})",
                    suggestion=f"Break '{name}' into smaller functions",
                )
            )

        # ── 2. Cyclomatic Complexity ────────────────────────────────
        visitor = ComplexityVisitor()
        visitor.visit(node)
        complexity = visitor.complexity
        max_complexity = self.config.rules.complexity.max_cyclomatic_complexity

        if complexity > max_complexity:
            if complexity > max_complexity * 2:
                sev = Severity.HIGH
            elif complexity > max_complexity * 1.5:
                sev = Severity.MEDIUM
            else:
                sev = Severity.LOW

            issues.append(
                Issue(
                    file=file.path,
                    line=start,
                    severity=sev,
                    category=Category.COMPLEXITY,
                    rule="C002",
                    message=f"Function '{name}' has high cyclomatic complexity ({complexity}, max {max_complexity})",
                    suggestion="Simplify by extracting logic into smaller functions",
                )
            )

        # ── 3. Nesting Depth ────────────────────────────────────────
        max_depth = visitor.max_depth
        max_allowed_depth = self.config.rules.complexity.max_nesting_depth

        if max_depth > max_allowed_depth:
            sev = (
                Severity.HIGH if max_depth > max_allowed_depth + 2 else Severity.MEDIUM
            )

            issues.append(
                Issue(
                    file=file.path,
                    line=start,
                    severity=sev,
                    category=Category.COMPLEXITY,
                    rule="C003",
                    message=f"Function '{name}' has deep nesting (depth {max_depth}, max {max_allowed_depth})",
                    suggestion="Reduce nesting with early returns or extract nested blocks",
                )
            )

        # ── 4. Too Many Return Statements ───────────────────────────
        if visitor.return_count > 4:
            issues.append(
                Issue(
                    file=file.path,
                    line=start,
                    severity=Severity.LOW,
                    category=Category.COMPLEXITY,
                    rule="C004",
                    message=f"Function '{name}' has {visitor.return_count} return statements",
                    suggestion="Consider consolidating return paths",
                )
            )

        return issues
