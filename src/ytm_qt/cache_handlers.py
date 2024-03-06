from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .dicts import SongMetaData


class AudioCache(TypedDict):
    thumbnail: Path
    audio: Path
    audio_format: str
    metadata: SongMetaData | None


class CacheItem:
    def __init__(self, parent: CacheHandler, key: str, d: AudioCache | None = None) -> None:
        self.__parent = parent
        self._key = key
        self.__dct: AudioCache = d if d is not None else {}  # type: ignore

    @property
    def key(self):
        return self._key

    def to_dict(self):
        dct = {}
        me = self.__dct
        if "audio" in me:
            dct["audio"] = str(me["audio"])
        if "thumbnail" in me:
            dct["thumbnail"] = str(me["thumbnail"])
        if "audio_format" in me:
            dct["audio_format"] = me["audio_format"]
        if "metadata" in me:
            dct["metadata"] = me["metadata"]

        return dct

    @classmethod
    def from_dict(cls, parent: CacheHandler, key: str, d: dict):
        dct = {}
        if "audio" in d:
            dct["audio"] = Path(d["audio"])
        if "thumbnail" in d:
            dct["thumbnail"] = Path(d["thumbnail"])
        if "audio_format" in d:
            dct["audio_format"] = d["audio_format"]
        if "metadata" in d:
            dct["metadata"] = d["metadata"]

        return cls(
            parent,
            key,
            AudioCache(**dct),
        )

    @property
    def thumbnail(self):
        if "thumbnail" not in self.__dct:
            self.__dct["thumbnail"] = self.__parent.new_object("thumbnail")
        return self.__dct["thumbnail"]

    @property
    def audio(self):
        if "audio" not in self.__dct:
            self.__dct["audio"] = self.__parent.new_object("audio")
        return self.__dct["audio"]

    @property
    def audio_format(self):
        return self.__dct.get("audio_format", None)

    @audio_format.setter
    def audio_format(self, v):
        self.__dct["audio_format"] = v

    @property
    def metadata(self):
        return self.__dct.get("metadata", {})

    @metadata.setter
    def metadata(self, v: SongMetaData):
        self.__dct["metadata"] = v


class CacheHandler:
    def __init__(self, pth: Path):
        self.__dct: dict[str, CacheItem] = {}
        self.pth = pth
        if not self.pth.exists():
            self.pth.mkdir(parents=True)

        self.__config_pth = self.pth / "index.json"
        self.items = [p.relative_to(self.pth) for p in self.pth.glob("*")]
        self.categories = []

    def __getitem__(self, k: str) -> CacheItem:
        if k not in self.__dct:
            self.__dct[k] = self.__new_key(k)
        return self.__dct[k]

    def __new_key(self, k: str) -> CacheItem:
        return CacheItem(self, k)

    def new_object(self, category="_uncategorized"):
        cat = self.pth / category
        if not cat.exists():
            cat.mkdir(parents=True)
        while (id_ := cat / Path(str(uuid.uuid4()))) in self.items:
            pass
        self.items.append(id_)
        return id_

    def to_dict(self):
        return {k: i.to_dict() for k, i in self.__dct.items()}

    def load(self):
        if self.__config_pth.exists():
            with self.__config_pth.open() as f:
                for k, v in json.loads(f.read()).items():
                    self.__dct.update({k: CacheItem.from_dict(self, k, v)})

    def save(self):
        with self.__config_pth.open("w") as f:
            f.write(json.dumps(self.to_dict(), indent=4))
