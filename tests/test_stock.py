"""Stock footage engines (Pexels, Pixabay): search by keywords, avoid repeats, record sources."""

import json
import subprocess
import types
from pathlib import Path

import pytest
from fakes import STORYBOARD, FakeText

from ai_content_agent.config import Config
from ai_content_agent.media.ffmpeg import ffmpeg_bin
from ai_content_agent.providers import stock_provider
from ai_content_agent.providers.local_provider import SilentVoiceProvider
from ai_content_agent.providers.stock_provider import (
    PexelsPhotoProvider, PexelsVideoProvider, PixabayVideoProvider, StockSearchError,
)
from ai_content_agent.studio import StudioSettings, VideoStudio, parse_storyboard
from ai_content_agent.studio.storyboard import build_storyboard_prompt


def _pexels_video(video_id, duration=8):
    return {"id": video_id, "duration": duration, "url": f"https://www.pexels.com/video/{video_id}/",
            "user": {"name": f"Author {video_id}"},
            "video_files": [
                {"link": f"https://cdn.example/{video_id}-4k.mp4", "width": 2160, "height": 3840},
                {"link": f"https://cdn.example/{video_id}-hd.mp4", "width": 1080, "height": 1920},
                {"link": f"https://cdn.example/{video_id}-wide.mp4", "width": 1920, "height": 1080},
            ]}


class FakeStockApi:
    """Answers search URLs from `results` (query -> payload) and serves any download."""

    def __init__(self, results, status=200, media=b"CLIP"):
        self.results, self.status, self.media = results, status, media
        self.searches, self.downloads = [], []

    def get(self, url, headers=None, params=None, timeout=None):
        if params is None:
            self.downloads.append(url)
            return types.SimpleNamespace(status_code=200, content=self.media)
        query = params.get("query", params.get("q"))
        self.searches.append((url, query, params, headers))
        payload = self.results.get(query, {})
        return types.SimpleNamespace(status_code=self.status, text="rate limited", json=lambda: payload)


def test_pexels_picks_the_full_hd_portrait_file_and_records_the_source(tmp_path, monkeypatch):
    api = FakeStockApi({"air conditioner remote": {"videos": [_pexels_video(11), _pexels_video(12, duration=2)]}})
    monkeypatch.setattr(stock_provider, "requests", api)
    provider = PexelsVideoProvider("KEY", used_file=str(tmp_path / "used.json"))

    provider.generate_clip("air conditioner remote", str(tmp_path / "scene_01_visual.mp4"))

    url, query, params, headers = api.searches[0]
    assert url.endswith("/videos/search") and headers == {"Authorization": "KEY"}
    assert params["orientation"] == "portrait"
    assert api.downloads == ["https://cdn.example/11-hd.mp4"]  # not the 4K file, not the landscape one, not the 2 s clip
    assert (tmp_path / "scene_01_visual.mp4").read_bytes() == b"CLIP"
    assert provider.sources == [{"file": "scene_01_visual.mp4", "provider": "pexels", "id": "pexels-11",
                                 "url": "https://www.pexels.com/video/11/", "author": "Author 11",
                                 "query": "air conditioner remote"}]
    assert provider.uses_keywords and json.loads((tmp_path / "used.json").read_text()) == ["pexels-11"]


def test_clips_are_not_repeated_within_or_across_videos(tmp_path, monkeypatch):
    api = FakeStockApi({"fan": {"videos": [_pexels_video(1), _pexels_video(2), _pexels_video(3)]}})
    monkeypatch.setattr(stock_provider, "requests", api)
    used = str(tmp_path / "data" / "used.json")

    first = PexelsVideoProvider("KEY", used_file=used)
    for n in range(2):
        first.generate_clip("fan", str(tmp_path / f"a{n}.mp4"))
    second = PexelsVideoProvider("KEY", used_file=used)  # the next video, a new process
    second.generate_clip("fan", str(tmp_path / "b.mp4"))
    assert len({source["id"] for source in first.sources + second.sources}) == 3

    second.generate_clip("fan", str(tmp_path / "c.mp4"))  # everything used once: reuse the oldest
    assert second.sources[-1]["id"] == first.sources[0]["id"]


def test_search_is_shortened_until_something_is_found(tmp_path, monkeypatch):
    api = FakeStockApi({"electricity bill": {"videos": [_pexels_video(5)]}})
    monkeypatch.setattr(stock_provider, "requests", api)
    provider = PexelsVideoProvider("KEY")

    provider.generate_clip("electricity bill shocked person", str(tmp_path / "v.mp4"))
    assert [query for _, query, _, _ in api.searches] == [
        "electricity bill shocked person", "electricity bill shocked", "electricity bill"]

    with pytest.raises(RuntimeError, match="no result for 'unicorn'"):
        provider.generate_clip("unicorn", str(tmp_path / "v.mp4"))


def test_api_errors_are_retryable_and_missing_key_is_explained(tmp_path, monkeypatch):
    from ai_content_agent.studio.studio import _is_transient

    monkeypatch.setattr(stock_provider, "requests", FakeStockApi({}, status=429))
    with pytest.raises(StockSearchError) as limited:
        PexelsVideoProvider("KEY").generate_clip("fan", str(tmp_path / "v.mp4"))
    assert limited.value.status_code == 429 and _is_transient(limited.value)
    with pytest.raises(ValueError, match="PEXELS_API_KEY"):
        PexelsVideoProvider(None)
    with pytest.raises(ValueError, match="PIXABAY_API_KEY"):
        PixabayVideoProvider("")


