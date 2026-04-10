from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml

CONFIG_FILENAME = ".reviewrc"


@dataclass
class StyleConfig:
    """Rules for codestyle checks."""

    max_line_length: int = 120
    max_function_length: int = 50
    naming_convention: str = "snake_case"  # snake_case | camelCase | PascalCase


@dataclass
class ComplexityConfig:
    """Rules for complexity checks."""

    max_cyclomatic_complexity: int = 10
    max_nesting_depth: int = 4
    max_function_length: int = 50


@dataclass
class SecurityConfig:
    """Rules for security checks."""

    scan_secrets: bool = True
    scan_sql_injection: bool = True
    scan_xss: bool = True


@dataclass
class RulesConfig:
    """Container for all rule configs."""

    style: StyleConfig = field(default_factory=StyleConfig)
    complexity: ComplexityConfig = field(default_factory=ComplexityConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)


@dataclass
class Config:
    """
    Master config object.
    Holds all settings for a review run.
    """

    # General settings
    severity_threshold: str = "low"  # low | medium | high
    ignore: list[str] = field(default_factory=list)

    # Output settings
    output_format: str = "console"  # console | json | html

    # Module toggles
    enabled_modules: list[str] = field(
        default_factory=lambda: ["style", "complexity", "security", "bug", "dead_code"]
    )

    # Rules
    rules: RulesConfig = field(default_factory=RulesConfig)

    # Internal — where the config file was found (None = using defaults)
    config_path: Optional[Path] = field(default=None, repr=False)


def _find_config_file(start: Path) -> Optional[Path]:
    """
    Walk UP the directory tree from `start` looking for .reviewrc.

    Example:
        start = C:/project/src/utils
        checks: C:/project/src/utils/.reviewrc  → not found
        checks: C:/project/src/.reviewrc        → not found
        checks: C:/project/.reviewrc            → found! ✅
    """
    # If start is a file, begin from its parent folder
    current = start if start.is_dir() else start.parent

    # Walk up until we hit the filesystem root
    while True:
        candidate = current / CONFIG_FILENAME
        if candidate.exists():
            return candidate

        parent = current.parent
        # If we've reached the root (parent == current), stop
        if parent == current:
            return None

        current = parent


def _parse_yaml(config_path: Path) -> dict:
    """
    Safely read and parse a YAML file.
    Returns empty dict if file is empty or invalid.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        print(f"[warning] Could not parse {config_path}: {e}")
        return {}


def _build_rules(data: dict) -> RulesConfig:
    """
    Build a RulesConfig from the 'rules' section of the YAML.
    Falls back to defaults for any missing values.
    """
    rules_data = data.get("rules", {})

    # Style rules
    style_data = rules_data.get("style", {})
    style = StyleConfig(
        max_line_length=style_data.get("max_line_length", 120),
        max_function_length=style_data.get("max_function_length", 50),
        naming_convention=style_data.get("naming_convention", "snake_case"),
    )

    # Complexity rules
    complexity_data = rules_data.get("complexity", {})
    complexity = ComplexityConfig(
        max_cyclomatic_complexity=complexity_data.get("max_cyclomatic_complexity", 10),
        max_nesting_depth=complexity_data.get("max_nesting_depth", 4),
        max_function_length=complexity_data.get("max_function_length", 50),
    )

    # Security rules
    security_data = rules_data.get("security", {})
    security = SecurityConfig(
        scan_secrets=security_data.get("scan_secrets", True),
        scan_sql_injection=security_data.get("scan_sql_injection", True),
        scan_xss=security_data.get("scan_xss", True),
    )

    return RulesConfig(style=style, complexity=complexity, security=security)


def load_config(start: Path) -> Config:
    """
    Main entry point — load config for a given path.

    1. Search for .reviewrc walking up from `start`
    2. Parse the YAML
    3. Build and return a Config object
    4. If no .reviewrc found, return Config with all defaults
    """
    config_path = _find_config_file(start)

    # No config file found — use all defaults
    if config_path is None:
        return Config()

    data = _parse_yaml(config_path)

    # Extract output section
    output_data = data.get("output", {})

    return Config(
        severity_threshold=data.get("severity_threshold", "low"),
        ignore=data.get("ignore", []),
        output_format=output_data.get("format", "console"),
        enabled_modules=data.get(
            "enabled_modules", ["style", "complexity", "security", "bug", "dead_code"]
        ),
        rules=_build_rules(data),
        config_path=config_path,
    )
