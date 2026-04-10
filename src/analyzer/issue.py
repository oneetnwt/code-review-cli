from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __lt__(self, other):
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH]
        return order.index(self) < order.index(other)

    def color(self) -> str:
        """Returns a Rich color string for terminal display"""
        return {Severity.LOW: "green", Severity.MEDIUM: "yellow", Severity.HIGH: "red"}[
            self
        ]

    def icon(self) -> str:
        """Returns an icon for terminal display."""
        return {
            Severity.LOW: "🟢",
            Severity.MEDIUM: "🟡",
            Severity.HIGH: "🔴",
        }[self]


class Category(str, Enum):
    STYLE = "style"
    COMPLEXITY = "complexity"
    SECURITY = "security"
    BUG = "bug"
    DEAD_CODE = "dead_code"


@dataclass
class Issue:
    """
    Represents a single problem found in a source file.
    All analyzers produce Issue objects.
    """

    file: Path  # Which file
    line: int  # Which line number
    severity: Severity  # How bad
    category: Category  # What kind
    message: str  # What the problem is
    suggestion: str = ""  # How to fix it
    col: int = 0  # Column number (optional)
    rule: str = ""  # Rule ID (e.g. "E001")

    def matches_severity(self, threshold: Severity) -> bool:
        """
        Checks if this issue meets or exceeds the severity threshold.

        Example:
            issue.severity = MEDIUM
            threshold = HIGH → False (medium < high, don't show)
            threshold = LOW  → True  (medium >= low, show it)
        """
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH]
        return order.index(self.severity) >= order.index(threshold)

    def __str__(self) -> str:
        return (
            f"{self.severity.icon()} [{self.severity.value.upper()}] "
            f"{self.file}:{self.line} — {self.message}"
        )
