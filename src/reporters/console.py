from __future__ import annotations
from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.analyzer.issue import Issue, Severity


class ConsoleReporter:
    """
    Gamified console reporter that prints a 'Technical Debt Receipt'.
    Instead of just listing errors, it calculates the 'cost' of the debt generated.
    """

    # Define "Debt Points" per severity level
    DEBT_COST = {
        Severity.LOW: 10,
        Severity.MEDIUM: 50,
        Severity.HIGH: 250,
    }

    @staticmethod
    def report(issues: list[Issue], console: Console):
        if not issues:
            console.print(
                Panel(
                    "[bold green]Clean Code! No Technical Debt Purchased Today.[/bold green]",
                    border_style="green",
                    expand=False,
                )
            )
            return

        # Group by file
        issues_by_file = defaultdict(list)
        total_debt = 0

        for issue in issues:
            issues_by_file[issue.file].append(issue)
            total_debt += ConsoleReporter.DEBT_COST.get(issue.severity, 0)

        console.print("\n[bold]TECHNICAL DEBT RECEIPT[/bold]")
        console.print("[dim]" + "=" * 80 + "[/dim]")

        # Build the receipt table
        table = Table(
            show_header=True, header_style="bold magenta", expand=True, box=None
        )
        table.add_column("Rule", style="dim", width=6)
        table.add_column("Location & Problem")
        table.add_column("Severity", justify="center", width=10)
        table.add_column("Debt", justify="right", style="bold red", width=8)

        for file, file_issues in sorted(
            issues_by_file.items(), key=lambda x: str(x[0])
        ):
            # Add file header row
            table.add_row(
                f"[bold cyan]FILE[/bold cyan]", f"[bold cyan]{file}[/bold cyan]", "", ""
            )

            for issue in sorted(file_issues, key=lambda i: i.line):
                cost = ConsoleReporter.DEBT_COST.get(issue.severity, 0)
                sev_color = issue.severity.color()

                # Format location + message + suggestion
                loc = f"[dim]Line {issue.line}[/dim]"
                message = f"{issue.message}"
                if issue.suggestion:
                    message += (
                        f"\n[dim italic]Suggestion: {issue.suggestion}[/dim italic]"
                    )

                table.add_row(
                    issue.rule or "---",
                    f"{loc} {message}\n",  # extra newline for spacing
                    f"[{sev_color}]{issue.severity.value.upper()}[/{sev_color}]",
                    f"-{cost} pts",
                )

        console.print(table)
        console.print("[dim]" + "=" * 80 + "[/dim]")

        # Summary Panel grading logic
        if total_debt > 1000:
            summary_color = "red"
            grade = "F - Code Bankruptcy Imminent"
        elif total_debt > 500:
            summary_color = "yellow"
            grade = "C - Heavy Debt Load"
        else:
            summary_color = "cyan"
            grade = "A - Manageable Debt"

        summary = Text()
        summary.append(
            f"TOTAL DEBT INCURRED: {total_debt} points\n", style=f"bold {summary_color}"
        )
        summary.append(f"PROJECT GRADE: {grade}", style="bold white")

        console.print(
            Panel(
                summary,
                title="[bold]Transaction Summary[/bold]",
                border_style=summary_color,
                expand=False,
            )
        )
        console.print()
