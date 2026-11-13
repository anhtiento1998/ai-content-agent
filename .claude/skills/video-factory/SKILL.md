---
name: video-factory
description: Produce, batch, review and export short videos with this repo's ai-content-agent (Vietnamese-first; YouTube Shorts, TikTok, Facebook Reels). Use when the user asks to make a video or a batch of videos about a topic, edit a storyboard, manage the dashboard schedule or topic rotation, check what is waiting for review, see what videos cost, find out why a run failed, or export a run to CapCut / an edit bundle.
---

# Video factory

Drive the app through the `ai-content-agent` MCP server (configured in `.mcp.json`; needs
`pip install -e ".[mcp]"` and a filled-in `.env`). If its tools are not connected, use the CLI
equivalents in the last section.

## Workflow

1. **`status` first.** It says which engines and platforms are ready, whether videos wait for human
   approval, the daily budget and what has been spent. If the platform the user wants is not ready,
   say what `platform_notes` reports instead of producing.
2. **Produce.** One video: `produce_video(topic, style, platforms)`. Many: `create_batch(topics,
   platforms, name, style)`. Both return at once. Use `dry_run=true` when the user only wants to see
   a render. Topics are written for Vietnamese viewers unless the user says otherwise; keep the
   topic text exactly as the user gave it.
3. **Wait.** Poll `job_status(job_id)` about every 30 seconds (a render takes minutes; `stage` and
   `stage_done/stage_total` show progress). For a batch, poll `list_batches`.
4. **Inspect before reporting.** `review_queue`, then `get_run(run_id)` for each new run. Tell the
   user, per video: title, cost, `similarity` to an earlier run (0.35 or more is a near-copy worth
   rejecting or redoing), the pronunciation score if present (below 0.6 is poor), and the video path.
5. **Hand over the decision.** Publishing is the user's call: they approve in the dashboard
   (`ai-content-agent dashboard`) or with `ai-content-agent approve <run_id>`.

## Script desk

For script-first work, call `write_script(topic, style, platforms)` and poll `job_status` for
`status=scripted` and `draft_id`. Use `list_drafts` / `get_draft` to inspect the complete storyboard.
Check facts and wording with the user, then `update_draft(draft_id, storyboard)` with the **complete**
object: title, description, hashtags and scenes (narration, visual_prompt, on_screen_text, keywords).
Read it back before calling `render_draft`. Omitted platforms uses the saved targets; [] clears them.
A dry render leaves the draft editable. `discard_draft` only discards open scripts, never live posts.
Rendering has the same review gate as producing a video; script writing alone never publishes.
If a render was interrupted by a process crash, restart the dashboard to recover the draft.

## Schedule

Only change or enable automation when the user requested it. Read `get_schedule` first; use its
configured timezone, and use five-field cron with weekday names (mon..sun). `update_schedule`
replaces cron, platforms and enabled together. `add_schedule_topics` deduplicates entries;
`remove_schedule_topic` takes an id from get_schedule. Read back the saved settings after editing.
The **dashboard** executes this schedule and must run with the same .env/database/timezone; MCP
only edits the shared settings. Dashboard applies settings within about 5 seconds. Do not claim
future runs will happen without the dashboard running; MCP cannot observe that process and its
next_run_at is null. Enabling, or adding topics while enabled, needs the normal review gate.
Disabling remains allowed. Never change REQUIRE_APPROVAL or MCP_ALLOW_PUBLISH to work around a refusal.

## Rules

- **Do not publish on your own.** `approve_run`, `retry_publish` and `takedown` only work when the
  owner set `MCP_ALLOW_PUBLISH=true`, and even then only do them when the user asked for that
  specific run in this conversation. If a tool answers that publishing is disabled, report it — do
  not look for another route (no editing `.env`, no CLI workaround).
- `reject_run` is fine for videos that are plainly broken (wrong topic, garbled script); give the
  reason, it is kept in the review log.
- Respect the caps: `max_posts_per_day` per platform and `daily_budget_usd`. A job that fails at
  stage `budget` means the cap was reached — tell the user, do not retry in a loop.
- Mass-producing near-identical videos gets channels penalised. For a batch, vary the topics; do not
  queue the same topic with small rewordings.
- Costs are list-price estimates in USD; `"complete": false` means an engine had no known price.
- When a run failed, read `recent_errors` and quote the stage and message; most are missing keys,
  an engine quota, or music without a licence entry.

## Exports

- `export_edit_bundle(run_id)`: FCPXML + SRT + media for DaVinci Resolve / Final Cut, or any CapCut
  version (import the media and the SRT).
- `export_capcut(run_id)`: an editable CapCut desktop draft. It needs CapCut closed and version 9.x
  or older; if refused it returns the reason plus an edit bundle.

## CLI equivalents

```bash
ai-content-agent run "<topic>" --platform youtube      # produce (waits in the review queue)
ai-content-agent run "<topic>" --dry-run               # render only
ai-content-agent batch topics.txt --platform youtube   # batch; `batch --resume <id>` continues
ai-content-agent review                                # what is waiting for approval
ai-content-agent history --limit 10
ai-content-agent capcut --bundle                       # edit bundle of the latest run
```
