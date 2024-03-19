from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import orjson

from ytm_qt.dicts import SongMetaData, YTMSmallVideoResponse


class AudioCache(TypedDict):
    thumbnail: Path
    audio: Path
    metadata: SongMetaData | None


@dataclass
class CacheItem:
    parent: CacheHandler
    key: str
    d: AudioCache

    def to_dict(self):
        dct = {}
        me = self.d
        if "audio" in me:
            dct["audio"] = str(me["audio"])
        if "thumbnail" in me:
            dct["thumbnail"] = str(me["thumbnail"])
        if "metadata" in me:
            dct["metadata"] = me["metadata"]
        dct["key"] = self.key

        return dct

    @classmethod
    def from_dict(cls, parent: CacheHandler, key: str, d: dict):
        dct = {}
        if "audio" in d:
            dct["audio"] = Path(d["audio"])
        if "thumbnail" in d:
            dct["thumbnail"] = Path(d["thumbnail"])
        if "metadata" in d:
            dct["metadata"] = d["metadata"]

        return cls(
            parent,
            key,
            AudioCache(**dct),
        )

    @property
    def thumbnail(self):
        if "thumbnail" not in self.d:
            self.d["thumbnail"] = self.parent.new_object("thumbnail")
        return self.parent.pth / self.d["thumbnail"]

    @property
    def audio(self):
        if "audio" not in self.d:
            self.d["audio"] = self.parent.new_object("audio")
        return self.parent.pth / self.d["audio"]

    @property
    def metadata(self) -> SongMetaData | None:
        return self.d["metadata"]

    @metadata.setter
    def metadata(self, v: SongMetaData):
        self.d["metadata"] = v

    @classmethod
    def from_ytmsvr(cls, dct: YTMSmallVideoResponse, parent: CacheHandler):
        if dct["id"] in parent:
            return parent[dct["id"]]

        thumbnail = max(
            dct["thumbnails"],
            key=lambda d: (
                d.get("height"),
                d.get("width"),
                d.get("preference"),
            ),
        )
        item = cls(
            parent,
            dct["id"],
            {
                "thumbnail": parent.new_object("thumbnail"),
                "audio": parent.new_object("audio"),
                "metadata": SongMetaData(
                    {
                        "title": dct["title"],
                        "description": dct["description"],
                        "duration": dct["duration"],
                        "artist": dct["channel"],
                        "url": dct["url"],
                        "thumbnail": thumbnail,
                        "audio_format": None,
                    }
                ),
            },
        )
        parent[dct["id"]] = item

        return item


class CacheHandler:
    def __init__(self, pth: Path):
        self.__dct: dict[str, CacheItem] = {}
        self.pth = pth
        if not self.pth.exists():
            self.pth.mkdir(parents=True)

        self.__config_pth = self.pth / "index.json"
        self.items = [p.relative_to(self.pth) for p in self.pth.glob("*")]
        self.categories = []

    def __setitem__(self, k: str, v: CacheItem):
        self.__dct[k] = v

    def __call__(self, key: str, metadata: SongMetaData | None = None) -> CacheItem:
        if key not in self.__dct:
            self.__dct[key] = CacheItem(
                self,
                key,
                {"thumbnail": self.new_object("thumbnail"), "audio": self.new_object("audio"), "metadata": metadata},
            )
        return self.__dct[key]

    def __contains__(self, k: str):
        return k in self.__dct

    def __getitem__(self, k: str) -> CacheItem:
        return self.__dct[k]

    def new_object(self, category="_uncategorized"):
        while (id_ := category / Path(str(uuid.uuid4()))) in self.items:
            pass
        self.items.append(id_)
        return id_

    def generate_dict(self):
        return ((k, i.to_dict()) for k, i in self.__dct.items())

    def to_dict(self):
        return dict(self.generate_dict())

    def load(self):
        if self.__config_pth.exists():
            with self.__config_pth.open("r", encoding="utf-8") as f:
                for k, v in orjson.loads(f.read()).items():
                    self.__dct.update({k: CacheItem.from_dict(self, k, v)})

    def save(self):
        with self.__config_pth.open("wb") as f:
            f.write(orjson.dumps(self.to_dict()))
