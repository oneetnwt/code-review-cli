import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Optional
from enum import Enum
from pathlib import Path
from rich.table import Table

from src.utils.file_walker import (
    walk_files,
    should_ignore,
    detect_language,
    DEFAULT_IGNORE,
    SourceFile,
)
from src.utils.config import load_config
from src.utils.git import get_staged_files
from src.analyzer.engine import AnalysisEngine
from src.analyzer.issue import Severity as IssueSeverity
from src.analyzer.style import StyleAnalyzer
from src.analyzer.complexity import ComplexityAnalyzer
from src.analyzer.dead_code import DeadCodeAnalyzer
from src.analyzer.big_o import BigOAnalyzer
from src.analyzer.bug import BugAnalyzer
from src.analyzer.security import SecurityAnalyzer
from src.reporters.console import ConsoleReporter
from src.reporters.json_reporter import JsonReporter
from src.reporters.html_reporter import HtmlReporter

app = typer.Typer(
    name="review",
    help="Code Review Assistant - analyze your code before pushing",
    add_completion=False,
)
console = Console()


class OutputFormat(str, Enum):
    console = "console"
    json = "json"
    html = "html"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


def version_callback(value: bool):
    if value:
        console.print(
            "[bold cyan]Code Review CLI[/bold cyan] version [green]0.1.0[/green]"
        )
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, help="Show version and exit"
    )
):
    pass


@app.command()
def init():
    """
    Initialize a new .reviewrc configuration file in the current directory.
    """
    config_path = Path(".reviewrc")
    if config_path.exists():
        console.print(
            "[yellow]A .reviewrc file already exists in this directory.[/yellow]"
        )
        raise typer.Exit(1)

    default_config = """# .reviewrc — Code Review Assistant config

severity_threshold: low   # low | medium | high

ignore:
  - venv
  - node_modules
  - dist
  - build
  - migrations
  - "*.min.js"

enabled_modules:
  - style
  - complexity
  - security
  - bug
  - dead_code
  - bigo

rules:
  style:
    max_line_length: 120
    max_function_length: 50
    naming_convention: snake_case

  complexity:
    max_cyclomatic_complexity: 10
    max_nesting_depth: 4

  security:
    scan_secrets: true
    scan_sql_injection: true
    scan_xss: true

output:
  format: console
"""
    config_path.write_text(default_config, encoding="utf-8")
    console.print(
        f"[bold green]✅ Successfully created [/bold green][cyan]{config_path.absolute()}[/cyan]"
    )


@app.command()
def review(
    path: str = typer.Argument(".", help="File or folder to review"),
    fix: bool = typer.Option(False, "--fix", help="Show auto-fix suggestions"),
    staged: bool = typer.Option(False, "--staged", help="Only review git staged files"),
    watch: bool = typer.Option(False, "--watch", help="Watch for file changes"),
    format: OutputFormat = typer.Option(
        OutputFormat.console, "--format", help="Output format"
    ),
    severity: Severity = typer.Option(
        Severity.low, "--severity", help="Minimum severity to report"
    ),
    only: Optional[str] = typer.Option(
        None,
        "--only",
        help="Run only one module: security, style, complexity, bug, dead_code",
    ),
):
    """
    Review code for bugs, security issues, style problems, and more.
    """

    console.print(
        Panel(
            Text("Code Review Assistant v0.1.0", justify="center", style="bold cyan"),
            subtitle="[dim]Analyzing your code...[/dim]",
            border_style="cyan",
        )
    )

    console.print(f"\n[dim]Path:[/dim] [bold]{path}[/bold]")
    console.print(f"[dim]Severity:[/dim] [bold]{severity.value}[/bold]")
    if only:
        console.print(f"[dim]Module:[/dim] [bold]{only}[/bold]")
    console.print()

    target = Path(path)
    config = load_config(target)

    # Override config with CLI arguments
    if severity != Severity.low:
        config.severity_threshold = severity.value
    if only:
        config.enabled_modules = [only]

    # Show config source
    if config.config_path:
        console.print(f"[dim]Config:[/dim] [bold]{config.config_path}[/bold]")
    else:
        console.print(
            f"[dim]Config:[/dim] [yellow]No .reviewrc found — using defaults[/yellow]"
        )

    console.print()

    if not target.exists():
        console.print(f"[red]Path not found:[/red] {path}")
        raise typer.Exit(1)

    with console.status("[cyan]Scanning files...[/cyan]"):
        if staged:
            staged_paths = get_staged_files(target)
            files = []

            # Combine default ignores with any user-defined ones from config
            ignore_dirs = DEFAULT_IGNORE.copy()
            if config.ignore:
                ignore_dirs.update(config.ignore)

            for sp in staged_paths:
                if should_ignore(sp, ignore_dirs):
                    continue

                lang = detect_language(sp)
                if not lang:
                    continue

                # Skip files that are too large (likely auto-generated)
                size = sp.stat().st_size
                if size > 500 * 1024:
                    continue

                try:
                    relative = str(sp.relative_to(target))
                except ValueError:
                    relative = str(sp)

                files.append(
                    SourceFile(
                        path=sp,
                        language=lang,
                        relative_path=relative,
                        size_bytes=size,
                    )
                )
        else:
            files = walk_files(target, set(config.ignore) if config.ignore else None)

    if not files:
        console.print("[yellow]No supported source files found.[/yellow]")
        raise typer.Exit(0)

    # Show what was found
    # Group files by language
    lang_counts = {}
    for f in files:
        lang_counts[f.language] = lang_counts.get(f.language, 0) + 1

    # Build a summary table using Rich
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Language", style="cyan")
    table.add_column("Files", justify="right")

    for lang, count in sorted(lang_counts.items()):
        table.add_row(lang, str(count))

    console.print(f"[green]Found [bold]{len(files)}[/bold] files[/green]")
    console.print(table)
    console.print()

    engine = AnalysisEngine(config)
    engine.register(StyleAnalyzer(config))
    engine.register(ComplexityAnalyzer(config))
    engine.register(DeadCodeAnalyzer(config))
    engine.register(BigOAnalyzer(config))
    engine.register(BugAnalyzer(config))
    engine.register(SecurityAnalyzer(config))

    console.print("[yellow]Running analysis...[/yellow]")
    issues = engine.run(files)

    if format == OutputFormat.console:
        ConsoleReporter.report(issues, console)
    elif format == OutputFormat.json:
        JsonReporter.report(issues)
    elif format == OutputFormat.html:
        HtmlReporter.report(issues, console)


if __name__ == "__main__":
    app()
