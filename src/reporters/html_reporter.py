from pathlib import Path
from rich.console import Console

from src.analyzer.issue import Issue, Severity


class HtmlReporter:
    """
    Generates a beautiful HTML report of the analysis.
    Useful for dropping into web servers or emailing after build completion.
    """

    @staticmethod
    def report(
        issues: list[Issue],
        console: Console,
        output_filename: str = "review_report.html",
    ):
        html_lines = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "    <title>Code Review CLI - Report</title>",
            "    <style>",
            "        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #fdfdfd; margin: 0; padding: 2rem; color: #333; }",
            "        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }",
            "        h1 { color: #2c3e50; border-bottom: 2px solid #eaeaea; padding-bottom: 0.5rem; }",
            "        .summary { background: #f8f9fa; padding: 1rem; border-left: 4px solid #3498db; margin-bottom: 2rem; }",
            "        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }",
            "        th { background: #f1f1f1; text-align: left; padding: 0.75rem; border-bottom: 2px solid #ccc; }",
            "        td { padding: 0.75rem; border-bottom: 1px solid #eee; vertical-align: top; }",
            "        .severity-high { color: #e74c3c; font-weight: bold; }",
            "        .severity-medium { color: #f39c12; font-weight: bold; }",
            "        .severity-low { color: #27ae60; font-weight: bold; }",
            "        .suggestion { font-size: 0.85em; color: #7f8c8d; margin-top: 0.25rem; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <div class='container'>",
            "        <h1>Code Review Report</h1>",
        ]

        if not issues:
            html_lines.extend(
                [
                    "        <div class='summary' style='border-left-color: #27ae60;'>",
                    "            <h2 style='margin:0; color:#27ae60;'>Clean Code!</h2>",
                    "            <p style='margin:0;'>No issues found in this scan.</p>",
                    "        </div>",
                ]
            )
        else:
            high_count = sum(1 for i in issues if i.severity == Severity.HIGH)
            med_count = sum(1 for i in issues if i.severity == Severity.MEDIUM)
            low_count = sum(1 for i in issues if i.severity == Severity.LOW)

            html_lines.extend(
                [
                    "        <div class='summary'>",
                    f"           <p><strong>Total Issues:</strong> {len(issues)} </p>",
                    "            <p>",
                    f"              <span class='severity-high'>HIGH: {high_count}</span> | ",
                    f"              <span class='severity-medium'>MEDIUM: {med_count}</span> | ",
                    f"              <span class='severity-low'>LOW: {low_count}</span>",
                    "            </p>",
                    "        </div>",
                    "        <table>",
                    "            <thead>",
                    "                <tr>",
                    "                    <th>File</th>",
                    "                    <th>Line</th>",
                    "                    <th>Rule</th>",
                    "                    <th>Severity</th>",
                    "                    <th>Message & Suggestion</th>",
                    "                </tr>",
                    "            </thead>",
                    "            <tbody>",
                ]
            )

            for issue in sorted(
                issues, key=lambda x: (x.severity, x.file, x.line), reverse=True
            ):
                sev_class = f"severity-{issue.severity.value.lower()}"
                rule = issue.rule or "—"
                suggestion_html = (
                    f"<div class='suggestion'>{issue.suggestion}</div>"
                    if issue.suggestion
                    else ""
                )

                html_lines.extend(
                    [
                        "                <tr>",
                        f"                   <td><code>{issue.file}</code></td>",
                        f"                   <td>{issue.line}</td>",
                        f"                   <td>{rule}</td>",
                        f"                   <td class='{sev_class}'>{issue.severity.value.upper()}</td>",
                        f"                   <td><strong>{issue.message}</strong>{suggestion_html}</td>",
                        "                </tr>",
                    ]
                )

            html_lines.append("            </tbody>\n        </table>")

        html_lines.extend(["    </div>", "</body>", "</html>"])

        output_path = Path(output_filename)
        output_path.write_text("\n".join(html_lines), encoding="utf-8")

        console.print(
            f"\n[bold green]HTML report successfully generated at:[/bold green] [cyan]{output_path.absolute()}[/cyan]"
        )
