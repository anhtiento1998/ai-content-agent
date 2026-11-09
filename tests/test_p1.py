"""P1: Vietnamese text normalisation, word-level captions, alignment, variation, similarity,
provenance / music licences, checkpoints and durable batch production."""

import json
import random
import threading
import unicodedata

import pytest
from fakes import STORYBOARD, FakePublisher, FakeStudio, FakeText
from fastapi.testclient import TestClient

from ai_content_agent.config import Config
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.batch import (
    ACTIVE, DONE, FAILED, PAUSED, QUEUED, REVIEW, RUNNING, BatchRunner, BatchStore, parse_manifest,
)
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers.local_provider import CardImageProvider, SilentVoiceProvider
from ai_content_agent.studio import StudioSettings, VideoStudio
from ai_content_agent.studio.align import Alignment, align_tokens
from ai_content_agent.studio.captions import build_ass, estimate_word_times, group_into_captions
from ai_content_agent.studio.provenance import MusicLibrary, metadata_tags, publish_blocker
from ai_content_agent.studio.studio import Checkpoint
from ai_content_agent.studio.variation import VariationPlan, Variator, most_similar, similarity
from ai_content_agent.studio.vi_text import nfc, read_integer, spoken, spoken_words
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import BatchWorker, JobManager

TOKEN = "t"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


# ---------- Vietnamese text ----------


@pytest.mark.parametrize("number, words", [
    (5, "năm"), (10, "mười"), (15, "mười lăm"), (21, "hai mươi mốt"), (24, "hai mươi tư"), (25, "hai mươi lăm"),
    (105, "một trăm lẻ năm"), (110, "một trăm mười"), (1005, "một nghìn không trăm lẻ năm"),
    (2026, "hai nghìn không trăm hai mươi sáu"), (1_000_000, "một triệu"),
    (1_250_000_000, "một tỷ hai trăm năm mươi triệu"),
])
def test_read_integer(number, words):
    assert read_integer(number) == words


@pytest.mark.parametrize("text, expected", [
    ("Để điều hòa ở 26°C.", "Để điều hòa ở hai mươi sáu độ C."),
    ("Giá 50.000đ, giảm 15%!", "Giá năm mươi nghìn đồng, giảm mười lăm phần trăm!"),
    ("Ngày 5/11/2026 lúc 9h30", "Ngày năm tháng mười một năm hai nghìn không trăm hai mươi sáu lúc chín giờ ba mươi"),
    ("Chạy 5 km", "Chạy năm ki-lô-mét"),
    ("Top 3–5 mẹo", "Top ba đến năm mẹo"),
    ("thứ 4", "thứ tư"),
    ("Pin 3,5 kWh", "Pin ba phẩy năm ki-lô-oát giờ"),
    ("chỉ 50k thôi", "chỉ năm mươi nghìn đồng thôi"),
    ("tỷ lệ 1/2 người", "tỷ lệ 1/2 người"),  # not a date: left for the TTS
])
def test_spoken_vietnamese(text, expected):
    assert spoken(text) == expected


def test_nfc_and_one_to_one_spoken_words():
    decomposed = unicodedata.normalize("NFD", "Tiết kiệm 26°C")
    assert decomposed != "Tiết kiệm 26°C" and nfc(decomposed) == "Tiết kiệm 26°C"
    words = nfc(decomposed).split()
    assert spoken_words(words) == ["Tiết", "kiệm", "hai mươi sáu độ C"]
    assert spoken_words(["26"], "en") == ["26"]


# ---------- captions ----------


def test_word_times_follow_spoken_length_and_pauses():
    words = ["Nhiệt", "độ", "2026,", "ok"]
    timed = estimate_word_times(words, spoken_words(words), 10.0, 6.0)
    assert timed[0].start == 10.0 and timed[-1].end == 16.0
    durations = [w.end - w.start for w in timed]
    assert durations[2] > 5 * durations[1]  # seven syllables plus a comma pause
    assert all(a.end == pytest.approx(b.start) for a, b in zip(timed, timed[1:]))


