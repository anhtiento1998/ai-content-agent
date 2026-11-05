from .base import Disclosure, Publisher, PublishResult
from .facebook_publisher import FacebookPublisher
from .tiktok_publisher import TikTokPublisher, TikTokTokens
from .youtube_publisher import YouTubePublisher

PUBLISHERS = {
    "youtube": YouTubePublisher,
    "tiktok": TikTokPublisher,
    "facebook": FacebookPublisher,
}

__all__ = [
    "Disclosure",
    "Publisher",
    "PublishResult",
    "TikTokTokens",
    "YouTubePublisher",
    "TikTokPublisher",
    "FacebookPublisher",
    "PUBLISHERS",
]
