from dataclasses import dataclass
from typing import Union

from .dicts import YTMSmallVideoResponse
from .playlist_generators.song_ops import SongOperation


@dataclass(frozen=True)
class SongRequest:
    data: YTMSmallVideoResponse


@dataclass(frozen=True)
class OperationRequest:
    data_type: type[SongOperation]
    data_config: dict
    songs: list[Union[SongRequest, "OperationRequest"]]
