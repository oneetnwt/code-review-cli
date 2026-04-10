import json
from src.analyzer.issue import Issue


class JsonReporter:
    """
    Exports the analysis results as structured JSON.
    Ideal for CI/CD pipelines, IDE plugins, or logging aggregation tools.
    """

    @staticmethod
    def report(issues: list[Issue]):
        data = []
        for issue in issues:
            data.append(
                {
                    "file": str(issue.file),
                    "line": issue.line,
                    "column": issue.col,
                    "severity": issue.severity.value,
                    "category": issue.category.value,
                    "rule": issue.rule,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                }
            )

        # In a real CI environment, you would print this to stdout so that a pipe can capture it
        # E.g. `review . --format json > report.json`
        print(json.dumps(data, indent=2))
