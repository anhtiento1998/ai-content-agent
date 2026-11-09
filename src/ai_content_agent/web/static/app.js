"use strict";

const TOKEN_KEY = "ai-content-agent.token";
const FAST_POLL_MS = 1500;
const SLOW_POLL_MS = 6000;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const PLATFORM_LABELS = { youtube: "YouTube Shorts", tiktok: "TikTok", facebook: "Facebook Page" };
const JOB_STATUS = {
  queued: ["Đang chờ", "info"],
  running: ["Đang chạy", "info"],
  succeeded: ["Thành công", "ok"],
  partial: ["Một phần", "warn"],
  skipped: ["Bỏ qua", "neutral"],
  failed: ["Thất bại", "bad"],
  review: ["Chờ duyệt", "warn"],
};
const RUN_STATUS = {
  pending_review: ["Chờ duyệt", "warn"],
  published: ["Đã đăng", "ok"],
  partial: ["Một phần", "warn"],
  failed: ["Thất bại", "bad"],
  rejected: ["Từ chối", "neutral"],
};
const TERMINAL = new Set(["succeeded", "partial", "skipped", "failed", "review"]);
const STAGES = {
  setup: "Khởi tạo",
  schedule: "Lịch tự động",
  script: "Kịch bản",
  voice: "Giọng đọc",
  visual: "Hình ảnh",
  render: "Dựng video",
  video: "Tạo video",
  thumbnail: "Thumbnail",
  publish: "Đăng bài",
  takedown: "Gỡ bài",
  capcut: "Xuất CapCut",
};
const ENGINE_CHIPS = [
  ["script", "text_provider", "text_providers"],
  ["visual", "visual_provider", "visual_providers"],
  ["voice", "voice_provider", "voice_providers"],
];
// Launch sequence shown for every job; error stages map onto these steps.
const ICONS = {
  script: "M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h7",
  assets: "M3 12h2l2-6 3 12 3-9 2 5 2-2h4",
  render: "M4 5h16v14H4zM4 9h16M4 15h16M9 5v4M15 5v4M9 15v4M15 15v4",
  publish: "M12 20v-8M8 8a5.7 5.7 0 0 1 8 0M5 5a10 10 0 0 1 14 0M12 12a1 1 0 1 0 0-.01",
};
const SEQUENCE = [
  ["script", "Kịch bản"],
  ["assets", "Giọng & hình"],
  ["render", "Dựng video"],
  ["publish", "Đăng bài"],
];
const FAILED_TO_STEP = {
  setup: "script", script: "script", voice: "assets", visual: "assets",
  render: "render", thumbnail: "render", video: "render", publish: "publish",
};

const state = {
  token: null,
  configLoaded: false,
  refreshing: false,
  pollTimer: null,
  firstLoad: true,
  jobStatus: new Map(),
  jobCards: new Map(),
  jobPercent: new Map(),
  seenRuns: new Set(),
  signatures: {},
  schedule: null,
  config: null,
};

// ---------- token ----------

function storeToken(value) {
  try { localStorage.setItem(TOKEN_KEY, value); } catch { /* storage unavailable */ }
}

function loadToken() {
  const match = location.hash.match(/token=([^&]+)/);
  if (match) {
    state.token = decodeURIComponent(match[1]);
    storeToken(state.token);
    history.replaceState(null, "", location.pathname + location.search);
    return;
  }
  try { state.token = localStorage.getItem(TOKEN_KEY); } catch { state.token = null; }
}

class AuthError extends Error {}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) throw new AuthError();
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail;
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return body;
}

// ---------- DOM helpers (textContent only — never innerHTML with data) ----------

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of [].concat(children)) {
    if (child) node.append(child);
  }
  return node;
}

const SVG_NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs = {}, children = []) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  for (const child of children) node.append(child);
  return node;
}

function icon(pathData) {
  return svg("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" }, [
    svg("path", { d: pathData, fill: "none", stroke: "currentColor", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round" }),
  ]);
}

function $(id) { return document.getElementById(id); }

function safeUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.href : null;
  } catch {
    return null;
  }
}

function formatTime(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

function relativeTime(iso) {
  if (!iso) return "Chưa có";
  const diffSec = (new Date(iso).getTime() - Date.now()) / 1000;
  const rtf = new Intl.RelativeTimeFormat("vi", { numeric: "auto" });
  for (const [unit, seconds] of [["day", 86400], ["hour", 3600], ["minute", 60]]) {
    if (Math.abs(diffSec) >= seconds) return rtf.format(Math.round(diffSec / seconds), unit);
  }
  return "vừa xong";
}

function badge(status) {
  const [label, tone] = JOB_STATUS[status] || [status, "neutral"];
  return el("span", { class: `badge ${tone}`, text: label });
}

function emptyRow(colspan, text) {
  return el("tr", {}, el("td", { class: "empty", colspan: String(colspan), text }));
}

function publishLinks(publishes) {
  if (!publishes.length) return el("span", { class: "muted", text: "Chưa đăng" });
  return el("div", { class: "links" }, publishes.map((p) => {
    const label = PLATFORM_LABELS[p.platform] || p.platform;
    const href = p.url && safeUrl(p.url);
    return href
      ? el("a", { class: "platform-link", href, target: "_blank", rel: "noopener noreferrer", text: `${label} ↗` })
      : el("span", { class: "badge neutral", text: label, title: p.remote_id });
  }));
}

/** Skip DOM work when the data for a region has not changed, so running CSS animations are not restarted. */
function changed(key, data) {
  const signature = JSON.stringify(data);
  if (state.signatures[key] === signature) return false;
  state.signatures[key] = signature;
  return true;
}

function setNumber(node, value) {
  const from = Number(node.dataset.value || 0);
  node.dataset.value = String(value);
  if (from === value && node.textContent === String(value)) return;
  if (reduceMotion) {
    node.textContent = String(value);
    return;
  }
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / 900);
    node.textContent = String(Math.round(from + (value - from) * (1 - (1 - t) ** 3)));
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  if (!state.firstLoad) {
    node.classList.remove("bump");
    void node.offsetWidth;
    node.classList.add("bump");
  }
}

