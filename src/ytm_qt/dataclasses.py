from dataclasses import dataclass
from typing import Union

from .cache_handlers import CacheItem
from .playlist_generators.song_ops import SongOperation


@dataclass(frozen=True)
class SongRequest:
    data: CacheItem


@dataclass(frozen=True)
class OperationRequest:
    data_type: type[SongOperation]
    data_config: dict
    songs: list[Union[SongRequest, "OperationRequest"]]
