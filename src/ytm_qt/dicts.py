from collections.abc import Generator
from typing import TypedDict

# * These are mostly cut down from their original length! only ommiting useful information

# Youtube video extractor: Youtube
# Youtube playlist extractor: YoutubeTab
# Youtube music search: YoutubeMusicSearchURL


class YTMResponse(TypedDict):
    webpage_url: str  # url
    original_url: str
    webpage_url_basename: str
    webpage_url_domain: str
    extractor: str
    extractor_key: str


class YTMThumbnail(TypedDict):
    height: int | None
    width: int | None
    url: str
    preference: int | None


class YTMSearchEntry(TypedDict):
    id: str
    ie_key: str
    title: str | None
    url: str


class YTMSearchResponse(YTMResponse):
    title: str


class YTMVideoResponse(YTMResponse):
    id: str
    album: str
    alt_title: str
    title: str
    release_year: int
    duration: int
    channel: str
    description: str
    upload_date: str
    view_count: int
    thumbnail: str  # url
    thumbnails: list[YTMThumbnail]
    categories: list[str]


class YTMSmallVideoResponse(YTMResponse):
    channel: str
    channel_id: str
    channel_url: str  # url
    description: str | None
    duration: int
    id: str
    title: str
    url: str  # url
    view_count: int
    thumbnails: list[YTMThumbnail]


class YTMPlaylistResponse(YTMResponse):
    channel: str
    channel_id: str
    channel_url: str
    description: str
    extractor: str
    id: str
    modified_date: str
    playlist_count: int
    thumbnails: list[YTMThumbnail]
    title: str
    entries: Generator[YTMSmallVideoResponse, None, None]


class YTMDownloadRequest(TypedDict):
    asr: int
    audio_channels: int
    audio_ext: str
    container: str
    ext: str
    filename: str
    filepath: str  # <-- Important!!
    filesize: int


class YTMDownloadResponse(YTMResponse):
    channel: str
    channel_id: str
    channel_url: str  # url
    description: str | None
    duration: int
    id: str
    title: str
    fulltitle: str
    url: str  # url
    view_count: int
    thumbnails: list[YTMThumbnail]

    audio_ext: str

    requested_downloads: list[YTMDownloadRequest]  # There should only be one entry in this list


class SongMetaData(TypedDict):
    title: str | None
    description: str | None
    duration: int | None
    artist: str
    url: str
    thumbnail: YTMThumbnail
    audio_format: str | None