// ---------- starfield ----------

function startStarfield() {
  const canvas = $("starfield");
  const ctx = canvas.getContext("2d");
  let width = 0, height = 0, stars = [], shooting = null, frame = 0;
  let nextShooting = performance.now() + 3000;
  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.min(420, Math.round((width * height) / 4500));
    stars = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      depth: Math.random() * 0.85 + 0.15,
      size: Math.random() * 1.3 + 0.3,
      phase: Math.random() * Math.PI * 2,
      hue: Math.random() < 0.18 ? (Math.random() < 0.5 ? 190 : 275) : null,
    }));
    if (reduceMotion) draw(performance.now());
  }

  function draw(now) {
    ctx.clearRect(0, 0, width, height);
    pointer.x += (pointer.tx - pointer.x) * 0.04;
    pointer.y += (pointer.ty - pointer.y) * 0.04;
    for (const star of stars) {
      if (!reduceMotion) {
        star.y += star.depth * 0.07;
        star.phase += 0.018 * star.depth;
        if (star.y > height + 2) { star.y = -2; star.x = Math.random() * width; }
      }
      const alpha = (0.35 + 0.65 * Math.abs(Math.sin(star.phase))) * (0.4 + 0.6 * star.depth);
      const x = star.x + pointer.x * star.depth * 18;
      const y = star.y + pointer.y * star.depth * 18;
      ctx.fillStyle = star.hue ? `hsla(${star.hue}, 100%, 78%, ${alpha})` : `rgba(235, 240, 255, ${alpha})`;
      ctx.beginPath();
      ctx.arc(x, y, star.size * star.depth + 0.15, 0, Math.PI * 2);
      ctx.fill();
    }

    if (!reduceMotion) {
      if (!shooting && now > nextShooting) {
        shooting = { x: width * (0.35 + Math.random() * 0.65), y: height * Math.random() * 0.35, vx: -(7 + Math.random() * 5), vy: 2.5 + Math.random() * 2.5, life: 1 };
      }
      if (shooting) {
        const tailX = shooting.x - shooting.vx * 14;
        const tailY = shooting.y - shooting.vy * 14;
        const gradient = ctx.createLinearGradient(shooting.x, shooting.y, tailX, tailY);
        gradient.addColorStop(0, `rgba(255, 255, 255, ${shooting.life})`);
        gradient.addColorStop(1, "rgba(77, 227, 255, 0)");
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(shooting.x, shooting.y);
        ctx.lineTo(tailX, tailY);
        ctx.stroke();
        shooting.x += shooting.vx;
        shooting.y += shooting.vy;
        shooting.life -= 0.014;
        if (shooting.life <= 0 || shooting.x < -200 || shooting.y > height + 200) {
          shooting = null;
          nextShooting = now + 4000 + Math.random() * 9000;
        }
      }
      frame = requestAnimationFrame(draw);
    }
  }

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 150);
  });
  window.addEventListener("pointermove", (event) => {
    pointer.tx = event.clientX / window.innerWidth - 0.5;
    pointer.ty = event.clientY / window.innerHeight - 0.5;
  });
  document.addEventListener("visibilitychange", () => {
    if (reduceMotion) return;
    if (document.hidden) cancelAnimationFrame(frame);
    else frame = requestAnimationFrame(draw);
  });
  resize();
  if (!reduceMotion) frame = requestAnimationFrame(draw);
}

// ---------- toasts ----------

function toast(tone, title, message) {
  const node = el("div", { class: `toast ${tone}`, role: "status" }, [
    el("span", { class: "toast-icon" }),
    el("div", {}, [el("strong", { text: title }), el("span", { text: message })]),
  ]);
  $("toasts").append(node);
  setTimeout(() => {
    node.classList.add("leaving");
    setTimeout(() => node.remove(), 400);
  }, 5200);
}

// ---------- renderers ----------

function renderConfig(cfg) {
  state.config = cfg;
  $("provider-chips").replaceChildren(...ENGINE_CHIPS.map(([label, key, group]) => {
    const name = cfg[key];
    const info = (cfg[group] || {})[name];
    return el("span", { class: `chip ${info && info.ready ? "on" : "off"}`, title: info ? info.note : "Engine không hợp lệ" }, [
      el("span", { class: "led" }),
      el("span", { class: "chip-key", text: `${label}:` }),
      el("span", { text: name }),
    ]);
  }));

  $("platforms").replaceChildren(...Object.entries(cfg.platforms).map(([name, info]) => {
    const input = el("input", { type: "checkbox", name: "platform", value: name, disabled: !info.ready });
    return el("label", { class: `platform${info.ready ? "" : " disabled"}` }, [
      input,
      el("span", {}, [
        el("span", { text: PLATFORM_LABELS[name] || name }),
        info.note ? el("small", { text: info.note }) : null,
        info.warning ? el("small", { class: "warn-note", text: `⚠ ${info.warning}` }) : null,
      ]),
    ]);
  }));
}