def test_karaoke_ass_fills_each_word_and_keeps_the_ai_label():
    words = "Xin chào các bạn".split()
    captions = group_into_captions(["Xin chào", "các bạn"], estimate_word_times(words, words, 0.0, 2.0))
    ass = build_ass(captions, [], font="Be Vietnam Pro", label="Video có sử dụng AI", duration=2.0)
    assert "{\\kf50}Xin {\\kf50}chào" in ass
    assert "Dialogue: 2,0:00:00.00,0:00:02.00,Label,,0,0,0,,Video có sử dụng AI" in ass
    assert "Style: Caption,Be Vietnam Pro,70,&H0000E5FF,&H00FFFFFF" in ass  # fills white -> yellow
    phrase = build_ass(captions, [], style="phrase")
    assert "\\kf" not in phrase and "Label" not in phrase.split("[Events]")[1]
    with pytest.raises(ValueError, match="CAPTION_STYLE"):
        build_ass(captions, [], style="bounce")


def test_align_tokens_matches_and_interpolates():
    expected = ["xin", "chào", "các", "bạn"]
    heard = [("Xin", 0.0, 0.3), ("chào", 0.3, 0.6), ("cái", 0.6, 0.8), ("bạn", 1.0, 1.4)]
    result = align_tokens(expected, heard)
    assert result.score == 0.75
    assert result.times[0] == (0.0, 0.3) and result.times[3] == (1.0, 1.4)
    assert result.times[2] == (0.6, 1.0)  # "các" was misheard: placed between its neighbours
    assert align_tokens(expected, [("hello", 0, 1)]).times is None


class FakeAligner:
    name = "fake"

    def __init__(self, score=0.9):
        self.calls, self.score = [], score

    def align(self, wav_path, spoken_text):
        tokens = spoken_text.split()
        self.calls.append(spoken_text)
        return Alignment([(i * 0.1, i * 0.1 + 0.1) for i in range(len(tokens))], self.score)


def _studio(tmp_path, writer=None, *, aligner=None, music_dir=None, require_license=True, visuals=None):
    settings = StudioSettings(output_dir=str(tmp_path / "out"), music_dir=music_dir,
                              require_music_license=require_license, ai_label="Video có sử dụng AI")
    return VideoStudio(writer or FakeText(), visuals or CardImageProvider(), SilentVoiceProvider(), settings,
                       aligner=aligner)


def test_studio_uses_aligner_times_and_records_pronunciation(tmp_path):
    aligner = FakeAligner(score=0.5)
    _, video = _studio(tmp_path, aligner=aligner).produce("x")

    assert "hai mươi sáu" in " ".join(aligner.calls)  # aligned against what the TTS was asked to say
    provenance = json.loads((tmp_path / "out").glob("*/provenance.json").__next__().read_text())
    assert provenance["pronunciation"]["min"] == 0.5
    assert video.raw["provenance"]["disclosure"] == "Video có sử dụng AI"
    ass = next((tmp_path / "out").glob("*/subtitles.ass")).read_text()
    assert "{\\kf10}" in ass and "Label" in ass


# ---------- variation & similarity ----------


def test_variator_rotates_away_from_recent_choices():
    variator = Variator(hooks=["question", "shock", "list"], visual_styles=["3d", "anime"], voices=["Kore", "Puck"],
                        rng=random.Random(1))
    recent = [{"hook": "question", "visual_style": "3d", "voice": "Kore", "music": "a.mp3"},
              {"hook": "shock", "visual_style": "anime", "voice": "Puck", "music": "b.mp3"}]
    plan = variator.plan(recent, ["a.mp3", "b.mp3", "c.mp3"])
    assert (plan.hook, plan.music) == ("list", "c.mp3")
    assert plan.visual_style == "anime" and plan.voice == "Puck"  # least recent of the two
    assert plan.visual_suffix and plan.hook_instruction


def test_similarity_scores():
    text = "Để điều hòa ở hai mươi sáu độ và bật thêm quạt để tiết kiệm điện"
    assert similarity(text, text) == 1.0
    assert similarity(text, "Cách chọn dưa hấu ngọt nước ngay tại chợ") == 0.0
    assert most_similar(text, [(1, "khác hẳn"), (2, text + " mỗi ngày")])[0] == 2


