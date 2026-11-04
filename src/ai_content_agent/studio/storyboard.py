"""Scene-by-scene storyboard: the LLM's plan for one short video."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from ai_content_agent.providers.base import ScriptResult, TextGenerator, parse_json_object

LANGUAGES = {"vi": "Vietnamese", "en": "English"}
WORDS_PER_SECOND = 2.5
MAX_SCENES = 12


@dataclass
class Scene:
    narration: str
    visual_prompt: str
    on_screen_text: str = ""


@dataclass
class Storyboard:
    title: str
    description: str
    hashtags: list[str]
    scenes: list[Scene] = field(default_factory=list)

    @property
    def narration(self) -> str:
        return " ".join(scene.narration for scene in self.scenes)

    def to_script_result(self) -> ScriptResult:
        script = f"{self.description}\n\n{self.narration}" if self.description else self.narration
        return ScriptResult(title=self.title, script=script, hashtags=self.hashtags, raw=self.to_dict())

    def to_dict(self) -> dict:
        return asdict(self)


def build_storyboard_prompt(topic: str, *, style: str = "", language: str = "vi", target_seconds: int = 40) -> str:
    lang = LANGUAGES.get(language, language)
    words = round(target_seconds * WORDS_PER_SECOND)
    max_scenes = min(MAX_SCENES, max(4, target_seconds // 5))
    return f"""You are a short-form video director. Plan a vertical 9:16 video about: {topic}
Style: {style or "engaging, fast-paced, social-media friendly"}
Target length: about {target_seconds} seconds of narration (~{words} words in total), split into 3 to {max_scenes} scenes.

Rules:
- Scene 1 is a hook that makes viewers keep watching.
- "narration": the voice-over for that scene, in {lang}, natural spoken style, no emojis, no stage directions.
- "visual_prompt": in English, a vivid description of the shot for an image/video generation model
  (subject, setting, lighting, camera angle, mood). Never ask for text, captions, logos or watermarks.
- "on_screen_text": a short overlay in {lang} of at most 6 words, or "" for none.
- "title": catchy, at most 90 characters, in {lang}. "description": 1-2 sentences in {lang}.
- "hashtags": 3 to 6 relevant tags, without the # sign.

Respond with ONLY a JSON object, no prose:
{{"title": str, "description": str, "hashtags": [str], "scenes": [{{"narration": str, "visual_prompt": str, "on_screen_text": str}}]}}"""


def _text(value, field_name: str, *, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"storyboard field {field_name!r} must be a non-empty string")
    return value.strip()


def parse_storyboard(text: str) -> Storyboard:
    data = parse_json_object(text)
    raw_scenes = data.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ValueError("storyboard has no scenes")

    scenes = [
        Scene(
            narration=_text(raw.get("narration"), f"scenes[{i}].narration"),
            visual_prompt=_text(raw.get("visual_prompt"), f"scenes[{i}].visual_prompt"),
            on_screen_text=_text(raw.get("on_screen_text"), f"scenes[{i}].on_screen_text", required=False),
        )
        for i, raw in enumerate(raw_scenes[:MAX_SCENES])
        if isinstance(raw, dict)
    ]
    if not scenes:
        raise ValueError("storyboard scenes are not objects")

    hashtags = data.get("hashtags") or []
    if isinstance(hashtags, str):
        hashtags = re.split(r"[,\s]+", hashtags)
    return Storyboard(
        title=_text(data.get("title"), "title")[:100],
        description=_text(data.get("description"), "description", required=False),
        hashtags=[str(tag).strip().lstrip("#").replace(" ", "") for tag in hashtags if str(tag).strip("# ")],
        scenes=scenes,
    )


def write_storyboard(
    writer: TextGenerator, topic: str, *, style: str = "", language: str = "vi", target_seconds: int = 40
) -> Storyboard:
    prompt = build_storyboard_prompt(topic, style=style, language=language, target_seconds=target_seconds)
    return parse_storyboard(writer.complete(prompt))
