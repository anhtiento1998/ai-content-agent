"""Quick manual trigger — same as `ai-content-agent run`, without installing the package.

    python scripts/run_once.py "5 mẹo tiết kiệm điện mùa hè" --dry-run
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_content_agent.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.argv.insert(1, "run")
    main()
