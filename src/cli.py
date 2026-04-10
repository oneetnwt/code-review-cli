import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Optional
from enum import Enum
from pathlib import Path
from rich.table import Table

from src.utils.file_walker import walk_files
from src.utils.config import load_config
from src.analyzer.engine import AnalysisEngine
from src.analyzer.issue import Severity as IssueSeverity
from src.analyzer.style import StyleAnalyzer
from src.analyzer.complexity import ComplexityAnalyzer
from src.analyzer.dead_code import DeadCodeAnalyzer

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
        files = walk_files(target)

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

    console.print("[yellow]⚙️  Running analysis...[/yellow]")
    issues = engine.run(files)

    if not issues:
        console.print("\n[bold green]✅ No issues found![/bold green]")
    else:
        console.print(f"\n[bold red]Found {len(issues)} issue(s)[/bold red]")
        for issue in issues:
            console.print(str(issue))


if __name__ == "__main__":
    app()