def test_near_copy_is_rewritten_once_with_an_avoid_instruction(tmp_path):
    writer = FakeText()
    calls = []

    def review(storyboard):
        calls.append(storyboard.title)
        return "kịch bản cũ" if len(calls) == 1 else None

    _studio(tmp_path, writer).produce("x", plan=VariationPlan(hook="myth"), review=review)

    assert len(writer.prompts) == 2 and len(calls) == 1
    assert "debunk" in writer.prompts[0] and "kịch bản cũ" in writer.prompts[1]


def test_pipeline_records_variation_and_similarity(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))
    pipeline = ContentPipeline(studio, [FakePublisher("youtube")], history=history, make_thumbnails=False,
                               require_approval=True, variator=Variator(rng=random.Random(0)))

    first = pipeline.run("Một")
    second = pipeline.run("Hai")

    assert history.get_run(first.run_id).variation["hook"]
    assert history.get_run(first.run_id).variation["hook"] != history.get_run(second.run_id).variation["hook"]
    run = history.get_run(second.run_id)
    assert (run.similar_to, run.similarity) == (first.run_id, 1.0)  # FakeStudio writes the same narration
    assert studio.last_review is not None


# ---------- provenance & music licences ----------


def test_music_library_only_uses_licensed_tracks(tmp_path):
    for name in ("a.mp3", "b.mp3", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "licenses.json").write_text(json.dumps({"a.mp3": {"license": "CC0", "source": "https://x"},
                                                        "b.mp3": {"license": ""}}))
    library = MusicLibrary(str(tmp_path))
    assert library.all_tracks() == ["a.mp3", "b.mp3"] and library.usable_tracks() == ["a.mp3"]
    assert library.license_for("a.mp3")["license"] == "CC0" and library.license_for("b.mp3") is None
    assert MusicLibrary(str(tmp_path), require_license=False).usable_tracks() == ["a.mp3", "b.mp3"]
    assert library.status() == {"tracks": 2, "licensed": 1, "require_license": True}


def test_publish_blocker_and_metadata():
    unlicensed = {"music": {"file": "x.mp3"}, "engines": {"text": {"provider": "claude", "model": "m"}},
                  "disclosure": "Video có sử dụng AI", "generator": "ai-content-agent 0.1"}
    assert "licenses.json" in publish_blocker(unlicensed, require_license=True)
    assert publish_blocker(unlicensed, require_license=False) is None
    assert publish_blocker(None, require_license=True) is None
    tags = metadata_tags(unlicensed, "Tiêu đề")
    assert tags["title"] == "Tiêu đề" and "AI-generated" in tags["comment"] and "text=claude/m" in tags["comment"]


def test_unlicensed_music_blocks_publishing(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))
    youtube = FakePublisher("youtube")
    pipeline = ContentPipeline(studio, [youtube], history=history, make_thumbnails=False, require_approval=True)
    run_id = pipeline.run("Chủ đề").run_id
    with history._connect() as conn:  # a run rendered before the licence was removed
        conn.execute("UPDATE runs SET provenance_json = ? WHERE id = ?",
                     (json.dumps({"music": {"file": "song.mp3"}}), run_id))

    with pytest.raises(ValueError, match="licence"):
        pipeline.publish_run(run_id)
    assert youtube.published == []


# ---------- checkpoints ----------


class CountingCards(CardImageProvider):
    def __init__(self):
        self.calls = 0

    def generate_image(self, prompt, out_path, *, aspect_ratio="9:16"):
        self.calls += 1
        super().generate_image(prompt, out_path, aspect_ratio=aspect_ratio)


def test_checkpoint_reuses_storyboard_and_scene_files(tmp_path):
    saved = []
    checkpoint = Checkpoint(save=lambda cp: saved.append((cp.storyboard is not None, cp.work_dir)))
    writer, cards = FakeText(), CountingCards()
    studio = _studio(tmp_path, writer, visuals=cards)
    studio._settings.keep_intermediates = True
    studio.produce("x", checkpoint=checkpoint)
    assert saved[0] == (True, None) and saved[-1][1] == checkpoint.work_dir
    assert cards.calls == len(STORYBOARD["scenes"])

    resumed_writer = FakeText(fail=True)  # would raise if the storyboard were written again
    resumed = _studio(tmp_path, resumed_writer, visuals=cards)
    _, video = resumed.produce("x", checkpoint=Checkpoint(storyboard=checkpoint.storyboard,
                                                          work_dir=checkpoint.work_dir))
    assert resumed_writer.prompts == [] and cards.calls == len(STORYBOARD["scenes"])
    assert video.file_path.startswith(checkpoint.work_dir)


