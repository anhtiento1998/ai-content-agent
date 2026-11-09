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

    sub.add_parser("review", help="List rendered runs waiting for approval")
    approve_p = sub.add_parser("approve", help="Approve a pending run and publish it")
    approve_p.add_argument("run_id", type=int)
    approve_p.add_argument("--platform", action="append", dest="platforms", choices=list(PUBLISHERS),
                           help="Override the run's platforms (repeatable)")
    reject_p = sub.add_parser("reject", help="Reject a pending run (it will not be published)")
    reject_p.add_argument("run_id", type=int)
    reject_p.add_argument("--reason", default=None, help="Why — kept in the review log")
    publish_p = sub.add_parser("publish", help="Retry publishing a run; platforms it is already live on are skipped")
    publish_p.add_argument("run_id", type=int)
    publish_p.add_argument("--platform", action="append", dest="platforms", choices=list(PUBLISHERS))
    takedown_p = sub.add_parser("takedown", help="Delete a run's post from a platform")
    takedown_p.add_argument("run_id", type=int)
    takedown_p.add_argument("--platform", required=True, choices=list(PUBLISHERS))
    takedown_p.add_argument("--reason", default=None, help="Why — kept in the review log")
    for review_parser in (approve_p, reject_p, publish_p, takedown_p):
        review_parser.add_argument("--by", dest="actor", default=None,
                                   help="Reviewer name for the audit log (default: your OS user name)")

    capcut_p = sub.add_parser("capcut", help="Export a rendered run as an editable CapCut desktop draft")
    capcut_p.add_argument("work_dir", nargs="?", help="Run folder under OUTPUT_DIR (default: the latest run)")
    capcut_p.add_argument("--drafts-dir", help="CapCut draft folder (default: CapCut's own, or CAPCUT_DRAFTS_DIR)")

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
        if outcome.capcut_draft:
            print(f"CapCut draft: {outcome.capcut_draft}")
        if outcome.pending_review:
            print(f"Waiting for review as run #{outcome.run_id} — approve with "
                  f"`ai-content-agent approve {outcome.run_id}` or in the dashboard (REQUIRE_APPROVAL=true).")
            return
        for result in outcome.published:
            print(f"{result.platform}: {result.url or result.remote_id}")
        failed = set(platforms) - {r.platform for r in outcome.published}
        if failed and not args.dry_run:
            print(f"Failed: {', '.join(sorted(failed))} (see `ai-content-agent history` / dashboard errors)")

    elif args.command == "schedule":
        from ai_content_agent.pipeline.scheduler import run_forever

        from ai_content_agent.history import HistoryStore

        pipeline = agent.build_pipeline(args.platforms)
        run_forever(
            pipeline, args.topics, cron_expr=args.cron, timezone=config.schedule_timezone,
            state=HistoryStore(config.history_db_path),
            jitter_seconds=max(0, config.schedule_jitter_minutes) * 60,
        )

    elif args.command == "history":
        from ai_content_agent.history import HistoryStore

        store = HistoryStore(config.history_db_path)
        runs = store.recent_runs(limit=args.limit)
        if not runs:
            print("No runs yet.")
        for run in runs:
            platforms = ", ".join(p.platform for p in run.publishes) or "not published"
            print(f"[{run.created_at}] #{run.id} {run.title!r} (topic={run.topic!r}) -> {platforms}")

    elif args.command in ("review", "approve", "reject", "publish", "takedown"):
        _review_commands(args, agent, config)

    elif args.command == "capcut":
        from ai_content_agent.export.capcut import CapCutExporter

        if args.work_dir:
            work_dir = Path(args.work_dir)
        else:
            runs = sorted(Path(config.output_dir).glob("*/timeline.json"), key=lambda p: p.stat().st_mtime)
            if not runs:
                sys.exit(f"No exportable runs in {config.output_dir} — render one with `ai-content-agent run ... --dry-run`")
            work_dir = runs[-1].parent
        try:
            draft = CapCutExporter(args.drafts_dir or config.capcut_drafts_dir).export(work_dir)
        except (RuntimeError, FileNotFoundError) as exc:
            sys.exit(f"CapCut export failed: {exc}")
        print(f"CapCut draft: {draft}")
        print("Close and reopen CapCut desktop to see it in the project list.")

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


def _review_commands(args, agent: ContentAgent, config: Config) -> None:
    from ai_content_agent.history import PENDING, REJECTED, HistoryStore

    store = HistoryStore(config.history_db_path)
    if args.command == "review":
        runs = store.pending_runs()
        if not runs:
            print("Nothing waiting for review.")
        for run in runs:
            print(f"#{run.id} [{run.created_at}] {run.title!r} -> {', '.join(run.platforms) or '-'}\n    {run.video_path}")
            if run.similar_to:
                print(f"    similar to run #{run.similar_to} ({run.similarity:.0%})")
        return

    import getpass

    try:
        actor = args.actor or f"cli:{getpass.getuser()}"
    except Exception:
        actor = "cli"

    run = store.get_run(args.run_id)
    if run is None:
        sys.exit(f"Run #{args.run_id} not found")

    if args.command == "reject":
        if run.status != PENDING:
            sys.exit(f"Run #{run.id} is {run.status}, not waiting for review")
        store.set_run_status(run.id, REJECTED)
        store.log_review(run.id, "reject", actor, note=args.reason)
        print(f"Run #{run.id} rejected.")
        return

    if args.command == "takedown":
        try:
            agent.build_pipeline([args.platform], publish_only=True).takedown(
                run.id, args.platform, actor=actor, note=args.reason
            )
        except (ValueError, NotImplementedError) as exc:
            sys.exit(f"Takedown failed: {exc}")
        print(f"Run #{run.id} taken down on {args.platform}.")
        return

    if args.command == "approve" and run.status != PENDING:
        sys.exit(f"Run #{run.id} is {run.status}, not waiting for review — use `publish` to retry")
    if args.command == "publish" and run.status in (PENDING, REJECTED):
        sys.exit(f"Run #{run.id} is {run.status} — approve it instead")
    platforms = args.platforms or run.platforms
    if not platforms:
        sys.exit("No platforms: pass --platform")
    try:
        outcome = agent.build_pipeline(platforms, publish_only=True).publish_run(
            run.id, actor=actor, action="approve" if args.command == "approve" else "retry"
        )
    except (ValueError, FileNotFoundError) as exc:
        sys.exit(f"Publish failed: {exc}")
    for result in outcome.published:
        print(f"{result.platform}: {result.url or result.remote_id} ({result.status or 'ok'})")
    failed = set(platforms) - {r.platform for r in outcome.published}
    if failed:
        print(f"Failed: {', '.join(sorted(failed))} — fix and retry with `ai-content-agent publish {run.id}`")


if __name__ == "__main__":
    main()
