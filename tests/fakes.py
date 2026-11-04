"""Test doubles shared by the test modules — no network, no API keys."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_content_agent.media.ffmpeg import ffmpeg_bin
from ai_content_agent.providers.base import TextGenerator, VideoGenerator, VideoResult, VoiceGenerator
from ai_content_agent.publishers.base import Publisher, PublishResult
from ai_content_agent.studio import Scene, Storyboard, StudioStageError

STORYBOARD = {
    "title": "5 mẹo tiết kiệm điện mùa hè",
    "description": "Mẹo nhỏ giúp hóa đơn tiền điện giảm hẳn.",
    "hashtags": ["#tietkiemdien", "meo hay"],
    "scenes": [
        {
            "narration": "Tiền điện tháng này lại tăng vọt? Đừng lo, có mẹo cực đơn giản.",
            "visual_prompt": "shocked person looking at an electricity bill",
            "on_screen_text": "Tiền điện tăng vọt?",
        },
        {
            "narration": "Để điều hòa ở 26 độ và bật thêm quạt.",
            "visual_prompt": "air conditioner display showing 26 degrees",
            "on_screen_text": "",
        },
    ],
}


class FakeText(TextGenerator):
    name = "fake-text"

    def __init__(self, reply=None, fail=False):
        self.prompts = []
        self._reply = reply if reply is not None else json.dumps(STORYBOARD, ensure_ascii=False)
        self._fail = fail

    def complete(self, prompt):
        self.prompts.append(prompt)
        if self._fail:
            raise RuntimeError("quota exceeded")
        return self._reply


class FailingVoice(VoiceGenerator):
    name = "failing-voice"

    def synthesize(self, text, out_path):
        raise RuntimeError("voice service down")


class TestPatternClips(VideoGenerator):
    """Writes a 1.5s 16:9 ffmpeg test pattern, so the studio has to crop and loop it."""

    name = "testsrc"
    __test__ = False

    def generate_clip(self, prompt, out_path, *, aspect_ratio="9:16"):
        subprocess.run(
            [ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=1.5:size=640x360:rate=30",
             "-pix_fmt", "yuv420p", out_path],
            check=True,
        )


class FakeStudio:
    """Stands in for VideoStudio in pipeline/dashboard tests — no rendering."""

    def __init__(self, video_path, fail_stage=None):
        self.calls = 0
        self._video_path = video_path
        self._fail_stage = fail_stage

    def produce(self, topic, *, style=""):
        self.calls += 1
        if self._fail_stage:
            raise StudioStageError(self._fail_stage, f"scene 1: RuntimeError: {self._fail_stage} broke")
        storyboard = Storyboard(
            title=f"Title for {topic}",
            description="desc",
            hashtags=["test"],
            scenes=[Scene(narration="Hello world", visual_prompt="a cat")],
        )
        return storyboard, VideoResult(file_path=self._video_path, duration_seconds=3.0)


class FakePublisher(Publisher):
    def __init__(self, name="fake", fail=False):
        self.name = name
        self.published = []
        self._fail = fail

    def publish(self, video, script):
        if self._fail:
            raise RuntimeError("boom")
        self.published.append((video, script))
        return PublishResult(
            platform=self.name,
            remote_id=str(len(self.published)),
            url=f"https://example.com/{self.name}/{len(self.published)}",
        )