# ---------- batches ----------


def test_parse_manifest_formats_and_errors():
    assert [i.topic for i in parse_manifest("# ý tưởng\nMột\n\n  Hai  \n")] == ["Một", "Hai"]
    jsonl = parse_manifest('{"topic": "A", "style": "vui", "platforms": ["youtube"]}\nB')
    assert (jsonl[0].style, jsonl[0].platforms, jsonl[1].platforms) == ("vui", ["youtube"], None)
    assert [i.topic for i in parse_manifest('[{"topic": "X", "force": true}]')] == ["X"]
    with pytest.raises(ValueError, match="topic"):
        parse_manifest('[{"style": "x"}]')
    with pytest.raises(ValueError, match="line 1"):
        parse_manifest('{"topic": ')


class Transient(Exception):
    status_code = 429


@pytest.fixture
def batch_world(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    store = BatchStore(str(tmp_path / "h.db"))
    publishers = {"youtube": FakePublisher("youtube")}
    failures = {}

    class Studio(FakeStudio):
        def produce(self, topic, **kwargs):
            if topic in failures:
                raise failures[topic]
            return super().produce(topic, **kwargs)

    studio = Studio(str(tmp_path / "run" / "final.mp4"))

    def factory(platforms, publish_only=False):
        return ContentPipeline(None if publish_only else studio, [publishers[p] for p in platforms],
                               history=history, make_thumbnails=False, require_approval=True)

    return history, store, BatchRunner(store, factory, backoff_seconds=0.01), failures, factory


def test_batch_runs_every_item_and_isolates_failures(batch_world):
    history, store, runner, failures, _ = batch_world
    failures["Hỏng"] = ValueError("bad topic")
    batch_id = store.create("Lô", ["youtube"], parse_manifest("Một\nHỏng\nHai"))

    runner.run_all(batch_id)

    batch = store.get(batch_id)
    assert [i.status for i in batch.items] == [REVIEW, FAILED, REVIEW]
    assert "bad topic" in batch.items[1].error and batch.status == "finished"
    assert len(history.pending_runs()) == 2

    del failures["Hỏng"]
    assert store.retry_failed(batch_id) == 1 and store.get(batch_id).status == ACTIVE
    runner.run_all(batch_id)
    assert store.get(batch_id).counts == {REVIEW: 3}


def test_transient_errors_retry_with_backoff(batch_world):
    _, store, runner, failures, _ = batch_world
    failures["Một"] = Transient("rate limited")
    batch_id = store.create("Lô", ["youtube"], parse_manifest("Một"))

    item = store.claim_next(batch_id)
    with pytest.raises(Transient):
        runner.process(item)
    item = store.get(batch_id).items[0]
    assert (item.status, item.attempts) == (QUEUED, 1) and item.not_before

    del failures["Một"]
    runner.run_all(batch_id)  # waits out the backoff, then succeeds
    assert store.get(batch_id).items[0].status == REVIEW


def test_pause_recover_and_checkpoint_persistence(batch_world):
    _, store, runner, _, _ = batch_world
    batch_id = store.create("Lô", ["youtube"], parse_manifest("Một\nHai"))
    item = store.claim_next(batch_id)
    store.save_checkpoint(item.id, Checkpoint(storyboard={"title": "T"}, work_dir="/tmp/w"))
    store.set_status(batch_id, PAUSED)
    assert store.claim_next(batch_id) is None

    assert store.recover() == 1  # the app died while item 1 was running
    first = store.get(batch_id).items[0]
    assert first.status == QUEUED and first.checkpoint == {"storyboard": {"title": "T"}, "work_dir": "/tmp/w"}
    store.set_status(batch_id, ACTIVE)
    assert store.claim_next(batch_id).id == first.id


def test_batch_api_and_worker(batch_world):
    history, store, runner, _, factory = batch_world
    jobs = JobManager(factory, history=history, batch_runner=runner)
    client = TestClient(create_app(history=history, jobs=jobs, token=TOKEN, config_status={},
                                   pipeline_factory=factory, batches=store))
    try:
        bad = client.post("/api/batches", json={"manifest": "Một", "platforms": []}, headers=AUTH)
        assert bad.status_code == 422
        assert client.post("/api/batches", json={"manifest": '{"topic": "A", "platforms": ["myspace"]}'},
                           headers=AUTH).status_code == 422

        created = client.post("/api/batches", json={"manifest": "Một\nHai", "platforms": ["youtube"],
                                                    "name": "Tuần 46", "style": "vui"}, headers=AUTH).json()
        assert (created["name"], created["total"], created["items"][0]["style"]) == ("Tuần 46", 2, "vui")
        assert "checkpoint" not in created["items"][0]

        assert client.post(f"/api/batches/{created['id']}/pause", headers=AUTH).json()["status"] == PAUSED
        worker = BatchWorker(jobs, runner)
        assert worker.step(timeout=5) is False
        client.post(f"/api/batches/{created['id']}/resume", headers=AUTH)
        assert worker.step(timeout=5) and worker.step(timeout=5)

        [listed] = client.get("/api/batches", headers=AUTH).json()
        assert listed["counts"] == {REVIEW: 2} and listed["status"] == "finished"
        assert any(job["source"] == "batch" and job["status"] == "review" for job in jobs.list())
        assert client.post("/api/batches/99/pause", headers=AUTH).status_code == 404
    finally:
        jobs.shutdown()


def test_batch_api_is_absent_without_a_store(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    client = TestClient(create_app(history=history, jobs=JobManager(lambda *a, **k: None), token=TOKEN,
                                   config_status={}))
    assert client.get("/api/batches", headers=AUTH).status_code == 501


# ---------- wiring ----------


def test_agent_wires_p1_settings(tmp_path):
    from ai_content_agent.agent import ContentAgent

    config = Config(history_db_path=str(tmp_path / "h.db"), text_provider="gemini", google_api_key="k",
                    visual_provider="card", voice_provider="silent", voice_names="Kore, Puck",
                    visual_styles="3d,anime", similarity_threshold=50, caption_style="phrase")
    agent = ContentAgent(config)
    pipeline = agent.build_pipeline(["youtube"])
    assert pipeline._variator._voices == ["Kore", "Puck"] and pipeline._variator._styles == ["3d", "anime"]
    assert pipeline._similarity_threshold == 0.5
    settings = pipeline._studio._settings
    assert settings.caption_style == "phrase" and settings.ai_label == "Video có sử dụng AI"
    assert settings.font == "Be Vietnam Pro"
    assert ContentAgent(Config(variation=False)).build_variator() is None
    assert config.status()["music"]["require_license"] is True

    with pytest.raises(RuntimeError, match="faster-whisper"):
        ContentAgent(Config(text_provider="gemini", google_api_key="k", visual_provider="card",
                            voice_provider="silent", caption_aligner="whisper")).build_studio()


def test_cli_batch_resume_flow(tmp_path, monkeypatch, capsys):
    from ai_content_agent import cli

    manifest = tmp_path / "topics.txt"
    manifest.write_text("Một\nHai\n", encoding="utf-8")
    db = str(tmp_path / "h.db")
    monkeypatch.setenv("HISTORY_DB_PATH", db)
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "out"))
    for key, value in {"TEXT_PROVIDER": "gemini", "GOOGLE_API_KEY": "k", "VISUAL_PROVIDER": "card",
                       "VOICE_PROVIDER": "silent"}.items():
        monkeypatch.setenv(key, value)

    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))
    youtube = FakePublisher("youtube")

    def fake_pipeline(self, platforms, *, publish_only=False):
        return ContentPipeline(studio, [youtube], history=HistoryStore(db), make_thumbnails=False,
                               require_approval=True)

    monkeypatch.setattr("ai_content_agent.agent.ContentAgent.build_pipeline", fake_pipeline)
    monkeypatch.setattr("sys.argv", ["ai-content-agent", "batch", str(manifest), "--platform", "youtube"])
    cli.main()
    out = capsys.readouterr().out
    assert "2 items queued" in out and "[2/2] 'Hai': ok" in out

    monkeypatch.setattr("sys.argv", ["ai-content-agent", "batches"])
    cli.main()
    assert "review 2" in capsys.readouterr().out
