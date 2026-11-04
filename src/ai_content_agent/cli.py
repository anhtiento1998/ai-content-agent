from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ai_content_agent.agent import ContentAgent
from ai_content_agent.config import Config
from ai_content_agent.publishers import PUBLISHERS
from ai_content_agent.studio import StudioStageError


def _cron(value: str) -> str:
    from apscheduler.triggers.cron import CronTrigger

    try:
        CronTrigger.from_crontab(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid cron expression {value!r}: {exc}") from exc
    return value


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
        choices=list(PUBLISHERS),
        help="Repeatable, e.g. --platform youtube --platform tiktok. Defaults to all configured platforms.",
    )
    run_p.add_argument("--dry-run", action="store_true", help="Generate but skip publishing")
    run_p.add_argument(
        "--force", action="store_true", help="Run even if this topic was already published recently"
    )

    schedule_p = sub.add_parser("schedule", help="Run forever on a cron schedule")
    schedule_p.add_argument("topics", nargs="+")
    schedule_p.add_argument("--cron", default="0 9 * * *", type=_cron)
    schedule_p.add_argument("--platform", action="append", dest="platforms", required=True, choices=list(PUBLISHERS))

    history_p = sub.add_parser("history", help="Show recently generated/published runs")
    history_p.add_argument("--limit", type=int, default=20)

    sub.add_parser("youtube-auth", help="One-time YouTube consent in a browser; caches the token for publishing")

    dash_p = sub.add_parser("dashboard", help="Start the web dashboard")
    dash_p.add_argument("--host", default="127.0.0.1")
    dash_p.add_argument("--port", type=int, default=8000)
    dash_p.add_argument("--cron", type=_cron, help="Also run automatically on this schedule, e.g. '0 9 * * *'")
    dash_p.add_argument("--topic", action="append", dest="topics", default=[], help="Repeatable; used with --cron")
    dash_p.add_argument(
        "--platform", action="append", dest="platforms", default=[], choices=list(PUBLISHERS),
        help="Repeatable; used with --cron",
    )

    args = parser.parse_args()
    if args.command == "dashboard" and args.cron and not (args.topics and args.platforms):
        dash_p.error("--cron needs at least one --topic and one --platform")
    try:
        config = Config.from_env()
    except ValueError as exc:
        sys.exit(f"Config error in .env: {exc}")
    agent = ContentAgent(config)

    if args.command == "run":
        platforms = args.platforms or ([] if args.dry_run else list(PUBLISHERS))
        try:
            pipeline = agent.build_pipeline(platforms)
            outcome = pipeline.run(args.topic, style=args.style, dry_run=args.dry_run, force=args.force)
        except StudioStageError as exc:
            sys.exit(f"Failed at stage '{exc.stage}': {exc}")
        except (ValueError, NotImplementedError) as exc:
            sys.exit(f"Setup error: {type(exc).__name__}: {exc}")
        if outcome.skipped:
            print("Skipped: this topic was already published recently (use --force to post again).")
            return
        print(f"Video: {outcome.video.file_path} ({outcome.video.duration_seconds:.1f}s)")
        for result in outcome.published:
            print(f"{result.platform}: {result.url or result.remote_id}")
        failed = set(platforms) - {r.platform for r in outcome.published}
        if failed and not args.dry_run:
            print(f"Failed: {', '.join(sorted(failed))} (see `ai-content-agent history` / dashboard errors)")

    elif args.command == "schedule":
        from ai_content_agent.pipeline.scheduler import run_forever

        pipeline = agent.build_pipeline(args.platforms)
        run_forever(pipeline, args.topics, cron_expr=args.cron)

    elif args.command == "history":
        from ai_content_agent.history import HistoryStore

        store = HistoryStore(config.history_db_path)
        runs = store.recent_runs(limit=args.limit)
        if not runs:
            print("No runs yet.")
        for run in runs:
            platforms = ", ".join(p.platform for p in run.publishes) or "not published"
            print(f"[{run.created_at}] #{run.id} {run.title!r} (topic={run.topic!r}) -> {platforms}")

    elif args.command == "youtube-auth":
        from ai_content_agent.publishers.youtube_publisher import authorize

        if not Path(config.youtube_client_secret_file).is_file():
            sys.exit(
                f"{config.youtube_client_secret_file} not found — download the OAuth client (Desktop app) JSON "
                "from Google Cloud Console and save it there (see README \"YouTube\")"
            )
        authorize(config.youtube_token_file, config.youtube_client_secret_file)
        print(f"YouTube token saved to {config.youtube_token_file}")

    elif args.command == "dashboard":
        from ai_content_agent.web.server import serve

        serve(
            config, host=args.host, port=args.port, cron=args.cron, topics=args.topics, platforms=args.platforms
        )


if __name__ == "__main__":
    main()