const REVIEWER_KEY = "aca.reviewer";

function reviewer() {
  return $("reviewer").value.trim();
}

function initReviewer() {
  const input = $("reviewer");
  try { input.value = localStorage.getItem(REVIEWER_KEY) || ""; } catch { /* storage unavailable */ }
  input.addEventListener("change", () => {
    try { localStorage.setItem(REVIEWER_KEY, reviewer()); } catch { /* storage unavailable */ }
  });
}

function reviewBody(extra = {}) {
  return JSON.stringify({ reviewer: reviewer(), ...extra });
}

const REVIEW_ACTIONS = { approve: "duyệt", reject: "từ chối", retry: "đăng lại", takedown: "gỡ" };

function lastReview(run) {
  const entry = (run.reviews || [])[run.reviews.length - 1];
  if (!entry) return null;
  const who = entry.actor.replace(/^dashboard:?/, "").replace(/^cli:?/, "CLI ") || "dashboard";
  const text = `${REVIEW_ACTIONS[entry.action] || entry.action} bởi ${who} · ${relativeTime(entry.created_at)}`;
  return el("div", { class: "muted review-log", title: entry.note || "", text: entry.note ? `${text} — “${entry.note}”` : text });
}

function renderStats(stats) {
  setNumber($("stat-runs"), stats.total_runs);
  $("stat-runs").nextElementSibling.textContent = stats.pending_review ? `video đã sản xuất · ${stats.pending_review} chờ duyệt` : "video đã sản xuất";
  setNumber($("stat-publishes"), stats.total_publishes);
  setNumber($("stat-errors"), stats.errors_last_7_days);
  $("stat-last").textContent = relativeTime(stats.last_run_at);
  $("stat-last-abs").textContent = stats.last_run_at ? formatTime(stats.last_run_at) : "chưa có lần phóng nào";
  const parts = Object.entries(stats.publishes_by_platform).map(([p, n]) => `${PLATFORM_LABELS[p] || p}: ${n}`);
  $("stat-platforms").textContent = parts.length ? parts.join(" · ") : "lượt đăng thành công";
}

function orbitGraphic() {
  return el("div", { class: "orbit" }, [
    svg("svg", { viewBox: "0 0 150 150", "aria-hidden": "true" }, [
      svg("circle", { class: "track-ring", cx: "75", cy: "75", r: "62" }),
      svg("circle", { class: "track-ring", cx: "75", cy: "75", r: "50" }),
      svg("circle", { class: "core", cx: "75", cy: "75", r: "38" }),
      svg("g", { class: "sat-arm" }, [svg("circle", { class: "satellite", cx: "75", cy: "13", r: "5" })]),
      svg("g", { class: "moon-arm" }, [svg("circle", { class: "moon", cx: "125", cy: "75", r: "3.5" })]),
    ]),
    el("div", { class: "orbit-center" }, [
      el("span", { class: "countdown", id: "countdown", text: "T-––:––:––" }),
      el("span", { class: "countdown-label", text: "NEXT LAUNCH" }),
    ]),
  ]);
}

function renderSchedule(schedule) {
  state.schedule = schedule;
  if (!changed("schedule", schedule)) return;
  const box = $("schedule");
  if (!schedule.enabled) {
    box.replaceChildren(el("div", { class: "schedule-off" }, [
      orbitGraphic(),
      el("div", {}, [
        el("p", { class: "muted", text: "Chưa có quỹ đạo nào. Chạy dashboard kèm lịch để tự động phóng, ví dụ:" }),
        el("p", {}, el("code", { text: 'ai-content-agent dashboard --cron "0 9 * * *" --topic "Chủ đề 1" --platform youtube' })),
      ]),
    ]));
    return;
  }
  const row = (label, value) => [el("dt", { text: label }), el("dd", { text: value })];
  box.replaceChildren(el("div", { class: "orbit-wrap" }, [
    orbitGraphic(),
    el("dl", { class: "schedule-grid" }, [
      ...row("cron", schedule.cron),
      ...row("lần tới", formatTime(schedule.next_run_at)),
      ...row("chủ đề", schedule.next_topic || "Hết chủ đề mới — mọi chủ đề đã đăng gần đây, hãy thêm chủ đề"),
      ...row("quỹ đạo", schedule.platforms.map((p) => PLATFORM_LABELS[p] || p).join(", ")),
      ...row("danh sách", `${schedule.topics.length} chủ đề, xoay vòng`),
    ]),
  ]));
  tickCountdown();
}

function tickCountdown() {
  const node = $("countdown");
  const schedule = state.schedule;
  if (!node || !schedule || !schedule.enabled || !schedule.next_run_at) return;
  let seconds = Math.max(0, Math.round((new Date(schedule.next_run_at).getTime() - Date.now()) / 1000));
  const days = Math.floor(seconds / 86400);
  seconds %= 86400;
  const pad = (n) => String(n).padStart(2, "0");
  const clock = `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor((seconds % 3600) / 60))}:${pad(seconds % 60)}`;
  node.textContent = days ? `T-${days}d ${clock}` : `T-${clock}`;
}

