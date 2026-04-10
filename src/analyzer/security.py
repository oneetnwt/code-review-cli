from __future__ import annotations
import ast
import re

from src.analyzer.base import BaseAnalyzer
from src.analyzer.issue import Issue, Severity, Category
from src.utils.file_walker import SourceFile

# Regex pattern to catch common sensitive variable names
SECRET_PATTERNS = re.compile(r"api_?key|secret|password|token|auth", re.IGNORECASE)


class SecurityAnalyzer(BaseAnalyzer):
    """
    Detects critical security vulnerabilities like:
    - Hardcoded secrets and passwords
    - SQL injection via formatted strings
    - Unsafe evaluations (eval/exec)
    """

    supported_languages = ["python"]

    def analyze(self, file: SourceFile) -> list[Issue]:
        tree = self.parse_python(file)
        if not tree:
            return []

        issues = []
        for node in ast.walk(tree):
            # 1. Check for Hardcoded Secrets
            if self.config.rules.security.scan_secrets:
                issues += self._check_hardcoded_secrets(file, node)

            # 2. Check for SQL Injection
            if self.config.rules.security.scan_sql_injection:
                issues += self._check_sql_injection(file, node)

            # 3. Check for Dangerous Evaluation Functions (eval, exec)
            issues += self._check_unsafe_eval(file, node)

        return issues

    def _check_hardcoded_secrets(self, file: SourceFile, node: ast.AST) -> list[Issue]:
        issues = []
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and SECRET_PATTERNS.search(target.id):
                    # Flag if assigning a static string to a secret-like variable name
                    if isinstance(node.value, ast.Constant) and isinstance(
                        node.value.value, str
                    ):
                        # Don't flag empty strings or 'TODO' stubs
                        val = node.value.value.strip()
                        if val and val.lower() not in ("todo", "none", "null"):
                            issues.append(
                                Issue(
                                    file=file.path,
                                    line=node.lineno,
                                    severity=Severity.HIGH,
                                    category=Category.SECURITY,
                                    rule="SEC001",
                                    message=f"Possible hardcoded secret assigned to '{target.id}'",
                                    suggestion="Use environment variables or a secrets manager (.env, AWS Secrets, etc)",
                                )
                            )
        return issues

    def _check_sql_injection(self, file: SourceFile, node: ast.AST) -> list[Issue]:
        issues = []
        """
        Flag pattern: cursor.execute(f"SELECT * FROM Users WHERE id = {user_id}")
        Requires looking for `.execute(...)` calls where the first arg is formatted.
        """
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "execute":
                if node.args:
                    arg = node.args[0]
                    # Check if it's an f-string (JoinedStr) or uses `.format()`
                    is_f_string = isinstance(arg, ast.JoinedStr)
                    is_format_call = (
                        isinstance(arg, ast.Call)
                        and isinstance(arg.func, ast.Attribute)
                        and arg.func.attr == "format"
                    )

                    if is_f_string or is_format_call:
                        issues.append(
                            Issue(
                                file=file.path,
                                line=node.lineno,
                                severity=Severity.HIGH,
                                category=Category.SECURITY,
                                rule="SEC002",
                                message="Potential SQL Injection via string formatting in .execute()",
                                suggestion="Use parameterized queries (e.g. execute('... %s', (val,))) instead of formatting strings",
                            )
                        )
        return issues

    def _check_unsafe_eval(self, file: SourceFile, node: ast.AST) -> list[Issue]:
        issues = []
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                issues.append(
                    Issue(
                        file=file.path,
                        line=node.lineno,
                        severity=Severity.HIGH,
                        category=Category.SECURITY,
                        rule="SEC003",
                        message=f"Use of dangerous built-in '{node.func.id}()'",
                        suggestion="Avoid eval/exec; find a safer alternative to evaluate dynamic input (like ast.literal_eval)",
                    )
                )
        return issues
