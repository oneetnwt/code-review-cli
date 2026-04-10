from __future__ import annotations
from pathlib import Path

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from src.analyzer.base import BaseAnalyzer
from src.analyzer.issue import Issue, Severity
from src.utils.file_walker import SourceFile
from src.utils.config import Config

console = Console()


class AnalysisEngine:
    """
    Runs all registered analyzers against all collected files.

    Think of it as a pipeline:
    Files → [Analyzer1, Analyzer2, Analyzer3] → Issues
    """

    def __init__(self, config: Config):
        self.config = config
        self.analyzers: list[BaseAnalyzer] = []

    def register(self, analyzer: BaseAnalyzer):
        """Add analyzer to the pipeline"""
        self.analyzers.append(analyzer)
        return self  # allows chaining: engine.register(A).register(B)

    def run(self, files: list[SourceFile]) -> list[Issue]:
        """
        Run all analyzers against all files.
        Shows a progress bar while working.
        Returns all issues found, filtered by severity threshold.
        """
        all_issues: list[Issue] = []

        threshold = Severity(self.config.severity_threshold)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Analyzing...", total=len(files))

            for file in files:
                progress.update(
                    task,
                    description=f"[cyan]Analyzing [bold]{file.relative_path}[/bold]",
                )

                for analyzer in self.analyzers:
                    # Skip analyzer if it doesn't support this file's language
                    if not analyzer.supports(file):
                        continue

                    # Skip analyzer if its module is disabled in config
                    module_name = analyzer.__class__.__name__.lower().replace(
                        "analyzer", ""
                    )
                    if module_name not in self.config.enabled_modules:
                        continue

                    try:
                        issues = analyzer.analyze(file)

                        # Filter by severity threshold
                        filtered = [i for i in issues if i.matches_severity(threshold)]
                        all_issues.extend(filtered)

                    except Exception as e:
                        # Never let one analyzer crash the whole run
                        console.print(
                            f"[dim red]⚠ Analyzer error in {file.relative_path}: {e}[/dim red]"
                        )

                progress.advance(task)

        return all_issues