/** Per-step state for the launch sequence, derived from real job progress. */
function sequenceFor(job) {
  // Publish jobs (approve/retry) only have the publish step; dry runs stop after rendering.
  const steps = job.kind === "publish" ? SEQUENCE.slice(3) : job.dry_run ? SEQUENCE.slice(0, 3) : SEQUENCE;
  const index = (key) => Math.max(0, steps.findIndex(([k]) => k === key));
  let states;
  let current = -1;
  if (job.status === "review") {
    states = steps.map(([k]) => (k === "publish" ? "warn" : "done"));
    return { steps, states, fraction: (steps.length - 1) / steps.length };
  }
  if (job.status === "queued") states = steps.map(() => "pending");
  else if (job.status === "skipped") states = steps.map(() => "skipped");
  else if (job.status === "succeeded") states = steps.map(() => "done");
  else if (job.status === "partial") states = steps.map(([k]) => (k === "publish" ? "warn" : "done"));
  else {
    current = index(job.status === "failed" ? FAILED_TO_STEP[job.failed_stage] || job.stage || "script" : job.stage || "script");
    const here = job.status === "failed" ? "failed" : "active";
    states = steps.map((_, i) => (i < current ? "done" : i === current ? here : "pending"));
  }

  let fraction = 0;
  if (job.status === "succeeded" || job.status === "partial") fraction = 1;
  else if (current >= 0) {
    const within = job.stage_total ? job.stage_done / job.stage_total : 0.35;
    fraction = (current + (job.status === "failed" ? 0.5 : within)) / steps.length;
  }
  return { steps, states, fraction };
}

function stageCount(job, key, stepState) {
  if (key !== job.stage || !job.stage_total) return "";
  if (stepState === "active" || stepState === "failed") return `${job.stage_done}/${job.stage_total}`;
  return "";
}

function buildJobCard(job, previousPercent, isNew) {
  const { steps, states, fraction } = sequenceFor(job);
  const platforms = job.platforms.map((p) => PLATFORM_LABELS[p] || p).join(", ") || "—";
  const meta = [
    { schedule: "⟲ theo lịch", review: "✓ duyệt & đăng", retry: "↻ đăng lại", batch: "▦ hàng loạt" }[job.source] || "▸ thủ công",
    job.dry_run ? "chạy thử" : platforms,
    formatTime(job.finished_at || job.started_at || job.created_at),
  ].join("  ·  ");

  const sequence = el("div", { class: "sequence", role: "list", "aria-label": "Tiến trình" });
  steps.forEach(([key, label], i) => {
    if (i > 0) {
      const prev = states[i - 1];
      const flowing = prev === "done" && states[i] === "active";
      sequence.append(el("div", { class: `link${prev === "done" && !flowing ? " done" : ""}${flowing ? " flowing" : ""}`, "aria-hidden": "true" }));
    }
    sequence.append(el("div", { class: `stage ${states[i]}`, role: "listitem" }, [
      el("div", { class: "node" }, icon(ICONS[key])),
      el("span", { class: "stage-name", text: label }),
      el("span", { class: "stage-count", text: stageCount(job, key, states[i]) }),
    ]));
  });

  const percent = Math.round(fraction * 100);
  const fill = el("div", { class: "thruster-fill" });
  fill.style.width = `${previousPercent ?? 0}%`;
  requestAnimationFrame(() => requestAnimationFrame(() => { fill.style.width = `${percent}%`; }));

  const stagePrefix = job.failed_stage ? `[${STAGES[job.failed_stage] || job.failed_stage}] ` : "";
  return el("li", { class: `job is-${job.status}${isNew ? " entering" : ""}` }, [
    el("div", { class: "job-head" }, [el("span", { class: "job-topic", text: job.topic }), badge(job.status)]),
    el("div", { class: "job-meta", text: meta }),
    sequence,
    el("div", { class: "thruster", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(percent) }, fill),
    job.error ? el("div", { class: "job-error", text: `> ${stagePrefix}${job.error}` }) : null,
    job.video_path ? el("div", { class: "job-meta job-path", text: `▣ ${job.video_path}` }) : null,
    job.capcut_draft ? el("div", { class: "job-meta job-path capcut-path", text: `◆ CapCut: ${job.capcut_draft}` }) : null,
    job.results.length ? el("div", { class: "job-links" }, publishLinks(job.results)) : null,
    capcutButton(job),
  ]);
}

function capcutButton(job) {
  if (!job.video_path) return null;
  const status = state.config && state.config.capcut;
  const ready = Boolean(status && status.ready);
  return el("div", { class: "job-actions" }, el("button", {
    type: "button",
    class: "btn small",
    "data-capcut": job.id,
    disabled: !ready,
    title: ready ? "Tạo project nháp để mở và chỉnh tay trong CapCut desktop" : status && status.note,
    text: job.capcut_draft ? "⇪ Xuất lại CapCut" : "⇪ Xuất CapCut",
  }));
}

async function exportCapcut(button) {
  button.disabled = true;
  button.classList.add("busy");
  try {
    const { draft } = await api(`/api/jobs/${encodeURIComponent(button.dataset.capcut)}/capcut`, { method: "POST" });
    toast("ok", "CAPCUT DRAFT READY", `Mở lại CapCut để thấy project: ${draft}`);
    await refresh();
  } catch (err) {
    if (err instanceof AuthError) showAuth(true);
    else toast("bad", "CAPCUT EXPORT FAILED", err.message);
    button.disabled = false;
  } finally {
    button.classList.remove("busy");
  }
}

