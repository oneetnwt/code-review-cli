from pathlib import Path
from src.utils.config import load_config
from src.analyzer.engine import AnalysisEngine
from src.analyzer.style import StyleAnalyzer
from src.utils.file_walker import SourceFile


def test_style_naming_convention(tmp_path):
    # Create a temporary python file
    test_file = tmp_path / "bad_style.py"
    test_file.write_text("def BadCamelCase():\n    pass\n")

    # Set up config and analyzer
    config = load_config(tmp_path)
    engine = AnalysisEngine(config)
    engine.register(StyleAnalyzer(config))

    # Mock a SourceFile
    sf = SourceFile(
        path=test_file,
        language="python",
        relative_path="bad_style.py",
        size_bytes=test_file.stat().st_size,
    )

    # Run Analysis
    issues = engine.run([sf])

    # We should have one issue regarding the function name
    assert len(issues) == 1
    assert issues[0].rule == "S004"
    assert "BadCamelCase" in issues[0].message
