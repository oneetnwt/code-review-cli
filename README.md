# Code Review CLI

A CLI tool to review your code before pushing. It analyzes your codebase for complexity, styling issues, and dead code, ensuring high quality before commits or pull requests are created.

## Features

- **Complexity Analysis**: Leverages `radon` to detect overly complex code blocks.
- **Style Checking**: Analyzes code style conventions to maintain a consistent codebase.
- **Dead Code Detection**: Identifies unused variables, functions, and imports.
- **Rich Output**: Beautiful, easy-to-read terminal output powered by `rich`.
- **Git Integration**: Leverages `gitpython` to analyze modified files and staged changes.

## Installation

You can install `code-review-cli` directly from GitHub into your global environment or project virtual environment using `pip`:

```bash
# Install the latest version directly from GitHub
pip install git+https://github.com/oneetnwt/code-review-cli.git
```

_(Note: Replace `yourusername` with your actual GitHub username!)_

### Local Development Installation

If you want to clone the repository to contribute or modify the rules:

```bash
# Clone the repository
git clone https://github.com/oneetnwt/code-review-cli.git
cd code-review-cli

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install the project and its dependencies in editable mode
pip install -e .
```

## Usage

Once installed, the CLI tool registers the `review` command globally.

```bash
# First, generate a default .reviewrc config file in your project
review init

# Run a full code review on the current directory
review review .

# Run a review on only git-staged files (Perfect for pre-commit hooks!)
review review . --staged

# Generate a beautiful HTML report
review review . --format html
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
```