function announce(job, previous) {
  if (!previous || previous === job.status || !TERMINAL.has(job.status)) return false;
  const messages = {
    succeeded: ["ok", job.dry_run ? "RENDER COMPLETE" : "MISSION COMPLETE", job.dry_run ? `Video đã dựng xong: ${job.topic}` : `Đã đăng: ${job.topic}`],
    partial: ["warn", "PARTIAL SUCCESS", `Một số nền tảng đăng lỗi: ${job.topic}`],
    skipped: ["info", "MISSION SKIPPED", `Chủ đề đã đăng gần đây: ${job.topic}`],
    failed: ["bad", "MISSION FAILED", `${job.topic} — ${STAGES[job.failed_stage] || "lỗi"}`],
    review: ["warn", "AWAITING REVIEW", `Video đã dựng xong, chờ bạn duyệt: ${job.topic}`],
  };
  const message = messages[job.status];
  if (message) toast(...message);
  return true;
}

function renderJobs(jobs) {
  const list = $("jobs");
  const visible = jobs.slice(0, 8);
  if (!visible.length) {
    if (changed("jobs-empty", true)) list.replaceChildren(el("li", { class: "empty-state", text: "// chưa có nhiệm vụ nào kể từ khi khởi động" }));
    return;
  }
  state.signatures["jobs-empty"] = undefined;

  const wanted = visible.map((job) => {
    const previous = state.jobStatus.get(job.id);
    const justFinished = announce(job, previous);
    state.jobStatus.set(job.id, job.status);

    const signature = JSON.stringify(job);
    const cached = state.jobCards.get(job.id);
    if (cached && cached.signature === signature) return cached.node;
    const node = buildJobCard(job, state.jobPercent.get(job.id), !cached);
    if (justFinished) node.classList.add("just-finished");
    state.jobPercent.set(job.id, Math.round(sequenceFor(job).fraction * 100));
    state.jobCards.set(job.id, { signature, node });
    return node;
  });

  [...list.children].forEach((child) => { if (!wanted.includes(child)) child.remove(); });
  wanted.forEach((node, i) => {
    if (list.children[i] !== node) list.insertBefore(node, list.children[i] || null);
  });
}

function runBadge(status) {
  const [label, tone] = RUN_STATUS[status] || [status, "neutral"];
  return el("span", { class: `badge ${tone}`, text: label });
}

function runActions(run) {
  const actions = [];
  const live = run.publishes.filter((p) => !p.deleted_at);
  if (run.status === "partial" || run.status === "failed") {
    actions.push(el("button", { type: "button", class: "btn small", "data-action": "retry", "data-run": String(run.id),
      title: "Đăng lại lên các nền tảng chưa thành công (nền tảng đã đăng sẽ được bỏ qua)", text: "↻ Đăng lại" }));
  }
  for (const p of live) {
    actions.push(el("button", { type: "button", class: "btn small bad", "data-action": "takedown",
      "data-run": String(run.id), "data-platform": p.platform, text: `Gỡ ${PLATFORM_LABELS[p.platform] || p.platform}` }));
  }
  return actions.length ? el("div", { class: "row-actions" }, actions) : el("span", { class: "muted", text: "—" });
}

function renderRuns(runs) {
  if (!changed("runs", runs)) return;
  const body = $("runs");
  if (!runs.length) {
    body.replaceChildren(emptyRow(5, "// mission log trống — chưa có video nào"));
    return;
  }
  body.replaceChildren(...runs.map((run) => {
    const fresh = !state.firstLoad && !state.seenRuns.has(run.id);
    state.seenRuns.add(run.id);
    const live = run.publishes.filter((p) => !p.deleted_at);
    const removed = run.publishes.filter((p) => p.deleted_at);
    return el("tr", { class: fresh ? "fresh" : "" }, [
      el("td", { class: "nowrap", "data-label": "Thời gian", text: formatTime(run.created_at) }),
      el("td", { "data-label": "Tiêu đề" }, [el("div", { text: run.title }), el("div", { class: "muted", text: run.topic })]),
      el("td", { "data-label": "Trạng thái" }, [runBadge(run.status), lastReview(run)]),
      el("td", { "data-label": "Đã đăng" }, [
        publishLinks(live),
        removed.length ? el("div", { class: "taken-down", text: `đã gỡ: ${removed.map((p) => PLATFORM_LABELS[p.platform] || p.platform).join(", ")}` }) : null,
      ]),
      el("td", { "data-label": "Thao tác" }, runActions(run)),
    ]);
  }));
}

// ---------- review queue ----------

const mediaCache = new Map();

/** Media needs the bearer token, which <img>/<video> cannot send — fetch it and use a blob URL. */
async function authedMedia(path) {
  if (!mediaCache.has(path)) {
    mediaCache.set(path, (async () => {
      const res = await fetch(path, { headers: { Authorization: `Bearer ${state.token}` } });
      if (res.status === 401) throw new AuthError();
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return URL.createObjectURL(await res.blob());
    })());
  }
  return mediaCache.get(path);
}

