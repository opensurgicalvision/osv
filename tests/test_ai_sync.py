"""Test that AI configuration files remain synchronized with .ai/ canonical source."""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_ai_configs_in_sync():
    build_script = ROOT_DIR / ".ai" / "build.py"
    result = subprocess.run(
        [sys.executable, str(build_script), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"AI configs out of sync:\n{result.stdout}\n{result.stderr}"
