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

    batch_p = sub.add_parser(
        "batch",
        help="Produce a batch from a manifest (JSONL, JSON array or one topic per line); resumable",
    )
    batch_p.add_argument("manifest", nargs="?", help="Manifest file; omit with --resume")
    batch_p.add_argument("--platform", action="append", dest="platforms", default=[], choices=list(PUBLISHERS),
                         help="Default platforms for items that do not set their own (repeatable)")
    batch_p.add_argument("--name", default="")
    batch_p.add_argument("--style", default="", help="Default style for items without one")
    batch_p.add_argument("--resume", nargs="?", type=int, const=0, default=None, metavar="BATCH_ID",
                         help="Continue queued items (of one batch, or all active batches)")
    batch_p.add_argument("--retry-failed", action="store_true", help="With --resume ID: re-queue failed items")
    sub.add_parser("batches", help="List batches and their progress")

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
    capcut_p.add_argument("--bundle", action="store_true",
                          help="Write an edit bundle (FCPXML + SRT + media) instead — any editor, any CapCut version")
    capcut_p.add_argument("--check", action="store_true", help="Show the detected CapCut version and exit")
    capcut_p.add_argument("--force", action="store_true",
                          help="Write even if CapCut is running or newer than 9.x (may corrupt nothing, but may not open)")

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

    elif args.command in ("batch", "batches"):
        _batch_commands(args, agent, config, batch_p)

    elif args.command in ("review", "approve", "reject", "publish", "takedown"):
        _review_commands(args, agent, config)

    elif args.command == "capcut":
        from ai_content_agent.export.capcut import CapCutExporter, CapCutRefused
        from ai_content_agent.export.edit_bundle import EditBundleExporter

        exporter = CapCutExporter(args.drafts_dir or config.capcut_drafts_dir, template=config.capcut_template,
                                  version=config.capcut_version, force=args.force or config.capcut_force_write)
        if args.check:
            info = exporter.check()
            print(f"CapCut store: {info['store']}")
            print(f"Version: {info['version'] or 'unknown'} ({info['version_source']})"
                  f"{'' if info['supported'] else ' — NOT supported for drafts, use --bundle'}")
            print(f"CapCut running: {'yes — quit it before exporting' if info['running'] else 'no'}")
            return
        if args.work_dir:
            work_dir = Path(args.work_dir)
        else:
            runs = sorted(Path(config.output_dir).glob("*/timeline.json"), key=lambda p: p.stat().st_mtime)
            if not runs:
                sys.exit(f"No exportable runs in {config.output_dir} — render one with `ai-content-agent run ... --dry-run`")
            work_dir = runs[-1].parent
        if args.bundle:
            print(f"Edit bundle: {EditBundleExporter().export(work_dir)}")
            print("Open the .fcpxml in DaVinci Resolve / Final Cut; import captions.srt + media/ into CapCut.")
            return
        try:
            draft = exporter.export(work_dir)
        except CapCutRefused as exc:
            sys.exit(f"CapCut export refused: {exc}\nUse `ai-content-agent capcut --bundle` for an FCPXML + SRT bundle.")
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


def _batch_commands(args, agent: ContentAgent, config: Config, parser) -> None:
    from ai_content_agent.pipeline.batch import BatchRunner, BatchStore, load_manifest

    store = BatchStore(config.history_db_path)
    if args.command == "batches":
        batches = store.list()
        if not batches:
            print("No batches yet.")
        for batch in batches:
            counts = ", ".join(f"{k} {v}" for k, v in sorted(batch.counts.items()))
            print(f"#{batch.id} {batch.name!r} [{batch.status}] {batch.total} items: {counts}")
        return

    if args.resume is None:
        if not args.manifest:
            parser.error("give a manifest file, or --resume")
        try:
            items = load_manifest(args.manifest)
        except (OSError, ValueError) as exc:
            sys.exit(f"Manifest error: {exc}")
        if not args.platforms and any(item.platforms is None for item in items):
            parser.error("--platform is required unless every item sets its own platforms")
        for item in items:
            item.style = item.style or args.style
        batch_id = store.create(args.name or Path(args.manifest).stem, args.platforms, items)
        print(f"Batch #{batch_id}: {len(items)} items queued. Ctrl+C is safe — continue with "
              f"`ai-content-agent batch --resume {batch_id}`.")
    else:
        batch_id = args.resume or None
        if args.retry_failed and batch_id:
            print(f"Re-queued {store.retry_failed(batch_id)} failed item(s).")
        store.recover()

    def report(item, status: str) -> None:
        fresh = store.get(item.batch_id, with_items=False)
        done = fresh.total - fresh.counts.get("queued", 0) - fresh.counts.get("running", 0)
        print(f"[{done}/{fresh.total}] {item.topic!r}: {status}", flush=True)

    BatchRunner(store, agent.build_pipeline).run_all(batch_id, on_item=report)
    for batch in [store.get(batch_id)] if batch_id else store.list(limit=5):
        counts = ", ".join(f"{k} {v}" for k, v in sorted(batch.counts.items()))
        print(f"Batch #{batch.id} [{batch.status}]: {counts}")
        for item in batch.items:
            if item.status == "failed":
                print(f"  failed: {item.topic!r} — {item.error}")


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
