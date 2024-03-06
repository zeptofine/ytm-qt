from dataclasses import dataclass
from functools import cache
from pathlib import Path

from PySide6.QtGui import QColor, QIcon, QPixmap, Qt

ICONS_PATH = Path(__file__).parent


@cache
def get_color(color: str) -> QColor:
    return QColor(color)


@dataclass
class Icons:
    play_button: QIcon
    pause_button: QIcon
    more_horiz: QIcon
    more_vert: QIcon
    next: QIcon
    prev: QIcon
    repeat: QIcon
    repeat_bold: QIcon
    repeat_one: QIcon
    shuffle: QIcon
    shuffle_bold: QIcon
    group: QIcon
    select: QIcon
    deselect: QIcon

    @classmethod
    @cache
    def get(cls, color: str = "black"):
        col = get_color(color)

        def google(p):
            return render_icon(ICONS_PATH / "google" / p, col)

        return cls(
            play_button=google("play_arrow.svg"),
            pause_button=google("pause.svg"),
            more_horiz=google("more_horiz.svg"),
            more_vert=google("more_vert.svg"),
            next=google("last_page.svg"),
            prev=google("first_page.svg"),
            repeat=google("repeat_FILL1_wght400.svg"),
            repeat_bold=google("repeat_FILL1_wght700.svg"),
            repeat_one=google("repeat_one_FILL1_wght700.svg"),
            shuffle=google("shuffle_FILL1_wght400.svg"),
            shuffle_bold=google("shuffle_FILL1_wght700.svg"),
            group=google("group.svg"),
            select=google("select.svg"),
            deselect=google("remove_selection.svg"),
        )


def render_icon(svg: Path, col: QColor) -> QIcon:
    pixmap = QPixmap(str(svg))
    mask = pixmap.createMaskFromColor(
        get_color("black"),
        Qt.MaskMode.MaskOutColor,
    )
    pixmap.fill(col)
    pixmap.setMask(mask)
    return QIcon(pixmap)
