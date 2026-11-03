from __future__ import annotations

import argparse
import logging

from ai_content_agent.agent import ContentAgent
from ai_content_agent.config import Config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(prog="ai-content-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Generate and publish one video now")
    run_p.add_argument("topic")
    run_p.add_argument("--style", default="")
    run_p.add_argument(
        "--platform",
        action="append",
        dest="platforms",
        default=None,
        help="Repeatable, e.g. --platform youtube --platform tiktok. Defaults to all configured platforms.",
    )
    run_p.add_argument("--dry-run", action="store_true", help="Generate but skip publishing")

    schedule_p = sub.add_parser("schedule", help="Run forever on a cron schedule")
    schedule_p.add_argument("topics", nargs="+")
    schedule_p.add_argument("--cron", default="0 9 * * *")
    schedule_p.add_argument("--platform", action="append", dest="platforms", required=True)

    args = parser.parse_args()
    config = Config.from_env()
    agent = ContentAgent(config)

    if args.command == "run":
        platforms = args.platforms or ["youtube", "tiktok", "facebook", "instagram"]
        pipeline = agent.build_pipeline(platforms)
        results = pipeline.run(args.topic, style=args.style, dry_run=args.dry_run)
        for result in results:
            print(f"{result.platform}: {result.url or result.remote_id}")

    elif args.command == "schedule":
        from ai_content_agent.pipeline.scheduler import run_forever

        pipeline = agent.build_pipeline(args.platforms)
        run_forever(pipeline, args.topics, cron_expr=args.cron)


if __name__ == "__main__":
    main()