function buildReviewCard(run) {
  const media = el("div", { class: "review-media" }, [
    el("button", { type: "button", class: "play", "data-action": "play", "data-run": String(run.id),
      "aria-label": "Xem video", text: "▶" }),
  ]);
  authedMedia(`/api/runs/${run.id}/thumbnail`).then((url) => {
    media.prepend(el("img", { src: url, alt: "" }));
  }).catch(() => { /* no thumbnail — the play button still works */ });

  const ready = (state.config && state.config.platforms) || {};
  const platforms = el("div", { class: "review-platforms" }, Object.keys(PLATFORM_LABELS).map((name) =>
    el("label", { title: ready[name] && ready[name].note }, [
      el("input", { type: "checkbox", name: `review-${run.id}`, value: name,
        checked: run.platforms.includes(name), disabled: ready[name] && !ready[name].ready }),
      el("span", { text: PLATFORM_LABELS[name] }),
    ])));

  return el("article", { class: "review-card", "data-run": String(run.id) }, [
    media,
    el("div", { class: "review-body" }, [
      el("div", { class: "review-title", text: run.title }),
      el("div", { class: "job-meta", text: `#${run.id} · ${run.topic} · ${formatTime(run.created_at)}` }),
      reviewFacts(run),
      platforms,
      el("div", { class: "review-actions" }, [
        el("button", { type: "button", class: "btn small ok", "data-action": "approve", "data-run": String(run.id), text: "✓ Duyệt & đăng" }),
        el("button", { type: "button", class: "btn small bad", "data-action": "reject", "data-run": String(run.id), text: "✕ Từ chối" }),
      ]),
    ]),
  ]);
}

const HOOK_LABELS = { question: "mở bằng câu hỏi", shock: "mở bằng sự thật gây sốc", list: "mở bằng danh sách",
  story: "mở bằng câu chuyện", myth: "phá lầm tưởng", contrast: "trước / sau" };

/** What a reviewer should know before approving: variation used, similarity, pronunciation, music licence. */
function reviewFacts(run) {
  const facts = [];
  const v = run.variation || {};
  if (v.hook) facts.push(el("span", { class: "fact", text: HOOK_LABELS[v.hook] || v.hook }));
  if (v.visual_style) facts.push(el("span", { class: "fact", text: `hình: ${v.visual_style}` }));
  if (v.voice) facts.push(el("span", { class: "fact", text: `giọng: ${v.voice}` }));
  const music = (run.provenance || {}).music;
  if (music) {
    facts.push(el("span", { class: `fact${music.license ? "" : " bad"}`, title: music.source || "",
      text: `nhạc: ${music.file} · ${music.license || "THIẾU GIẤY PHÉP"}` }));
  }
  if (run.similar_to && run.similarity != null) {
    const pct = Math.round(run.similarity * 100);
    facts.push(el("span", { class: `fact ${pct >= 35 ? "bad" : "warn"}`,
      title: "Độ trùng ý với kịch bản đã làm trước đó (3 từ liên tiếp giống nhau)",
      text: `giống #${run.similar_to}: ${pct}%` }));
  }
  const pron = ((run.provenance || {}).pronunciation || {}).min;
  if (pron != null) {
    const pct = Math.round(pron * 100);
    facts.push(el("span", { class: `fact ${pct < 60 ? "bad" : ""}`, title: "Tỷ lệ từ nhận dạng lại được từ giọng đọc (cảnh kém nhất)",
      text: `phát âm: ${pct}%` }));
  }
  return facts.length ? el("div", { class: "facts" }, facts) : null;
}

function renderReviews(runs) {
  const count = $("review-count");
  count.textContent = String(runs.length);
  count.classList.toggle("zero", runs.length === 0);
  if (!changed("reviews", runs.map((r) => [r.id, r.platforms, r.similarity, r.variation]))) return;
  const box = $("reviews");
  if (!runs.length) {
    box.replaceChildren(el("div", { class: "empty-state", text: "// không có video nào đang chờ duyệt" }));
    return;
  }
  box.replaceChildren(...runs.map(buildReviewCard));
}

async function runAction(button, request, success) {
  button.disabled = true;
  try {
    await request();
    if (success) toast(...success);
    state.signatures.reviews = undefined;
    state.signatures.runs = undefined;
    await refresh();
  } catch (err) {
    if (err instanceof AuthError) showAuth(true);
    else toast("bad", "ACTION FAILED", err.message);
    button.disabled = false;
  }
}

async function onReviewClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button || button.disabled) return;
  const runId = button.dataset.run;
  if (button.dataset.action === "play") {
    const media = button.closest(".review-media");
    try {
      const url = await authedMedia(`/api/runs/${runId}/video`);
      media.replaceChildren(el("video", { src: url, controls: true, autoplay: true, playsinline: true }));
    } catch (err) {
      toast("bad", "PREVIEW FAILED", err.message);
    }
    return;
  }
  if (button.dataset.action === "approve") {
    const platforms = [...document.querySelectorAll(`input[name="review-${runId}"]:checked`)].map((i) => i.value);
    if (!platforms.length) {
      toast("warn", "CHỌN NỀN TẢNG", "Chọn ít nhất 1 nền tảng để đăng.");
      return;
    }
    await runAction(button, () => api(`/api/runs/${runId}/approve`, { method: "POST", body: reviewBody({ platforms }) }),
      ["info", "APPROVED", `Đang đăng video #${runId} lên ${platforms.map((p) => PLATFORM_LABELS[p]).join(", ")}`]);
  } else if (button.dataset.action === "reject") {
    const reason = window.prompt(`Từ chối video #${runId}? Video sẽ không được đăng.\nLý do (không bắt buộc, ghi vào nhật ký):`, "");
    if (reason === null) return;
    await runAction(button, () => api(`/api/runs/${runId}/reject`, { method: "POST", body: reviewBody({ reason: reason.trim() }) }),
      ["info", "REJECTED", `Đã từ chối video #${runId}`]);
  }
}

