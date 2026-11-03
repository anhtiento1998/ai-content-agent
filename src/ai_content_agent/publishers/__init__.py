from .base import Publisher, PublishResult
from .meta_publisher import FacebookPublisher, InstagramPublisher
from .tiktok_publisher import TikTokPublisher
from .youtube_publisher import YouTubePublisher

PUBLISHERS = {
    "youtube": YouTubePublisher,
    "tiktok": TikTokPublisher,
    "facebook": FacebookPublisher,
    "instagram": InstagramPublisher,
}

__all__ = [
    "Publisher",
    "PublishResult",
    "YouTubePublisher",
    "TikTokPublisher",
    "FacebookPublisher",
    "InstagramPublisher",
    "PUBLISHERS",
]