def test_pexels_photos_and_pixabay_videos(tmp_path, monkeypatch):
    photos = {"photos": [{"id": 7, "url": "https://www.pexels.com/photo/7/", "photographer": "Lan",
                          "src": {"original": "https://img.example/7.jpg", "large2x": "https://img.example/7@2x.jpg"}}]}
    api = FakeStockApi({"watermelon": photos})
    monkeypatch.setattr(stock_provider, "requests", api)
    photo = PexelsPhotoProvider("KEY")
    photo.generate_image("watermelon", str(tmp_path / "p.png"))
    assert api.searches[0][0].endswith("/v1/search") and api.downloads == ["https://img.example/7@2x.jpg"]
    assert photo.sources[0]["author"] == "Lan"

    hits = {"hits": [{"id": 9, "duration": 12, "pageURL": "https://pixabay.com/videos/9/", "user": "Minh",
                      "videos": {"large": {"url": "https://pix.example/9-large.mp4", "width": 3840, "height": 2160},
                                 "medium": {"url": "https://pix.example/9-medium.mp4", "width": 1080, "height": 1920}}}]}
    api = FakeStockApi({"sleep": hits})
    monkeypatch.setattr(stock_provider, "requests", api)
    pixabay = PixabayVideoProvider("PIXKEY")
    pixabay.generate_clip("sleep", str(tmp_path / "x.mp4"))
    assert api.searches[0][2]["key"] == "PIXKEY" and api.downloads == ["https://pix.example/9-medium.mp4"]
    assert pixabay.sources[0]["id"] == "pixabay-9"


# ---------- storyboard keywords & studio ----------


def test_storyboard_carries_keywords_for_stock_search():
    assert '"keywords"' in build_storyboard_prompt("x")
    board = dict(STORYBOARD, scenes=[dict(STORYBOARD["scenes"][0], keywords="electricity bill")])
    assert parse_storyboard(json.dumps(board)).scenes[0].keywords == "electricity bill"
    assert parse_storyboard(json.dumps(STORYBOARD)).scenes[0].keywords == ""  # older scripts still load


class TestClipStock(PexelsVideoProvider):
    """A Pexels engine whose "downloads" are real test clips, so the studio can render them."""

    __test__ = False

    def __init__(self, tmp_path):
        super().__init__("KEY")
        self.queries = []
        self._clip = tmp_path / "stock.mp4"
        subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=duration=2:size=540x960:rate=30", "-pix_fmt", "yuv420p", str(self._clip)], check=True)

    def _candidates(self, query, aspect_ratio):
        self.queries.append(query)
        return [{"id": f"pexels-{len(self.queries)}", "download": "file", "page": "https://www.pexels.com/video/1/",
                 "author": "A"}]

    def _fetch(self, query, out_path, aspect_ratio):
        chosen = self._candidates(query, aspect_ratio)[0]
        Path(out_path).write_bytes(self._clip.read_bytes())
        self.sources.append({"file": Path(out_path).name, "provider": self.name, "id": chosen["id"],
                             "url": chosen["page"], "author": chosen["author"], "query": query})


def test_studio_searches_stock_by_keywords_and_keeps_the_sources(tmp_path):
    board = dict(STORYBOARD, scenes=[dict(STORYBOARD["scenes"][0], keywords="electricity bill"),
                                     dict(STORYBOARD["scenes"][1])])  # second scene has no keywords
    stock = TestClipStock(tmp_path)
    studio = VideoStudio(FakeText(reply=json.dumps(board, ensure_ascii=False)), stock, SilentVoiceProvider(),
                         StudioSettings(output_dir=str(tmp_path / "out"), music_dir=None, font="DejaVu Sans"))
    from ai_content_agent.studio.variation import VariationPlan

    _, video = studio.produce("x", plan=VariationPlan(visual_style="anime"))

    # Keywords when present, else the first words of the image prompt; never the AI style suffix.
    assert sorted(stock.queries) == ["air conditioner display showing", "electricity bill"]
    provenance = video.raw["provenance"]
    # Scenes are fetched concurrently, so compare without relying on order.
    assert sorted(s["file"] for s in provenance["visual_sources"]) == ["scene_01_visual.mp4", "scene_02_visual.mp4"]
    assert video.raw["cost"]["by_kind"].get("video", 0) == 0 and video.raw["cost"]["complete"] is True


def test_agent_builds_stock_engines_with_a_shared_used_file(tmp_path):
    from ai_content_agent.agent import ContentAgent

    config = Config(visual_provider="pexels", pexels_api_key="KEY", text_provider="gemini", google_api_key="k",
                    voice_provider="silent", history_db_path=str(tmp_path / "data" / "history.db"))
    visuals = ContentAgent(config).build_studio()._visuals
    assert isinstance(visuals, PexelsVideoProvider)
    assert visuals._used._path == tmp_path / "data" / "stock_used.json"
    status = config.status()["visual_providers"]
    assert status["pexels"]["ready"] is True and status["pixabay"]["ready"] is False
