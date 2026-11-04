from .base import Publisher, PublishResult
from .facebook_publisher import FacebookPublisher
from .tiktok_publisher import TikTokPublisher
from .youtube_publisher import YouTubePublisher

PUBLISHERS = {
    "youtube": YouTubePublisher,
    "tiktok": TikTokPublisher,
    "facebook": FacebookPublisher,
}

__all__ = [
    "Publisher",
    "PublishResult",
    "YouTubePublisher",
    "TikTokPublisher",
    "FacebookPublisher",
    "PUBLISHERS",
]
