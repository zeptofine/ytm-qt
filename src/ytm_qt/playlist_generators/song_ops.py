import itertools
import random
from abc import abstractmethod
from collections.abc import Generator
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from ytm_qt import SongWidget


class InfiniteLoopType(Enum):
    NONE = 0
    MAYBE = 1
    ALWAYS = 2


class SongOperation:
    no_return = InfiniteLoopType.NONE

    @classmethod
    def key(cls):
        return cls.__name__.lower()

    @abstractmethod
    def get(self) -> Generator[SongWidget, None, None]: ...

    @abstractmethod
    def is_infinite(self) -> InfiniteLoopType:
        return self.no_return

    @abstractmethod
    def is_valid(self) -> bool:
        return False


@dataclass
class RecursiveSongOperation(SongOperation):
    songs: list[SongOperation]

    @abstractmethod
    def is_infinite(self):
        for s in self.songs:
            if (i := s.is_infinite()) != InfiniteLoopType.NONE:
                return i
        return self.no_return

    @abstractmethod
    def is_valid(self) -> bool:
        return len(self.songs) > 0 and all(s.is_valid() for s in self.songs)


@dataclass
class SinglePlay(SongOperation):
    """Plays a song."""

    song: SongWidget

    def get(self):
        yield self.song

    @abstractmethod
    def is_valid(self) -> bool:
        return True


class PlayOnce(RecursiveSongOperation):
    def get(self):
        for song in self.songs:
            yield from song.get()


@dataclass
class LoopNTimes(RecursiveSongOperation):
    songs: list[SongOperation]
    times: int

    def __post_init__(self):
        assert self.times > 0 and isinstance(self.times, int)

    def get(self):
        for _ in range(self.times):
            for song in self.songs:
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