async function onRunsClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button || button.disabled) return;
  const runId = button.dataset.run;
  if (button.dataset.action === "retry") {
    await runAction(button, () => api(`/api/runs/${runId}/publish`, { method: "POST", body: reviewBody({ platforms: [] }) }),
      ["info", "RETRY", `Đang đăng lại video #${runId} lên các nền tảng còn thiếu`]);
  } else if (button.dataset.action === "takedown") {
    const label = PLATFORM_LABELS[button.dataset.platform] || button.dataset.platform;
    const reason = window.prompt(`Gỡ video #${runId} khỏi ${label}? Thao tác này xóa bài trên nền tảng.\nLý do (không bắt buộc):`, "");
    if (reason === null) return;
    await runAction(button, () => api(`/api/runs/${runId}/takedown`, { method: "POST", body: reviewBody({ platform: button.dataset.platform, reason: reason.trim() }) }),
      ["ok", "TAKEN DOWN", `Đã gỡ video #${runId} khỏi ${label}`]);
  }
}

// ---------- batches ----------

const BATCH_STATUS = { active: ["Đang chạy", "info"], paused: ["Tạm dừng", "neutral"], finished: ["Xong", "ok"] };
const ITEM_STATUS = {
  queued: ["Chờ", "neutral"], running: ["Đang làm", "info"], review: ["Chờ duyệt", "warn"],
  done: ["Xong", "ok"], skipped: ["Bỏ qua", "neutral"], failed: ["Lỗi", "bad"],
};

function batchCard(batch) {
  const counts = batch.counts || {};
  const finished = batch.total - (counts.queued || 0) - (counts.running || 0);
  const percent = batch.total ? Math.round((finished / batch.total) * 100) : 0;
  const [label, tone] = BATCH_STATUS[batch.status] || [batch.status, "neutral"];
  const fill = el("div", { class: "thruster-fill" });
  fill.style.width = `${percent}%`;
  const summary = Object.entries(ITEM_STATUS)
    .filter(([key]) => counts[key])
    .map(([key, [text]]) => `${text} ${counts[key]}`).join(" · ");
  const actions = [];
  if (batch.status === "active") actions.push(["pause", "❚❚ Tạm dừng", ""]);
  if (batch.status === "paused") actions.push(["resume", "▶ Tiếp tục", "ok"]);
  if (counts.failed) actions.push(["retry", `↻ Làm lại ${counts.failed} mục lỗi`, ""]);
  const items = el("ol", { class: "batch-items" }, batch.items.map((item) => {
    const [itemLabel, itemTone] = ITEM_STATUS[item.status] || [item.status, "neutral"];
    return el("li", {}, [
      el("span", { class: `badge ${itemTone}`, text: itemLabel }),
      el("span", { class: "batch-topic", text: item.topic }),
      item.run_id ? el("span", { class: "muted", text: ` #${item.run_id}` }) : null,
      item.error && item.status !== "done" ? el("div", { class: "muted batch-error", text: item.error }) : null,
    ]);
  }));
  return el("article", { class: "batch-card" }, [
    el("div", { class: "batch-head" }, [
      el("div", {}, [
        el("div", { class: "review-title", text: batch.name }),
        el("div", { class: "job-meta", text: `#${batch.id} · ${finished}/${batch.total} · ${summary || "—"}` }),
      ]),
      el("span", { class: `badge ${tone}`, text: label }),
    ]),
    el("div", { class: "thruster", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100",
      "aria-valuenow": String(percent) }, fill),
    actions.length ? el("div", { class: "row-actions" }, actions.map(([action, text, cls]) =>
      el("button", { type: "button", class: `btn small ${cls}`, "data-batch-action": action,
        "data-batch": String(batch.id), text }))) : null,
    el("details", {}, [el("summary", { text: `Xem ${batch.total} mục` }), items]),
  ]);
}

function renderBatches(batches) {
  const panel = $("batch-panel");
  panel.hidden = batches === null;
  if (batches === null || !changed("batches", batches)) return;
  const open = new Set([...document.querySelectorAll("#batches details[open]")].map((d) => d.closest(".batch-card").dataset.id));
  $("batches").replaceChildren(...(batches.length ? batches.map((b) => {
    const card = batchCard(b);
    card.dataset.id = String(b.id);
    if (open.has(String(b.id))) card.querySelector("details").open = true;
    return card;
  }) : [el("div", { class: "empty-state", text: "// chưa có lô nào" })]));
}

async function submitBatch(event) {
  event.preventDefault();
  const errorBox = $("batch-error");
  errorBox.hidden = true;
  const manifest = $("batch-manifest").value.trim();
  const platforms = [...document.querySelectorAll('input[name="platform"]:checked')].map((i) => i.value);
  if (!manifest) {
    errorBox.textContent = "Nhập ít nhất 1 chủ đề.";
    errorBox.hidden = false;
    return;
  }
  const button = $("batch-submit");
  button.disabled = true;
  try {
    const batch = await api("/api/batches", { method: "POST", body: JSON.stringify({
      manifest, platforms, name: $("batch-name").value.trim(), style: $("style").value.trim() }) });
    $("batch-manifest").value = "";
    $("batch-name").value = "";
    toast("ok", "BATCH QUEUED", `Lô #${batch.id}: ${batch.total} video đã vào hàng đợi`);
    state.signatures.batches = undefined;
    await refresh();
  } catch (err) {
    if (err instanceof AuthError) showAuth(true);
    else {
      errorBox.textContent = err.message;
      errorBox.hidden = false;
    }
  } finally {
    button.disabled = false;
  }
}

async function onBatchClick(event) {
  const button = event.target.closest("button[data-batch-action]");
  if (!button || button.disabled) return;
  const { batchAction, batch } = button.dataset;
  await runAction(button, () => api(`/api/batches/${batch}/${batchAction}`, { method: "POST" }), null);
  state.signatures.batches = undefined;
}

