"""Quick manual trigger: generate + publish one video right now.

    python scripts/run_once.py "5 mẹo tiết kiệm điện mùa hè" --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_content_agent.agent import ContentAgent
from ai_content_agent.config import Config
from ai_content_agent.publishers import PUBLISHERS


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("topic")
    parser.add_argument("--platform", action="append", dest="platforms", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = Config.from_env()
    agent = ContentAgent(config)
    pipeline = agent.build_pipeline(args.platforms or list(PUBLISHERS))
    results = pipeline.run(args.topic, dry_run=args.dry_run)
    for result in results:
        print(f"{result.platform}: {result.url or result.remote_id}")


if __name__ == "__main__":
    main()
