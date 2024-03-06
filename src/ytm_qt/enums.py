from enum import Enum

from .dicts import YTMPlaylistResponse, YTMSearchResponse, YTMVideoResponse


class ResponseTypes(Enum):
    VIDEO = YTMVideoResponse
    PLAYLIST = YTMPlaylistResponse
    SEARCH = YTMSearchResponse

    @classmethod
    def from_extractor_key(cls, k: str):
        if k == "Youtube":
            return cls.VIDEO
        if k == "YoutubeTab":
            return cls.PLAYLIST
        if k == "YoutubeMusicSearchURL":
            return cls.SEARCH
        raise ValueError(f"Unknown extractor key: {k}")