function renderErrors(errors) {
  if (!changed("errors", errors)) return;
  const body = $("errors");
  if (!errors.length) {
    body.replaceChildren(emptyRow(5, "// không có sự cố — mọi hệ thống bình thường"));
    return;
  }
  body.replaceChildren(...errors.map((err) => el("tr", {}, [
    el("td", { class: "nowrap", "data-label": "Thời gian", text: formatTime(err.created_at) }),
    el("td", { class: "nowrap stage-tag", "data-label": "Bước", text: STAGES[err.stage] || err.stage }),
    el("td", { class: "nowrap", "data-label": "Nền tảng", text: err.platform ? PLATFORM_LABELS[err.platform] || err.platform : "—" }),
    el("td", { "data-label": "Chủ đề", text: err.topic }),
    el("td", { class: "err-msg", "data-label": "Chi tiết", text: err.message }),
  ])));
}

// ---------- flow ----------

function showAuth(failed) {
  $("app").hidden = true;
  $("auth").hidden = false;
  $("auth-error").hidden = !failed;
  $("updated-at").textContent = "awaiting credentials";
}

function showApp() {
  $("auth").hidden = true;
  $("app").hidden = false;
}

function schedulePoll(jobs) {
  clearTimeout(state.pollTimer);
  const active = (jobs || []).some((job) => !TERMINAL.has(job.status));
  state.pollTimer = setTimeout(() => {
    if (document.hidden || !$("auth").hidden) schedulePoll(jobs);
    else refresh();
  }, active ? FAST_POLL_MS : SLOW_POLL_MS);
}

async function refresh() {
  if (state.refreshing) return;
  state.refreshing = true;
  let jobs = [];
  try {
    if (!state.configLoaded) {
      renderConfig(await api("/api/config"));
      state.configLoaded = true;
    }
    const [stats, runs, errors, jobList, schedule, reviews, batches] = await Promise.all([
      api("/api/stats"), api("/api/runs"), api("/api/errors"), api("/api/jobs"), api("/api/schedule"),
      api("/api/reviews"),
      api("/api/batches").catch((err) => { if (err instanceof AuthError) throw err; return null; }),
    ]);
    jobs = jobList;
    showApp();
    renderStats(stats);
    renderRuns(runs);
    renderErrors(errors);
    renderJobs(jobs);
    renderSchedule(schedule);
    renderReviews(reviews);
    renderBatches(batches);
    state.firstLoad = false;
    $("updated-at").textContent = `telemetry synced ${new Date().toLocaleTimeString("vi-VN")}`;
  } catch (err) {
    if (err instanceof AuthError) showAuth(Boolean(state.token));
    else $("updated-at").textContent = `signal lost: ${err.message}`;
  } finally {
    state.refreshing = false;
    schedulePoll(jobs);
  }
}

async function submitRun(event) {
  event.preventDefault();
  const errorBox = $("run-error");
  const topic = $("topic").value.trim();
  const platforms = [...document.querySelectorAll('input[name="platform"]:checked')].map((i) => i.value);
  const dryRun = $("dry-run").checked;

  errorBox.hidden = true;
  if (!topic) {
    errorBox.textContent = "Nhập chủ đề trước đã.";
    errorBox.hidden = false;
    return;
  }
  if (!dryRun && !platforms.length) {
    errorBox.textContent = "Chọn ít nhất 1 nền tảng, hoặc bật “Chạy thử”.";
    errorBox.hidden = false;
    return;
  }

  const button = $("run-submit");
  button.disabled = true;
  button.classList.remove("launching");
  void button.offsetWidth;
  button.classList.add("launching");
  setTimeout(() => button.classList.remove("launching"), 1000);
  try {
    await api("/api/runs", {
      method: "POST",
      body: JSON.stringify({ topic, platforms, style: $("style").value.trim(), dry_run: dryRun, force: $("force").checked }),
    });
    toast("info", "LIFTOFF", `Đã phóng nhiệm vụ: ${topic}`);
    $("topic").value = "";
    await refresh();
  } catch (err) {
    if (err instanceof AuthError) showAuth(true);
    errorBox.textContent = `Không gửi được: ${err.message || "lỗi không xác định"}`;
    errorBox.hidden = false;
  } finally {
    button.disabled = false;
  }
}

function submitAuth(event) {
  event.preventDefault();
  state.token = $("auth-token").value.trim();
  storeToken(state.token);
  state.configLoaded = false;
  refresh();
}

document.addEventListener("DOMContentLoaded", () => {
  startStarfield();
  initReviewer();
  loadToken();
  $("run-form").addEventListener("submit", submitRun);
  $("reviews").addEventListener("click", onReviewClick);
  $("runs").addEventListener("click", onRunsClick);
  $("batch-form").addEventListener("submit", submitBatch);
  $("batches").addEventListener("click", onBatchClick);
  $("jobs").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-capcut]");
    if (button && !button.disabled) exportCapcut(button);
  });
  $("auth-form").addEventListener("submit", submitAuth);
  window.addEventListener("hashchange", () => {
    if (!location.hash.includes("token=")) return;
    loadToken();
    state.configLoaded = false;
    refresh();
  });
  document.addEventListener("visibilitychange", () => { if (!document.hidden && $("auth").hidden) refresh(); });
  setInterval(tickCountdown, 1000);
  if (state.token) refresh();
  else showAuth(false);
});
