# Code Review CLI

A CLI tool to review your code before pushing. It analyzes your codebase for complexity, styling issues, and dead code, ensuring high quality before commits or pull requests are created.

## Features

- **Complexity Analysis**: Leverages `radon` to detect overly complex code blocks.
- **Style Checking**: Analyzes code style conventions to maintain a consistent codebase.
- **Dead Code Detection**: Identifies unused variables, functions, and imports.
- **Rich Output**: Beautiful, easy-to-read terminal output powered by `rich`.
- **Git Integration**: Leverages `gitpython` to analyze modified files and staged changes.

## Installation

This project uses modern Python packaging via `hatchling`.

Ensure you have Python 3.11+ installed.

```bash
# Clone the repository
git clone https://github.com/yourusername/code-review-cli.git
cd code-review-cli

# Create a virtual environment and structure
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install the project locally
pip install -e .
```

## Usage

Once installed, the CLI tool registers the `review` command.

```bash
# Run a basic code review on the current directory
review

# Get help
review --help
```

## Development

The architecture is divided into clear and extensible modules:

- `rules/`: Definition of review rules.
- `src/analyzer/`: Core analyzers for stylistic and complexity checks.
- `src/fixers/`: Auto-fixers for resolvable issues (Coming soon).
- `src/languages/`: Multi-language parsers and support.
- `src/reporters/`: Modules for displaying or exporting analysis results.
- `src/utils/`: Generic helpers and filesystem walkers.

### Testing

Tests are managed in the `tests/` directory. (Note: Currently undergoing scaffolding).

## License

MIT License
