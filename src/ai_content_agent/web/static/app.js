"use strict";

const TOKEN_KEY = "ai-content-agent.token";
const REFRESH_MS = 5000;

const PLATFORM_LABELS = {
  youtube: "YouTube Shorts",
  tiktok: "TikTok",
  facebook: "Facebook Page",
};
const JOB_STATUS = {
  queued: ["Đang chờ", "info"],
  running: ["Đang chạy", "info"],
  succeeded: ["Thành công", "ok"],
  partial: ["Một phần", "warn"],
  skipped: ["Bỏ qua", "neutral"],
  failed: ["Thất bại", "bad"],
};
const STAGES = {
  setup: "Khởi tạo",
  script: "Viết script",
  video: "Tạo video",
  thumbnail: "Thumbnail",
  publish: "Đăng bài",
};

let token = null;
let configLoaded = false;
let refreshing = false;

// ---------- token ----------

function storeToken(value) {
  try { localStorage.setItem(TOKEN_KEY, value); } catch { /* storage unavailable */ }
}

function loadToken() {
  const match = location.hash.match(/token=([^&]+)/);
  if (match) {
    token = decodeURIComponent(match[1]);
    storeToken(token);
    history.replaceState(null, "", location.pathname + location.search);
    return;
  }
  try { token = localStorage.getItem(TOKEN_KEY); } catch { token = null; }
}

class AuthError extends Error {}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) throw new AuthError();
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg).join("; ")
      : body.detail;
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
  const units = [["day", 86400], ["hour", 3600], ["minute", 60]];
  for (const [unit, seconds] of units) {
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
      ? el("a", { href, target: "_blank", rel: "noopener noreferrer", text: label })
      : el("span", { class: "badge neutral", text: label, title: p.remote_id });
  }));
}

// ---------- renderers ----------

function renderConfig(cfg) {
  const chips = $("provider-chips");
  const text = cfg.text_providers[cfg.text_provider];
  const video = cfg.video_providers[cfg.video_provider];
  chips.replaceChildren(
    el("span", {
      class: `chip ${text && text.ready ? "on" : "off"}`,
      title: text && text.note,
      text: `Script: ${cfg.text_provider}`,
    }),
    el("span", {
      class: `chip ${video && video.ready ? "on" : "off"}`,
      title: video && video.note,
      text: `Video: ${cfg.video_provider}`,
    }),
  );

  const container = $("platforms");
  container.replaceChildren(...Object.entries(cfg.platforms).map(([name, info]) => {
    const input = el("input", { type: "checkbox", name: "platform", value: name, disabled: !info.ready });
    return el("label", { class: `platform${info.ready ? "" : " disabled"}` }, [
      input,
      el("span", {}, [
        el("span", { text: PLATFORM_LABELS[name] || name }),
        info.note ? el("small", { text: info.note }) : null,
      ]),
    ]);
  }));
}

function renderStats(stats) {
  $("stat-runs").textContent = stats.total_runs;
  $("stat-publishes").textContent = stats.total_publishes;
  $("stat-errors").textContent = stats.errors_last_7_days;
  $("stat-last").textContent = relativeTime(stats.last_run_at);
  $("stat-last").title = formatTime(stats.last_run_at);
  const parts = Object.entries(stats.publishes_by_platform)
    .map(([p, n]) => `${PLATFORM_LABELS[p] || p}: ${n}`);
  $("stat-platforms").textContent = parts.join(" · ");
}

function renderSchedule(schedule) {
  const box = $("schedule");
  if (!schedule.enabled) {
    box.replaceChildren(
      el("p", { class: "muted", text: "Chưa bật. Chạy dashboard kèm lịch để tự động đăng, ví dụ:" }),
      el("p", {}, el("code", {
        text: 'ai-content-agent dashboard --cron "0 9 * * *" --topic "Chủ đề 1" --platform youtube',
      })),
    );
    return;
  }
  const row = (label, value) => [el("dt", { text: label }), el("dd", { text: value })];
  box.replaceChildren(el("dl", { class: "schedule-grid" }, [
    ...row("Cron", schedule.cron),
    ...row("Lần chạy tới", `${formatTime(schedule.next_run_at)} (${relativeTime(schedule.next_run_at)})`),
    ...row("Chủ đề tiếp theo", schedule.next_topic),
    ...row("Nền tảng", schedule.platforms.map((p) => PLATFORM_LABELS[p] || p).join(", ")),
    ...row("Danh sách chủ đề", `${schedule.topics.length} chủ đề, xoay vòng`),
  ]));
}

