import random
from abc import abstractmethod
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from enum import Enum
from functools import cache
from typing import TypedDict, Union

from ytm_qt.icons import Icons


class InfiniteLoopType(Enum):
    NONE = 0
    MAYBE = 1
    ALWAYS = 2


class SongOperation[T]:
    no_return = InfiniteLoopType.NONE

    @classmethod
    def key(cls):
        return cls.__name__

    @classmethod
    def lkey(cls):
        return cls.key().lower()

    @abstractmethod
    def get(self) -> Generator[T, None, None]: ...

    @abstractmethod
    def is_infinite(self) -> InfiniteLoopType:
        return self.no_return

    @abstractmethod
    def is_valid(self) -> bool:
        return False


@dataclass
class RecursiveSongOperation[T](SongOperation[T]):
    songs: list[SongOperation[T]]

    @abstractmethod
    def is_infinite(self):
        for s in self.songs:
            if (i := s.is_infinite()) != InfiniteLoopType.NONE:
                return i
        return self.no_return

    @abstractmethod
    def is_valid(self) -> bool:
        return len(self.songs) > 0 and all(s.is_valid() for s in self.songs)

    @abstractmethod
    def get_kwargs(self) -> dict:
        return {}

    def simplify(self):
        ops = []
        for song in self.songs:
            if isinstance(song, RecursiveSongOperation):
                if not song.is_valid():
                    continue

                ops.append(song.simplify())

                if song.is_infinite() == InfiniteLoopType.ALWAYS:
                    break

            if isinstance(song, SinglePlay):
                ops.append(song)

        return self.__class__(songs=ops, **self.get_kwargs())


@dataclass
class SinglePlay[T](SongOperation[T]):
    """Plays a song."""

    song: T

    def get(self):
        yield self.song

    @abstractmethod
    def is_valid(self) -> bool:
        return True

    def key(self):
        return str(self.song)


class PlayOnce[T](RecursiveSongOperation[T]):
    def get(self):
        for song in self.songs:
            yield from song.get()


@dataclass
class LoopNTimes[T](RecursiveSongOperation[T]):
    songs: list[SongOperation[T]]
    times: int

    def __post_init__(self):
        assert self.times > 0 and isinstance(self.times, int)

    def get(self):
        for _ in range(self.times):
            for song in self.songs:
                yield from song.get()

    def get_kwargs(self):
        return {"times": self.times}


@dataclass
class Stretch(LoopNTimes):
    def get(self):
        for song in self.songs:
            for _ in range(self.times):
                yield from song.get()


class LoopWholeList(RecursiveSongOperation):
    no_return = InfiniteLoopType.ALWAYS

    def get(self):
        while True:
            for song in self.songs:
                yield from song.get()


class RandomPlay(RecursiveSongOperation):
    def get(self):
        for song in sorted(self.songs, key=lambda _: random.random()):
            yield from song.get()

    def is_infinite(self):
        for s in self.songs:
            if s.is_infinite() != InfiniteLoopType.NONE:
                return InfiniteLoopType.MAYBE
        return self.no_return


class RandomPlayForever(RandomPlay):
    no_return = InfiniteLoopType.ALWAYS

    def get(self):
        while True:
            yield random.choice(self.songs).get()


@cache
def get_mode_icons(icons: Icons):
    return {
        PlayOnce: icons.play_button,
        LoopNTimes: icons.repeat_one,
        Stretch: icons.pan_zoom,
        LoopWholeList: icons.repeat_bold,
        RandomPlay: icons.shuffle,
        RandomPlayForever: icons.shuffle_bold,
    }


SongOpJson = str


class RecursiveOperationDict(TypedDict):
    key: str
    songs: list[Union["RecursiveOperationDict", SongOpJson]]
    settings: dict


class OperationSerializer[T]:
    def __init__(self, operations: Iterable[type[RecursiveSongOperation[T]]]):
        self.operations = {op.key(): op for op in operations}

    @classmethod
    def default(cls):
        return cls(
            [
                PlayOnce,
                LoopNTimes,
                Stretch,
                LoopWholeList,
                RandomPlay,
                RandomPlayForever,
            ]
        )

    def to_dict(
        self, sop: RecursiveSongOperation[T], song_serializer: Callable[[T], SongOpJson]
    ) -> RecursiveOperationDict:
        dct: RecursiveOperationDict = {"key": sop.key(), "settings": sop.get_kwargs(), "songs": []}
        songs = []
        for song in sop.songs:
            if isinstance(song, RecursiveSongOperation):
                songs.append(self.to_dict(song, song_serializer))
            elif isinstance(song, SinglePlay):
                songs.append(song_serializer(song.song))
        dct["songs"] = songs

        return dct

    def from_dict(
        self,
        d: RecursiveOperationDict,
        song_factory: Callable[[SongOpJson], T],
    ) -> RecursiveSongOperation[T]:
        assert d["key"] in self.operations
        mode = self.operations[d["key"]]
        songs = []
        for song in d["songs"]:
            if isinstance(song, SongOpJson):
                songs.append(SinglePlay(song_factory(song)))
            else:
                songs.append(self.from_dict(song, song_factory))
        return mode(songs, **d["settings"])
