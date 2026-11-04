from __future__ import annotations

import re


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w]+", "_", text.strip().lower()).strip("_")
    return slug[:max_len] or "video"