function renderJobs(jobs) {
  const list = $("jobs");
  if (!jobs.length) {
    list.replaceChildren(el("li", { class: "muted", text: "Chưa có tiến trình nào kể từ khi dashboard khởi động." }));
    return;
  }
  list.replaceChildren(...jobs.slice(0, 8).map((job) => {
    const platforms = job.platforms.map((p) => PLATFORM_LABELS[p] || p).join(", ") || "—";
    const meta = [
      job.source === "schedule" ? "Theo lịch" : "Thủ công",
      job.dry_run ? "chạy thử" : platforms,
      formatTime(job.finished_at || job.started_at || job.created_at),
    ].join(" · ");
    return el("li", { class: "job" }, [
      el("div", { class: "job-head" }, [el("span", { class: "job-topic", text: job.topic }), badge(job.status)]),
      el("div", { class: "job-meta", text: meta }),
      job.error ? el("div", { class: "job-error", text: job.error }) : null,
      job.results.length ? el("div", { class: "job-links" }, publishLinks(job.results)) : null,
    ]);
  }));
}

function renderRuns(runs) {
  const body = $("runs");
  if (!runs.length) {
    body.replaceChildren(emptyRow(4, "Chưa có video nào."));
    return;
  }
  body.replaceChildren(...runs.map((run) => el("tr", {}, [
    el("td", { class: "nowrap", "data-label": "Thời gian", text: formatTime(run.created_at) }),
    el("td", { "data-label": "Tiêu đề", text: run.title }),
    el("td", { "data-label": "Chủ đề", text: run.topic }),
    el("td", { "data-label": "Đã đăng" }, publishLinks(run.publishes)),
  ])));
}

function renderErrors(errors) {
  const body = $("errors");
  if (!errors.length) {
    body.replaceChildren(emptyRow(5, "Không có lỗi nào."));
    return;
  }
  body.replaceChildren(...errors.map((err) => el("tr", {}, [
    el("td", { class: "nowrap", "data-label": "Thời gian", text: formatTime(err.created_at) }),
    el("td", { class: "nowrap", "data-label": "Bước", text: STAGES[err.stage] || err.stage }),
    el("td", {
      class: "nowrap",
      "data-label": "Nền tảng",
      text: err.platform ? PLATFORM_LABELS[err.platform] || err.platform : "—",
    }),
    el("td", { "data-label": "Chủ đề", text: err.topic }),
    el("td", { "data-label": "Chi tiết", text: err.message }),
  ])));
}

// ---------- flow ----------

function showAuth(failed) {
  $("app").hidden = true;
  $("auth").hidden = false;
  $("auth-error").hidden = !failed;
  $("updated-at").textContent = "Cần đăng nhập";
}

function showApp() {
  $("auth").hidden = true;
  $("app").hidden = false;
}

async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    if (!configLoaded) {
      renderConfig(await api("/api/config"));
      configLoaded = true;
    }
    const [stats, runs, errors, jobs, schedule] = await Promise.all([
      api("/api/stats"), api("/api/runs"), api("/api/errors"), api("/api/jobs"), api("/api/schedule"),
    ]);
    renderStats(stats);
    renderRuns(runs);
    renderErrors(errors);
    renderJobs(jobs);
    renderSchedule(schedule);
    showApp();
    $("updated-at").textContent = `Cập nhật lúc ${new Date().toLocaleTimeString("vi-VN")}`;
  } catch (err) {
    if (err instanceof AuthError) showAuth(Boolean(token));
    else $("updated-at").textContent = `Không tải được dữ liệu: ${err.message}`;
  } finally {
    refreshing = false;
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
  try {
    await api("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        topic,
        platforms,
        style: $("style").value.trim(),
        dry_run: dryRun,
        force: $("force").checked,
      }),
    });
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
  token = $("auth-token").value.trim();
  storeToken(token);
  configLoaded = false;
  refresh();
}

document.addEventListener("DOMContentLoaded", () => {
  loadToken();
  $("run-form").addEventListener("submit", submitRun);
  $("auth-form").addEventListener("submit", submitAuth);
  window.addEventListener("hashchange", () => {
    if (!location.hash.includes("token=")) return;
    loadToken();
    configLoaded = false;
    refresh();
  });
  if (token) refresh();
  else showAuth(false);
  setInterval(() => {
    if (!document.hidden && $("auth").hidden) refresh();
  }, REFRESH_MS);
});
