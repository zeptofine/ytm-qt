from dataclasses import dataclass
from functools import cache
from pathlib import Path

from PySide6.QtGui import QColor, QIcon, QPixmap, Qt

ICONS_PATH = Path(__file__).parent


@cache
def get_color(color: str) -> QColor:
    return QColor(color)


@dataclass(frozen=True)
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
    c_up: QIcon
    c_down: QIcon
    c_left: QIcon
    c_right: QIcon
    pan_zoom: QIcon

    @classmethod
    @cache
    def get(cls, color: str = "black"):
        col = get_color(color)

        def google(p):
            return render_icon(ICONS_PATH / "google" / p, col)

        def garrows(p):
            return google(Path("arrows") / p)

        def gplay(p):
            return google(Path("playback") / p)

        return cls(
            play_button=gplay("play_arrow.svg"),
            pause_button=gplay("pause.svg"),
            more_horiz=google("more_horiz.svg"),
            more_vert=google("more_vert.svg"),
            next=garrows("last_page.svg"),
            prev=garrows("first_page.svg"),
            repeat=gplay("repeat_FILL1_wght400.svg"),
            repeat_bold=gplay("repeat_FILL1_wght700.svg"),
            repeat_one=gplay("repeat_one_FILL1_wght700.svg"),
            shuffle=gplay("shuffle_FILL1_wght400.svg"),
            shuffle_bold=gplay("shuffle_FILL1_wght700.svg"),
            group=google("group.svg"),
            select=google("select.svg"),
            deselect=google("remove_selection.svg"),
            c_up=garrows("chevron_up.svg"),
            c_down=garrows("chevron_down.svg"),
            c_left=garrows("chevron_left.svg"),
            c_right=garrows("chevron_right.svg"),
            pan_zoom=google("pan_zoom.svg"),
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
