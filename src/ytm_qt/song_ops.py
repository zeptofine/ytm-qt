import itertools
import random
from abc import abstractmethod
from collections.abc import Generator
from dataclasses import dataclass
from typing import ClassVar

from .song_widget import SongWidget


# %%
class Song:
    song: str


class SongOperation:
    no_return: ClassVar = False

    @classmethod
    def key(cls):
        return cls.__name__.lower()

    @abstractmethod
    def get(self) -> Generator[SongWidget, None, None]:
        ...

    @abstractmethod
    def is_infinite(self) -> bool:
        return self.no_return


@dataclass
class SinglePlay(SongOperation):
    song: Song

    def get(self):
        yield self.song


@dataclass
class Play(SongOperation):
    songs: list[SongOperation]

    def get(self):
        for song in self.songs:
            yield from song.get()


@dataclass
class LoopNTimes(SongOperation):
    songs: list[SongOperation]
    times: int

    def __post_init__(self):
        assert self.times > 0 and isinstance(self.times, int)

    def get(self):
        for _ in range(self.times):
            for song in self.songs:
                yield from song.get()

    def is_infinite(self) -> bool:
        return super().is_infinite() or any(s.is_infinite() for s in self.songs)


@dataclass
class LoopWholeList(SongOperation):
    no_return = True
    songs: list[SongOperation]

    def get(self):
        while True:
            for song in self.songs:
                yield from song.get()


@dataclass
class RandomPlay(SongOperation):
    songs: list[SongOperation]

    def get(self):
        for song in sorted(self.songs, key=lambda _: random.random()):
            yield from song.get()

    def is_infinite(self) -> bool:
        return super().is_infinite() or any(s.is_infinite() for s in self.songs)


class RandomPlayForever(RandomPlay):
    no_return = True

    def get(self):
        while True:
            yield random.choice(self.songs).get()


@dataclass(frozen=True)
class SongOperations:
    operations: list[SongOperation]

    def generate(self):
        ...
