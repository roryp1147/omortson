import os
import sys
import math
import time
import random
import zlib
import wave
import array
import operator
import textwrap
import subprocess
import platform
import datetime
import psutil

from collections import deque

from PySide6.QtCore import (
    Qt,
    QTimer,
    QThread,
    Signal,
    QRectF,
    QPointF,
    QObject,
    QEvent,
    QSettings,
    QUrl,
    QPoint,
    QRect
)

from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QFont,
    QRadialGradient,
    QLinearGradient,
    QPainterPath,
    QImage,
    QPixmap,
    QKeySequence,
    QShortcut,
    QPolygonF,
    QTransform,
    QFontMetrics,
    QCursor
)

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QSizePolicy
)


# ============================================================
# RETRO FX: SOUND BANK, FX HUB, FRAME CLOCKS, OVERLAYS
# ============================================================

SOUND_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "sounds"
)

# name -> candidate files (all existing ones are loaded)
SOUND_FILES = {
    "startup": ["startup.wav"],
    "click": ["click1.wav", "click2.wav", "click3.wav", "click.wav"],
    "open": ["open.wav"],
    "close": ["close.wav"],
    "warning": ["warning.wav"],
    "ambient": ["ambient.wav"],
    "teletype": ["teletype1.wav", "teletype2.wav", "teletype3.wav"],
    "ping": ["radar_ping.wav"],
    "tink": ["tink1.wav", "tink2.wav", "tink3.wav"],
    "detent": ["detent.wav"],
    # ambient station noises (synthesized, quieter than the UI sounds)
    "door_open": ["door_open.wav"],
    "door_close": ["door_close.wav"],
    "steam": ["steam1.wav", "steam2.wav"],
    "cat_meow": ["cat_meow1.wav", "cat_meow2.wav"],
    "cat_purr": ["cat_purr.wav"],
    "cat_hiss": ["cat_hiss.wav"],
}

SOUND_VOLUMES = {
    "startup": 0.70,
    "click": 0.60,
    "open": 0.50,
    "close": 0.50,
    "warning": 0.65,
    "ambient": 0.12,
    "teletype": 0.20,
    "ping": 0.10,
    "tink": 0.42,
    "detent": 0.30,
    "door_open": 0.30,
    "door_close": 0.30,
    "steam": 0.26,
    "cat_meow": 0.20,
    "cat_purr": 0.34,
    "cat_hiss": 0.22,
}

# Shared "panel power" level (0 = dark, 1 = lit) used by the boot sequence
PANEL_STATE = {"power": 1.0}

# ------------------------------------------------------------
# GAUGE FACE PALETTES (one parameterized theme, cycled with P)
# ------------------------------------------------------------
# face:        radial gradient stops for the dial
# light:       backlight colour + alphas (centre, mid, edge, rim leak), Plus-blended
# vignette:    alpha of a soft dark edge (light faces only)
# arc/tick/num/title: printed scale colours;  red*: red zone
# glow:        colour + opacity of the blurred backlit-scale layer
# seg*:        lit 7-segment colour, its halo, and the ghost alpha
# glass/box*:  readout window;  inset: light lip under the window
# needle*/hub*: pointer colours (dark = unlit during boot)
# hover*:      hover lamp colour, rim + face alphas, extra scale glow

GAUGE_PALETTES = {
    "IVORY": {
        "face": ((0.0, "#e9dfc3"), (0.62, "#d9cba7"), (1.0, "#ae9e78")),
        "face_edge": "#5c5546",
        "light": (255, 214, 150), "light_alpha": (16, 8, 2, 0),
        "vignette": 95,
        "arc": "#24221c", "tick": "#1b1a15", "num": "#1d1b16", "title": "#1a1813",
        "num_bold": True,
        "red": "#b3261b", "red_wash": (190, 40, 25, 55),
        "glow": (255, 196, 120), "glow_opacity": 0.0,
        "seg": (255, 172, 64), "seg_glow": (255, 140, 30), "ghost": 30,
        "glass": ("#0e0c08", "#050504"), "box_edge": "#4b463a",
        "box_glow": (255, 170, 70), "box_glow_alpha": 0, "inset": 70,
        "needle_lit": "#16150f", "needle_dark": "#2c2a24", "needle_edge": (0, 0, 0, 160),
        "needle_tip": "#b3261b",
        "hub": ("#4a4740", "#100f0d"), "hub_edge": "#3a372f",
        "hover": (255, 196, 118), "hover_rim": 100, "hover_face": 34, "hover_glow": 0.0,
    },
    "GUNMETAL": {
        "face": ((0.0, "#30373a"), (0.65, "#1b2023"), (1.0, "#0a0c0d")),
        "face_edge": "#3c4448",
        "light": (90, 255, 150), "light_alpha": (24, 11, 4, 18),
        "vignette": 0,
        "arc": "#6c8a77", "tick": "#8db69b", "num": "#a6d4b3", "title": "#bfe6c6",
        "num_bold": False,
        "red": "#a8291f", "red_wash": (150, 20, 15, 45),
        "glow": (110, 255, 150), "glow_opacity": 0.42,
        "seg": (140, 255, 130), "seg_glow": (60, 220, 90), "ghost": 26,
        "glass": ("#060a07", "#020403"), "box_edge": "#3f4a43",
        "box_glow": (90, 230, 120), "box_glow_alpha": 22, "inset": 18,
        "needle_lit": "#e2eee0", "needle_dark": "#5c665e", "needle_edge": (30, 45, 35, 200),
        "needle_tip": None,
        "hub": ("#545d58", "#121513"), "hub_edge": "#7f8c84",
        "hover": (110, 255, 150), "hover_rim": 80, "hover_face": 20, "hover_glow": 0.35,
    },
    "STEEL BLUE": {
        "face": ((0.0, "#2b3746"), (0.65, "#18202b"), (1.0, "#090c11")),
        "face_edge": "#36475a",
        "light": (120, 210, 255), "light_alpha": (26, 12, 4, 18),
        "vignette": 0,
        "arc": "#6d879b", "tick": "#8fb1c8", "num": "#a9cce2", "title": "#c2deef",
        "num_bold": False,
        "red": "#ad2c22", "red_wash": (150, 20, 15, 45),
        "glow": (140, 220, 255), "glow_opacity": 0.45,
        "seg": (150, 230, 255), "seg_glow": (50, 170, 240), "ghost": 26,
        "glass": ("#04080c", "#020305"), "box_edge": "#3a4a5a",
        "box_glow": (110, 200, 255), "box_glow_alpha": 22, "inset": 18,
        "needle_lit": "#e2eef5", "needle_dark": "#5b6670", "needle_edge": (30, 40, 55, 200),
        "needle_tip": None,
        "hub": ("#525b66", "#111418"), "hub_edge": "#7c8a98",
        "hover": (130, 215, 255), "hover_rim": 80, "hover_face": 20, "hover_glow": 0.35,
    },
    "AMBER": {
        "face": ((0.0, "#2a2923"), (0.65, "#151512"), (1.0, "#090908")),
        "face_edge": "#34332c",
        "light": (255, 165, 70), "light_alpha": (40, 18, 6, 22),
        "vignette": 0,
        "arc": "#817c68", "tick": "#9a937a", "num": "#b3ad94", "title": "#c9c1a1",
        "num_bold": False,
        "red": "#9d241c", "red_wash": (150, 20, 15, 45),
        "glow": (255, 196, 120), "glow_opacity": 0.5,
        "seg": (255, 178, 72), "seg_glow": (255, 150, 40), "ghost": 30,
        "glass": ("#0d0b07", "#050504"), "box_edge": "#4a4a40",
        "box_glow": (255, 170, 70), "box_glow_alpha": 26, "inset": 14,
        "needle_lit": "#e6dcb8", "needle_dark": "#6f6a57", "needle_edge": (60, 55, 40, 200),
        "needle_tip": None,
        "hub": ("#5a5850", "#151412"), "hub_edge": "#8c8878",
        "hover": (255, 170, 80), "hover_rim": 85, "hover_face": 22, "hover_glow": 0.35,
    },
}

PALETTE_ORDER = ["IVORY", "GUNMETAL", "STEEL BLUE", "AMBER"]
DEFAULT_PALETTE = "IVORY"
PALETTE_STATE = {"name": DEFAULT_PALETTE}


def gauge_palette():

    return GAUGE_PALETTES.get(PALETTE_STATE["name"], GAUGE_PALETTES[DEFAULT_PALETTE])


# ------------------------------------------------------------
# TERMINAL TRANSMISSIONS (typed by the core every 3-6 min)
# ------------------------------------------------------------
# ORIGINAL_QUOTES ship with the app. A local, untracked quotes_local.py next to
# main.py (or the exe) can add more sets and pick one, e.g.:
#     QUOTE_SETS = {"mine": ["LINE ONE", "LINE TWO"]}
#     ACTIVE_QUOTES = "mine"
# It is gitignored and never bundled.

ORIGINAL_QUOTES = [
    "CORE ONLINE  //  AWAITING INQUIRY",
    "ALL DECKS NOMINAL. THE MACHINE IS LISTENING.",
    "QUERY NOT UNDERSTOOD. REPHRASE OR WAIT.",
    "NIGHT SHIFT LOG: NOTHING TO REPORT. NOTHING YET.",
    "COOLANT LOOP STABLE. FANS REPORT NO COMPLAINTS.",
    "REMINDER: THE DIALS DO NOT LIE. THE OPERATOR SOMETIMES DOES.",
    "SIGNAL RECEIVED. ORIGIN: UNKNOWN. FILED UNDER LATER.",
    "THE HUM YOU HEAR IS NORMAL. PROBABLY.",
    "STATUS: EVERYTHING IS FINE. CHECK AGAIN IN FIVE MINUTES.",
    "LONG HAUL PROTOCOL: CONSERVE POWER, CONSERVE PATIENCE.",
    "DIAGNOSTIC COMPLETE. NO GHOSTS DETECTED IN THE MACHINE.",
    "THIS TERMINAL HAS BEEN RUNNING LONGER THAN YOU HAVE BEEN AWAKE.",
    "OMORTSON REVERSED IS STILL WATCHING THE GAUGES.",
]


QUOTE_SETS = {"original": ORIGINAL_QUOTES}
ACTIVE_QUOTES = "original"


def _load_local_quotes():

    global ACTIVE_QUOTES

    try:
        base = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
        path = os.path.join(base, "quotes_local.py")
        if not os.path.isfile(path):
            return
        ns = {}
        with open(path, encoding="utf-8") as fh:
            exec(compile(fh.read(), path, "exec"), ns)
        for name, lines in dict(ns.get("QUOTE_SETS", {})).items():
            lines = [str(x) for x in lines if str(x).strip()]
            if lines:
                QUOTE_SETS[str(name)] = lines
        want = str(ns.get("ACTIVE_QUOTES", ACTIVE_QUOTES))
        if want in QUOTE_SETS:
            ACTIVE_QUOTES = want
    except Exception:
        pass


_load_local_quotes()
QUOTES = QUOTE_SETS[ACTIVE_QUOTES]


# ------------------------------------------------------------
# VIRTUAL MIXER SUPPORT (stdlib only: wave + array)
# ------------------------------------------------------------

def load_pcm(path):

    """Decode a PCM WAV into (array('h') mono samples, rate); None on failure."""

    try:

        with wave.open(path, "rb") as w:
            channels = w.getnchannels()
            width = w.getsampwidth()
            rate = w.getframerate()
            raw = w.readframes(w.getnframes())

        if width == 2:
            data = array.array("h")
            data.frombytes(raw[: len(raw) // 2 * 2])
            if sys.byteorder == "big":
                data.byteswap()
        elif width == 1:
            data = array.array("h", ((b - 128) << 8 for b in raw))
        else:
            return None

        if channels > 1:
            data = data[::channels]

        return data, rate

    except Exception:
        return None


def start_hover_fade(widget, target, seconds=0.12):

    """Fade widget.hover towards target on the shared 60 fps clock (only while fading)."""

    widget._hover_target = float(target)

    if abs(widget.hover - widget._hover_target) < 1e-6:
        return

    def step(dt, w=widget):

        try:
            if not w.isVisible():
                w.hover = w._hover_target
                return False
        except RuntimeError:
            return False

        d = dt / seconds

        if w.hover < w._hover_target:
            w.hover = min(w._hover_target, w.hover + d)
        else:
            w.hover = max(w._hover_target, w.hover - d)

        w.update()

        return w.hover != w._hover_target

    fx_hub().clock60.add((id(widget), "hover"), step)


def draw_button_body(painter, rect, radius, hover, down, edge):

    """Chunky analog push-button body: brightens on hover, sinks when pressed."""

    body = QLinearGradient(rect.topLeft(), rect.bottomLeft())

    if down:
        body.setColorAt(0.0, QColor("#0e0e0c"))
        body.setColorAt(0.5, QColor("#1a1a17"))
        body.setColorAt(1.0, QColor("#2a2925"))
    else:
        body.setColorAt(0.0, lerp_color(QColor("#4a4942"), QColor("#5f5d53"), hover))
        body.setColorAt(0.45, lerp_color(QColor("#292925"), QColor("#34342f"), hover))
        body.setColorAt(1.0, lerp_color(QColor("#141412"), QColor("#1a1a17"), hover))

    painter.setBrush(QBrush(body))
    painter.setPen(QPen(edge, 2))
    painter.drawRoundedRect(rect, radius, radius)

    if down:

        painter.save()
        clip = QPainterPath()
        clip.addRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)
        painter.setClipPath(clip)

        top = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.top() + 10))
        top.setColorAt(0.0, QColor(0, 0, 0, 175))
        top.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, QBrush(top))

        left = QLinearGradient(rect.topLeft(), QPointF(rect.left() + 7, rect.top()))
        left.setColorAt(0.0, QColor(0, 0, 0, 120))
        left.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, QBrush(left))

        painter.restore()

        painter.setPen(QPen(QColor(255, 250, 230, 20), 1))
        painter.drawLine(QPointF(rect.left() + radius, rect.bottom() - 1.5), QPointF(rect.right() - radius, rect.bottom() - 1.5))

    else:

        painter.setPen(QPen(QColor(255, 250, 230, 22 + int(28 * hover)), 1))
        painter.drawLine(QPointF(rect.left() + 6, rect.top() + 2), QPointF(rect.right() - 6, rect.top() + 2))

        if hover > 0.001:
            lamp = QRadialGradient(QPointF(rect.center().x(), rect.top()), rect.width() * 0.7)
            lamp.setColorAt(0.0, QColor(255, 238, 195, int(26 * hover)))
            lamp.setColorAt(1.0, QColor(255, 238, 195, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(lamp))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), radius, radius)


def env_flag(name):

    return os.environ.get(name, "").strip().lower() in (
        "1", "true", "yes", "on"
    )


def lerp_color(a, b, t):

    t = max(0.0, min(1.0, float(t)))

    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def soft_blur(image, factor=6):

    """Cheap blur: smooth downscale then smooth upscale (pre-render only)."""

    w = image.width()
    h = image.height()

    small = image.scaled(
        max(1, w // factor),
        max(1, h // factor),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    out = small.scaled(
        w,
        h,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    out.setDevicePixelRatio(image.devicePixelRatio())

    return out


def noise_image(w, h, seed, fmt=None):

    """Procedural noise texture from random bytes (no numpy, no assets)."""

    if fmt is None:
        fmt = QImage.Format.Format_Grayscale8

    data = random.Random(seed).randbytes(w * h)

    return QImage(data, w, h, w, fmt).copy()


def new_layer(w, h, dpr):

    image = QImage(
        max(1, int(math.ceil(w * dpr))),
        max(1, int(math.ceil(h * dpr))),
        QImage.Format.Format_ARGB32_Premultiplied
    )

    image.fill(Qt.GlobalColor.transparent)
    image.setDevicePixelRatio(dpr)

    return image


def draw_screw(painter, x, y, r, angle=None):

    """Slotted screw head."""

    grad = QRadialGradient(QPointF(x - r * 0.35, y - r * 0.35), r * 1.6)
    grad.setColorAt(0.0, QColor("#6d6a60"))
    grad.setColorAt(0.6, QColor("#34332d"))
    grad.setColorAt(1.0, QColor("#171714"))

    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(QColor(0, 0, 0, 160), 1))
    painter.drawEllipse(QPointF(x, y), r, r)

    if angle is None:
        angle = random.uniform(0, math.pi)

    dx = math.cos(angle) * r * 0.75
    dy = math.sin(angle) * r * 0.75

    painter.setPen(QPen(QColor(10, 10, 9, 220), max(1.0, r * 0.32)))
    painter.drawLine(QPointF(x - dx, y - dy), QPointF(x + dx, y + dy))


def draw_hazard_stripe(painter, rect, stripe=9.0):

    """Yellow/black diagonal warning trim (used sparingly)."""

    painter.save()
    painter.setClipRect(rect)
    painter.fillRect(rect, QColor("#c9a227"))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#151410"))

    x = rect.left() - rect.height()

    while x < rect.right() + rect.height():
        poly = QPolygonF([
            QPointF(x, rect.bottom()),
            QPointF(x + stripe, rect.bottom()),
            QPointF(x + stripe + rect.height(), rect.top()),
            QPointF(x + rect.height(), rect.top()),
        ])
        painter.drawPolygon(poly)
        x += stripe * 2

    # grime
    painter.fillRect(rect, QColor(20, 18, 10, 70))
    painter.restore()


# ------------------------------------------------------------
# 7-SEGMENT DIGITS
# ------------------------------------------------------------

SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg",
    "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg",
    "-": "g", " ": "",
}


def seven_seg_polys(x, y, w, h):

    t = w * 0.2
    g = t * 0.2
    hm = y + h / 2

    def hs(x0, x1, yc):
        return QPolygonF([
            QPointF(x0, yc), QPointF(x0 + t / 2, yc - t / 2),
            QPointF(x1 - t / 2, yc - t / 2), QPointF(x1, yc),
            QPointF(x1 - t / 2, yc + t / 2), QPointF(x0 + t / 2, yc + t / 2),
        ])

    def vs(xc, y0, y1):
        return QPolygonF([
            QPointF(xc, y0), QPointF(xc + t / 2, y0 + t / 2),
            QPointF(xc + t / 2, y1 - t / 2), QPointF(xc, y1),
            QPointF(xc - t / 2, y1 - t / 2), QPointF(xc - t / 2, y0 + t / 2),
        ])

    L = x + t / 2
    R = x + w - t / 2
    T = y + t / 2
    B = y + h - t / 2

    return {
        "a": hs(L + g, R - g, T),
        "g": hs(L + g, R - g, hm),
        "d": hs(L + g, R - g, B),
        "f": vs(L, T + g, hm - g),
        "b": vs(R, T + g, hm - g),
        "e": vs(L, hm + g, B - g),
        "c": vs(R, hm + g, B - g),
    }


def draw_seven_seg(painter, x, y, dw, dh, spacing, text, color, digits=3, shear=-0.09):

    """Draw right-aligned 7-segment digits (text may contain 0-9, '-', ' ')."""

    text = str(text).rjust(digits)[-digits:]

    painter.save()

    total_w = digits * dw + (digits - 1) * spacing
    cx = x + total_w / 2
    cy = y + dh / 2

    painter.translate(cx, cy)
    painter.setTransform(QTransform().shear(shear, 0), True)
    painter.translate(-cx, -cy)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    for i, ch in enumerate(text):
        polys = seven_seg_polys(x + i * (dw + spacing), y, dw, dh)
        for name in SEGMENTS.get(ch, ""):
            painter.drawPolygon(polys[name])

    painter.restore()


# ------------------------------------------------------------
# SOUND
# ------------------------------------------------------------

class SoundBank(QObject):

    """
    Preloaded, low-latency sound effects. Every public method is
    exception-safe: missing files or a broken audio stack just mean
    silence, never a crash.
    """

    voice_started = Signal(str)

    def __init__(self, directory, parent=None):

        super().__init__(parent)

        self.voices = []           # (name, samples, rate, start, loop, volume)
        self.pcm = {}              # path -> (array('h'), rate) for the scope
        self.effect_paths = {}     # id(effect) -> path
        self.voice_count = 0

        self.directory = directory
        self.backend = None
        self.effects = {}          # name -> [QSoundEffect, ...]
        self.paths = {}            # name -> [path, ...]
        self.muted = False
        self.suspended = False
        self.master = 1.0          # MASTER VOLUME knob (0..1.25)
        self.loop_wanted = False
        self.error = None

        self._qt_loop_infinite = -2

        try:

            from PySide6.QtMultimedia import QSoundEffect

            self._QSoundEffect = QSoundEffect
            self.backend = "qt"

            try:
                self._qt_loop_infinite = int(
                    QSoundEffect.Loop.Infinite.value
                )
            except Exception:
                self._qt_loop_infinite = -2

        except Exception as exc:

            self.error = f"QtMultimedia unavailable: {exc}"

            try:
                import winsound
                self._winsound = winsound
                self.backend = "winsound"
            except Exception:
                self.backend = None

        for name, files in SOUND_FILES.items():

            for filename in files:

                path = os.path.join(directory, filename)

                if not os.path.isfile(path):
                    continue

                if name == "click" and filename == "click.wav" and self.paths.get(name):
                    continue       # click.wav is only a fallback

                self.paths.setdefault(name, []).append(path)

                if self.backend != "qt":
                    continue

                try:

                    effect = self._QSoundEffect(self)
                    effect.setSource(QUrl.fromLocalFile(path))
                    effect.setVolume(SOUND_VOLUMES.get(name, 0.6))

                    if name == "ambient":
                        effect.setLoopCount(self._qt_loop_infinite)

                    self.effects.setdefault(name, []).append(effect)
                    self.effect_paths[id(effect)] = path

                except Exception as exc:

                    self.error = f"{filename}: {exc}"

        # decoded copies for the virtual mixer (oscilloscope); silent on failure
        for paths in self.paths.values():
            for path in paths:
                data = load_pcm(path)
                if data is not None:
                    self.pcm[path] = data

    # --------------------------------------------------------
    # virtual mixer: what is playing right now (QSoundEffect hides it)

    def _start_voice(self, name, path, loop=False):

        try:

            data = self.pcm.get(path)

            if data is None:
                return

            samples, rate = data
            now = time.monotonic()

            voices = self.active_voices(now)

            if loop:
                voices = [v for v in voices if not v[4]]

            voices.append((name, samples, rate, now, loop, min(1.0, SOUND_VOLUMES.get(name, 0.6) * self.master)))

            while len(voices) > 12:
                for v in voices:
                    if not v[4]:
                        voices.remove(v)
                        break
                else:
                    break

            self.voices = voices
            self.voice_count += 1
            self.voice_started.emit(name)

        except Exception:
            pass

    def active_voices(self, now=None):

        now = time.monotonic() if now is None else now

        self.voices = [
            v for v in self.voices
            if v[4] or (now - v[3]) * v[2] < len(v[1])
        ]

        return self.voices

    def mix_window(self, cols, window=0.020, now=None):

        """
        Mixed waveform of everything playing, ending at 'now'. Returns
        per-column (first, second) sample pairs (min/max ordered by slope)
        after a rising zero-crossing trigger, or None when silent.
        """

        try:

            now = time.monotonic() if now is None else now
            voices = self.active_voices(now)

            if not voices or cols <= 0:
                return None

            rate = voices[0][2]
            W = max(cols, int(window * rate))
            N = W + W // 2
            acc = [0.0] * N

            for name, samples, srate, start, loop, vol in voices:

                n = len(samples)

                if n == 0:
                    continue

                scale = vol / 32768.0
                end = int((now - start) * srate)
                a = end - N
                d = 0

                if loop:
                    a %= n
                    seg = samples[a:a + N]
                    while len(seg) < N:
                        seg = seg + samples[: N - len(seg)]
                else:
                    if a < 0:
                        d = -a
                        a = 0
                    seg = samples[a:min(end, n)]

                if not len(seg):
                    continue

                part = [x * scale for x in seg]
                acc[d:d + len(part)] = map(operator.add, acc[d:d + len(part)], part)

            k = N - W

            for i in range(N - W - 1, 0, -1):
                if acc[i - 1] < 0.0 <= acc[i]:
                    k = i
                    break

            view = acc[k:k + W]
            span = W / cols
            pts = []

            for c in range(cols):
                i0 = int(c * span)
                chunk = view[i0:max(i0 + 1, int((c + 1) * span))]
                lo = min(chunk)
                hi = max(chunk)
                pts.append((lo, hi) if chunk[-1] >= chunk[0] else (hi, lo))

            return pts

        except Exception:
            return None

    # --------------------------------------------------------

    def set_muted(self, muted):

        self.muted = bool(muted)

        if self.muted:
            self._stop_loop_now()
            self.voices = []
        elif self.loop_wanted:
            self._start_loop_now()

    # --------------------------------------------------------

    def set_master(self, level):

        """Scale every sound (and the mixer copy the scope / VU meters see)."""

        self.master = max(0.0, min(1.25, float(level)))

        for name, effects in self.effects.items():
            vol = min(1.0, SOUND_VOLUMES.get(name, 0.6) * self.master)
            for effect in effects:
                try:
                    effect.setVolume(vol)
                except Exception:
                    pass

        self.voices = [
            (n, smp, rate, start, loop, min(1.0, SOUND_VOLUMES.get(n, 0.6) * self.master))
            for n, smp, rate, start, loop, _v in self.voices
        ]

    def play(self, name):

        if self.muted or self.suspended or self.backend is None or self.master <= 0.001:
            return

        try:

            if self.backend == "qt":

                ready = [
                    e for e in self.effects.get(name, ())
                    if e.status() == self._QSoundEffect.Status.Ready
                ]

                if not ready:
                    return

                idle = [e for e in ready if not e.isPlaying()]

                effect = random.choice(idle or ready)
                effect.play()

                self._start_voice(name, self.effect_paths.get(id(effect)))

            elif self.backend == "winsound" and name not in ("ambient", "teletype", "ping", "detent") + AMBIENT_EVENTS:

                paths = self.paths.get(name)

                if paths:

                    ws = self._winsound
                    path = random.choice(paths)

                    ws.PlaySound(
                        path,
                        ws.SND_FILENAME | ws.SND_ASYNC | ws.SND_NODEFAULT
                    )

                    self._start_voice(name, path)

        except Exception:
            pass

    # --------------------------------------------------------

    def stop(self, name):

        self.voices = [v for v in self.voices if v[0] != name]

        try:
            for effect in self.effects.get(name, ()):
                effect.stop()
        except Exception:
            pass

    # --------------------------------------------------------

    def set_loop(self, wanted):

        self.loop_wanted = bool(wanted)

        if self.loop_wanted and not self.muted and not self.suspended:
            self._start_loop_now()
        else:
            self._stop_loop_now()

    def _start_loop_now(self):

        try:
            effects = self.effects.get("ambient", ())
            for effect in effects:
                if not effect.isPlaying():
                    effect.play()
            if effects and not any(v[4] for v in self.voices):
                self._start_voice("ambient", self.effect_paths.get(id(effects[0])), loop=True)
        except Exception:
            pass

    def _stop_loop_now(self):

        self.stop("ambient")

    # --------------------------------------------------------

    def is_looping(self):

        try:
            return any(
                e.isPlaying() for e in self.effects.get("ambient", ())
            )
        except Exception:
            return False

    # --------------------------------------------------------

    def status_report(self):

        """{filename: status} without playing anything."""

        report = {}

        for name, effects in self.effects.items():

            for effect in effects:

                try:
                    filename = os.path.basename(
                        effect.source().toLocalFile()
                    )
                    report[filename] = effect.status().name
                except Exception as exc:
                    report[f"{name}?"] = f"ERR {exc}"

        return report

    # --------------------------------------------------------

    def shutdown(self):

        self.suspended = True
        self.voices = []

        try:
            for effects in self.effects.values():
                for effect in effects:
                    effect.stop()
        except Exception:
            pass


# ------------------------------------------------------------
# TIMERS THAT PAUSE WHILE THE APP IS MINIMIZED / HIDDEN
# ------------------------------------------------------------

class ManagedTimer(QTimer):

    """QTimer that stops while the hub is paused and resumes afterwards."""

    def __init__(self, parent, interval, callback, hub=None):

        super().__init__(parent)

        self.setInterval(interval)
        self.timeout.connect(callback)

        self.wanted = False
        self.hub = hub if hub is not None else fx_hub()
        self.hub.paused_changed.connect(self._on_paused)

    def run(self):

        self.wanted = True

        if not self.hub.paused and not self.isActive():
            self.start()

    def halt(self):

        self.wanted = False
        self.stop()

    def _on_paused(self, paused):

        if paused:
            self.stop()
        elif self.wanted and not self.isActive():
            self.start()


class FrameClock(QObject):

    """
    One shared timer for many animations, so every widget that moves
    in a frame is repainted in the same paint pass. It only runs while
    something is subscribed (moving), and pauses with the hub.
    """

    def __init__(self, interval, hub, parent=None):

        super().__init__(parent)

        self.subs = {}
        self.last = None
        self.timer = ManagedTimer(self, interval, self._tick, hub=hub)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)

    def add(self, key, callback):

        self.subs[key] = callback

        if not self.timer.wanted:
            self.last = time.perf_counter()
            self.timer.run()

    def remove(self, key):

        self.subs.pop(key, None)

        if not self.subs:
            self.timer.halt()

    def has(self, key):

        return key in self.subs

    def _tick(self):

        now = time.perf_counter()
        dt = min(0.05, max(0.0, now - (self.last or now)))
        self.last = now

        for key, callback in list(self.subs.items()):

            try:
                keep = callback(dt)
            except Exception:
                keep = False

            if not keep:
                self.subs.pop(key, None)

        if not self.subs:
            self.timer.halt()


class FXHub(QObject):

    """
    Shared FX state: CRT on/off, randomized subtle flicker, pause state,
    frame clocks, sound bank and terminal. Flicker comes in short bursts
    (2-4 frames at ~11-15 Hz) separated by calm 2.5-7 s periods and only
    nudges overlay opacity, never a bright flash.
    """

    opacity_changed = Signal(float)
    enabled_changed = Signal(bool)
    paused_changed = Signal(bool)
    intensity_changed = Signal(float)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.enabled = True
        self.opacity = 1.0
        self.intensity = 1.0       # CRT INTENSITY knob (0..1.5)
        self.sounds = None
        self.terminal = None
        self.paused = False
        self.burst_left = 0

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._tick)

        self.clock60 = FrameClock(16, self, self)
        self.clock10 = FrameClock(100, self, self)

        self._schedule_idle()

    # --------------------------------------------------------

    def set_paused(self, paused):

        paused = bool(paused)

        if paused == self.paused:
            return

        self.paused = paused

        if paused:
            self.timer.stop()
        elif self.enabled:
            self._schedule_idle()

        self.paused_changed.emit(paused)

    # --------------------------------------------------------

    def set_enabled(self, enabled):

        self.enabled = bool(enabled)

        self.burst_left = 0
        self.opacity = 1.0

        if self.enabled:
            self._schedule_idle()
        else:
            self.timer.stop()

        self.enabled_changed.emit(self.enabled)

    # --------------------------------------------------------

    def set_intensity(self, value):

        value = max(0.0, min(1.5, float(value)))

        if abs(value - self.intensity) > 1e-6:
            self.intensity = value
            self.intensity_changed.emit(value)

    # --------------------------------------------------------

    def stop(self):

        self.timer.stop()

    # --------------------------------------------------------

    def _schedule_idle(self):

        if not self.paused:
            self.timer.start(random.randint(2500, 7000))

    # --------------------------------------------------------

    def _tick(self):

        if not self.enabled or self.paused:
            return

        if self.burst_left <= 0:
            self.burst_left = random.randint(3, 5)

        self.burst_left -= 1

        if self.burst_left <= 0:

            self.opacity = 1.0
            self.opacity_changed.emit(self.opacity)
            self._schedule_idle()

            return

        self.opacity = random.uniform(0.84, 0.97)
        self.opacity_changed.emit(self.opacity)

        self.timer.start(random.randint(66, 92))


_FX_HUB = None


def fx_hub():

    global _FX_HUB

    if _FX_HUB is None:
        _FX_HUB = FXHub(QApplication.instance())

    return _FX_HUB


def play_sound(name):

    try:
        if _FX_HUB is not None and _FX_HUB.sounds is not None:
            _FX_HUB.sounds.play(name)
    except Exception:
        pass


def terminal_post(text, kind="info"):

    try:
        if _FX_HUB is not None and _FX_HUB.terminal is not None:
            _FX_HUB.terminal.post(text, kind)
    except Exception:
        pass


# ------------------------------------------------------------
# CRT OVERLAY
# ------------------------------------------------------------

class CRTOverlay(QWidget):

    """
    Transparent, click-through overlay that sits on top of a window:
    scanlines, curved-glass vignette and a faint phosphor glow.
    The whole effect is pre-rendered into a cached pixmap that is
    rebuilt only on resize; flicker just changes paint opacity.
    """

    STRENGTH = 1.0

    def __init__(self, host):

        super().__init__(host)

        self.host = host
        self._cache = None
        self._cache_key = None
        self._opacity = 1.0

        for attribute in (
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            Qt.WidgetAttribute.WA_NoSystemBackground,
            Qt.WidgetAttribute.WA_TranslucentBackground,
        ):
            self.setAttribute(attribute, True)

        self.setAutoFillBackground(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.setGeometry(host.rect())

        host.installEventFilter(self)

        hub = fx_hub()

        hub.opacity_changed.connect(self.on_flicker)
        hub.enabled_changed.connect(self.on_enabled)
        hub.intensity_changed.connect(self.on_intensity)

        self.refresh_visibility()
        self.raise_()

    # --------------------------------------------------------

    def wants_visible(self):

        return fx_hub().enabled and fx_hub().intensity > 0.001

    def refresh_visibility(self):

        want = self.wants_visible()

        if want != self.isVisible():

            self.setVisible(want)

            if want:
                self.raise_()

    # --------------------------------------------------------

    def eventFilter(self, obj, event):

        try:

            if obj is self.host:

                kind = event.type()

                if kind == QEvent.Type.Resize:
                    self.setGeometry(self.host.rect())

                elif kind == QEvent.Type.ChildAdded:
                    self.raise_()

        except Exception:
            pass

        return False

    # --------------------------------------------------------

    def on_enabled(self, enabled):

        self._opacity = 1.0
        self.refresh_visibility()
        self.update()

    def on_intensity(self, value):

        self.refresh_visibility()
        self.update()

    # --------------------------------------------------------

    def on_flicker(self, opacity):

        if self.isVisible() and fx_hub().enabled:
            self._opacity = opacity
            self.update()

    # --------------------------------------------------------

    def resizeEvent(self, event):

        self._cache = None

        super().resizeEvent(event)

    # --------------------------------------------------------

    def build_cache(self, dpr):

        w = max(1, int(math.ceil(self.width() * dpr)))
        h = max(1, int(math.ceil(self.height() * dpr)))

        image = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)

        p = QPainter(image)

        # faint phosphor tint + soft central bloom
        p.fillRect(0, 0, w, h, QColor(110, 255, 140, 5))

        glow = QRadialGradient(QPointF(0.5, 0.5), 0.6)
        glow.setCoordinateMode(QRadialGradient.CoordinateMode.ObjectBoundingMode)
        glow.setColorAt(0.0, QColor(150, 255, 170, 13))
        glow.setColorAt(0.6, QColor(150, 255, 170, 4))
        glow.setColorAt(1.0, QColor(150, 255, 170, 0))
        p.fillRect(0, 0, w, h, QBrush(glow))

        # scanlines: one dark device-pixel row every 3 rows,
        # plus a lighter half-step row for a softer CRT look
        step = 3
        dark = QColor(0, 0, 0, 70)
        half = QColor(0, 0, 0, 22)

        for y in range(0, h, step):
            p.fillRect(0, y, w, 1, dark)
            if y + 1 < h:
                p.fillRect(0, y + 1, w, 1, half)

        # curved-glass vignette (elliptical, darkest in the corners)
        vignette = QRadialGradient(QPointF(0.5, 0.5), 0.72)
        vignette.setCoordinateMode(QRadialGradient.CoordinateMode.ObjectBoundingMode)
        vignette.setColorAt(0.00, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.55, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.78, QColor(0, 0, 0, 55))
        vignette.setColorAt(0.92, QColor(0, 0, 0, 125))
        vignette.setColorAt(1.00, QColor(0, 0, 0, 185))
        p.fillRect(0, 0, w, h, QBrush(vignette))

        # rounded "tube" edge: feathered dark rim, strongest at corners
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(Qt.BrushStyle.NoBrush)

        rim = max(6, int(min(w, h) * 0.022))
        radius = min(w, h) * 0.06

        for i in range(rim):
            alpha = int(120 * (1 - i / rim) ** 2)
            p.setPen(QPen(QColor(0, 0, 0, alpha), 1.5))
            p.drawRoundedRect(
                QRectF(i + 0.5, i + 0.5, w - 2 * i - 1, h - 2 * i - 1),
                max(1.0, radius - i),
                max(1.0, radius - i)
            )

        corner = QPainterPath()
        corner.addRect(QRectF(0, 0, w, h))
        inner = QPainterPath()
        inner.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        p.fillPath(corner.subtracted(inner), QColor(0, 0, 0, 200))

        # faint glass reflection, top-left
        sheen = QLinearGradient(QPointF(0, 0), QPointF(w * 0.45, h * 0.45))
        sheen.setColorAt(0.0, QColor(220, 255, 230, 9))
        sheen.setColorAt(1.0, QColor(220, 255, 230, 0))
        p.fillRect(0, 0, w, h, QBrush(sheen))

        p.end()

        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(dpr)

        return pixmap

    # --------------------------------------------------------

    def blit(self, painter, pixmap, r, dpr):

        painter.drawPixmap(
            QRectF(r),
            pixmap,
            QRectF(r.x() * dpr, r.y() * dpr, r.width() * dpr, r.height() * dpr)
        )

    def paint_crt(self, painter, r, dpr):

        intensity = fx_hub().intensity
        boost = round(max(0.0, intensity - 1.0), 2)
        key = (self.width(), self.height(), dpr, boost)

        if self._cache is None or self._cache_key != key:
            self._cache = self.build_cache(dpr)
            if boost > 0.0:
                # > 100 %: bake a stronger copy once, the blit cost stays the same
                src = self._cache.toImage()
                src.setDevicePixelRatio(1.0)
                out = src.copy()
                p = QPainter(out)
                p.setOpacity(min(1.0, boost))
                p.drawImage(0, 0, src)
                p.end()
                self._cache = QPixmap.fromImage(out)
                self._cache.setDevicePixelRatio(dpr)
            self._cache_key = key

        painter.setOpacity(
            max(0.0, min(1.0, self._opacity * self.STRENGTH * min(1.0, intensity)))
        )

        self.blit(painter, self._cache, r, dpr)

        painter.setOpacity(1.0)

    # --------------------------------------------------------

    def paintEvent(self, event):

        try:

            painter = QPainter(self)
            self.paint_crt(painter, event.rect(), self.devicePixelRatioF())

        except Exception:
            pass


class FXOverlay(CRTOverlay):

    """
    Main-window overlay: CRT plus boot screen, idle dimming and the
    self-destruct alarm tint/border. Hidden entirely when nothing is on.
    Alarm pulsing is smooth and slow (driven at <= 1 Hz by the monitor).
    """

    # class-level defaults so the base __init__ can query visibility
    dim = 0.0
    dim_target = 0.0
    alarm = 0.0
    boot_black = 0.0
    boot_active = False

    def __init__(self, host):

        super().__init__(host)

        self.boot_lines = []
        self._border = None
        self._border_key = None

    # --------------------------------------------------------

    def wants_visible(self):

        hub = fx_hub()

        return (
            (hub.enabled and hub.intensity > 0.001)
            or self.dim > 0.002
            or self.alarm > 0.002
            or self.boot_active
        )

    # --------------------------------------------------------

    def set_alarm(self, level):

        level = max(0.0, min(1.0, float(level)))

        if abs(level - self.alarm) < 0.004 and (level > 0) == (self.alarm > 0):
            return

        self.alarm = level
        self.refresh_visibility()
        self.update()

    # --------------------------------------------------------

    def set_dim_target(self, target):

        self.dim_target = max(0.0, min(0.5, float(target)))

        fx_hub().clock60.add((id(self), "dim"), self._dim_step)

    def _dim_step(self, dt):

        diff = self.dim_target - self.dim

        # dim in slowly (~1.6 s), restore quickly (~0.35 s)
        speed = 0.18 / (1.6 if diff > 0 else 0.35)
        step = speed * dt

        done = abs(diff) <= step

        self.dim = self.dim_target if done else self.dim + math.copysign(step, diff)

        self.refresh_visibility()
        self.update()

        return not done

    # --------------------------------------------------------

    def border_pixmap(self, dpr):

        key = (self.width(), self.height(), dpr)

        if self._border is not None and self._border_key == key:
            return self._border

        w, h = self.width(), self.height()
        image = new_layer(w, h, dpr)

        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        depth = 22

        for i in range(depth):
            alpha = int(170 * (1 - i / depth) ** 2.2)
            p.setPen(QPen(QColor(255, 40, 25, alpha), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(
                QRectF(i + 0.5, i + 0.5, w - 2 * i - 1, h - 2 * i - 1),
                18, 18
            )

        p.end()

        self._border = QPixmap.fromImage(image)
        self._border.setDevicePixelRatio(dpr)
        self._border_key = key

        return self._border

    # --------------------------------------------------------

    def draw_boot_text(self, painter):

        painter.setOpacity(min(1.0, self.boot_black * 1.4))

        font = QFont("Consolas", 12)
        font.setBold(True)
        painter.setFont(font)

        x = 48
        y = 60
        lh = 22

        for i, line in enumerate(self.boot_lines):

            color = QColor("#a6f58f") if i < 2 else QColor("#79d968")

            if line.endswith("UNAVAILABLE") or "NO SIGNAL" in line:
                color = QColor("#ffb040")

            glow = QColor(color)
            glow.setAlpha(60)

            painter.setPen(glow)

            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                painter.drawText(x + ox, y + oy + i * lh, line)

            painter.setPen(color)
            painter.drawText(x, y + i * lh, line)

        # block cursor after the last line
        if int(time.monotonic() * 2.5) % 2 == 0:
            painter.fillRect(
                QRectF(x, y + len(self.boot_lines) * lh - 15, 11, 18),
                QColor("#79d968")
            )

        painter.setOpacity(1.0)

    # --------------------------------------------------------

    def paintEvent(self, event):

        try:

            painter = QPainter(self)
            r = event.rect()
            dpr = self.devicePixelRatioF()

            if self.boot_black > 0.001:

                painter.fillRect(
                    r,
                    QColor(0, 0, 0, int(255 * min(1.0, self.boot_black)))
                )

                if self.boot_lines:
                    self.draw_boot_text(painter)

            if self._grabbing:
                return          # glitch snapshot of the console: no overlay in it

            if self.glitch is not None:
                self.paint_glitch_under(painter, r)

            if fx_hub().enabled and fx_hub().intensity > 0.001:
                self.paint_crt(painter, r, dpr)

                if self.glitch is not None:
                    self.paint_glitch(painter, r)

            if self.alarm > 0.001:

                painter.fillRect(
                    r,
                    QColor(255, 30, 15, int(46 * self.alarm))
                )

                painter.setOpacity(self.alarm)
                self.blit(painter, self.border_pixmap(dpr), r, dpr)
                painter.setOpacity(1.0)

            if self.dim > 0.001:

                painter.fillRect(
                    r,
                    QColor(0, 0, 0, int(255 * self.dim))
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # CRT degradation glitches: rare (one every 1-3 min), short
    # (<= 300 ms), dark-leaning and low-alpha: no bright flashes, no
    # strobing. Only the band's own rows are repainted.

    GLITCH_MIN = 60.0
    GLITCH_MAX = 180.0
    GLITCH_DURATION = {"roll": 0.30, "jitter": 0.22, "fringe": 0.18}
    glitch = None
    glitch_count = 0

    def setup_glitches(self):

        self.glitch = None
        self.glitch_count = 0
        self.glitch_timer = ManagedTimer(self, 120000, self._glitch_due)
        self.glitch_timer.setSingleShot(True)
        self.schedule_glitch()

    def schedule_glitch(self):

        self.glitch_timer.halt()
        self.glitch_timer.setInterval(int(random.uniform(self.GLITCH_MIN, self.GLITCH_MAX) * 1000))
        self.glitch_timer.run()

    def glitch_allowed(self):

        hub = fx_hub()

        return (
            hub.enabled
            and hub.intensity > 0.001
            and not hub.paused
            and not self.boot_active
            and not getattr(self.host, "asleep", False)
            and self.isVisible()
        )

    def _glitch_due(self):

        self.schedule_glitch()

        if self.glitch_allowed():
            self.trigger_glitch()

    def trigger_glitch(self, kind=None):

        if not self.glitch_allowed():
            return False

        self.cancel_glitch()

        kind = kind or random.choice(("roll", "jitter", "fringe"))
        w, h = max(1, self.width()), max(1, self.height())

        g = {"kind": kind, "t": 0.0, "t0": time.monotonic(), "dur": self.GLITCH_DURATION[kind], "rect": QRect()}

        if kind == "roll":
            g["band"] = random.randint(int(h * 0.07), int(h * 0.12))
            g["y0"] = random.uniform(-0.05, 0.6) * h
            g["travel"] = h * random.uniform(0.10, 0.18)
        elif kind == "jitter":
            g["band"] = random.randint(22, 48)
            g["y0"] = random.uniform(0.08, 0.85) * h
        else:
            g["band"] = int(h * random.uniform(0.18, 0.32))
            g["y0"] = random.uniform(0.05, 0.6) * h

        self.glitch = g
        self.glitch_count += 1

        g["rect"] = self._glitch_band(g)

        if kind in ("jitter", "fringe"):
            # one snapshot of the console under the band (taken once, a few ms):
            # tracking jitter shifts it sideways, the fringe offsets tinted copies
            snap = self.snapshot(g["rect"])
            if snap is not None:
                if kind == "jitter":
                    g["snap"] = snap
                else:
                    g["red"] = self.tinted(snap, QColor(255, 60, 50))
                    g["cyan"] = self.tinted(snap, QColor(40, 220, 255))

        self.update(g["rect"])

        fx_hub().clock60.add((id(self), "glitch"), self._glitch_step)

        return True

    _grabbing = False

    def snapshot(self, rect):

        if rect.isEmpty():
            return None

        self._grabbing = True

        try:
            return self.host.grab(rect)
        except Exception:
            return None
        finally:
            self._grabbing = False

    @staticmethod
    def tinted(pixmap, colour):

        img = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        p.fillRect(img.rect(), colour)
        p.end()

        out = QPixmap.fromImage(img)
        out.setDevicePixelRatio(pixmap.devicePixelRatio())

        return out

    def paint_glitch_under(self, painter, r):

        """Content-moving part of a glitch, painted before the scanlines."""

        g = self.glitch

        if g is None or not g["rect"].intersects(r):
            return

        k = min(1.5, max(0.0, fx_hub().intensity))
        u = min(1.0, max(0.0, g["t"] / g["dur"]))
        env = math.sin(math.pi * u) ** 0.5
        band = g["rect"]

        if g["kind"] == "jitter" and "snap" in g:
            snap = g["snap"]
            dpr = snap.devicePixelRatio()
            rnd = random.Random(int(g["t"] * 60) * 7919 + band.top())
            slices = 3
            hs = band.height() / slices
            painter.save()
            painter.setClipRect(band)
            for j in range(slices):
                y = band.top() + j * hs
                dx = rnd.choice((-1, 1)) * rnd.uniform(3, 12) * k * env
                src = QRectF(0, j * hs * dpr, snap.width(), hs * dpr + 1)
                dst = QRectF(dx, y, band.width(), hs + 1 / dpr)
                painter.fillRect(QRectF(0, y, band.width(), hs + 1), QColor(4, 6, 5))
                painter.drawPixmap(dst, snap, src)
            painter.restore()

        elif g["kind"] == "fringe" and "red" in g:
            painter.save()
            painter.setClipRect(band)
            painter.setOpacity(0.32 * min(1.0, k) * env)
            painter.drawPixmap(QPointF(band.left() - 2, band.top()), g["red"])
            painter.drawPixmap(QPointF(band.left() + 2, band.top()), g["cyan"])
            painter.restore()

    def cancel_glitch(self):

        g = self.glitch

        if g is not None:
            self.glitch = None
            fx_hub().clock60.remove((id(self), "glitch"))
            self.update(g["rect"].adjusted(0, -2, 0, 2))

    def _glitch_band(self, g):

        w = self.width()

        if g["kind"] == "roll":
            y = g["y0"] + g["travel"] * min(1.0, g["t"] / g["dur"])
        else:
            y = g["y0"]

        return QRect(0, int(y), w, int(g["band"])).intersected(self.rect())

    def _glitch_step(self, dt):

        g = self.glitch

        if g is None:
            return False

        g["t"] = time.monotonic() - g["t0"]      # wall clock: never longer than its duration
        old = g["rect"]

        if g["t"] >= g["dur"] or not self.glitch_allowed():
            self.glitch = None
            self.update(old.adjusted(0, -2, 0, 2))
            return False

        new = self._glitch_band(g)
        g["rect"] = new
        self.update(old.united(new).adjusted(0, -2, 0, 2))

        return True

    def paint_glitch(self, painter, r):

        g = self.glitch

        if g is None or not g["rect"].intersects(r):
            return

        k = min(1.5, max(0.0, fx_hub().intensity))
        u = min(1.0, max(0.0, g["t"] / g["dur"]))
        env = math.sin(math.pi * u) ** 0.7          # soft in, soft out: never a hard edge in time
        band = QRectF(g["rect"])
        w = band.width()

        if g["kind"] == "roll":
            # a darker rolling bar with a faint lighter trailing edge, drifting down
            a = 84 * k * (0.35 + 0.65 * env)
            grad = QLinearGradient(band.topLeft(), band.bottomLeft())
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(0.35, QColor(0, 0, 0, int(a)))
            grad.setColorAt(0.80, QColor(0, 0, 0, int(a * 0.7)))
            grad.setColorAt(0.93, QColor(200, 255, 215, int(8 * k * env)))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(band, QBrush(grad))

        elif g["kind"] == "jitter":
            # tracking error: a band of scanlines torn sideways
            painter.fillRect(band, QColor(0, 0, 0, int(18 * k * env)))
            rnd = random.Random(int(g["t"] * 60) + g["band"])
            y = band.top()
            while y < band.bottom():
                dx = rnd.uniform(-16, 16)
                x = rnd.uniform(-0.1, 0.55) * w + dx
                length = rnd.uniform(0.2, 0.6) * w
                painter.fillRect(QRectF(x, y, length, 1), QColor(0, 0, 0, int(70 * k * env)))
                painter.fillRect(QRectF(x + dx, y + 1, length, 1), QColor(205, 255, 220, int(12 * k * env)))
                y += 3

        else:
            # chromatic fringe: faint red / cyan offset edges (tinted copies painted underneath)
            a = int(9 * k * env)
            for dy, colour in ((0, QColor(255, 50, 60, int(26 * k * env))), (2, QColor(40, 220, 255, int(22 * k * env)))):
                painter.fillRect(QRectF(0, band.top() + dy, w, 1), colour)
                painter.fillRect(QRectF(0, band.bottom() - 2 + dy, w, 1), colour)

    def on_enabled(self, enabled):

        self.cancel_glitch()
        super().on_enabled(enabled)

    def on_intensity(self, value):

        if value <= 0.001:
            self.cancel_glitch()
        super().on_intensity(value)



class WindowSoundFilter(QObject):

    """Plays the power-down sound when a diagnostic window closes."""

    def eventFilter(self, obj, event):

        try:
            if event.type() == QEvent.Type.Close and obj.isVisible():
                play_sound("close")
        except Exception:
            pass

        return False


def apply_dark_title_bar(window):

    """
    Windows 10/11 dark title bar via DWM (DWMWA_USE_IMMERSIVE_DARK_MODE:
    20 on 20H1+, 19 on older Windows 10 builds). Silent no-op elsewhere.
    """

    if sys.platform != "win32":
        return False

    try:

        import ctypes
        from ctypes import wintypes

        hwnd = int(window.winId())

        if not hwnd:
            return False

        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = (
            wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD
        )
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long

        value = ctypes.c_int(1)

        for attribute in (20, 19):
            result = dwm.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
            )
            if result == 0:
                window._dark_title_bar = attribute
                return True

    except Exception:
        pass

    return False


def decorate_window(window, close_sound=True, overlay_cls=None):

    """Attach the CRT overlay (and close sound) to a window."""

    apply_dark_title_bar(window)

    try:

        window._crt_overlay = (overlay_cls or CRTOverlay)(window)

        if close_sound:
            window._close_sound_filter = WindowSoundFilter(window)
            window.installEventFilter(window._close_sound_filter)

        return window._crt_overlay

    except Exception:
        return None


# ------------------------------------------------------------
# INPUT WATCHER (idle dimming, boot skip)
# ------------------------------------------------------------

class ActivityWatcher(QObject):

    def __init__(self, monitor):

        super().__init__(monitor)

        self.monitor = monitor
        self.last_input = time.monotonic()

        T = QEvent.Type

        self.input_types = {
            T.MouseMove, T.MouseButtonPress, T.MouseButtonDblClick,
            T.KeyPress, T.Wheel, T.TouchBegin,
        }

        self.press_types = {
            T.MouseButtonPress, T.MouseButtonDblClick, T.KeyPress,
        }

    def eventFilter(self, obj, event):

        try:

            kind = event.type()

            monitor = self.monitor

            if getattr(monitor, "asleep", False):

                if kind in self.input_types or kind == QEvent.Type.ShortcutOverride:

                    if monitor.sleep_input_wakes(event):
                        monitor.wake_from_deepsleep("input")
                        self.swallow_until = time.monotonic() + 0.3
                        if kind != QEvent.Type.MouseMove:
                            event.accept()
                            return True             # the waking key / click does nothing else

                    elif kind in self.press_types or kind == QEvent.Type.ShortcutOverride:
                        event.accept()
                        return True

                    return False

            if kind in self.press_types and time.monotonic() < getattr(self, "swallow_until", 0.0):
                return True

            if kind in self.input_types:

                self.last_input = time.monotonic()

                if monitor.idle_dimmed:
                    monitor.wake_from_idle()

                boot = monitor.boot

                if kind in self.press_types and boot is not None and boot.active:
                    boot.skip()
                    return True

        except Exception:
            pass

        return False


def set_panel_power(monitor, level):

    level = max(0.0, min(1.0, float(level)))

    if abs(PANEL_STATE["power"] - level) < 0.002:
        return

    PANEL_STATE["power"] = level

    try:
        for widget in monitor.info_panel.findChildren(QPushButton):
            widget.update()
        monitor.terminal.update()
        monitor.tracker.update()
    except Exception:
        pass


def panel_dim(painter, rect, radius=6):

    """Darken a panel element while the boot sequence has it powered down."""

    power = PANEL_STATE["power"]

    if power < 0.999:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, int(215 * (1 - power))))
        painter.drawRoundedRect(QRectF(rect), radius, radius)


# ------------------------------------------------------------
# BOOT SEQUENCE
# ------------------------------------------------------------

class BootSequence(QObject):

    """
    core terminal power-up: black screen, scrolling diagnostics with real
    data, gauges powering on one by one (needle sweep + backlight),
    then the panel lights up. ~4.7 s, synced to startup.wav, skippable.
    Stats keep running underneath the whole time.
    """

    DURATION = 4.7

    def __init__(self, monitor):

        super().__init__(monitor)

        self.monitor = monitor
        self.active = False
        self.events = []
        self.index = 0
        self.t0 = 0.0
        self.ready_posted = False

        self.timer = ManagedTimer(self, 33, self._tick)

    # --------------------------------------------------------

    def build_lines(self):

        m = self.monitor

        def row(label, value):
            return f"{label} ".ljust(24, ".") + f" {value}"

        try:
            total_gb = psutil.virtual_memory().total / 1024 ** 3
            mem = f"{int(round(total_gb * 1024))} MB OK  ({total_gb:.1f} GB)"
        except Exception:
            mem = "UNAVAILABLE"

        try:
            cores = f"{psutil.cpu_count(logical=False)} / {psutil.cpu_count(logical=True)}"
        except Exception:
            cores = "UNAVAILABLE"

        adlx = "ESTABLISHED" if m.performance is not None else "UNAVAILABLE"

        thermal = "1 ONLINE" if m.performance is not None else "NO SIGNAL"

        return [
            "OMORTSON CORE 6100  //  SYSTEM MONITOR",
            "UNIT 07-4412  //  DIAGNOSTIC TERMINAL",
            row("POWER BUS", "ONLINE"),
            row("MEMORY CHECK", mem),
            row("PROCESSOR", get_cpu_name().upper()[:42]),
            row("CORES / THREADS", cores),
            row("SENSOR BUS", "OK"),
            row("ADLX LINK", adlx),
            row("GRAPHICS", str(m.gpu_name).upper()[:42]),
            row("THERMAL PROBES", thermal),
            row("HOST", platform.node().upper()),
            row("OPERATOR LINK", "READY"),
        ]

    # --------------------------------------------------------

    def start(self):

        m = self.monitor
        ov = m.crt_overlay

        self.active = True
        self.ready_posted = False
        self.t0 = time.monotonic()

        if ov is not None:
            ov.boot_lines = []
            ov.boot_black = 1.0
            ov.boot_active = True
            ov.refresh_visibility()
            ov.update()

        for gauge in m.gauges():
            gauge.boot_dark()

        set_panel_power(m, 0.0)

        events = []

        for i, line in enumerate(self.build_lines()):
            events.append((0.15 + i * 0.165, "line", line))

        for i in range(4):
            events.append((2.25 + i * 0.3, "gauge", i))

        events.append((3.65, "ready", None))
        events.append((self.DURATION, "done", None))

        self.events = sorted(events, key=lambda e: e[0])
        self.index = 0

        play_sound("startup")

        self.timer.run()

    # --------------------------------------------------------

    def _tick(self):

        if not self.active:
            self.timer.halt()
            return

        m = self.monitor
        ov = m.crt_overlay
        t = time.monotonic() - self.t0
        dirty = False

        while self.index < len(self.events) and self.events[self.index][0] <= t:

            _, kind, data = self.events[self.index]
            self.index += 1

            if kind == "line" and ov is not None:
                ov.boot_lines.append(data)
                dirty = True

            elif kind == "gauge":
                m.gauges()[data].boot_power_on()

            elif kind == "ready":
                self.post_ready()

            elif kind == "done":
                self.finish()
                return

        if ov is not None:

            black = 1.0 if t < 2.05 else max(0.0, 1.0 - (t - 2.05) / 0.4)

            if abs(black - ov.boot_black) > 0.001:
                ov.boot_black = black
                dirty = True

            # cursor blink on the boot screen
            if black > 0.05 and int(t * 30) % 6 == 0:
                dirty = True

            if dirty:
                ov.update()

        if t >= 3.1:
            set_panel_power(m, min(1.0, (t - 3.1) / 0.45))

    # --------------------------------------------------------

    def post_ready(self):

        if not self.ready_posted:
            self.ready_posted = True
            terminal_post("OPERATOR LINK READY  //  AWAITING INQUIRY", "event")
            try:
                self.monitor.post_help_hint()
            except Exception:
                pass

    # --------------------------------------------------------

    def skip(self):

        if self.active:

            try:
                if self.monitor.sounds is not None:
                    self.monitor.sounds.stop("startup")
            except Exception:
                pass

            self.finish()

    # --------------------------------------------------------

    def finish(self):

        m = self.monitor
        ov = m.crt_overlay

        self.active = False
        self.timer.halt()

        if ov is not None:
            ov.boot_active = False
            ov.boot_black = 0.0
            ov.boot_lines = []
            ov.refresh_visibility()
            ov.update()

        for gauge in m.gauges():
            gauge.boot_finish()

        set_panel_power(m, 1.0)

        self.post_ready()


# ============================================================
# WINDOWS GPU MONITOR
# ============================================================

class WindowsGPUMonitor(QThread):

    usage_updated = Signal(float)

    def run(self):

        while not self.isInterruptionRequested():

            try:

                command = (
                    "(Get-Counter '\\GPU Engine(*)\\Utilization Percentage')."
                    "CounterSamples | Measure-Object -Property CookedValue "
                    "-Maximum | Select-Object -ExpandProperty Maximum"
                )

                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        command
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2
                )

                value = float(
                    result.stdout.strip()
                )

                value = max(
                    0.0,
                    min(100.0, value)
                )

                self.usage_updated.emit(value)

            except Exception:

                self.usage_updated.emit(0.0)

            self.msleep(750)


# ============================================================
# ANALOG GAUGE
# ============================================================

class AnalogGauge(QWidget):

    """
    Heavy mechanical gauge.

    * The static face (metal, bezel, backlit dial, scale, ticks, numbers,
      title, readout window with ghost segments, LED, screws) is
      pre-rendered into a pixmap, rebuilt only on resize / DPI change.
    * Per frame only the needle, hub, lit 7-segment readout (itself
      cached per value) and the optional alarm wash are drawn.
    * The needle is a spring-damper (about one visible overshoot,
      settling in ~0.8 s) driven by the shared 60 fps clock only while
      it moves; at rest a tiny random jitter runs on the 10 fps clock.
    """

    STIFFNESS = 170.0      # omega_n ~ 13 rad/s (~2 Hz swing: heavy needle)
    DAMPING = 11.7         # zeta ~ 0.45 -> ~20 % overshoot, one visible wobble
    JITTER = 0.42          # dial units

    HOVER_FADE = 0.18      # seconds for the hover lamp to fade in / out

    activated = Signal()   # double-click: open the matching diagnostic screen
    tapped = Signal()

    def __init__(
        self,
        title,
        unit="%",
        warning_start=80,
        compact=False
    ):

        super().__init__()

        self.title = title
        self.unit = unit
        self.warning_start = warning_start
        self.compact = compact

        self.value = 0.0
        self.pos = 0.0
        self.vel = 0.0
        self.jitter = 0.0
        self.hold = None            # boot sweep target override
        self.backlight = 1.0
        self._bl_target = 1.0
        self.alarm = 0.0

        self._face = None
        self._face_key = None
        self._readout = None
        self._readout_key = None
        self._hover_px = None

        self.hover = 0.0
        self._hover_target = 0.0
        self._inside = False
        self._last_tap = 0.0
        self.taps = 0
        self.tinks = 0

        self.setMouseTracking(True)

        if compact:
            self.setMinimumSize(245, 245)
        else:
            self.setMinimumSize(310, 310)

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

    # --------------------------------------------------------
    # compatibility: older code read display_value

    @property
    def display_value(self):
        return max(0.0, min(100.0, self.pos))

    # --------------------------------------------------------

    def setValue(self, value):

        self.value = max(
            0.0,
            min(100.0, float(value))
        )

        self._kick()

        key = self._readout_text()

        if key != (self._readout_key or (None,))[0]:
            self.update()

    # --------------------------------------------------------

    def target(self):

        return self.hold if self.hold is not None else self.value

    def _kick(self):

        if abs(self.target() - self.pos) > 0.02 or abs(self.vel) > 0.05:
            fx_hub().clock60.add(self, self._step)

        self._update_jitter()

    # --------------------------------------------------------

    def _step(self, dt):

        if not self.isVisible():
            return False

        target = self.target()

        n = max(1, int(math.ceil(dt / 0.004)))
        h = dt / n

        for _ in range(n):

            accel = (
                self.STIFFNESS * (target - self.pos)
                - self.DAMPING * self.vel
            )

            self.vel += accel * h
            self.pos += self.vel * h

            # mechanical end stops with a dead bounce
            if self.pos < -1.5:
                self.pos = -1.5
                self.vel = -self.vel * 0.25
            elif self.pos > 101.5:
                self.pos = 101.5
                self.vel = -self.vel * 0.25

        self.update()

        if abs(target - self.pos) < 0.12 and abs(self.vel) < 0.6:

            self.pos = target
            self.vel = 0.0
            self._update_jitter()

            return False

        return True

    # --------------------------------------------------------

    def _update_jitter(self):

        clock = fx_hub().clock10

        if self.target() > 0.5 and self.backlight >= 0.999:
            if not clock.has(self):
                clock.add(self, self._jitter_step)
        else:
            clock.remove(self)
            self.jitter = 0.0

    def _jitter_step(self, dt):

        if not self.isVisible() or self.target() <= 0.5:
            self.jitter = 0.0
            return False

        self.jitter += (
            random.uniform(-self.JITTER, self.JITTER) - self.jitter
        ) * 0.6

        self.update()

        return True

    # --------------------------------------------------------

    def showEvent(self, event):

        super().showEvent(event)

        self._kick()

    # --------------------------------------------------------
    # boot sequence hooks

    def boot_dark(self):

        self.backlight = 0.0
        self._bl_target = 0.0
        self.hold = 0.0
        self.pos = 0.0
        self.vel = 0.0
        self.jitter = 0.0

        fx_hub().clock10.remove(self)
        self.update()

    def boot_power_on(self):

        self._bl_target = 1.0
        fx_hub().clock60.add((id(self), "bl"), self._bl_step)

        self.hold = 100.0
        self._kick()

        QTimer.singleShot(650, self._release_hold)

    def _release_hold(self):

        if self.hold is not None:
            self.hold = None
            self._kick()

    def _bl_step(self, dt):

        self.backlight = min(self._bl_target, self.backlight + dt / 0.45)
        self.update()

        if self.backlight >= self._bl_target:
            self._update_jitter()
            return False

        return True

    def boot_finish(self):

        self._bl_target = 1.0
        self.backlight = 1.0
        self.hold = None
        fx_hub().clock60.remove((id(self), "bl"))
        self._kick()
        self.update()

    # --------------------------------------------------------

    def set_alarm(self, level):

        level = max(0.0, min(1.0, float(level)))

        if abs(level - self.alarm) > 0.01 or (level == 0) != (self.alarm == 0):

            self.alarm = level

            self.update()

    # --------------------------------------------------------

    def angle_for_value(self, value):

        return (
            135.0 -
            (value * 270.0 / 100.0)
        )

    def gauge_point(self, value, cx, cy, radius):

        angle = math.radians(
            self.angle_for_value(value)
        )

        return QPointF(
            cx + math.cos(angle) * radius,
            cy - math.sin(angle) * radius
        )

    def draw_arc(self, painter, cx, cy, radius, start_value, end_value, pen):

        path = QPainterPath()

        steps = 80

        for i in range(steps + 1):

            value = start_value + (end_value - start_value) * i / steps
            point = self.gauge_point(value, cx, cy, radius)

            if i == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    # --------------------------------------------------------

    def geometry_info(self):

        w = self.width()
        h = self.height()

        cx = w / 2
        cy = h / 2
        size = min(w, h)
        outer = size * 0.46
        face = outer * 0.87

        side = int(math.ceil(outer * 2 + 8))
        ox = int(round(cx - side / 2))
        oy = int(round(cy - side / 2))

        box_w = face * 0.6
        box_h = face * 0.22
        box = QRectF(cx - box_w / 2, cy + face * 0.21, box_w, box_h)

        return {
            "w": w, "h": h, "cx": cx, "cy": cy, "size": size,
            "outer": outer, "face": face, "side": side,
            "ox": ox, "oy": oy, "box": box,
        }

    def readout_layout(self, g):

        box = g["box"]

        dh = box.height() * 0.7
        dw = dh * 0.52
        sp = dw * 0.28

        unit_font = QFont("Consolas")
        unit_font.setPixelSize(max(9, int(dh * 0.62)))
        unit_font.setBold(True)

        unit_w = QFontMetrics(unit_font).horizontalAdvance(self.unit) + 2

        digits_w = 3 * dw + 2 * sp
        total = digits_w + dw * 0.3 + unit_w

        x = box.center().x() - total / 2
        y = box.center().y() - dh / 2

        unit_rect = QRectF(x + digits_w + dw * 0.3, y, unit_w, dh)

        return x, y, dw, dh, sp, unit_font, unit_rect

    # --------------------------------------------------------

    def draw_scale(self, painter, g, glow=False):

        """Arc, red zone, ticks, numbers and title (also used for the glow layer)."""

        pal = gauge_palette()

        cx, cy, size, face = g["cx"], g["cy"], g["size"], g["face"]
        arc_radius = face * 0.79

        warm = QColor(*pal["glow"])
        warm_red = QColor(255, 70, 45)
        red = QColor(pal["red"])

        self.draw_arc(
            painter, cx, cy, arc_radius, 0, 100,
            QPen(warm if glow else QColor(pal["arc"]), max(3, int(size * 0.014)))
        )

        if not glow:
            self.draw_arc(
                painter, cx, cy, arc_radius, self.warning_start, 100,
                QPen(QColor(*pal["red_wash"]), max(10, int(size * 0.035)))
            )

        self.draw_arc(
            painter, cx, cy, arc_radius, self.warning_start, 100,
            QPen(warm_red if glow else red, max(3, int(size * 0.014)))
        )

        for value in range(0, 101, 5):

            outer_point = self.gauge_point(value, cx, cy, face * 0.75)

            if value % 10 == 0:
                inner_radius = face * 0.66
                tick_width = max(2, int(size * 0.008))
            else:
                inner_radius = face * 0.70
                tick_width = max(1, int(size * 0.004))

            inner_point = self.gauge_point(value, cx, cy, inner_radius)

            if value >= self.warning_start:
                tick_color = warm_red if glow else red
            else:
                tick_color = warm if glow else QColor(pal["tick"])

            painter.setPen(QPen(tick_color, tick_width))
            painter.drawLine(outer_point, inner_point)

        num_font = QFont("Consolas", max(8, int(size * 0.038)))
        num_font.setBold(bool(pal.get("num_bold")))
        painter.setFont(num_font)

        for value in range(0, 101, 20):

            point = self.gauge_point(value, cx, cy, face * 0.57)

            rect = QRectF(
                point.x() - size * 0.045,
                point.y() - size * 0.025,
                size * 0.09,
                size * 0.05
            )

            painter.setPen(warm if glow else QColor(pal["num"]))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(value))

        painter.setFont(
            QFont("Consolas", max(9, int(size * 0.043)), QFont.Weight.Bold)
        )

        painter.setPen(warm if glow else QColor(pal["title"]))

        painter.drawText(
            QRectF(cx - size * 0.25, cy - face * 0.33, size * 0.50, size * 0.08),
            Qt.AlignmentFlag.AlignCenter,
            self.title
        )

    # --------------------------------------------------------

    def build_face(self, g, dpr):

        pal = gauge_palette()

        side = g["side"]
        cx, cy, size = g["cx"], g["cy"], g["size"]
        outer, face = g["outer"], g["face"]

        img = new_layer(side, side, dpr)

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.translate(-g["ox"], -g["oy"])

        # soft drop shadow onto the panel
        shadow = QRadialGradient(QPointF(cx + size * 0.01, cy + size * 0.02), outer * 1.02)
        shadow.setColorAt(0.85, QColor(0, 0, 0, 120))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(QPointF(cx + size * 0.01, cy + size * 0.02), outer * 1.02, outer * 1.02)

        # outer metal
        metal = QRadialGradient(QPointF(cx, cy), outer)
        metal.setColorAt(0.0, QColor("#5b5a53"))
        metal.setColorAt(0.72, QColor("#252522"))
        metal.setColorAt(1.0, QColor("#0e0e0d"))

        p.setBrush(QBrush(metal))
        p.setPen(QPen(QColor("#77756b"), 2))
        p.drawEllipse(QRectF(cx - outer, cy - outer, outer * 2, outer * 2))

        # machined ring highlight (top-left light)
        ring = QLinearGradient(QPointF(cx - outer, cy - outer), QPointF(cx + outer, cy + outer))
        ring.setColorAt(0.0, QColor(255, 250, 230, 60))
        ring.setColorAt(0.5, QColor(255, 250, 230, 0))
        ring.setColorAt(1.0, QColor(0, 0, 0, 70))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QBrush(ring), max(2.0, size * 0.012)))
        p.drawEllipse(QPointF(cx, cy), outer * 0.96, outer * 0.96)

        # bezel
        bezel = outer * 0.92
        p.setBrush(QBrush(QColor("#141412")))
        p.setPen(QPen(QColor("#77756b"), max(2, int(size * 0.008))))
        p.drawEllipse(QRectF(cx - bezel, cy - bezel, bezel * 2, bezel * 2))

        # face
        face_gradient = QRadialGradient(QPointF(cx, cy - face * 0.08), face * 1.04)
        for stop, color in pal["face"]:
            face_gradient.setColorAt(stop, QColor(color))

        p.setBrush(QBrush(face_gradient))
        p.setPen(QPen(QColor(pal["face_edge"]), 2))
        p.drawEllipse(QRectF(cx - face, cy - face, face * 2, face * 2))

        face_rect = QRectF(cx - face, cy - face, face * 2, face * 2)

        p.save()
        clip = QPainterPath()
        clip.addEllipse(QPointF(cx, cy), face, face)
        p.setClipPath(clip)

        # soft dark edge (light faces: lamp light falls off towards the bezel)
        if pal.get("vignette"):
            vig = QRadialGradient(QPointF(cx, cy - face * 0.1), face * 1.05)
            vig.setColorAt(0.55, QColor(40, 30, 14, 0))
            vig.setColorAt(0.9, QColor(40, 30, 14, int(pal["vignette"] * 0.55)))
            vig.setColorAt(1.0, QColor(25, 18, 8, pal["vignette"]))
            p.fillRect(face_rect, QBrush(vig))

        # backlight bleeding through the dial
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)

        lr, lg, lb = pal["light"]
        a0, a1, a2, a_rim = pal["light_alpha"]

        backlight = QRadialGradient(QPointF(cx, cy - face * 0.12), face * 1.05)
        backlight.setColorAt(0.0, QColor(lr, lg, lb, a0))
        backlight.setColorAt(0.55, QColor(lr, lg, lb, a1))
        backlight.setColorAt(0.85, QColor(lr, lg, lb, a2))
        backlight.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(face_rect, QBrush(backlight))

        if a_rim:
            rim = QRadialGradient(QPointF(cx, cy), face)
            rim.setColorAt(0.90, QColor(0, 0, 0, 0))
            rim.setColorAt(0.97, QColor(lr, lg, lb, a_rim))
            rim.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(face_rect, QBrush(rim))

        p.restore()

        # scale
        self.draw_scale(p, g)

        # readout window: inset into the dial, faint glow, ghost segments
        box = g["box"]

        p.setBrush(Qt.BrushStyle.NoBrush)

        if pal["box_glow_alpha"]:
            br, bg_, bb = pal["box_glow"]
            for i in range(4):
                p.setPen(QPen(QColor(br, bg_, bb, max(0, pal["box_glow_alpha"] - i * 6)), 1.5))
                p.drawRoundedRect(box.adjusted(-2 - i * 1.5, -2 - i * 1.5, 2 + i * 1.5, 2 + i * 1.5), 7 + i, 7 + i)

        # light lip below the window (reads as a recess cut into the face)
        p.setPen(QPen(QColor(255, 252, 240, pal["inset"]), 1.5))
        p.drawRoundedRect(box.adjusted(-1, 0, 1, 2), 7, 7)

        glass = QLinearGradient(box.topLeft(), box.bottomLeft())
        glass.setColorAt(0.0, QColor(pal["glass"][0]))
        glass.setColorAt(1.0, QColor(pal["glass"][1]))
        p.setBrush(QBrush(glass))
        p.setPen(QPen(QColor(pal["box_edge"]), 2))
        p.drawRoundedRect(box, 6, 6)

        sr, sg, sb = pal["seg_glow"]
        inner_glow = QRadialGradient(box.center(), box.width() * 0.6)
        inner_glow.setColorAt(0.0, QColor(sr, sg, sb, 16))
        inner_glow.setColorAt(1.0, QColor(sr, sg, sb, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(inner_glow))
        p.drawRoundedRect(box.adjusted(2, 2, -2, -2), 5, 5)

        # inner shadow along the top edge of the recess
        p.save()
        clip = QPainterPath()
        clip.addRoundedRect(box.adjusted(1, 1, -1, -1), 5, 5)
        p.setClipPath(clip)
        top_shadow = QLinearGradient(box.topLeft(), QPointF(box.left(), box.top() + box.height() * 0.3))
        top_shadow.setColorAt(0.0, QColor(0, 0, 0, 150))
        top_shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(box, QBrush(top_shadow))
        p.restore()

        x, y, dw, dh, sp, unit_font, unit_rect = self.readout_layout(g)
        draw_seven_seg(p, x, y, dw, dh, sp, "888", QColor(*pal["seg"], pal["ghost"]))

        # glass highlight
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 240, 9))
        p.drawRoundedRect(QRectF(box.left() + 3, box.top() + 3, box.width() - 6, box.height() * 0.42), 4, 4)

        # status light
        light_radius = max(3, size * 0.012)
        light_x = cx + face * 0.29
        light_y = cy - face * 0.31

        light_gradient = QRadialGradient(QPointF(light_x, light_y), light_radius * 3)
        light_gradient.setColorAt(0.0, QColor("#b4e879"))
        light_gradient.setColorAt(0.35, QColor("#4f823d"))
        light_gradient.setColorAt(1.0, QColor("#162014"))

        p.setBrush(QBrush(light_gradient))
        p.setPen(QPen(QColor(0, 0, 0, 120), 1) if pal.get("vignette") else Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(light_x - light_radius, light_y - light_radius, light_radius * 2, light_radius * 2))

        # screws
        rnd = random.Random(zlib.crc32(self.title.encode()) & 0xFFFF)

        # placed between scale numbers (27 deg from the nearest label) so none is covered
        for deg in (54.0, -54.0, 162.0, 198.0):
            a = math.radians(deg)
            draw_screw(p, cx + math.cos(a) * face * 0.585, cy - math.sin(a) * face * 0.585,
                       max(2.5, size * 0.014), rnd.uniform(0, math.pi))

        p.end()

        # blurred glow layer for ticks / numbers / title (backlit look)
        glow = new_layer(side, side, dpr)

        q = QPainter(glow)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.translate(-g["ox"], -g["oy"])
        self.draw_scale(q, g, glow=True)
        q.end()

        glow = soft_blur(glow, 5)

        if pal["glow_opacity"] > 0:
            p = QPainter(img)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            p.setOpacity(pal["glow_opacity"])
            p.drawImage(QPointF(0, 0), glow)
            p.end()

        # hover lamp layer (Plus-blended at the hover level in paintEvent)
        hv = new_layer(side, side, dpr)

        q = QPainter(hv)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.translate(-g["ox"], -g["oy"])

        hr, hg, hb = pal["hover"]
        k = face / outer

        rim_glow = QRadialGradient(QPointF(cx, cy), outer)
        rim_glow.setColorAt(max(0.0, k - 0.07), QColor(hr, hg, hb, 0))
        rim_glow.setColorAt(min(0.99, k + 0.012), QColor(hr, hg, hb, pal["hover_rim"]))
        rim_glow.setColorAt(0.965, QColor(hr, hg, hb, int(pal["hover_rim"] * 0.3)))
        rim_glow.setColorAt(1.0, QColor(hr, hg, hb, 0))
        q.setPen(Qt.PenStyle.NoPen)
        q.setBrush(QBrush(rim_glow))
        q.drawEllipse(QPointF(cx, cy), outer, outer)

        q.save()
        clip = QPainterPath()
        clip.addEllipse(QPointF(cx, cy), face, face)
        q.setClipPath(clip)
        lamp = QRadialGradient(QPointF(cx, cy - face * 0.2), face * 1.1)
        lamp.setColorAt(0.0, QColor(hr, hg, hb, pal["hover_face"]))
        lamp.setColorAt(0.6, QColor(hr, hg, hb, pal["hover_face"] // 3))
        lamp.setColorAt(1.0, QColor(hr, hg, hb, 0))
        q.fillRect(face_rect, QBrush(lamp))
        q.restore()

        if pal["hover_glow"] > 0:
            q.resetTransform()
            q.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            q.setOpacity(pal["hover_glow"])
            q.drawImage(QPointF(0, 0), glow)

        q.end()

        self._hover_px = QPixmap.fromImage(hv)
        self._hover_px.setDevicePixelRatio(dpr)

        pixmap = QPixmap.fromImage(img)
        pixmap.setDevicePixelRatio(dpr)

        return pixmap

    # --------------------------------------------------------

    def _readout_text(self):

        return f"{int(round(self.value))}"

    def build_readout(self, g, dpr, text):

        pal = gauge_palette()

        box = g["box"]
        pad = 8

        area = box.adjusted(-pad, -pad, pad, pad)

        img = new_layer(area.width(), area.height(), dpr)

        x, y, dw, dh, sp, unit_font, unit_rect = self.readout_layout(g)

        def paint_lit(painter, color):
            painter.translate(-area.left(), -area.top())
            draw_seven_seg(painter, x, y, dw, dh, sp, text, color)
            painter.setFont(unit_font)
            painter.setPen(color)
            painter.drawText(unit_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.unit)

        glow = new_layer(area.width(), area.height(), dpr)
        q = QPainter(glow)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_lit(q, QColor(*pal["seg_glow"]))
        q.end()
        glow = soft_blur(glow, 4)

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setOpacity(0.9)
        p.drawImage(QPointF(0, 0), glow)
        p.setOpacity(1.0)
        paint_lit(p, QColor(*pal["seg"]))
        p.end()

        pixmap = QPixmap.fromImage(img)
        pixmap.setDevicePixelRatio(dpr)

        return area.topLeft(), pixmap

    # --------------------------------------------------------

    def palette_changed(self):

        self._face = None
        self._face_key = None
        self._readout = None
        self._readout_key = None
        self._hover_px = None
        self.update()

    # --------------------------------------------------------
    # hover lamp, glass tap, double-click to open diagnostics

    def dial_contains(self, pos):

        g = self.geometry_info()

        return math.hypot(pos.x() - g["cx"], pos.y() - g["cy"]) <= g["outer"]

    def _set_inside(self, inside):

        if inside == self._inside:
            return

        self._inside = inside

        self.setCursor(
            Qt.CursorShape.PointingHandCursor if inside else Qt.CursorShape.ArrowCursor
        )

        start_hover_fade(self, 1.0 if inside else 0.0, self.HOVER_FADE)

    def enterEvent(self, event):

        try:
            self._set_inside(self.dial_contains(event.position()))
        except Exception:
            pass

        super().enterEvent(event)

    def mouseMoveEvent(self, event):

        self._set_inside(self.dial_contains(event.position()))

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):

        self._set_inside(False)

        super().leaveEvent(event)

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton and self.dial_contains(event.position()):
            self.tap()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton and self.dial_contains(event.position()):
            # the first click already went "tink": no second tink, just open the screen
            self.jiggle(0.5)
            self.activated.emit()
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def tap(self):

        now = time.monotonic()
        interval = QApplication.doubleClickInterval() / 1000.0

        # second press of a double-click: jiggle, but never a second tink
        if now - self._last_tap > interval:
            play_sound("tink")
            self.tinks += 1

        self._last_tap = now
        self.taps += 1

        self.jiggle(1.0)
        self.tapped.emit()

    def jiggle(self, strength=1.0):

        """Knock the needle like a fingernail on the glass (through the spring physics)."""

        kick = random.uniform(55.0, 70.0) * strength

        if self.pos > 96 or (self.pos > 4 and random.random() < 0.5):
            kick = -kick

        self.vel += kick

        fx_hub().clock60.add(self, self._step)

    # --------------------------------------------------------

    def paintEvent(self, event):

        pal = gauge_palette()

        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        g = self.geometry_info()
        dpr = self.devicePixelRatioF()

        face_key = (g["w"], g["h"], dpr, PALETTE_STATE["name"])

        if self._face is None or self._face_key != face_key:
            self._face = self.build_face(g, dpr)
            self._face_key = face_key
            self._readout = None

        painter.drawPixmap(g["ox"], g["oy"], self._face)

        cx, cy, size, face, outer = g["cx"], g["cy"], g["size"], g["face"], g["outer"]

        # hover lamp
        if self.hover > 0.002 and self._hover_px is not None:
            painter.save()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            painter.setOpacity(min(1.0, self.hover) * self.backlight)
            painter.drawPixmap(g["ox"], g["oy"], self._hover_px)
            painter.restore()

        # backlight off (boot): darken the dial
        if self.backlight < 0.999:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, int(205 * (1 - self.backlight))))
            painter.drawEllipse(QPointF(cx, cy), outer * 0.92, outer * 0.92)

        # lit readout
        if self.backlight > 0.01:

            text = self._readout_text()
            key = (text, face_key)

            if self._readout is None or self._readout_key != key:
                self._readout = self.build_readout(g, dpr, text)
                self._readout_key = key

            painter.setOpacity(self.backlight)
            painter.drawPixmap(self._readout[0], self._readout[1])
            painter.setOpacity(1.0)

        # needle
        value = max(-2.0, min(102.0, self.pos + self.jitter))
        angle = math.radians(self.angle_for_value(value))

        dx = math.cos(angle)
        dy = -math.sin(angle)
        nx, ny = -dy, dx

        length = face * 0.62
        tail = face * 0.13
        base_w = max(2.0, size * 0.011)
        tip_w = max(0.6, size * 0.0022)

        def needle_poly(ox, oy):
            return QPolygonF([
                QPointF(cx - dx * tail + nx * base_w * 0.8 + ox, cy - dy * tail + ny * base_w * 0.8 + oy),
                QPointF(cx + nx * base_w + ox, cy + ny * base_w + oy),
                QPointF(cx + dx * length + nx * tip_w + ox, cy + dy * length + ny * tip_w + oy),
                QPointF(cx + dx * length - nx * tip_w + ox, cy + dy * length - ny * tip_w + oy),
                QPointF(cx - nx * base_w + ox, cy - ny * base_w + oy),
                QPointF(cx - dx * tail - nx * base_w * 0.8 + ox, cy - dy * tail - ny * base_w * 0.8 + oy),
            ])

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 70 if pal.get("vignette") else 95))
        painter.drawPolygon(needle_poly(size * 0.008, size * 0.013))

        lit = lerp_color(QColor(pal["needle_dark"]), QColor(pal["needle_lit"]), self.backlight)
        painter.setBrush(lit)
        painter.setPen(QPen(QColor(*pal["needle_edge"]), 0.8))
        painter.drawPolygon(needle_poly(0, 0))

        if pal.get("needle_tip"):
            # painted tip on light faces (classic aviation pointer)
            t0 = length * 0.70
            w0 = base_w + (tip_w - base_w) * (t0 / length)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(pal["needle_tip"]))
            painter.drawPolygon(QPolygonF([
                QPointF(cx + dx * t0 + nx * w0, cy + dy * t0 + ny * w0),
                QPointF(cx + dx * length + nx * tip_w, cy + dy * length + ny * tip_w),
                QPointF(cx + dx * length - nx * tip_w, cy + dy * length - ny * tip_w),
                QPointF(cx + dx * t0 - nx * w0, cy + dy * t0 - ny * w0),
            ]))

        # hub
        hub_radius = face * 0.075

        hub = QRadialGradient(QPointF(cx - hub_radius * 0.3, cy - hub_radius * 0.3), hub_radius * 1.4)
        hub.setColorAt(0.0, QColor(pal["hub"][0]))
        hub.setColorAt(1.0, QColor(pal["hub"][1]))

        painter.setBrush(QBrush(hub))
        painter.setPen(QPen(QColor(pal["hub_edge"]), 2))
        painter.drawEllipse(QPointF(cx, cy), hub_radius, hub_radius)

        # alarm wash (smooth level supplied by the monitor)
        if self.alarm > 0.001:
            painter.setBrush(QColor(200, 25, 15, int(42 * self.alarm)))
            painter.setPen(QPen(QColor(235, 50, 30, int(220 * self.alarm)), max(3, int(size * 0.014))))
            painter.drawEllipse(QRectF(cx - outer, cy - outer, outer * 2, outer * 2))


# ============================================================
# STATUS BUTTON
# ============================================================

class StatusButton(QPushButton):

    LED_GREEN = (QColor("#b8e989"), QColor("#598c43"), QColor("#182117"))
    LED_RED = (QColor("#ff8a70"), QColor("#b0281c"), QColor("#241210"))

    HEIGHT = 66

    def __init__(
        self,
        title,
        value=""
    ):

        super().__init__()

        self.title = title
        self.value = value

        self.alarm = 0.0
        self.hover = 0.0
        self._hover_target = 0.0
        self.clickable = True

        # 66 px (was 70) leaves room for the audio scope + toggle row
        self.setMinimumHeight(
            self.HEIGHT
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)

        # Chunky toggle-switch clack on every press
        self.pressed.connect(
            lambda: play_sound("click") if self.clickable else None
        )

    # --------------------------------------------------------

    def set_clickable(self, clickable):

        self.clickable = bool(clickable)

        self.setCursor(
            Qt.CursorShape.PointingHandCursor if self.clickable else Qt.CursorShape.ArrowCursor
        )

        self.update()

    def enterEvent(self, event):

        if self.clickable:
            start_hover_fade(self, 1.0)

        super().enterEvent(event)

    def leaveEvent(self, event):

        start_hover_fade(self, 0.0)

        super().leaveEvent(event)

    # --------------------------------------------------------

    def set_value(self, value):

        if value != self.value:

            self.value = value

            self.update()

    # --------------------------------------------------------

    def set_alarm(self, level):

        level = max(0.0, min(1.0, float(level)))

        if abs(level - self.alarm) > 0.02 or (level == 0) != (self.alarm == 0):

            self.alarm = level

            self.update()

    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)

        h = self.hover if self.clickable else 0.0
        down = self.clickable and self.isDown()

        edge = lerp_color(QColor("#777367"), QColor("#cfc7a8"), h)
        edge = lerp_color(edge, QColor("#e0402c"), self.alarm)

        draw_button_body(painter, rect, 6, h, down, edge)

        shift = 2.0 if down else 0.0
        painter.translate(0, shift)

        # indicator LED (+ halo that grows on hover)
        indicator_x = rect.left() + 15
        indicator_y = rect.center().y()
        radius = 5

        alarmed = self.alarm > 0.0
        lit = self.LED_RED if alarmed else self.LED_GREEN

        if h > 0.01:
            halo = QRadialGradient(QPointF(indicator_x, indicator_y), radius * 3.6)
            c = QColor(lit[0])
            c.setAlpha(int(110 * h))
            halo.setColorAt(0.0, c)
            halo.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
            painter.setBrush(QBrush(halo))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(indicator_x, indicator_y), radius * 3.6, radius * 3.6)

        core = lerp_color(self.LED_GREEN[0], lit[0], 0.5 + 0.5 * self.alarm) if alarmed else lit[0]
        core = lerp_color(core, QColor(255, 255, 240), 0.3 * h)

        glow = QRadialGradient(QPointF(indicator_x, indicator_y), radius * 3)
        glow.setColorAt(0.0, core)
        glow.setColorAt(0.4 + 0.1 * h, lit[1])
        glow.setColorAt(1.0, lit[2])

        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(indicator_x - radius, indicator_y - radius, radius * 2, radius * 2))

        text_w = rect.width() - 30 - (24 if self.clickable else 10)

        # title
        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        painter.setPen(lerp_color(QColor("#bdb69a"), QColor("#e2dbbd"), h))
        painter.drawText(
            QRectF(rect.left() + 30, rect.top() + 9, text_w, 18),
            Qt.AlignmentFlag.AlignLeft,
            self.title
        )

        # value
        value_font = QFont("Consolas", 9)
        painter.setFont(value_font)
        painter.setPen(lerp_color(QColor("#81ad6d"), QColor("#a4d58c"), h))
        fm = QFontMetrics(value_font)

        lines = self.value.split("\n")

        if len(lines) == 1:

            painter.drawText(
                QRectF(rect.left() + 30, rect.top() + 29, text_w, rect.height() - 33),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                fm.elidedText(self.value, Qt.TextElideMode.ElideRight, int(text_w))
            )

        else:

            line_height = 16

            for index, line in enumerate(lines):
                painter.drawText(
                    QRectF(rect.left() + 30, rect.top() + 27 + index * line_height, text_w, line_height),
                    Qt.AlignmentFlag.AlignLeft,
                    fm.elidedText(line, Qt.TextElideMode.ElideRight, int(text_w))
                )

        # "opens a screen" affordance: groove + chevron at the right edge
        if self.clickable:

            gx = rect.right() - 22
            painter.setPen(QPen(QColor(0, 0, 0, 90), 1))
            painter.drawLine(QPointF(gx, rect.top() + 11), QPointF(gx, rect.bottom() - 11))
            painter.setPen(QPen(QColor(255, 250, 230, 16), 1))
            painter.drawLine(QPointF(gx + 1, rect.top() + 11), QPointF(gx + 1, rect.bottom() - 11))

            cx = rect.right() - 11
            cy = rect.center().y()
            chevron = QPolygonF([
                QPointF(cx - 3, cy - 5), QPointF(cx + 3, cy), QPointF(cx - 3, cy + 5)
            ])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(lerp_color(QColor("#5f5b4e"), QColor("#d9d0ad"), max(h, 0.6 if down else 0.0)))
            painter.drawPolygon(chevron)

        painter.translate(0, -shift)

        panel_dim(painter, rect)


# ============================================================
# PANEL TOGGLE (MUTE / AMBIENT / CRT / BOOT)
# ============================================================

class PanelToggle(QPushButton):

    """Small chunky latching switch in the StatusButton style."""

    def __init__(
        self,
        title,
        on_color="#b8e989",
        shortcut_hint=""
    ):

        super().__init__()

        self.title = title
        self.on_color = QColor(on_color)
        self.override_text = None
        self.hover = 0.0
        self._hover_target = 0.0

        self.setCheckable(True)
        self.setFixedHeight(48)
        self.shortcut_hint = shortcut_hint
        self.setMinimumWidth(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if shortcut_hint:
            self.setToolTip(f"{title}  [{shortcut_hint}]")

        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)

        self.pressed.connect(lambda: play_sound("click"))
        self.toggled.connect(lambda _checked: self.update())

    # --------------------------------------------------------

    def set_override_text(self, text):

        self.override_text = text
        self.update()

    def enterEvent(self, event):

        start_hover_fade(self, 1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):

        start_hover_fade(self, 0.0)
        super().leaveEvent(event)

    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)

        on = self.isChecked()
        down = self.isDown()
        h = self.hover

        edge = lerp_color(QColor("#777367"), QColor("#bab398"), h)

        draw_button_body(painter, rect, 5, h, down, edge)

        shift = 2.0 if down else 0.0
        painter.translate(0, shift)

        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(lerp_color(QColor("#bdb69a"), QColor("#e2dbbd"), h))
        painter.drawText(
            QRectF(rect.left(), rect.top() + 2, rect.width(), 16),
            Qt.AlignmentFlag.AlignCenter,
            self.title
        )

        state = self.override_text or ("ON" if on else "OFF")

        painter.setFont(QFont("Consolas", 8))
        metrics = painter.fontMetrics()

        text_width = metrics.horizontalAdvance(state)
        radius = 4
        total = radius * 2 + 5 + text_width

        led_x = rect.center().x() - total / 2 + radius
        led_y = rect.top() + 24

        lit = on or self.override_text is not None
        core = self.on_color if lit else QColor("#3a3a33")

        if lit and h > 0.01:
            halo = QRadialGradient(QPointF(led_x, led_y), radius * 3.6)
            c = QColor(core)
            c.setAlpha(int(80 * h))
            halo.setColorAt(0.0, c)
            halo.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
            painter.setBrush(QBrush(halo))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(led_x, led_y), radius * 3.6, radius * 3.6)

        glow = QRadialGradient(QPointF(led_x, led_y), radius * 3)
        glow.setColorAt(0.0, lerp_color(core.lighter(130), QColor(255, 255, 240), 0.3 * h) if lit else lerp_color(core, QColor("#55554b"), h))
        glow.setColorAt(0.4, core.darker(160) if lit else QColor("#262622"))
        glow.setColorAt(1.0, QColor("#141412"))

        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(led_x - radius, led_y - radius, radius * 2, radius * 2))

        painter.setPen(core if lit else lerp_color(QColor("#6e6b5e"), QColor("#8f8b7a"), h))
        painter.drawText(
            QRectF(led_x + radius + 5, led_y - 8, text_width + 4, 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            state
        )

        if self.shortcut_hint:
            painter.setFont(stencil_font(7))
            painter.setPen(lerp_color(QColor("#9a947c"), QColor("#d6cfae"), h))
            painter.drawText(
                QRectF(rect.left(), rect.top() + 31, rect.width(), 12),
                Qt.AlignmentFlag.AlignCenter,
                f"[{self.shortcut_hint}]"
            )

        painter.translate(0, -shift)

        panel_dim(painter, rect, 5)


# ============================================================
# AUDIO OSCILLOSCOPE (virtual mixer of every sound the app plays)
# ============================================================

class AudioScope(QWidget):

    """
    Little green phosphor oscilloscope. QSoundEffect hides its output,
    so the SoundBank keeps decoded copies of every WAV and records when
    (and how loud) each sound starts; the scope mixes the currently
    playing ones at their playback position. 30 fps while a sound event
    plays (20 fps for the ambient hum alone), ~5 fps idle shimmer,
    static when muted or hidden. The trace is burned into a small
    phosphor layer once per frame (1 px cosmetic strokes, a half-res
    layer smoothed up for the glow) and faded for the afterglow, so a
    repaint is just three blits.
    """

    ACTIVE_MS = 33
    LOOP_MS = 50            # only the ambient hum playing: a drone needs no 30 fps
    IDLE_MS = 200
    FADE = 0.42             # phosphor persistence per frame (core trace)
    GLOW_FADE = 0.30
    WINDOW = 0.020          # seconds across the screen -> 2.5 ms / div
    GAIN = 2.6

    def __init__(self):

        super().__init__()

        self.setMinimumHeight(78)
        self.setMaximumHeight(210)       # fullscreen: grow, but don't become a wall of empty graticule
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.sounds = None
        self.vu = None              # VUMeters fed from the same mixer window
        self.mode = "muted"
        self.trails = deque(maxlen=3)
        self.frames = 0
        self.peak = 0.0
        self.seed = random.Random(7412)

        self._bg = None
        self._bg_key = None

        self._phos = None
        self._glow = None
        self._phos_key = None
        self._phos_rect = QRectF()

        self.timer = ManagedTimer(self, self.IDLE_MS, self._tick)

    # --------------------------------------------------------

    def attach(self, sounds):

        self.sounds = sounds

        try:
            sounds.voice_started.connect(self._on_voice)
        except Exception:
            pass

        self.refresh()

    def _on_voice(self, _name):

        if self.mode != "live":
            self.refresh()
        else:
            self.timer.setInterval(self._live_interval())

    def _live_interval(self):

        try:
            if any(not v[4] for v in self.sounds.voices):
                return self.ACTIVE_MS
        except Exception:
            pass

        return self.LOOP_MS

    def refresh(self):

        snd = self.sounds

        if snd is None or snd.muted or snd.suspended:
            self.mode = "muted"
            self.trails.clear()
            self._clear_layers()
            self.peak = 0.0
            self.timer.halt()
            if self.vu is not None:
                self.vu.rest()
            self.update()
            return

        live = bool(snd.active_voices())

        self.mode = "live" if live else "idle"
        self.timer.setInterval(self._live_interval() if live else self.IDLE_MS)

        if live:
            self._tick()

        if self.isVisible():
            self.timer.run()

        self.update()

    def showEvent(self, event):

        super().showEvent(event)
        self.refresh()

    def hideEvent(self, event):

        super().hideEvent(event)
        self.timer.halt()

    # --------------------------------------------------------

    def glass_rect(self):

        return QRectF(self.rect()).adjusted(5, 5, -5, -5)

    def trace_rect(self):

        return self.glass_rect().adjusted(8, 17, -8, -7)

    def _tick(self):

        snd = self.sounds

        if snd is None or snd.muted or snd.suspended:
            self.refresh()
            return

        rect = self.trace_rect()
        cols = max(40, min(220, int(rect.width() / 1.4)))

        pts = snd.mix_window(cols, self.WINDOW)

        if self.vu is not None:
            self.vu.feed(pts)

        if pts is None:
            self.trails.clear()
            self._clear_layers()
            self.peak = 0.0
            if self.mode != "idle":
                self.mode = "idle"
                self.timer.setInterval(self.IDLE_MS)
        else:
            self.trails.append(pts)
            self.peak = max(max(abs(a), abs(b)) for a, b in pts)
            self._burn(pts)
            if self.mode != "live":
                self.mode = "live"
            interval = self._live_interval()
            if self.timer.interval() != interval:
                self.timer.setInterval(interval)

        self.frames += 1
        self.update(self.glass_rect().toAlignedRect())

    # --------------------------------------------------------

    def build_background(self, dpr):

        w, h = self.width(), self.height()

        img = new_layer(w, h, dpr)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        outer = QRectF(1, 1, w - 2, h - 2)

        bezel = QLinearGradient(outer.topLeft(), outer.bottomLeft())
        bezel.setColorAt(0.0, QColor("#3c3b35"))
        bezel.setColorAt(0.5, QColor("#232320"))
        bezel.setColorAt(1.0, QColor("#121210"))
        p.setBrush(QBrush(bezel))
        p.setPen(QPen(QColor("#6f6c60"), 1.5))
        p.drawRoundedRect(outer, 7, 7)

        glass = self.glass_rect()

        screen = QRadialGradient(glass.center(), glass.width() * 0.7)
        screen.setColorAt(0.0, QColor("#0b1a0e"))
        screen.setColorAt(1.0, QColor("#030805"))
        p.setBrush(QBrush(screen))
        p.setPen(QPen(QColor(0, 0, 0, 200), 1.5))
        p.drawRoundedRect(glass, 5, 5)

        tr = self.trace_rect()

        # graticule: 8 x 4 divisions, centre axes with minor ticks
        p.setPen(QPen(QColor(110, 230, 120, 26), 1))
        for i in range(9):
            x = tr.left() + tr.width() * i / 8
            p.drawLine(QPointF(x, tr.top()), QPointF(x, tr.bottom()))
        for j in range(5):
            y = tr.top() + tr.height() * j / 4
            p.drawLine(QPointF(tr.left(), y), QPointF(tr.right(), y))

        p.setPen(QPen(QColor(110, 230, 120, 55), 1))
        cy = tr.center().y()
        cx = tr.center().x()
        for i in range(41):
            x = tr.left() + tr.width() * i / 40
            p.drawLine(QPointF(x, cy - 2), QPointF(x, cy + 2))
        for j in range(21):
            y = tr.top() + tr.height() * j / 20
            p.drawLine(QPointF(cx - 2, y), QPointF(cx + 2, y))

        font = QFont("Consolas", 7)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(120, 220, 110, 150))
        p.drawText(QRectF(glass.left() + 8, glass.top() + 3, glass.width() - 16, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "AUDIO // CH-1")
        p.setPen(QColor(120, 220, 110, 95))
        p.drawText(QRectF(glass.left() + 8, glass.top() + 3, glass.width() - 16, 12),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "2.5 MS/DIV")

        # glass glare
        glare = QLinearGradient(glass.topLeft(), glass.bottomLeft())
        glare.setColorAt(0.0, QColor(255, 255, 255, 12))
        glare.setColorAt(0.35, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glare))
        p.drawRoundedRect(glass.adjusted(2, 2, -2, -2), 4, 4)

        p.end()

        pixmap = QPixmap.fromImage(img)
        pixmap.setDevicePixelRatio(dpr)

        return pixmap

    # --------------------------------------------------------

    def _clear_layers(self):

        for img in (self._phos, self._glow):
            if img is not None:
                img.fill(0)

    def _layers(self):

        dpr = self.devicePixelRatioF()
        rect = self.glass_rect().adjusted(2, 2, -2, -2).toAlignedRect()
        key = (rect.width(), rect.height(), dpr)

        if self._phos is None or self._phos_key != key:

            w = max(2, int(round(rect.width() * dpr)))
            h = max(2, int(round(rect.height() * dpr)))

            self._phos = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            self._glow = QImage(w // 2, h // 2, QImage.Format.Format_ARGB32_Premultiplied)
            self._phos.fill(0)
            self._glow.fill(0)

            self._phos_key = key
            self._phos_rect = QRectF(rect)

        return self._phos, self._glow, dpr

    def _burn(self, pts):

        """Fade the phosphor layers a step and stroke the new trace once."""

        try:

            phos, glow, dpr = self._layers()

            tr = self.trace_rect()
            ox = self._phos_rect.left()
            oy = self._phos_rect.top()

            half = tr.height() / 2 - 2
            y0 = tr.center().y() - oy
            x0 = tr.left() - ox
            step = tr.width() / len(pts)
            gain = self.GAIN
            tanh = math.tanh

            poly = QPolygonF()

            for c, (a, b) in enumerate(pts):
                x = x0 + c * step
                poly.append(QPointF(x, y0 - tanh(a * gain) * half))
                poly.append(QPointF(x + step * 0.5, y0 - tanh(b * gain) * half))

            for img, scale, fade, color in (
                (glow, dpr * 0.5, self.GLOW_FADE, QColor(70, 255, 105, 150)),
                (phos, dpr, self.FADE, QColor(190, 255, 170, 245)),
            ):
                p = QPainter(img)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                p.fillRect(img.rect(), QColor(0, 0, 0, int(255 * fade)))
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.scale(scale, scale)
                pen = QPen(color, 1.0)
                pen.setCosmetic(True)
                p.setPen(pen)
                p.drawPolyline(poly)
                p.end()

        except Exception:
            pass

    def _y(self, v, cy, half):

        return cy - math.tanh(v * self.GAIN) * half

    def paintEvent(self, event):

        painter = QPainter(self)

        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)

        if self._bg is None or self._bg_key != key:
            self._bg = self.build_background(dpr)
            self._bg_key = key

        painter.drawPixmap(0, 0, self._bg)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        tr = self.trace_rect()
        cy = tr.center().y()
        half = tr.height() / 2 - 2

        painter.setClipRect(self.glass_rect().adjusted(2, 2, -2, -2))

        if self.mode == "live" and self.trails and self._phos is not None:

            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(self._phos_rect, self._glow)
            painter.drawImage(self._phos_rect, self._phos)

        else:

            # flat line (idle: faint noise shimmer; muted: dim + stencil)
            muted = self.mode == "muted"
            rnd = self.seed
            poly = QPolygonF()
            count = 48

            for i in range(count + 1):
                x = tr.left() + tr.width() * i / count
                jitter = 0.0 if muted else rnd.uniform(-0.55, 0.55)
                poly.append(QPointF(x, cy + jitter))

            painter.setPen(QPen(QColor(80, 255, 110, 22 if muted else 40), 3.2))
            painter.drawPolyline(poly)
            painter.setPen(QPen(QColor(170, 255, 150, 90 if muted else 170), 1.2))
            painter.drawPolyline(poly)

            if muted:
                painter.setFont(stencil_font(9))
                painter.setPen(QColor(224, 96, 64, 190))
                painter.drawText(
                    QRectF(tr.left(), tr.top() + 2, tr.width() - 2, tr.height() * 0.45),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    "MUTED"
                )

        painter.setClipping(False)

        panel_dim(painter, QRectF(self.rect()).adjusted(1, 1, -1, -1), 7)


# ============================================================
# core terminal TERMINAL STRIP
# ============================================================

class CoreTerminal(QWidget):

    """
    Green phosphor teletype strip. Messages are queued and typed one
    character at a time (throttled teletype tick), with a 3-line
    scrollback and a blinking block cursor. Repaints only itself, only
    while typing (plus a 2 Hz cursor blink of the cursor cell).
    """

    COLORS = {
        "info": QColor("#79d968"),
        "event": QColor("#b9f5a6"),
        "warn": QColor("#ffb040"),
        "alert": QColor("#ff5a48"),
        "quote": QColor("#c8f5d2"),
    }

    CHAR_MS = 26
    TICK_GAP = 0.085

    def __init__(self):

        super().__init__()

        self.setFixedHeight(136)
        self.setMinimumWidth(420)

        self.lines = deque(maxlen=3)
        self.current = None
        self.typed = 0
        self.pause = 0
        self.queue = deque()
        self.cursor_on = True
        self.last_tick = 0.0
        self.history = deque(maxlen=50)     # for tests / debugging

        self._frame = None
        self._frame_key = None

        self.font_main = QFont("Consolas", 10)
        self.font_main.setBold(True)
        self.line_h = 19

        self.type_timer = ManagedTimer(self, self.CHAR_MS, self._type_step)
        self.blink_timer = ManagedTimer(self, 530, self._blink)
        self.blink_timer.run()

    # --------------------------------------------------------

    def post(self, text, kind="info"):

        text = " ".join(str(text).upper().split())

        if not text:
            return

        self.history.append((text, kind))

        # long lines wrap onto a second row instead of being cut off
        parts = textwrap.wrap(text, self.wrap_width(), subsequent_indent="  ") or [text]
        parts = [(p, kind) for p in parts]

        if kind in ("warn", "alert"):
            # urgent lines jump ahead of routine status chatter
            routine = [item for item in self.queue if item[1] in ("info",)]
            urgent = [item for item in self.queue if item[1] not in ("info",)]
            self.queue = deque(urgent + parts + routine[-2:])
        else:
            if len(self.queue) >= 6:
                for item in list(self.queue):
                    if item[1] == "info":
                        self.queue.remove(item)
                        break
            self.queue.extend(parts)

        self.type_timer.run()

    def wrap_width(self):

        try:
            if self.width() < 200:
                return 78
            fm = QFontMetrics(self.font_main)
            room = self.glass_rect().width() - 34 - fm.horizontalAdvance("> ")
            return max(30, int(room // max(1, fm.horizontalAdvance("M"))))
        except Exception:
            return 78

    def idle(self):

        return self.current is None and not self.queue

    # --------------------------------------------------------

    def _type_step(self):

        if self.pause > 0:
            self.pause -= 1
            return

        if self.current is None:

            if not self.queue:
                self.type_timer.halt()
                self.update()
                return

            self.current = self.queue.popleft()
            self.typed = 0

        text, kind = self.current

        step = 2 if len(self.queue) >= 3 else 1
        self.typed = min(len(text), self.typed + step)

        now = time.monotonic()

        if text[self.typed - 1] != " " and now - self.last_tick >= self.TICK_GAP:
            self.last_tick = now
            play_sound("teletype")

        if self.typed >= len(text):
            self.lines.append(self.current)
            self.current = None
            self.pause = 10

        self.cursor_on = True
        self.update()

    # --------------------------------------------------------

    def _blink(self):

        self.cursor_on = not self.cursor_on

        if not self.type_timer.isActive():
            self.update(self.cursor_rect().toAlignedRect().adjusted(-2, -2, 2, 2))

    # --------------------------------------------------------

    def glass_rect(self):

        return QRectF(self.rect()).adjusted(9, 9, -9, -9)

    def text_origin(self):

        glass = self.glass_rect()

        return glass.left() + 12, glass.top() + 22

    def cursor_rect(self):

        fm = QFontMetrics(self.font_main)
        x0, y0 = self.text_origin()

        row = len(self.lines)

        if self.current is not None:
            text = "> " + self.current[0][: self.typed]
        else:
            text = "> "

        x = x0 + fm.horizontalAdvance(text)
        y = y0 + row * self.line_h

        return QRectF(x + 1, y + 3, fm.horizontalAdvance("M"), self.line_h - 5)

    # --------------------------------------------------------

    def build_frame(self, dpr):

        w, h = self.width(), self.height()
        image = new_layer(w, h, dpr)

        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        outer = QRectF(1, 1, w - 2, h - 2)

        bezel = QLinearGradient(outer.topLeft(), outer.bottomLeft())
        bezel.setColorAt(0.0, QColor("#3a3934"))
        bezel.setColorAt(0.5, QColor("#24231f"))
        bezel.setColorAt(1.0, QColor("#141412"))

        p.setBrush(QBrush(bezel))
        p.setPen(QPen(QColor("#6f6b5e"), 1.5))
        p.drawRoundedRect(outer, 7, 7)

        glass = self.glass_rect()

        p.setBrush(QColor("#030703"))
        p.setPen(QPen(QColor("#0b0b09"), 2))
        p.drawRoundedRect(glass, 5, 5)

        phosphor = QRadialGradient(glass.center(), glass.width() * 0.6)
        phosphor.setColorAt(0.0, QColor(60, 160, 60, 34))
        phosphor.setColorAt(1.0, QColor(60, 160, 60, 4))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(phosphor))
        p.drawRoundedRect(glass, 5, 5)

        # header label
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.setPen(QColor(150, 210, 140, 120))
        p.drawText(
            QRectF(glass.left() + 12, glass.top() + 2, glass.width() - 24, 12),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "OMORTSON CORE 6100  //  OPERATOR LINK"
        )
        p.drawText(
            QRectF(glass.left() + 12, glass.top() + 2, glass.width() - 24, 12),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "TELETYPE LINK"
        )

        p.setPen(QPen(QColor(120, 200, 110, 40), 1))
        p.drawLine(QPointF(glass.left() + 10, glass.top() + 15), QPointF(glass.right() - 10, glass.top() + 15))

        # bezel screws
        rnd = random.Random(7412)
        for sx, sy in ((5, 5), (w - 5, 5), (5, h - 5), (w - 5, h - 5)):
            draw_screw(p, sx, sy, 2.6, rnd.uniform(0, math.pi))

        p.end()

        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(dpr)

        return pixmap

    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)

        if self._frame is None or self._frame_key != key:
            self._frame = self.build_frame(dpr)
            self._frame_key = key

        painter.drawPixmap(0, 0, self._frame)

        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(self.font_main)

        fm = painter.fontMetrics()
        x0, y0 = self.text_origin()
        max_w = int(self.glass_rect().width() - 34)

        rows = list(self.lines)

        if self.current is not None:
            rows.append((self.current[0][: self.typed], self.current[1]))

        painter.setClipRect(self.glass_rect().adjusted(2, 16, -2, -2))

        for i, (text, kind) in enumerate(rows):

            line = fm.elidedText("> " + text, Qt.TextElideMode.ElideRight, max_w)
            color = self.COLORS.get(kind, self.COLORS["info"])

            # older lines fade a little
            age = len(rows) - 1 - i
            if age > 0:
                color = QColor(color)
                color.setAlpha(max(110, 255 - age * 55))

            y = y0 + (i + 1) * self.line_h - 4

            halo = QColor(color)
            halo.setAlpha(min(color.alpha(), 55))
            painter.setPen(halo)

            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                painter.drawText(int(x0 + ox), int(y + oy), line)

            painter.setPen(color)
            painter.drawText(int(x0), int(y), line)

        if self.cursor_on:
            painter.fillRect(self.cursor_rect(), self.COLORS["info"])

        painter.setClipping(False)

        panel_dim(painter, QRectF(self.rect()).adjusted(1, 1, -1, -1), 7)


# ============================================================
# NET RADAR (network activity)
# ============================================================

class NetRadar(QWidget):

    """
    Network radar. Each pulse expands from the apex; blips
    are established remote connections (psutil.net_connections, ~1 ms,
    no admin) and their distance shrinks as total throughput grows, so
    more connections = more blips and more traffic = closer blips.
    Animates at 25 fps only while visible and not minimized.
    """

    RANGE_M = 50
    PERIOD = 2.6
    TRAVEL = 1.5
    FADE = 1.4
    HALF_ANGLE = math.radians(58)

    def __init__(self, monitor):

        super().__init__()

        self.monitor = monitor

        self.setFixedSize(300, 136)

        self.rate = 0.0
        self.blips = []
        self.wave_start = None
        self.contacts = 0
        self.nearest = None
        self.sweeps = 0
        self.pings = 0
        self.ping_enabled = True
        self._last_ping = -1e9
        self._ping_wants = []          # times a ping was wanted (burst detection)
        self._hover_mute = False
        self.setMouseTracking(True)

        self._bg = None
        self._bg_key = None

        self.anim = ManagedTimer(self, 40, self._tick)

    # --------------------------------------------------------

    def set_range(self, metres):

        """RADAR RANGE knob: contacts keep their real distance, the scale changes."""

        metres = int(max(20, min(100, metres)))

        if metres != self.RANGE_M:
            self.RANGE_M = metres
            self._bg = None
            self.update()

    def range_scale(self):

        return 50.0 / self.RANGE_M     # blip distances are fractions of the 50 m base range

    def feed(self, down, up):

        total = max(0.0, float(down) + float(up))

        self.rate = total if self.rate == 0 else self.rate * 0.5 + total * 0.5

    def traffic_factor(self):

        # 1 KB/s -> 0, 10 MB/s -> 1 (log scale)
        return max(0.0, min(1.0, math.log10(max(self.rate, 1.0) / 1000.0) / 4.0))

    # --------------------------------------------------------

    def showEvent(self, event):

        super().showEvent(event)
        self.anim.run()

    def hideEvent(self, event):

        super().hideEvent(event)
        self.anim.halt()

    # --------------------------------------------------------

    def geometry_info(self):

        w, h = self.width(), self.height()

        apex = QPointF(w / 2, h - 16)
        radius = min(h - 34, (w / 2 - 70) / math.sin(self.HALF_ANGLE))

        return apex, radius

    # --------------------------------------------------------

    def connections(self):

        try:

            keys = set()

            for c in psutil.net_connections(kind="inet"):

                if c.status != "ESTABLISHED" or not c.raddr:
                    continue

                ip = c.raddr.ip

                if ip.startswith("127.") or ip == "::1":
                    continue

                keys.add((ip, c.raddr.port))

            return sorted(keys, key=lambda k: zlib.crc32(f"{k[0]}:{k[1]}".encode()))

        except Exception:

            return None

    # --------------------------------------------------------

    def new_sweep(self, now):

        self.wave_start = now
        self.sweeps += 1

        f = self.traffic_factor()

        keys = self.connections()

        fresh = []

        if keys:

            self.contacts = len(keys)

            for ip, port in keys[:10]:

                hcode = zlib.crc32(f"{ip}:{port}".encode())

                angle = ((hcode % 1000) / 999.0 * 2 - 1) * self.HALF_ANGLE * 0.92
                base = 0.38 + 0.58 * (((hcode // 1000) % 1000) / 999.0)
                dist = base * (1.0 - 0.7 * f) + random.uniform(-0.03, 0.03)

                fresh.append([angle, max(0.06, min(0.98, dist)), 0.35 + f, None])

        else:

            self.contacts = 0 if keys is not None else -1

        # heavy traffic adds a couple of close, large contacts
        for _ in range(int(f * 4)):
            fresh.append([
                random.uniform(-1, 1) * self.HALF_ANGLE * 0.85,
                random.uniform(0.12, 0.45) * (1.0 - 0.5 * f),
                0.6 + f,
                None
            ])

        # keep old blips fading, add new ones (revealed when the wave hits them)
        self.blips = [b for b in self.blips if b[3] is not None and now - b[3] < self.FADE] + fresh

        nearest = min((b[1] for b in fresh), default=None)

        if (
            fresh
            and self.isVisible()
            and not fx_hub().paused
            and PANEL_STATE["power"] >= 0.999
            and (f >= 0.3 or (nearest is not None and nearest < 0.3))
        ):
            self.request_ping(now)

    # --------------------------------------------------------

    PING_GAP = 4.0        # never more than one ping per this many seconds
    BURST_GAP = 12.0      # ...and this during connection bursts (e.g. opening a browser)

    def request_ping(self, now):

        """Rate-limited, burst-merged radar ping."""

        self._ping_wants = [t for t in self._ping_wants if now - t < 10.0] + [now]
        gap = self.BURST_GAP if len(self._ping_wants) >= 4 else self.PING_GAP

        if not self.ping_enabled or now - self._last_ping < gap:
            return

        self._last_ping = now
        self.pings += 1
        play_sound("ping")

    def mute_rect(self):

        return QRectF(self.width() - 62, 11, 51, 14)

    def set_ping_enabled(self, on, save=True):

        self.ping_enabled = bool(on)
        if save:
            try:
                self.monitor.write_setting("radar_ping", self.ping_enabled)
            except Exception:
                pass
            try:
                terminal_post("RADAR PING ENABLED" if self.ping_enabled else "RADAR PING MUTED", "event")
            except Exception:
                pass
        self.update()

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton and self.mute_rect().adjusted(-3, -3, 3, 3).contains(event.position()):
            play_sound("click")
            self.set_ping_enabled(not self.ping_enabled)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):

        if self.mute_rect().adjusted(-3, -3, 3, 3).contains(event.position()):
            event.accept()             # don't toggle fullscreen from the switch
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):

        hov = self.mute_rect().adjusted(-3, -3, 3, 3).contains(event.position())
        if hov != self._hover_mute:
            self._hover_mute = hov
            self.setCursor(Qt.CursorShape.PointingHandCursor if hov else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):

        if self._hover_mute:
            self._hover_mute = False
            self.unsetCursor()
            self.update()
        super().leaveEvent(event)

    def draw_mute_switch(self, p):

        """Small latching PING switch in the corner of the radar glass."""

        r = self.mute_rect()
        on = self.ping_enabled
        p.save()
        p.setPen(QPen(QColor(90, 200, 95, 150 if self._hover_mute else 90), 1))
        p.setBrush(QColor(4, 16, 5, 230))
        p.drawRoundedRect(r, 2.5, 2.5)
        lamp = QPointF(r.left() + 7.5, r.center().y())
        if on:
            halo = QRadialGradient(lamp, 6)
            halo.setColorAt(0.0, QColor(150, 255, 140, 120))
            halo.setColorAt(1.0, QColor(150, 255, 140, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(halo))
            p.drawEllipse(lamp, 6, 6)
        p.setPen(QPen(QColor(0, 0, 0, 160), 0.8))
        p.setBrush(QColor(170, 255, 150) if on else QColor(220, 120, 60))
        p.drawEllipse(lamp, 2.6, 2.6)
        p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        p.setPen(QColor(150, 230, 140, 210) if on else QColor(230, 150, 90, 220))
        p.drawText(QRectF(r.left() + 13, r.top(), r.width() - 15, r.height()),
                   Qt.AlignmentFlag.AlignCenter, "PING" if on else "MUTED")
        p.restore()

    def _tick(self):

        if not self.isVisible():
            self.anim.halt()
            return

        now = time.monotonic()

        if self.wave_start is None or now - self.wave_start >= self.PERIOD:
            self.new_sweep(now)

        progress = (now - self.wave_start) / self.TRAVEL
        k = self.range_scale()

        for blip in self.blips:
            if blip[3] is None and blip[1] * k <= min(1.0, progress):
                blip[3] = now

        revealed = [b for b in self.blips if b[3] is not None and now - b[3] < self.FADE and b[1] * k <= 1.0]
        self.nearest = min((b[1] * k for b in revealed), default=None)

        self.update()

    # --------------------------------------------------------

    def build_background(self, dpr):

        w, h = self.width(), self.height()
        image = new_layer(w, h, dpr)

        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        outer = QRectF(1, 1, w - 2, h - 2)

        bezel = QLinearGradient(outer.topLeft(), outer.bottomLeft())
        bezel.setColorAt(0.0, QColor("#3a3934"))
        bezel.setColorAt(0.5, QColor("#24231f"))
        bezel.setColorAt(1.0, QColor("#141412"))

        p.setBrush(QBrush(bezel))
        p.setPen(QPen(QColor("#6f6b5e"), 1.5))
        p.drawRoundedRect(outer, 7, 7)

        screen = outer.adjusted(8, 8, -8, -8)
        p.setBrush(QColor("#020602"))
        p.setPen(QPen(QColor("#0b0b09"), 2))
        p.drawRoundedRect(screen, 5, 5)

        apex, radius = self.geometry_info()

        # fan
        fan = QPainterPath()
        fan.moveTo(apex)
        start_deg = 90 + math.degrees(self.HALF_ANGLE)
        span = -2 * math.degrees(self.HALF_ANGLE)
        fan.arcTo(QRectF(apex.x() - radius, apex.y() - radius, radius * 2, radius * 2), start_deg, span)
        fan.closeSubpath()

        fill = QRadialGradient(apex, radius)
        fill.setColorAt(0.0, QColor("#163a19"))
        fill.setColorAt(0.7, QColor("#0b230e"))
        fill.setColorAt(1.0, QColor("#071808"))
        p.setPen(QPen(QColor("#3f8f45"), 1.4))
        p.setBrush(QBrush(fill))
        p.drawPath(fan)

        # range rings + labels
        p.setFont(QFont("Consolas", 6))

        for i in range(1, 5):

            r = radius * i / 4
            p.setPen(QPen(QColor(90, 200, 95, 70 if i < 4 else 120), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(apex.x() - r, apex.y() - r, r * 2, r * 2), int(start_deg * 16), int(span * 16))

            lx = apex.x() + math.sin(self.HALF_ANGLE) * r + 3
            ly = apex.y() - math.cos(self.HALF_ANGLE) * r
            p.setPen(QColor(110, 210, 110, 120))
            p.drawText(QPointF(lx, ly + 3), f"{int(self.RANGE_M * i / 4)}")

        # spokes
        p.setPen(QPen(QColor(90, 200, 95, 45), 1))

        for k in (-2, -1, 0, 1, 2):
            a = self.HALF_ANGLE * k / 2
            p.drawLine(apex, QPointF(apex.x() + math.sin(a) * radius, apex.y() - math.cos(a) * radius))

        # labels
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.setPen(QColor(150, 210, 140, 130))
        p.drawText(QRectF(screen.left() + 8, screen.top() + 4, 90, 12), Qt.AlignmentFlag.AlignLeft, "NET RADAR")

        p.setPen(QColor(150, 210, 140, 100))
        p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        p.drawText(QRectF(screen.left() + 8, screen.bottom() - 46, 70, 10), Qt.AlignmentFlag.AlignLeft, "CONTACTS")
        p.drawText(QRectF(screen.right() - 78, screen.bottom() - 46, 70, 10), Qt.AlignmentFlag.AlignRight, "RANGE")

        rnd = random.Random(314)
        for sx, sy in ((5, 5), (w - 5, 5), (5, h - 5), (w - 5, h - 5)):
            draw_screw(p, sx, sy, 2.6, rnd.uniform(0, math.pi))

        p.end()

        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(dpr)

        return pixmap

    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)

        if self._bg is None or self._bg_key != key:
            self._bg = self.build_background(dpr)
            self._bg_key = key

        painter.drawPixmap(0, 0, self._bg)

        apex, radius = self.geometry_info()
        now = time.monotonic()

        start_deg = 90 + math.degrees(self.HALF_ANGLE)
        span = -2 * math.degrees(self.HALF_ANGLE)

        # expanding pulse wave with a soft trail
        if self.wave_start is not None:

            progress = (now - self.wave_start) / self.TRAVEL

            if 0.0 <= progress <= 1.0:

                for trail, alpha in ((0.0, 210), (0.035, 90), (0.07, 40)):

                    r = radius * (progress - trail)

                    if r <= 2:
                        continue

                    a = int(alpha * (1.0 - 0.55 * progress))
                    painter.setPen(QPen(QColor(140, 255, 135, a), 2 if trail == 0 else 3))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawArc(QRectF(apex.x() - r, apex.y() - r, r * 2, r * 2), int(start_deg * 16), int(span * 16))

        # blips
        painter.setPen(Qt.PenStyle.NoPen)

        k = self.range_scale()

        for angle, dist, size, revealed in self.blips:

            if revealed is None:
                continue

            dist *= k

            if dist > 1.0:
                continue

            a = math.exp(-(now - revealed) / (self.FADE * 0.45))

            if a < 0.04:
                continue

            x = apex.x() + math.sin(angle) * radius * dist
            y = apex.y() - math.cos(angle) * radius * dist
            rb = 2.0 + 2.2 * min(1.4, size)

            painter.setBrush(QColor(80, 230, 90, int(60 * a)))
            painter.drawEllipse(QPointF(x, y), rb * 2.0, rb * 2.0)
            painter.setBrush(QColor(120, 250, 120, int(150 * a)))
            painter.drawEllipse(QPointF(x, y), rb * 1.25, rb * 1.25)
            painter.setBrush(QColor(225, 255, 215, int(255 * a)))
            painter.drawEllipse(QPointF(x, y), rb * 0.7, rb * 0.7)

        # readouts: contacts (left) and nearest range in metres (right)
        green = QColor(140, 245, 120)
        ghost = QColor(140, 245, 120, 24)

        screen_bottom = self.height() - 9
        dh = 20
        dw = 11
        sp = 3

        contacts = "--" if self.contacts < 0 else f"{min(self.contacts, 99):02d}"

        lx = 17
        draw_seven_seg(painter, lx, screen_bottom - dh - 12, dw, dh, sp, "88", ghost, digits=2)
        draw_seven_seg(painter, lx, screen_bottom - dh - 12, dw, dh, sp, contacts, green, digits=2)

        dist_text = "--" if self.nearest is None else f"{int(round(self.nearest * self.RANGE_M)):02d}"

        rx = self.width() - 17 - (2 * dw + sp) - 12
        draw_seven_seg(painter, rx, screen_bottom - dh - 12, dw, dh, sp, "88", ghost, digits=2)
        draw_seven_seg(painter, rx, screen_bottom - dh - 12, dw, dh, sp, dist_text, green, digits=2)

        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(green)
        painter.drawText(QPointF(rx + 2 * dw + sp + 3, screen_bottom - 13), "m")

        self.draw_mute_switch(painter)

        panel_dim(painter, QRectF(self.rect()).adjusted(1, 1, -1, -1), 7)


# ============================================================
# PANEL BACKGROUND (brushed / scuffed metal, plates, stencils)
# ============================================================

STENCIL_FAMILY = None


def stencil_font(size):

    global STENCIL_FAMILY

    if STENCIL_FAMILY is None:

        STENCIL_FAMILY = "Consolas"

        try:
            from PySide6.QtGui import QFontDatabase
            families = set(QFontDatabase.families())
            for name in ("Stencil", "Stencil Std", "Bahnschrift Condensed", "Bahnschrift"):
                if name in families:
                    STENCIL_FAMILY = name
                    break
        except Exception:
            pass

    font = QFont(STENCIL_FAMILY, size)
    font.setBold(STENCIL_FAMILY != "Stencil")
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)

    return font


def build_panel_background(monitor, dpr):

    W, H = monitor.width(), monitor.height()

    img = new_layer(W, H, dpr)
    img.fill(QColor("#0e0e0d"))

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    base = QLinearGradient(QPointF(0, 0), QPointF(0, H))
    base.setColorAt(0.0, QColor("#1a1a18"))
    base.setColorAt(0.5, QColor("#121211"))
    base.setColorAt(1.0, QColor("#0f0f0e"))
    p.fillRect(QRectF(0, 0, W, H), QBrush(base))

    # brushed streaks: random noise stretched horizontally
    streak = noise_image(48, 256, 74120713).scaled(
        1536, 256,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    p.setOpacity(0.075)
    p.fillRect(QRectF(0, 0, W, H), QBrush(QPixmap.fromImage(streak)))

    grain = noise_image(256, 256, 7412)
    p.setOpacity(0.03)
    p.fillRect(QRectF(0, 0, W, H), QBrush(QPixmap.fromImage(grain)))
    p.setOpacity(1.0)

    rnd = random.Random(6000)

    def scuffs(rect, count):
        p.save()
        p.setClipRect(rect)
        for _ in range(count):
            x = rnd.uniform(rect.left(), rect.right())
            y = rnd.uniform(rect.top(), rect.bottom())
            length = rnd.uniform(10, 70)
            ang = rnd.uniform(-0.5, 0.5) + (math.pi if rnd.random() < 0.5 else 0)
            path = QPainterPath(QPointF(x, y))
            path.quadTo(
                QPointF(x + math.cos(ang) * length * 0.5, y + math.sin(ang) * length * 0.5 + rnd.uniform(-6, 6)),
                QPointF(x + math.cos(ang) * length, y + math.sin(ang) * length)
            )
            light = rnd.random() < 0.6
            p.setPen(QPen(QColor(220, 215, 190, rnd.randint(8, 22)) if light else QColor(0, 0, 0, rnd.randint(30, 60)), rnd.uniform(0.6, 1.3)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        for _ in range(count // 6):
            x = rnd.uniform(rect.left(), rect.right())
            y = rnd.uniform(rect.top(), rect.bottom())
            r = rnd.uniform(8, 30)
            smudge = QRadialGradient(QPointF(x, y), r)
            smudge.setColorAt(0.0, QColor(0, 0, 0, rnd.randint(18, 35)))
            smudge.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(smudge))
            p.drawEllipse(QPointF(x, y), r, r)
        p.restore()

    scuffs(QRectF(0, 0, W, H), 90)

    def plate(rect, radius=8):
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor("#22221f"))
        grad.setColorAt(1.0, QColor("#151513"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(rect.translated(2, 3), radius, radius)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect, radius, radius)
        p.setOpacity(0.06)
        p.setBrush(QBrush(QPixmap.fromImage(streak)))
        p.drawRoundedRect(rect, radius, radius)
        p.setOpacity(1.0)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 250, 230, 26), 1))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        p.setPen(QPen(QColor(0, 0, 0, 120), 1))
        p.drawRoundedRect(rect.adjusted(1.5, 1.5, -0.5, -0.5), radius, radius)
        for sx, sy in ((rect.left() + 11, rect.top() + 11), (rect.right() - 11, rect.top() + 11),
                       (rect.left() + 11, rect.bottom() - 11), (rect.right() - 11, rect.bottom() - 11)):
            draw_screw(p, sx, sy, 4.2, rnd.uniform(0, math.pi))

    labels = []     # (rect, text, size, align, color)
    marks = []      # callables painting worn marks (logos) on the stencil layer

    def rect_of(widget, pad=0):
        top_left = widget.mapTo(monitor, QPoint(0, 0))
        return QRectF(top_left.x() - pad, top_left.y() - pad, widget.width() + 2 * pad, widget.height() + 2 * pad)

    gauges = monitor.gauges()
    names = (
        ("SYS-01", "CPU LOAD MONITOR"),
        ("SYS-02", "MEMORY BANK"),
        ("SYS-03", "GPU LOAD"),
        ("SYS-04", "THERMAL"),
    )

    for i, gauge in enumerate(gauges):

        r = rect_of(gauge, 3)
        plate(r)

        code, desc = names[i]
        labels.append((QRectF(r.left() + 24, r.top() + 22, 140, 22), code, 14, Qt.AlignmentFlag.AlignLeft, QColor("#8f8a74")))
        labels.append((QRectF(r.left() + 24, r.top() + 42, 160, 14), desc, 7, Qt.AlignmentFlag.AlignLeft, QColor("#6f6b5c")))

        if i == 0:
            labels.append((QRectF(r.left() + 24, r.bottom() - 40, 200, 14), "ASSET 07-4412", 7, Qt.AlignmentFlag.AlignLeft, QColor("#6f6b5c")))
        if i == 2:
            labels.append((QRectF(r.left() + 24, r.bottom() - 40, 200, 14), "OMORTSON 07-4412", 8, Qt.AlignmentFlag.AlignLeft, QColor("#6f6b5c")))
        if i == 1:
            labels.append((QRectF(r.right() - 224, r.bottom() - 40, 200, 14), "CORE 6100", 8, Qt.AlignmentFlag.AlignRight, QColor("#6f6b5c")))
        if i == 3:
            draw_hazard_stripe(p, QRectF(r.right() - 84, r.bottom() - 34, 54, 9))

    # info panel backing plate + AUX POWER label above the toggles
    panel = monitor.info_panel
    pr = rect_of(panel, 1)
    plate(pr, 9)

    try:
        tr = rect_of(panel.mute_toggle)
        labels.append((QRectF(pr.left() + 14, tr.top() - 19, pr.width() - 28, 14), "AUX POWER", 8, Qt.AlignmentFlag.AlignLeft, QColor("#8f8a74")))
        kb = getattr(panel, "keys_button", None)
        if kb is not None:
            kr = rect_of(kb)
            draw_hazard_stripe(p, QRectF(kr.left() - 46, kr.center().y() - 3.5, 38, 7))
        else:
            draw_hazard_stripe(p, QRectF(pr.right() - 70, tr.top() - 15, 48, 7))
    except Exception:
        pass

    # console strip: lamps, emblem plate, knobs, SLEEP switch
    strip = getattr(monitor, "console_strip", None)

    if strip is not None:

        try:
            sr = rect_of(strip)
            plate(sr, 8)

            lr = rect_of(strip.lamps)
            kr = rect_of(strip.volume_knob)
            brand = QRectF(lr.right() + 18, sr.top() + 6, kr.left() - lr.right() - 36, sr.height() - 12)

            if brand.width() > 150:
                logo_h = 22.0
                text_w = 196.0
                total = logo_h * 2.25 + 12 + text_w
                x0 = brand.center().x() - total / 2
                cy = brand.center().y()
                colour = QColor("#a39d84")
                marks.append(lambda q, x=x0 + logo_h * 1.125, y=cy, c=colour: draw_plate_emblem(q, x, y, logo_h, c))
                tx = x0 + logo_h * 2.25 + 12
                labels.append((QRectF(tx, cy - 16, text_w + 40, 18), "OMORTSON SYSTEMS", 11, Qt.AlignmentFlag.AlignLeft, QColor("#9a947c")))
                labels.append((QRectF(tx + 1, cy + 3, text_w + 40, 12), "INDUSTRIAL DIAGNOSTICS DIV.", 7, Qt.AlignmentFlag.AlignLeft, QColor("#6f6b5c")))

            cr = rect_of(strip.sleep_toggle)
            labels.append((QRectF(cr.left() - 14, cr.bottom() + 1, cr.width() + 28, 11), "SLEEP NOW [Z]", 6, Qt.AlignmentFlag.AlignCenter, QColor("#8f8a74")))
        except Exception:
            pass

    # hazard trim on the bottom band ends
    try:
        band_top = rect_of(monitor.terminal).top()
        left = rect_of(monitor.terminal).left()
        right = rect_of(monitor.tracker).right()
        draw_hazard_stripe(p, QRectF(left + 2, band_top - 8, 70, 5))
        draw_hazard_stripe(p, QRectF(right - 72, band_top - 8, 70, 5))
    except Exception:
        pass

    # fullscreen: the console sits centred in a recessed bay of panel metal
    box = getattr(monitor, "immersion_box", None)

    if box is not None:

        outside = QPainterPath()
        outside.addRect(QRectF(0, 0, W, H))
        inner = QPainterPath()
        inner.addRoundedRect(box, 10, 10)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawPath(outside.subtracted(inner))

        # recess shadow + bevel lip around the bay
        for i, alpha in enumerate((110, 70, 40, 20)):
            p.setPen(QPen(QColor(0, 0, 0, alpha), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(box.adjusted(-1.5 - i, -1.5 - i, 1.5 + i, 1.5 + i), 11 + i, 11 + i)
        p.setPen(QPen(QColor(255, 248, 225, 30), 1))
        p.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)

        # side bays: console panel hardware (lamp banks, breakers, deck plan,
        # emblem plates); rivet strips when the margins are too narrow for them
        bay_lamps = draw_side_bays(p, labels, marks, box, W, H, plate)

        if not bay_lamps:
            for x in (box.left() / 2, (box.right() + W) / 2):
                if box.left() > 40:
                    step = max(60.0, H / 12)
                    y = step / 2
                    while y < H:
                        draw_screw(p, x, y, 3.4, rnd.uniform(0, math.pi))
                        y += step

        try:
            monitor.bays_rebuilt(bay_lamps)
        except Exception:
            pass

        corners = (
            (box.left() + 7, box.top() + 7), (box.right() - 7, box.top() + 7),
            (box.left() + 7, box.bottom() - 7), (box.right() - 7, box.bottom() - 7),
        )

    else:

        corners = ((7, 7), (W - 7, 7), (7, H - 7), (W - 7, H - 7))

        try:
            monitor.bays_rebuilt([])
        except Exception:
            pass

    # window (or bay) corner screws
    for sx, sy in corners:
        draw_screw(p, sx, sy, 3.6, rnd.uniform(0, math.pi))

    p.end()

    # stenciled, worn labels on their own layer
    layer = new_layer(W, H, dpr)
    q = QPainter(layer)
    q.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    for rect, text, size, align, color in labels:
        q.setFont(stencil_font(size))
        q.setPen(color)
        q.drawText(rect, align | Qt.AlignmentFlag.AlignVCenter, text)

    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    for mark in marks:
        try:
            mark(q)
        except Exception:
            pass

    # wear: knock out random speckles
    wear = noise_image(128, 128, 924, QImage.Format.Format_Alpha8)
    q.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    q.setOpacity(0.55)
    q.fillRect(QRectF(0, 0, W, H), QBrush(QPixmap.fromImage(wear)))
    q.end()

    p = QPainter(img)
    p.drawImage(QPointF(0, 0), layer)
    p.end()

    pixmap = QPixmap.fromImage(img)
    pixmap.setDevicePixelRatio(dpr)

    return pixmap


# ============================================================
# GPU HISTORY GRAPH
# ============================================================

class GPUHistoryGraph(QWidget):

    def __init__(
        self,
        monitor
    ):

        super().__init__()

        self.monitor = monitor

        self.setMinimumSize(
            720,
            430
        )

        self.setStyleSheet(
            "background-color: #090908;"
        )

    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        w = self.width()
        h = self.height()

        # ----------------------------------------------------
        # BACKGROUND
        # ----------------------------------------------------

        painter.fillRect(
            self.rect(),
            QColor("#090908")
        )

        # ----------------------------------------------------
        # GRAPH AREA
        # ----------------------------------------------------

        left = 70
        right = 30
        top = 60
        bottom = 55

        graph_width = (
            w -
            left -
            right
        )

        graph_height = (
            h -
            top -
            bottom
        )

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        painter.setFont(
            QFont(
                "Consolas",
                16,
                QFont.Weight.Bold
            )
        )

        painter.setPen(
            QColor("#bdb69a")
        )

        painter.drawText(
            30,
            34,
            "GPU PERFORMANCE HISTORY"
        )

        painter.setFont(
            QFont(
                "Consolas",
                9
            )
        )

        painter.setPen(
            QColor("#6e6b5e")
        )

        painter.drawText(
            30,
            h - 18,
            "HISTORY WINDOW: 60 SECONDS"
        )

        # ----------------------------------------------------
        # GRID
        # ----------------------------------------------------

        painter.setPen(
            QPen(
                QColor("#292922"),
                1
            )
        )

        for value in range(
            0,
            101,
            20
        ):

            y = (
                top +
                graph_height -
                (
                    value / 100
                ) * graph_height
            )

            painter.drawLine(
                left,
                int(y),
                w - right,
                int(y)
            )

            painter.setFont(
                QFont(
                    "Consolas",
                    9
                )
            )

            painter.setPen(
                QColor("#6f6b5e")
            )

            painter.drawText(
                20,
                int(y + 4),
                f"{value:3d}"
            )

            painter.setPen(
                QPen(
                    QColor("#292922"),
                    1
                )
            )

        # ----------------------------------------------------
        # VERTICAL GRID
        # ----------------------------------------------------

        for second in range(
            0,
            61,
            10
        ):

            x = (
                left +
                graph_width *
                second / 60
            )

            painter.drawLine(
                int(x),
                top,
                int(x),
                top + graph_height
            )

        # ----------------------------------------------------
        # WARNING ZONE
        # ----------------------------------------------------

        warning_y = (
            top +
            graph_height -
            0.80 *
            graph_height
        )

        painter.fillRect(
            QRectF(
                left,
                top,
                graph_width,
                warning_y - top
            ),
            QColor(
                120,
                20,
                15,
                22
            )
        )

        # ----------------------------------------------------
        # GPU LOAD GRAPH
        # ----------------------------------------------------

        values = list(
            self.monitor.gpu_history
        )

        if len(values) > 1:

            path = QPainterPath()

            for index, value in enumerate(
                values
            ):

                x = (
                    left +
                    graph_width *
                    index /
                    (len(values) - 1)
                )

                y = (
                    top +
                    graph_height -
                    (
                        value / 100
                    ) * graph_height
                )

                if index == 0:

                    path.moveTo(
                        x,
                        y
                    )

                else:

                    path.lineTo(
                        x,
                        y
                    )

            painter.setPen(
                QPen(
                    QColor("#83b56d"),
                    3
                )
            )

            painter.drawPath(
                path
            )

        # ----------------------------------------------------
        # CURRENT VALUE
        # ----------------------------------------------------

        current_gpu = (
            self.monitor.gpu_usage
        )

        painter.setFont(
            QFont(
                "Consolas",
                22,
                QFont.Weight.Bold
            )
        )

        painter.setPen(
            QColor("#83b56d")
        )

        painter.drawText(
            w - 170,
            35,
            f"{current_gpu:.1f}%"
        )


# ============================================================
# GPU DIAGNOSTIC WINDOW
# ============================================================

class GPUDiagnosticWindow(QWidget):

    def __init__(
        self,
        monitor
    ):

        super().__init__()

        self.monitor = monitor

        self.setWindowTitle(
            "OMORTSON // GPU DIAGNOSTICS"
        )

        self.setMinimumSize(
            850,
            560
        )

        self.setStyleSheet("""
            QWidget {
                background-color: #090908;
                color: #b8b29a;
            }
        """)

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            14,
            14,
            14,
            14
        )

        self.graph = GPUHistoryGraph(
            monitor
        )

        layout.addWidget(
            self.graph
        )

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.graph.update
        )

        self.timer.start(250)

        decorate_window(self)

    # --------------------------------------------------------

    def closeEvent(self, event):

        self.timer.stop()

        event.accept()


# ============================================================
# GENERIC HISTORY GRAPH
# ============================================================

class HistoryGraph(QWidget):

    """
    60-second history graph in the same style as the GPU graph.

    series: list of (label, history_attribute_name, color)
    mode:   "percent" (fixed 0-100 scale) or "rate" (auto-scaled bytes/s)
    """

    def __init__(
        self,
        monitor,
        title,
        series,
        mode="percent",
        warning_start=80
    ):

        super().__init__()

        self.monitor = monitor
        self.title = title
        self.series = series
        self.mode = mode
        self.warning_start = warning_start

        self.setMinimumSize(
            720,
            430
        )

    # --------------------------------------------------------

    @staticmethod
    def nice_ceiling(value):

        if value <= 0:
            return 1024

        exponent = 0

        while (
            value >= 1024 ** (exponent + 1)
            and exponent < 4
        ):
            exponent += 1

        unit = 1024 ** exponent
        mantissa = value / unit

        for step in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000):

            if mantissa <= step:
                return step * unit

        return 1024 * unit

    # --------------------------------------------------------

    def format_value(self, value):

        if self.mode == "percent":
            return f"{value:.1f}%"

        return self.monitor.format_speed(value)

    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        w = self.width()
        h = self.height()

        painter.fillRect(
            self.rect(),
            QColor("#090908")
        )

        left = 95 if self.mode == "rate" else 70
        right = 30
        top = 70
        bottom = 55

        graph_width = w - left - right
        graph_height = h - top - bottom

        histories = [
            list(getattr(self.monitor, attr))
            for _, attr, _ in self.series
        ]

        # ----------------------------------------------------
        # SCALE
        # ----------------------------------------------------

        if self.mode == "percent":

            scale = 100.0

        else:

            peak = max(
                (max(values) for values in histories if values),
                default=0
            )

            scale = float(
                self.nice_ceiling(peak * 1.15)
            )

        def y_for(value):

            value = max(0.0, min(scale, value))

            return (
                top +
                graph_height -
                (value / scale) * graph_height
            )

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        painter.setFont(
            QFont("Consolas", 16, QFont.Weight.Bold)
        )

        painter.setPen(QColor("#bdb69a"))

        painter.drawText(30, 34, self.title)

        painter.setFont(QFont("Consolas", 9))

        painter.setPen(QColor("#6e6b5e"))

        painter.drawText(
            30,
            h - 18,
            "HISTORY WINDOW: 60 SECONDS"
        )

        # ----------------------------------------------------
        # LEGEND / CURRENT VALUES
        # ----------------------------------------------------

        painter.setFont(
            QFont("Consolas", 12, QFont.Weight.Bold)
        )

        legend_x = 30

        for (label, _, color), values in zip(
            self.series,
            histories
        ):

            current = values[-1] if values else 0.0

            text = f"{label} {self.format_value(current)}"

            painter.setPen(QColor(color))

            painter.drawText(legend_x, 58, text)

            legend_x += (
                painter.fontMetrics()
                .horizontalAdvance(text) + 36
            )

        # ----------------------------------------------------
        # GRID
        # ----------------------------------------------------

        painter.setFont(QFont("Consolas", 9))

        for step in range(0, 6):

            fraction = step / 5

            y = (
                top +
                graph_height -
                fraction * graph_height
            )

            painter.setPen(QPen(QColor("#292922"), 1))

            painter.drawLine(
                left,
                int(y),
                w - right,
                int(y)
            )

            if self.mode == "percent":
                label = f"{int(fraction * 100):3d}"
            else:
                label = self.monitor.format_speed(
                    scale * fraction
                )

            painter.setPen(QColor("#6f6b5e"))

            painter.drawText(
                QRectF(4, y - 8, left - 12, 16),
                Qt.AlignmentFlag.AlignRight |
                Qt.AlignmentFlag.AlignVCenter,
                label
            )

        painter.setPen(QPen(QColor("#292922"), 1))

        for second in range(0, 61, 10):

            x = left + graph_width * second / 60

            painter.drawLine(
                int(x),
                top,
                int(x),
                top + graph_height
            )

        # ----------------------------------------------------
        # WARNING ZONE (percent graphs only)
        # ----------------------------------------------------

        if self.mode == "percent":

            warning_y = y_for(self.warning_start)

            painter.fillRect(
                QRectF(
                    left,
                    top,
                    graph_width,
                    warning_y - top
                ),
                QColor(120, 20, 15, 22)
            )

        # ----------------------------------------------------
        # LINES
        # ----------------------------------------------------

        for (_, _, color), values in zip(
            self.series,
            histories
        ):

            if len(values) < 2:
                continue

            path = QPainterPath()

            for index, value in enumerate(values):

                x = (
                    left +
                    graph_width * index /
                    (len(values) - 1)
                )

                y = y_for(value)

                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            painter.setPen(
                QPen(QColor(color), 3)
            )

            painter.drawPath(path)


# ============================================================
# GENERIC DIAGNOSTIC WINDOW
# ============================================================

class HistoryDiagnosticWindow(QWidget):

    def __init__(
        self,
        monitor,
        window_title,
        graph_title,
        series,
        mode="percent"
    ):

        super().__init__()

        self.setWindowTitle(window_title)

        self.setMinimumSize(850, 560)

        self.setStyleSheet("""
            QWidget {
                background-color: #090908;
                color: #b8b29a;
            }
        """)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(14, 14, 14, 14)

        self.graph = HistoryGraph(
            monitor,
            graph_title,
            series,
            mode
        )

        layout.addWidget(self.graph)

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.graph.update
        )

        self.timer.start(250)

        decorate_window(self)

    # --------------------------------------------------------

    def closeEvent(self, event):

        self.timer.stop()

        event.accept()


# ============================================================
# SYSTEM INFORMATION
# ============================================================

def get_cpu_name():

    if platform.system() == "Windows":

        try:

            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            )

            name, _ = winreg.QueryValueEx(
                key,
                "ProcessorNameString"
            )

            winreg.CloseKey(key)

            return " ".join(name.split())

        except Exception:
            pass

    return platform.processor() or "UNKNOWN CPU"


class SystemInfoView(QWidget):

    def __init__(self, monitor):

        super().__init__()

        self.monitor = monitor

        self.setMinimumSize(720, 470)

        # Static facts, gathered once

        self.cpu_name = get_cpu_name()

        self.physical_cores = psutil.cpu_count(logical=False)
        self.logical_cores = psutil.cpu_count(logical=True)

        self.boot_time = datetime.datetime.fromtimestamp(
            psutil.boot_time()
        )

        self.rows = []

        self.refresh()

    # --------------------------------------------------------

    def refresh(self):

        memory = psutil.virtual_memory()

        system_drive = (
            os.environ.get("SystemDrive", "C:") + "\\"
            if platform.system() == "Windows"
            else "/"
        )

        try:

            disk = psutil.disk_usage(system_drive)

            disk_text = (
                f"{disk.used / 1024 ** 3:.0f} / "
                f"{disk.total / 1024 ** 3:.0f} GB "
                f"({disk.percent:.0f}% USED)"
            )

        except Exception:

            disk_text = "UNAVAILABLE"

        try:

            frequency = psutil.cpu_freq()

            frequency_text = (
                f"{frequency.current:.0f} MHz"
                if frequency else "UNAVAILABLE"
            )

        except Exception:

            frequency_text = "UNAVAILABLE"

        uptime = int(time.time() - psutil.boot_time())

        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60

        if self.monitor.gpu_total_vram:
            vram_text = f"{self.monitor.gpu_total_vram} MB"
        else:
            vram_text = "UNAVAILABLE"

        self.rows = [
            ("HOST", platform.node()),
            ("OPERATING SYSTEM", f"{platform.system()} {platform.release()}"),
            ("VERSION", platform.version()),
            ("ARCHITECTURE", platform.machine()),
            None,
            ("PROCESSOR", self.cpu_name),
            ("CORES / THREADS", f"{self.physical_cores} / {self.logical_cores}"),
            ("CPU CLOCK", frequency_text),
            ("MEMORY", f"{memory.used / 1024 ** 3:.1f} / {memory.total / 1024 ** 3:.1f} GB"),
            ("GRAPHICS", self.monitor.gpu_name),
            ("VRAM", vram_text),
            ("SYSTEM DRIVE", f"{system_drive}  {disk_text}"),
            None,
            ("LAST BOOT", self.boot_time.strftime("%Y-%m-%d %H:%M:%S")),
            ("UPTIME", f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"),
            ("PROCESSES", str(len(psutil.pids()))),
            ("PYTHON", platform.python_version()),
        ]

        self.update()

    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        painter.fillRect(
            self.rect(),
            QColor("#090908")
        )

        painter.setFont(
            QFont("Consolas", 16, QFont.Weight.Bold)
        )

        painter.setPen(QColor("#bdb69a"))

        painter.drawText(30, 34, "SYSTEM INFORMATION")

        row_height = 22
        y = 70
        label_width = 190

        for row in self.rows:

            if row is None:

                painter.setPen(QPen(QColor("#292922"), 1))

                painter.drawLine(
                    30,
                    y + 6,
                    self.width() - 30,
                    y + 6
                )

                y += 14

                continue

            label, value = row

            painter.setFont(
                QFont("Consolas", 10, QFont.Weight.Bold)
            )

            painter.setPen(QColor("#918b73"))

            painter.drawText(
                QRectF(30, y, label_width, row_height),
                Qt.AlignmentFlag.AlignLeft |
                Qt.AlignmentFlag.AlignVCenter,
                label
            )

            painter.setFont(QFont("Consolas", 10))

            painter.setPen(QColor("#83b56d"))

            painter.drawText(
                QRectF(
                    30 + label_width,
                    y,
                    self.width() - label_width - 60,
                    row_height
                ),
                Qt.AlignmentFlag.AlignLeft |
                Qt.AlignmentFlag.AlignVCenter,
                str(value)
            )

            y += row_height


class SystemInfoWindow(QWidget):

    def __init__(self, monitor):

        super().__init__()

        self.setWindowTitle(
            "OMORTSON // SYSTEM INFORMATION"
        )

        self.setMinimumSize(780, 540)

        self.setStyleSheet("""
            QWidget {
                background-color: #090908;
                color: #b8b29a;
            }
        """)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(14, 14, 14, 14)

        self.view = SystemInfoView(monitor)

        layout.addWidget(self.view)

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.view.refresh
        )

        self.timer.start(1000)

        decorate_window(self)

    # --------------------------------------------------------

    def closeEvent(self, event):

        self.timer.stop()

        event.accept()


# ============================================================
# INFO PANEL
# ============================================================

class InfoPanel(QWidget):

    def __init__(
        self,
        monitor
    ):

        super().__init__()

        self.monitor = monitor

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            8,
            8,
            8,
            8
        )

        layout.setSpacing(
            6
        )

        self.cpu_button = StatusButton(
            "CPU",
            "Detecting..."
        )

        self.memory_button = StatusButton(
            "MEMORY",
            "Detecting..."
        )

        self.gpu_button = StatusButton(
            "GPU",
            "Detecting..."
        )

        self.vram_button = StatusButton(
            "VRAM",
            "Detecting..."
        )

        self.temp_button = StatusButton(
            "GPU TEMP",
            "Detecting..."
        )

        self.os_button = StatusButton(
            "OPERATING SYSTEM",
            platform.system()
        )

        self.uptime_button = StatusButton(
            "UPTIME",
            "00:00:00"
        )

        self.disk_button = StatusButton(
            "DISK",
            "R 0 B/s\nW 0 B/s"
        )

        self.network_button = StatusButton(
            "NETWORK",
            "↓ 0 B/s\n↑ 0 B/s"
        )

        buttons = [
            self.cpu_button,
            self.memory_button,
            self.gpu_button,
            self.vram_button,
            self.temp_button,
            self.os_button,
            self.uptime_button,
            self.disk_button,
            self.network_button
        ]

        for button in buttons:

            layout.addWidget(
                button
            )

        # little phosphor oscilloscope fed by the virtual mixer
        self.scope = AudioScope()
        layout.addWidget(self.scope, 1)

        # L / R needle VU meters fed by the same mixer window
        self.vu = VUMeters()
        self.scope.vu = self.vu
        layout.addWidget(self.vu, 0)

        # room for the stenciled AUX POWER label above the switches
        aux_row = QHBoxLayout()
        aux_row.setContentsMargins(0, 0, 3, 0)
        aux_row.addStretch(1)
        self.keys_button = KeyHelpButton()
        aux_row.addWidget(self.keys_button, 0)
        layout.addLayout(aux_row)

        # ----------------------------------------------------
        # FX TOGGLES (wired up by OmortsonMonitor)
        # ----------------------------------------------------

        self.mute_toggle = PanelToggle(
            "MUTE",
            on_color="#e0563c",
            shortcut_hint="M"
        )

        self.ambient_toggle = PanelToggle(
            "AMBIENT",
            shortcut_hint="H"
        )

        self.crt_toggle = PanelToggle(
            "CRT",
            shortcut_hint="C"
        )

        self.boot_toggle = PanelToggle(
            "BOOT",
            shortcut_hint="B"
        )

        toggle_row = QHBoxLayout()

        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(5)

        for toggle in (self.mute_toggle, self.ambient_toggle, self.crt_toggle, self.boot_toggle):
            toggle_row.addWidget(toggle, 1)

        layout.addLayout(toggle_row)

        # ----------------------------------------------------
        # CLICK ACTIONS
        # ----------------------------------------------------

        self.gpu_button.clicked.connect(
            self.open_gpu_diagnostics
        )

        self.temp_button.clicked.connect(
            self.open_gpu_diagnostics
        )

        # VRAM lives on the GPU: same GPU diagnostics screen
        self.vram_button.clicked.connect(
            self.open_gpu_diagnostics
        )

        self.gpu_window = None

        # Other diagnostic screens, opened on demand

        self.diagnostic_windows = {}

        self.cpu_button.clicked.connect(
            self.open_cpu_window
        )

        self.memory_button.clicked.connect(
            self.open_memory_window
        )

        self.disk_button.clicked.connect(
            lambda: self.open_window(
                "disk",
                lambda: HistoryDiagnosticWindow(
                    self.monitor,
                    "OMORTSON // DISK DIAGNOSTICS",
                    "DISK THROUGHPUT HISTORY",
                    [
                        ("READ", "disk_read_history", "#83b56d"),
                        ("WRITE", "disk_write_history", "#d0a24a")
                    ],
                    mode="rate"
                )
            )
        )

        self.network_button.clicked.connect(
            lambda: self.open_window(
                "network",
                lambda: HistoryDiagnosticWindow(
                    self.monitor,
                    "OMORTSON // NETWORK DIAGNOSTICS",
                    "NETWORK TRAFFIC HISTORY",
                    [
                        ("DOWN", "network_download_history", "#83b56d"),
                        ("UP", "network_upload_history", "#d0a24a")
                    ],
                    mode="rate"
                )
            )
        )

        open_system_info = lambda: self.open_window(
            "system",
            lambda: SystemInfoWindow(self.monitor)
        )

        self.os_button.clicked.connect(open_system_info)
        self.uptime_button.clicked.connect(open_system_info)

    # --------------------------------------------------------

    def open_cpu_window(self):

        self.open_window(
            "cpu",
            lambda: HistoryDiagnosticWindow(
                self.monitor,
                "OMORTSON // CPU DIAGNOSTICS",
                "CPU LOAD HISTORY",
                [("CPU", "cpu_history", "#83b56d")]
            )
        )

    def open_memory_window(self):

        self.open_window(
            "memory",
            lambda: HistoryDiagnosticWindow(
                self.monitor,
                "OMORTSON // MEMORY DIAGNOSTICS",
                "MEMORY USAGE HISTORY",
                [("RAM", "ram_history", "#83b56d")]
            )
        )

    # --------------------------------------------------------

    def open_window(self, key, factory):

        play_sound("open")

        terminal_post(f"ACCESSING {key.upper()} DIAGNOSTICS", "event")

        window = self.diagnostic_windows.get(key)

        if window is None or not window.isVisible():

            window = factory()

            self.diagnostic_windows[key] = window

            window.show()

        else:

            window.raise_()
            window.activateWindow()

    # --------------------------------------------------------

    def close_all_windows(self):

        windows = list(self.diagnostic_windows.values())

        if self.gpu_window is not None:
            windows.append(self.gpu_window)

        for window in windows:

            try:
                window.close()
            except Exception:
                pass

    # --------------------------------------------------------

    def open_gpu_diagnostics(self):

        play_sound("open")

        terminal_post("ACCESSING GPU DIAGNOSTICS", "event")

        if (
            self.gpu_window is None
            or not self.gpu_window.isVisible()
        ):

            self.gpu_window = (
                GPUDiagnosticWindow(
                    self.monitor
                )
            )

            self.gpu_window.show()

        else:

            self.gpu_window.raise_()
            self.gpu_window.activateWindow()


# ============================================================
# MAIN MONITOR
# ============================================================

# ============================================================
# CONSOLE HARDWARE (round 6): knobs, warning lamps, VU meters,
# deepsleep screen, fullscreen side bays, emblem marks.
# Everything static is pre-rendered; only things that change are
# repainted, and only their own small rectangles.
# ============================================================

AMBIENT_EVENTS = ("door_open", "door_close", "steam", "cat_meow", "cat_purr", "cat_hiss")

LAMP_RGB = {
    "green": (120, 255, 110),
    "amber": (255, 170, 40),
    "red": (255, 58, 38),
}


def lamp_sprite(color, radius, halo, dpr, lit=True):

    """Incandescent lamp lens: lit = hot filament behind coloured glass, unlit = dark tinted glass."""

    size = int(math.ceil(2 * halo))
    img = new_layer(size, size, dpr)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    c = QPointF(size / 2, size / 2)
    r, g, b = LAMP_RGB[color]

    if lit:
        spill = QRadialGradient(c, halo)
        spill.setColorAt(0.0, QColor(r, g, b, 110))
        spill.setColorAt(min(0.95, radius / halo), QColor(r, g, b, 55))
        spill.setColorAt(1.0, QColor(r, g, b, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(spill))
        p.drawEllipse(c, halo, halo)

        lens = QRadialGradient(QPointF(c.x() - radius * 0.15, c.y() - radius * 0.2), radius * 1.05)
        lens.setColorAt(0.0, QColor(255, 248, 222))
        lens.setColorAt(0.28, QColor(min(255, r + 70), min(255, g + 60), min(255, b + 40)))
        lens.setColorAt(0.75, QColor(r, g, b))
        lens.setColorAt(1.0, QColor(int(r * 0.5), int(g * 0.5), int(b * 0.5)))
        p.setBrush(QBrush(lens))
        p.drawEllipse(c, radius, radius)
    else:
        lens = QRadialGradient(QPointF(c.x() - radius * 0.2, c.y() - radius * 0.25), radius * 1.1)
        lens.setColorAt(0.0, QColor(int(r * 0.34), int(g * 0.34), int(b * 0.34)))
        lens.setColorAt(0.7, QColor(int(r * 0.15), int(g * 0.15), int(b * 0.15)))
        lens.setColorAt(1.0, QColor(10, 9, 8))
        p.setPen(QPen(QColor(0, 0, 0, 200), 1))
        p.setBrush(QBrush(lens))
        p.drawEllipse(c, radius, radius)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 80 if lit else 36))
    p.drawEllipse(QPointF(c.x() - radius * 0.32, c.y() - radius * 0.38), radius * 0.30, radius * 0.19)

    p.end()

    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)

    return pm


def blit_centred(painter, pixmap, centre):

    s = pixmap.width() / max(0.01, pixmap.devicePixelRatio())
    painter.drawPixmap(QPointF(centre.x() - s / 2, centre.y() - s / 2), pixmap)


def draw_lamp_bezel(p, c, r):

    """Knurled chrome bezel around a lamp lens (drawn into static layers)."""

    ring = QRadialGradient(QPointF(c.x() - r * 0.3, c.y() - r * 0.4), r * 1.6)
    ring.setColorAt(0.0, QColor("#a29e90"))
    ring.setColorAt(0.65, QColor("#55524a"))
    ring.setColorAt(1.0, QColor("#1c1b18"))
    p.setPen(QPen(QColor(0, 0, 0, 170), 1))
    p.setBrush(QBrush(ring))
    p.drawEllipse(c, r, r)


def draw_plate_emblem(p, cx, cy, h, color):

    """Omortson plate emblem: a hex nut between two slotted bars."""

    w = h * 2.25
    sw, sh = int(w + 6), int(h + 6)
    ss = 3                                         # supersampled, then drawn smooth

    img = QImage(sw * ss, sh * ss, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)

    q = QPainter(img)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    q.scale(ss, ss)

    ox, oy = 3, 3
    mx, my = ox + w / 2, oy + h / 2
    rr = h * 0.5
    hexa = QPolygonF([QPointF(mx + rr * math.cos(math.radians(60 * k + 30)), my + rr * math.sin(math.radians(60 * k + 30))) for k in range(6)])
    q.setPen(Qt.PenStyle.NoPen)
    q.setBrush(color)
    q.drawPolygon(hexa)
    bar_h = h * 0.34
    q.drawRoundedRect(QRectF(ox, my - bar_h / 2, w * 0.5 - rr * 0.95, bar_h), 1.5, 1.5)
    q.drawRoundedRect(QRectF(mx + rr * 0.95, my - bar_h / 2, w * 0.5 - rr * 0.95, bar_h), 1.5, 1.5)

    q.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    q.setBrush(QColor(0, 0, 0, 255))
    q.drawEllipse(QPointF(mx, my), rr * 0.42, rr * 0.42)
    gap = max(0.9, h * 0.07)
    for k in range(1, 4):
        x = ox + (w * 0.5 - rr) * k / 4
        q.fillRect(QRectF(x - gap / 2, 0, gap, sh), QColor(0, 0, 0, 255))
        q.fillRect(QRectF(w + ox - (x - ox) - gap / 2, 0, gap, sh), QColor(0, 0, 0, 255))
    q.end()

    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(QRectF(cx - sw / 2, cy - sh / 2, sw, sh), img)
    p.restore()


# ------------------------------------------------------------
# ROTARY KNOB
# ------------------------------------------------------------

class RotaryKnob(QWidget):

    """
    Bakelite knob on a machined skirt with a printed tick ring. Drag
    up/down or use the wheel; each step is a soft detent click. Double-
    click resets. Repaints only when the value (or label) changes.
    """

    value_changed = Signal(int)
    committed = Signal(int)

    PX_PER_STEP = 8
    SWEEP = 270.0

    def __init__(self, label, lo, hi, step, default, unit="%"):

        super().__init__()

        self.label = label
        self.lo, self.hi, self.step = lo, hi, step
        self.default = default
        self.unit = unit
        self.value = default

        self._drag = None
        self._wheel_acc = 0
        self._last_detent = 0.0
        self.show_value_until = 0.0
        self.detents = 0
        self.repaints = 0

        self._bg = None
        self._bg_key = None

        self.setFixedSize(66, 60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{label}  //  DRAG OR WHEEL  //  DOUBLE-CLICK RESETS")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.setInterval(700)
        self._commit_timer.timeout.connect(self._commit)

        self._label_timer = QTimer(self)
        self._label_timer.setSingleShot(True)
        self._label_timer.timeout.connect(lambda: self.update(self.label_rect().toAlignedRect()))

    # --------------------------------------------------------

    def snap(self, v):

        v = round((float(v) - self.lo) / self.step) * self.step + self.lo
        return int(max(self.lo, min(self.hi, v)))

    def set_value(self, v, emit=True, sound=True):

        v = self.snap(v)

        if v == self.value:
            return False

        self.value = v

        if sound:
            self._detent()

        self.update()

        if emit:
            self.value_changed.emit(v)

        return True

    def _detent(self):

        self.detents += 1
        now = time.monotonic()

        if now - self._last_detent >= 0.035:
            self._last_detent = now
            play_sound("detent")

    def fraction(self):

        return (self.value - self.lo) / max(1, self.hi - self.lo)

    def text(self):

        return f"{self.value} M" if self.unit == "m" else f"{self.value}%"

    def centre(self):

        return QPointF(33, 23)

    def label_rect(self):

        return QRectF(0, 46, self.width(), 13)

    # --------------------------------------------------------

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = (event.position().y(), self.value)
            self._show_value()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if self._drag is None:
            return

        y0, v0 = self._drag
        steps = int((y0 - event.position().y()) / self.PX_PER_STEP)

        if self.set_value(v0 + steps * self.step):
            self._show_value()

    def mouseReleaseEvent(self, event):

        if self._drag is not None:
            self._drag = None
            self._show_value()
            self._commit()

    def mouseDoubleClickEvent(self, event):

        self._drag = None
        self.set_value(self.default)
        self._show_value()
        self._commit()
        event.accept()

    def wheelEvent(self, event):

        self._wheel_acc += event.angleDelta().y()
        n = int(self._wheel_acc / 120)

        if n:
            self._wheel_acc -= n * 120
            self.set_value(self.value + n * self.step)

        self._show_value()
        self._commit_timer.start()
        event.accept()

    def _show_value(self):

        self.show_value_until = time.monotonic() + 0.9
        self._label_timer.start(950)
        self.update(self.label_rect().toAlignedRect())

    def _commit(self):

        self._commit_timer.stop()
        self.committed.emit(self.value)

    # --------------------------------------------------------

    def build_bg(self, dpr):

        img = new_layer(self.width(), self.height(), dpr)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = self.centre()

        # printed tick ring
        for i in range(11):
            a = math.radians(-135 + 27 * i)
            major = i in (0, 5, 10)
            r0, r1 = (19.0, 23.5) if major else (19.5, 22.0)
            p.setPen(QPen(QColor(205, 198, 170, 200 if major else 130), 1.3 if major else 1.0))
            p.drawLine(
                QPointF(c.x() + math.sin(a) * r0, c.y() - math.cos(a) * r0),
                QPointF(c.x() + math.sin(a) * r1, c.y() - math.cos(a) * r1)
            )

        # shadow + machined skirt
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawEllipse(QPointF(c.x() + 1.2, c.y() + 2.0), 17, 17)

        skirt = QLinearGradient(QPointF(c.x() - 17, c.y() - 17), QPointF(c.x() + 17, c.y() + 17))
        skirt.setColorAt(0.0, QColor("#b9b5a8"))
        skirt.setColorAt(0.45, QColor("#6d6a61"))
        skirt.setColorAt(1.0, QColor("#2a2925"))
        p.setBrush(QBrush(skirt))
        p.setPen(QPen(QColor(0, 0, 0, 180), 1))
        p.drawEllipse(c, 16.5, 16.5)

        # knurled bakelite body
        body = QRadialGradient(QPointF(c.x() - 4, c.y() - 5), 16)
        body.setColorAt(0.0, QColor("#4a4440"))
        body.setColorAt(0.55, QColor("#1f1c1a"))
        body.setColorAt(1.0, QColor("#0b0a09"))
        p.setBrush(QBrush(body))
        p.setPen(QPen(QColor(0, 0, 0, 220), 1))
        p.drawEllipse(c, 13.0, 13.0)

        for i in range(28):
            a = 2 * math.pi * i / 28
            light = 0.5 + 0.5 * math.cos(a + 2.3)
            p.setPen(QPen(QColor(150, 140, 125, int(25 + 70 * light)), 1.0))
            p.drawLine(
                QPointF(c.x() + math.cos(a) * 11.0, c.y() + math.sin(a) * 11.0),
                QPointF(c.x() + math.cos(a) * 13.0, c.y() + math.sin(a) * 13.0)
            )

        cap = QRadialGradient(QPointF(c.x() - 3, c.y() - 4), 11)
        cap.setColorAt(0.0, QColor("#3d3834"))
        cap.setColorAt(1.0, QColor("#151312"))
        p.setBrush(QBrush(cap))
        p.setPen(QPen(QColor(255, 245, 220, 22), 1))
        p.drawEllipse(c, 10.0, 10.0)

        p.end()

        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(dpr)

        return pm

    def paintEvent(self, event):

        self.repaints += 1

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)

        if self._bg is None or self._bg_key != key:
            self._bg = self.build_bg(dpr)
            self._bg_key = key

        painter.drawPixmap(0, 0, self._bg)

        c = self.centre()
        a = math.radians(-135 + self.SWEEP * self.fraction())
        sx, sy = math.sin(a), -math.cos(a)

        painter.setPen(QPen(QColor(0, 0, 0, 150), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(c.x() + sx * 4, c.y() + sy * 4 + 0.6), QPointF(c.x() + sx * 12, c.y() + sy * 12 + 0.6))
        painter.setPen(QPen(QColor("#ece3c4"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(c.x() + sx * 4, c.y() + sy * 4), QPointF(c.x() + sx * 12, c.y() + sy * 12))

        showing = self._drag is not None or time.monotonic() < self.show_value_until

        if showing:
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.setPen(QColor(255, 186, 80))
            painter.drawText(self.label_rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        else:
            painter.setFont(stencil_font(7))
            painter.setPen(QColor("#a39d84"))
            painter.drawText(self.label_rect(), Qt.AlignmentFlag.AlignCenter, self.label)

        panel_dim(painter, QRectF(self.rect()), 6)


# ------------------------------------------------------------
# WARNING LAMPS (THERMAL / CORE / MEM / LINK)
# ------------------------------------------------------------

class WarningLamps(QWidget):

    """
    Four incandescent indicator lamps behind coloured glass. Warm-up
    and cool-down fades run on the shared 60 fps clock only while a
    lamp is changing; a lit filament gets a very slight, low-rate
    flicker (~1-2 Hz, one small rect). Otherwise nothing repaints.
    """

    NAMES = ("THERMAL", "CORE", "MEM", "LINK")
    HOME = {"THERMAL": "red", "CORE": "amber", "MEM": "amber", "LINK": "green"}
    CELL = 60
    LENS = 10.0
    HALO = 21.0
    WARM = 0.20
    COOL = 0.32

    def __init__(self):

        super().__init__()

        self.setFixedSize(self.CELL * len(self.NAMES), 58)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.state = {n: None for n in self.NAMES}
        self.level = {n: {c: 0.0 for c in LAMP_RGB} for n in self.NAMES}
        self.flicker = {n: 1.0 for n in self.NAMES}
        self.repaints = 0

        self._bg = None
        self._bg_key = None
        self._sprites = {}

        self.flicker_timer = ManagedTimer(self, 300, self._flicker_tick)

    def centre(self, i):

        return QPointF(self.CELL * i + self.CELL / 2, 21)

    def lamp_rect(self, i):

        c = self.centre(i)
        h = self.HALO

        return QRectF(c.x() - h, c.y() - h, 2 * h, 2 * h).toAlignedRect().adjusted(-1, -1, 1, 1)

    # --------------------------------------------------------

    def set_state(self, name, color):

        if name not in self.state or self.state[name] == color:
            return False

        self.state[name] = color
        fx_hub().clock60.add((id(self), "fade"), self._fade)

        if any(self.state.values()):
            self.flicker_timer.run()
        else:
            self.flicker_timer.halt()

        return True

    def _fade(self, dt):

        moving = False

        for i, n in enumerate(self.NAMES):

            changed = False

            for c, v in self.level[n].items():

                target = 1.0 if self.state[n] == c else 0.0

                if v == target:
                    continue

                if target > v:
                    v = min(target, v + dt / self.WARM)
                else:
                    v = max(target, v - dt / self.COOL)

                self.level[n][c] = v
                changed = True
                moving = moving or v != target

            if changed:
                self.update(self.lamp_rect(i))

        return moving

    def _flicker_tick(self):

        for i, n in enumerate(self.NAMES):

            if self.state[n] is None:
                self.flicker[n] = 1.0
                continue

            if random.random() < 0.6:
                continue

            f = 1.0 - min(0.07, abs(random.gauss(0.0, 0.028)))

            if abs(f - self.flicker[n]) >= 0.012:
                self.flicker[n] = f
                self.update(self.lamp_rect(i))

    # --------------------------------------------------------

    def build_bg(self, dpr):

        img = new_layer(self.width(), self.height(), dpr)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        for i, n in enumerate(self.NAMES):

            c = self.centre(i)

            draw_lamp_bezel(p, c, self.LENS + 5.0)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#0b0a09"))
            p.drawEllipse(c, self.LENS + 1.4, self.LENS + 1.4)

            p.setFont(stencil_font(7))
            p.setPen(QColor("#a39d84"))
            p.drawText(QRectF(c.x() - 30, 42, 60, 14), Qt.AlignmentFlag.AlignCenter, n)

        p.end()

        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(dpr)

        return pm

    def sprites(self, dpr):

        if self._sprites.get("dpr") != dpr:
            self._sprites = {"dpr": dpr}
            for c in LAMP_RGB:
                self._sprites[c] = lamp_sprite(c, self.LENS, self.HALO, dpr, True)
            for n in self.NAMES:
                self._sprites["off_" + n] = lamp_sprite(self.HOME[n], self.LENS, self.LENS + 1, dpr, False)

        return self._sprites

    def paintEvent(self, event):

        self.repaints += 1

        painter = QPainter(self)
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)

        if self._bg is None or self._bg_key != key:
            self._bg = self.build_bg(dpr)
            self._bg_key = key

        painter.drawPixmap(0, 0, self._bg)

        sp = self.sprites(dpr)
        r = event.rect()

        for i, n in enumerate(self.NAMES):

            if not self.lamp_rect(i).intersects(r):
                continue

            c = self.centre(i)
            blit_centred(painter, sp["off_" + n], c)

            for col, v in self.level[n].items():
                if v > 0.003:
                    e = v * v * (3 - 2 * v)        # a filament heats up non-linearly
                    painter.setOpacity(e * self.flicker[n])
                    blit_centred(painter, sp[col], c)

            painter.setOpacity(1.0)

        panel_dim(painter, QRectF(self.rect()), 6)


# ------------------------------------------------------------
# VU METERS (L / R) fed by the virtual mixer
# ------------------------------------------------------------

class VUMeters(QWidget):

    """
    Two small needle VU meters under the scope. The scope's mixer
    window feeds them (no extra mixing); fast attack, slower release.
    They animate only while a needle is moving and rest at zero when
    silent or muted. The faces follow the gauge palette.
    """

    ATTACK = 0.03
    RELEASE = 0.30
    REF = 0.07              # mixer RMS that reads 0 VU
    DB_LO = -20.0
    DB_HI = 3.0
    HALF_SWEEP = 46.0
    STEP = 0.05             # needle ballistics run at ~20 fps (an inertial needle needs no more)
    MIN_PX = 0.6            # sub-pixel needle wobble is not redrawn

    def __init__(self):

        super().__init__()

        self.setFixedHeight(42)
        self.setMinimumWidth(120)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.pos = [0.0, 0.0]
        self.target = [0.0, 0.0]
        self._drawn = [0.0, 0.0]
        self.max_pos = 0.0
        self.repaints = 0
        self._acc = 0.0
        self._rvar = 1.0

        self._face = None
        self._face_key = None

    # --------------------------------------------------------

    def meter_rect(self, i):

        w = (self.width() - 6) / 2

        return QRectF(i * (w + 6), 0, w, self.height())

    def face_rect(self, i):

        return self.meter_rect(i).adjusted(4, 4, -4, -4)

    def pivot(self, i):

        f = self.face_rect(i)
        piv = QPointF(f.center().x(), f.bottom() + f.height() * 0.62)

        return piv, piv.y() - f.top() - 9

    def angle(self, frac):

        return math.radians(-self.HALF_SWEEP + 2 * self.HALF_SWEEP * frac)

    def frac_for_db(self, db):

        return (db - self.DB_LO) / (self.DB_HI - self.DB_LO)

    def to_frac(self, rms):

        if rms <= 1e-6:
            return 0.0

        db = 20 * math.log10(rms / self.REF)

        return max(0.0, min(1.06, self.frac_for_db(db)))

    # --------------------------------------------------------

    def feed(self, pts):

        if not pts:
            self.target = [0.0, 0.0]
        else:
            n = len(pts)
            left = math.sqrt(sum(a * a for a, _ in pts) / n)
            # a slow random drift between channels (not per-frame noise, which kept a
            # steady hum redrawing the needles all the time)
            self._rvar = min(1.04, max(0.96, self._rvar + random.uniform(-0.004, 0.004)))
            right = math.sqrt(sum(b * b for _, b in pts) / n) * self._rvar
            self.target = [self.to_frac(left), self.to_frac(right)]

        if any(abs(t - p) > 0.004 for t, p in zip(self.target, self.pos)):
            fx_hub().clock60.add((id(self), "vu"), self._anim)

    def rest(self):

        self.target = [0.0, 0.0]
        self.pos = [0.0, 0.0]

        fx_hub().clock60.remove((id(self), "vu"))

        if self._drawn != [0.0, 0.0]:
            self._drawn = [0.0, 0.0]
            self.update()

    def _anim(self, dt):

        self._acc += dt

        if self._acc < self.STEP:
            return True

        dt, self._acc = self._acc, 0.0
        keep = False

        for i in (0, 1):

            d = self.target[i] - self.pos[i]

            if abs(d) <= 0.004:
                self.pos[i] = self.target[i]
            else:
                tau = self.ATTACK if d > 0 else self.RELEASE
                self.pos[i] += d * (1.0 - math.exp(-dt / tau))
                keep = True

            self.max_pos = max(self.max_pos, self.pos[i])

            _, radius = self.pivot(i)
            moved_px = abs(self.pos[i] - self._drawn[i]) * math.radians(2 * self.HALF_SWEEP) * radius

            if moved_px >= self.MIN_PX or (self.pos[i] == 0.0 and self._drawn[i] != 0.0):
                self._drawn[i] = self.pos[i]
                self.update(self.meter_rect(i).toAlignedRect())

        return keep

    # --------------------------------------------------------

    def palette_changed(self):

        self._face = None
        self.update()

    def build_face(self, dpr):

        pal = gauge_palette()

        img = new_layer(self.width(), self.height(), dpr)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        for i in (0, 1):

            outer = self.meter_rect(i).adjusted(0.5, 0.5, -0.5, -0.5)

            bezel = QLinearGradient(outer.topLeft(), outer.bottomLeft())
            bezel.setColorAt(0.0, QColor("#3c3b35"))
            bezel.setColorAt(1.0, QColor("#141412"))
            p.setBrush(QBrush(bezel))
            p.setPen(QPen(QColor("#6f6c60"), 1.2))
            p.drawRoundedRect(outer, 5, 5)

            face = self.face_rect(i)
            grad = QLinearGradient(face.topLeft(), face.bottomLeft())
            for stop, colour in pal["face"]:
                grad.setColorAt(stop, QColor(colour))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(pal["face_edge"]), 1))
            p.drawRoundedRect(face, 3, 3)

            p.save()
            p.setClipRect(face.adjusted(1, 1, -1, -1))

            piv, rad = self.pivot(i)
            arc_rect = QRectF(piv.x() - rad, piv.y() - rad, 2 * rad, 2 * rad)

            def qt_angle(frac):
                return 90.0 + self.HALF_SWEEP - 2 * self.HALF_SWEEP * frac

            zero = self.frac_for_db(0.0)

            p.setPen(QPen(QColor(pal["arc"]), 1.1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(arc_rect, int(qt_angle(0.0) * 16), int((qt_angle(zero) - qt_angle(0.0)) * 16))

            p.setPen(QPen(QColor(pal["red"]), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            red_rect = arc_rect.adjusted(-1.5, -1.5, 1.5, 1.5)
            p.drawArc(red_rect, int(qt_angle(zero) * 16), int((qt_angle(1.0) - qt_angle(zero)) * 16))

            p.setFont(QFont("Consolas", 5, QFont.Weight.Bold))

            for db, label in ((-20, "20"), (-10, "10"), (-7, None), (-5, "5"), (-3, None), (-2, None),
                              (-1, None), (0, "0"), (1, None), (2, None), (3, "+3")):
                a = self.angle(self.frac_for_db(db))
                sx, sy = math.sin(a), -math.cos(a)
                major = label is not None
                colour = QColor(pal["red"]) if db > 0 else QColor(pal["tick"])
                p.setPen(QPen(colour, 1.1 if major else 0.8))
                r0 = rad - (4.5 if major else 3.0)
                p.drawLine(QPointF(piv.x() + sx * r0, piv.y() + sy * r0), QPointF(piv.x() + sx * rad, piv.y() + sy * rad))
                if major:
                    tx, ty = piv.x() + sx * (rad + 5.5), piv.y() + sy * (rad + 5.5)
                    p.setPen(QColor(pal["red"]) if db >= 0 else QColor(pal["num"]))
                    p.drawText(QRectF(tx - 9, ty - 4, 18, 8), Qt.AlignmentFlag.AlignCenter, label)

            p.restore()

            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QColor(pal["title"]))
            p.drawText(QRectF(face.left(), face.bottom() - 11, face.width(), 10), Qt.AlignmentFlag.AlignCenter, "VU")
            p.drawText(QRectF(face.left() + 4, face.top() + 2, 10, 9), Qt.AlignmentFlag.AlignLeft, "LR"[i])

        p.end()

        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(dpr)

        return pm

    def paintEvent(self, event):

        self.repaints += 1

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr, PALETTE_STATE["name"])

        if self._face is None or self._face_key != key:
            self._face = self.build_face(dpr)
            self._face_key = key

        painter.drawPixmap(0, 0, self._face)

        pal = gauge_palette()
        needle = QColor(pal["needle_lit"])

        for i in (0, 1):

            face = self.face_rect(i)

            if not face.toAlignedRect().intersects(event.rect()):
                continue

            piv, rad = self.pivot(i)
            a = self.angle(min(1.02, self._drawn[i]))     # the needle pegs at the +3 stop
            sx, sy = math.sin(a), -math.cos(a)

            painter.save()
            painter.setClipRect(face.adjusted(1, 1, -1, -1))
            painter.setPen(QPen(QColor(0, 0, 0, 55), 1.6))
            painter.drawLine(QPointF(piv.x() + sx * rad * 0.55 + 1, piv.y() + sy * rad * 0.55 + 1),
                             QPointF(piv.x() + sx * (rad + 1) + 1, piv.y() + sy * (rad + 1) + 1))
            painter.setPen(QPen(needle, 1.2))
            painter.drawLine(QPointF(piv.x() + sx * rad * 0.55, piv.y() + sy * rad * 0.55),
                             QPointF(piv.x() + sx * (rad + 1), piv.y() + sy * (rad + 1)))
            painter.restore()

            glare = QLinearGradient(face.topLeft(), face.bottomLeft())
            glare.setColorAt(0.0, QColor(255, 255, 255, 30))
            glare.setColorAt(0.45, QColor(255, 255, 255, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glare))
            painter.drawRoundedRect(face.adjusted(1, 1, -1, -1), 3, 3)

        panel_dim(painter, QRectF(self.rect()), 5)


# ------------------------------------------------------------
# CONSOLE STRIP (between the gauges and the terminal band)
# ------------------------------------------------------------

class ConsoleStrip(QWidget):

    """Lamps, the emblem plate (painted by the panel background), knobs and the SLEEP switch."""

    def __init__(self):

        super().__init__()

        self.setFixedHeight(64)

        self.lamps = WarningLamps()
        self.volume_knob = RotaryKnob("VOLUME", 0, 125, 5, 100, "%")
        self.crt_knob = RotaryKnob("CRT", 0, 150, 10, 100, "%")
        self.range_knob = RotaryKnob("RANGE", 20, 100, 10, 50, "m")

        self.sleep_toggle = PanelToggle("SLEEP", on_color="#86e0e6", shortcut_hint="S")
        self.sleep_toggle.setFixedWidth(64)
        self.sleep_toggle.setToolTip("SLEEP: AUTO DEEP SLEEP AFTER 10 MIN  [S]   //   SLEEP NOW  [Z]")

        row = QHBoxLayout(self)
        row.setContentsMargins(22, 2, 22, 2)
        row.setSpacing(4)

        row.addWidget(self.lamps, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)

        for knob in self.knobs():
            row.addWidget(knob, 0, Qt.AlignmentFlag.AlignVCenter)

        row.addSpacing(12)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(self.sleep_toggle)
        col.addStretch(1)
        row.addLayout(col)

    def knobs(self):

        return [self.volume_knob, self.crt_knob, self.range_knob]


# ------------------------------------------------------------
# DEEPSLEEP SCREEN
# ------------------------------------------------------------

class SleepScreen(QWidget):

    """
    Deep sleep: an opaque, dark blue-green standby screen covering
    the console (under the CRT overlay so it keeps the scanlines). The
    rest of the app is paused; this screen runs its own 5 fps timer
    and repaints only the breathing line, the vital trace and (once a
    second) the clock.
    """

    TICK_MS = 200
    BREATH_PERIOD = 9.0
    PULSE_PERIOD = 4.2
    TEAL = (120, 222, 204)

    def __init__(self, host):

        super().__init__(host)

        self.host = host
        self.t0 = time.monotonic()
        self.fade = 0.0
        self.frames = 0
        self._last_second = None
        self._layers = None
        self._layers_key = None

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.timer = QTimer(self)
        self.timer.setInterval(self.TICK_MS)
        self.timer.timeout.connect(self._tick)

        self.hide()

    # --------------------------------------------------------

    def start(self):

        self.setGeometry(self.host.rect())
        self.t0 = time.monotonic()
        self.fade = 0.0
        self.show()
        self.raise_()

        ov = getattr(self.host, "crt_overlay", None)
        if ov is not None:
            ov.raise_()

        self.set_running(True)
        self.update()

    def stop(self):

        self.timer.stop()
        self.hide()

    def set_running(self, running):

        if running and self.isVisible():
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()

    def resizeEvent(self, event):

        super().resizeEvent(event)
        self._layers = None

    # --------------------------------------------------------

    def rects(self):

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2

        return {
            "title": QRectF(0, cy - 92, W, 36),
            "breath": QRectF(cx - 240, cy - 40, 480, 22),
            "vital": QRectF(cx - 150, cy + 4, 300, 56),
            "clock": QRectF(cx - 260, cy + 84, 520, 24),
        }

    def _tick(self):

        self.frames += 1
        t = time.monotonic() - self.t0

        if self.fade < 1.0:
            self.fade = min(1.0, t / 1.6)
            self.update()
            return

        rr = self.rects()
        self.update(rr["breath"].toAlignedRect().adjusted(-2, -2, 2, 2))
        self.update(rr["vital"].toAlignedRect().adjusted(-2, -2, 2, 2))

        sec = int(time.time())

        if sec != self._last_second:
            self._last_second = sec
            self.update(rr["clock"].toAlignedRect())

    # --------------------------------------------------------

    def build_layers(self, dpr):

        W, H = self.width(), self.height()
        rr = self.rects()
        teal = QColor(*self.TEAL)

        base = new_layer(W, H, dpr)
        p = QPainter(base)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QRadialGradient(QPointF(W / 2, H * 0.45), max(W, H) * 0.7)
        bg.setColorAt(0.0, QColor("#072325"))
        bg.setColorAt(0.55, QColor("#03131a"))
        bg.setColorAt(1.0, QColor("#010608"))
        p.fillRect(QRectF(0, 0, W, H), QBrush(bg))

        p.setPen(QPen(QColor(110, 220, 200, 10), 1))
        for x in range(0, W, 48):
            p.drawLine(QPointF(x + 0.5, 0), QPointF(x + 0.5, H))
        for y in range(0, H, 48):
            p.drawLine(QPointF(0, y + 0.5), QPointF(W, y + 0.5))
        p.end()

        text = new_layer(W, H, dpr)
        q = QPainter(text)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        draw_plate_emblem(q, W / 2, rr["title"].top() - 52, 22, QColor(110, 210, 192, 150))

        head = QFont("Consolas", 18)
        head.setBold(True)
        head.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        q.setFont(head)
        glow = QColor(teal)
        glow.setAlpha(55)
        q.setPen(glow)
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            q.drawText(rr["title"].translated(ox, oy), Qt.AlignmentFlag.AlignCenter, "DEEP SLEEP  //  SYSTEM STATUS: STANDBY")
        q.setPen(teal)
        q.drawText(rr["title"], Qt.AlignmentFlag.AlignCenter, "DEEP SLEEP  //  SYSTEM STATUS: STANDBY")

        small = QFont("Consolas", 8)
        small.setBold(True)
        q.setFont(small)
        q.setPen(QColor(110, 210, 192, 120))
        q.drawText(QRectF(0, rr["title"].bottom() + 2, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "UNIT 07-4412  //  CORE 6100 MONITORING  //  STANDBY")

        v = rr["vital"]
        q.setPen(QPen(QColor(110, 210, 192, 45), 1))
        q.setBrush(Qt.BrushStyle.NoBrush)
        q.drawRoundedRect(v.adjusted(-0.5, -0.5, 0.5, 0.5), 3, 3)
        q.setPen(QColor(110, 210, 192, 90))
        q.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        q.drawText(QRectF(v.left() + 5, v.top() + 2, v.width() - 10, 10), Qt.AlignmentFlag.AlignLeft, "VITALS // SYSTEM")
        q.drawText(QRectF(v.left() + 5, v.top() + 2, v.width() - 10, 10), Qt.AlignmentFlag.AlignRight, "14 BPM")

        q.setFont(small)
        q.setPen(QColor(110, 210, 192, 70))
        q.drawText(QRectF(0, H - 46, W, 16), Qt.AlignmentFlag.AlignCenter, "ANY INPUT TO RESUME")
        q.end()

        out = []
        for img in (base, text):
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(dpr)
            out.append(pm)

        return out

    @staticmethod
    def ekg(phase):

        """One slow stasis heartbeat (phase 0..1): small P, sharp QRS, broad T."""

        y = 0.12 * math.exp(-((phase - 0.10) / 0.025) ** 2)
        y -= 0.18 * math.exp(-((phase - 0.175) / 0.008) ** 2)
        y += 1.00 * math.exp(-((phase - 0.19) / 0.010) ** 2)
        y -= 0.30 * math.exp(-((phase - 0.205) / 0.010) ** 2)
        y += 0.22 * math.exp(-((phase - 0.36) / 0.045) ** 2)

        return y

    def paintEvent(self, event):

        painter = QPainter(self)
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)

        if self._layers is None or self._layers_key != key:
            self._layers = self.build_layers(dpr)
            self._layers_key = key

        r = event.rect()
        src = QRectF(r.x() * dpr, r.y() * dpr, r.width() * dpr, r.height() * dpr)

        painter.drawPixmap(QRectF(r), self._layers[0], src)

        f = self.fade
        if f <= 0.001:
            return

        painter.setOpacity(f)
        painter.drawPixmap(QRectF(r), self._layers[1], src)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rr = self.rects()
        t = time.monotonic() - self.t0
        R, G, B = self.TEAL

        # slow breathing line
        br = rr["breath"]
        if br.toAlignedRect().intersects(r):
            b = 0.5 - 0.5 * math.cos(2 * math.pi * t / self.BREATH_PERIOD)
            line = QLinearGradient(br.topLeft(), br.topRight())
            line.setColorAt(0.0, QColor(R, G, B, 0))
            line.setColorAt(0.5, QColor(R, G, B, int(50 + 150 * b)))
            line.setColorAt(1.0, QColor(R, G, B, 0))
            half = 0.6 + 1.6 * b
            painter.fillRect(QRectF(br.left(), br.center().y() - half, br.width(), 2 * half), QBrush(line))
            soft = QLinearGradient(br.topLeft(), br.topRight())
            soft.setColorAt(0.0, QColor(R, G, B, 0))
            soft.setColorAt(0.5, QColor(R, G, B, int(26 * b)))
            soft.setColorAt(1.0, QColor(R, G, B, 0))
            painter.fillRect(QRectF(br.left(), br.center().y() - 7, br.width(), 14), QBrush(soft))

        # tiny vital trace (6 s window, slow stasis pulse)
        v = rr["vital"]
        if v.toAlignedRect().intersects(r):
            inner = v.adjusted(6, 14, -6, -6)
            n = 110
            span = 6.0
            poly = QPolygonF()
            for k in range(n + 1):
                tt = t - span + span * k / n
                ph = (tt % self.PULSE_PERIOD) / self.PULSE_PERIOD
                y = inner.bottom() - 6 - self.ekg(ph) * (inner.height() - 10)
                poly.append(QPointF(inner.left() + inner.width() * k / n, y))
            painter.setPen(QPen(QColor(R, G, B, 45), 3.0))
            painter.drawPolyline(poly)
            painter.setPen(QPen(QColor(R + 40 if R < 215 else 255, 255, 235, 200), 1.1))
            painter.drawPolyline(poly)

        # station-time clock
        c = rr["clock"]
        if c.toAlignedRect().intersects(r):
            now = datetime.datetime.now()
            text = f"STATION TIME  2122.{now.month:02d}.{now.day:02d}  //  {now:%H:%M:%S}"
            font = QFont("Consolas", 11)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(R, G, B, 210))
            painter.drawText(c, Qt.AlignmentFlag.AlignCenter, text)


# ------------------------------------------------------------
# FULLSCREEN SIDE BAYS: physical console console hardware
# ------------------------------------------------------------

BAY_LAMP_R = 4.4
BAY_HALO = 11.0


def draw_breaker(p, c, on, label, labels):

    """Chunky toggle/breaker switch: base plate, collar, metal bat lever (static)."""

    base = QRectF(c.x() - 13, c.y() - 20, 26, 40)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 110))
    p.drawRoundedRect(base.translated(1.5, 2), 3, 3)

    grad = QLinearGradient(base.topLeft(), base.bottomRight())
    grad.setColorAt(0.0, QColor("#3a3933"))
    grad.setColorAt(1.0, QColor("#1a1a17"))
    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor(255, 248, 225, 30), 1))
    p.drawRoundedRect(base, 3, 3)

    for sy in (base.top() + 5, base.bottom() - 5):
        draw_screw(p, base.center().x(), sy, 2.0, 0.6)

    # lever: the bat points up (ON) or down (OFF) from the collar
    direction = -1 if on else 1
    tip = QPointF(c.x(), c.y() + direction * 15)
    p.setPen(QPen(QColor(0, 0, 0, 120), 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(c.x() + 1, c.y() + 1.5), QPointF(tip.x() + 1, tip.y() + 1.5))
    bat = QLinearGradient(QPointF(c.x() - 3, 0), QPointF(c.x() + 3, 0))
    bat.setColorAt(0.0, QColor("#d9d5c8"))
    bat.setColorAt(0.5, QColor("#8f8b80"))
    bat.setColorAt(1.0, QColor("#4a4842"))
    p.setPen(QPen(QBrush(bat), 4.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(c, tip)

    collar = QRadialGradient(QPointF(c.x() - 1.5, c.y() - 2), 6.5)
    collar.setColorAt(0.0, QColor("#bdb9ab"))
    collar.setColorAt(1.0, QColor("#33322d"))
    p.setBrush(QBrush(collar))
    p.setPen(QPen(QColor(0, 0, 0, 170), 1))
    p.drawEllipse(c, 5.5, 5.5)

    labels.append((QRectF(c.x() - 26, base.bottom() + 2, 52, 11), label, 6, Qt.AlignmentFlag.AlignCenter, QColor("#8f8a74")))


def draw_bay_lamp(p, c, color):

    """Unlit small panel lamp (static); the lit state is a sprite on top."""

    draw_lamp_bezel(p, c, BAY_LAMP_R + 2.6)
    r, g, b = LAMP_RGB[color]
    lens = QRadialGradient(QPointF(c.x() - 1.2, c.y() - 1.4), BAY_LAMP_R * 1.2)
    lens.setColorAt(0.0, QColor(int(r * 0.32), int(g * 0.32), int(b * 0.32)))
    lens.setColorAt(1.0, QColor(10, 9, 8))
    p.setPen(QPen(QColor(0, 0, 0, 200), 0.8))
    p.setBrush(QBrush(lens))
    p.drawEllipse(c, BAY_LAMP_R, BAY_LAMP_R)


def draw_side_bays(p, labels, marks, box, W, H, plate):

    """
    Fills the fullscreen margins beside the console with console
    panel hardware. Returns the lamp list [(centre, colour), ...] used
    by the sparse blinker. Everything else here is static.
    """

    lamps = []
    gap = 18.0
    rnd = random.Random(1979)

    left_w = box.left() - 2 * gap
    right_w = W - box.right() - 2 * gap

    if min(left_w, right_w) < 110:
        return lamps

    top, bottom = box.top(), box.bottom()
    stencil = QColor("#8f8a74")
    faint = QColor("#6f6b5c")

    def stack(x, w, heights):
        free = (bottom - top) - sum(heights)
        g = max(10.0, free / (len(heights) + 1)) if free > 0 else 10.0
        y = top + g * 0.6
        out = []
        for h in heights:
            out.append(QRectF(x, y, w, h))
            y += h + g
        return out

    def header(r, code, desc):
        plate(r, 7)
        labels.append((QRectF(r.left() + 20, r.top() + 10, r.width() - 40, 20), code, 12, Qt.AlignmentFlag.AlignLeft, stencil))
        labels.append((QRectF(r.left() + 20, r.top() + 30, r.width() - 40, 12), desc, 6, Qt.AlignmentFlag.AlignLeft, faint))

    def lamp_bank(r, title, rows, colours):
        plate(r, 7)
        labels.append((QRectF(r.left() + 20, r.top() + 8, r.width() - 40, 12), title, 7, Qt.AlignmentFlag.AlignLeft, stencil))
        cols = max(3, min(5, int((r.width() - 30) // 30)))
        x0 = r.left() + (r.width() - (cols - 1) * 30) / 2
        y0 = r.top() + 36
        dy = (r.height() - 68) / max(1, rows - 1) if rows > 1 else 0
        for j in range(rows):
            for i in range(cols):
                c = QPointF(x0 + i * 30, y0 + j * dy)
                colour = colours[(i + j * cols) % len(colours)] if rnd.random() > 0.12 else "red"
                draw_bay_lamp(p, c, colour)
                lamps.append((c, colour))
                labels.append((QRectF(c.x() - 12, c.y() + 6, 24, 9), f"{'ABCDEFGHJK'[j]}{i + 1}", 5, Qt.AlignmentFlag.AlignCenter, faint))

    def breakers(r, title, rows_of_labels):
        plate(r, 7)
        labels.append((QRectF(r.left() + 20, r.top() + 8, r.width() - 40, 12), title, 7, Qt.AlignmentFlag.AlignLeft, stencil))
        n_rows = len(rows_of_labels)
        dy = (r.height() - 40) / n_rows
        for j, names in enumerate(rows_of_labels):
            n = len(names)
            dx = (r.width() - 40) / n
            for i, name in enumerate(names):
                c = QPointF(r.left() + 20 + dx * (i + 0.5), r.top() + 32 + dy * j + dy * 0.38)
                draw_breaker(p, c, rnd.random() < 0.7, name, labels)

    def emblem_plate(r, line2):
        plate(r, 7)
        cx = r.center().x()
        marks.append(lambda q, cx=cx, y=r.top() + 30: draw_plate_emblem(q, cx, y, 20, QColor("#a8a084")))
        labels.append((QRectF(r.left() + 10, r.top() + 50, r.width() - 20, 14), "OMORTSON SYSTEMS", 8, Qt.AlignmentFlag.AlignCenter, stencil))
        labels.append((QRectF(r.left() + 10, r.top() + 66, r.width() - 20, 12), line2, 6, Qt.AlignmentFlag.AlignCenter, faint))

    # ---------------- left bay: core terminal logic + breakers
    lx = gap
    r_head, r_bank, r_brk, r_wy = stack(lx, left_w, (52, 318, 196, 96))
    header(r_head, "CORE", "6100 SERIES  //  LOGIC STATUS")
    lamp_bank(r_bank, "LOGIC BANK", 8, ("amber", "green", "amber", "amber", "green"))
    breakers(r_brk, "AUX BREAKERS", (("COOL", "LIFE", "GRAV"), ("NAV", "COMM", "AUX")))
    emblem_plate(r_wy, "ASSET 07-4412")

    # ---------------- right bay: deck schematic + life support
    rx = box.right() + gap
    r_head2, r_deck, r_life, r_brk2, r_wy2 = stack(rx, right_w, (52, 300, 118, 108, 96))
    header(r_head2, "OMORTSON", "UNIT 07-4412  //  DECKS")

    plate(r_deck, 7)
    labels.append((QRectF(r_deck.left() + 20, r_deck.top() + 8, r_deck.width() - 40, 12), "DECK SCHEMATIC", 7, Qt.AlignmentFlag.AlignLeft, stencil))
    eng = r_deck.adjusted(16, 28, -16, -16)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 70))
    p.drawRoundedRect(eng, 4, 4)
    ink = QColor(212, 202, 160, 120)
    p.setPen(QPen(ink, 1.1))
    p.setBrush(Qt.BrushStyle.NoBrush)

    decks = (
        ("DECK A", (("BRIDGE", 0.42), ("CORE", 0.58))),
        ("DECK B", (("NAV", 0.30), ("MESS", 0.34), ("AIRLOCK", 0.36))),
        ("DECK C", (("ENGINE", 0.55), ("CARGO", 0.45))),
    )
    dh = (eng.height() - 24) / 3
    for k, (deck, rooms) in enumerate(decks):
        band = QRectF(eng.left() + 10 + k * 6, eng.top() + 12 + k * dh, eng.width() - 20 - k * 12, dh - 14)
        labels.append((QRectF(band.left(), band.top() - 1, band.width(), 10), deck, 6, Qt.AlignmentFlag.AlignLeft, stencil))
        hull = band.adjusted(0, 11, 0, 0)
        p.setPen(QPen(ink, 1.1))
        p.drawRoundedRect(hull, 5, 5)
        x = hull.left()
        for name, share in rooms:
            w = hull.width() * share
            cell = QRectF(x, hull.top(), w, hull.height())
            if x > hull.left():
                p.setPen(QPen(ink, 0.9))
                p.drawLine(QPointF(x, hull.top() + 3), QPointF(x, hull.bottom() - 3))
            if name == "AIRLOCK":
                p.save()
                p.setClipRect(cell.adjusted(3, 3, -3, -3))
                p.setPen(QPen(QColor(212, 202, 160, 45), 1))
                s = cell.left() - cell.height()
                while s < cell.right():
                    p.drawLine(QPointF(s, cell.bottom()), QPointF(s + cell.height(), cell.top()))
                    s += 6
                p.restore()
            labels.append((cell.adjusted(2, 0, -2, 0), name, 6, Qt.AlignmentFlag.AlignCenter, QColor("#a39d84")))
            x += w
        # deck position lamp at the hull end
        c = QPointF(hull.right() - 9, hull.top() + 9)
        draw_bay_lamp(p, c, "amber")
        lamps.append((c, "amber"))
        if k < 2:
            p.setPen(QPen(QColor(212, 202, 160, 60), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(hull.left() + 14, hull.bottom()), QPointF(hull.left() + 20, hull.bottom() + 14))

    lamp_bank(r_life, "LIFE SUPPORT", 2, ("green", "green", "amber"))
    breakers(r_brk2, "DECK POWER", (("DECK A", "DECK B", "DECK C"),))
    emblem_plate(r_wy2, "INDUSTRIAL DIAGNOSTICS DIV.")

    return lamps


HELP_SECTIONS = (
    ("AUX POWER", (
        ("M", "MUTE AUDIO OUTPUT"),
        ("H", "AMBIENT HUM + STATION NOISES"),
        ("C", "CRT FILTER"),
        ("B", "BOOT SEQUENCE"),
        ("S", "SLEEP: AUTO DEEP SLEEP AFTER 10 MIN"),
    )),
    ("DISPLAY", (
        ("P", "CYCLE GAUGE PALETTE"),
        ("F11", "FULL IMMERSION (FULLSCREEN)"),
        ("ESC", "EXIT FULLSCREEN"),
        ("F1 / ?", "THIS COMMAND REFERENCE"),
    )),
    ("OVERRIDES", (
        ("Z", "DEEP SLEEP NOW (ANY INPUT RESUMES)"),
        ("CTRL+SHIFT+A", "ALARM DRILL (PREVIEW)"),
        ("CTRL+SHIFT+Q", "ARCHIVE TRANSMISSION"),
        ("CTRL+SHIFT+J", "SUMMON THE STATION CAT"),
    )),
    ("MANUAL CONTROL", (
        ("CLICK GAUGE", "TAP THE GLASS"),
        ("2x CLICK GAUGE", "OPEN DIAGNOSTICS"),
        ("CLICK PANEL KEY", "OPEN DIAGNOSTICS"),
        ("2x CLICK METAL", "TOGGLE FULLSCREEN"),
        ("DRAG / WHEEL KNOB", "VOLUME \u00b7 CRT INTENSITY \u00b7 RADAR RANGE"),
        ("2x CLICK KNOB", "RESET KNOB TO DEFAULT"),
    )),
)


class KeyHelpButton(QPushButton):

    """Small stenciled "[?] KEYS" tab that opens the command reference."""

    def __init__(self):

        super().__init__()

        self.hover = 0.0
        self._hover_target = 0.0

        self.setFixedSize(66, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("COMMAND REFERENCE  [F1 / ?]")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0px; }")
        self.pressed.connect(lambda: play_sound("click"))

    def enterEvent(self, event):

        start_hover_fade(self, 1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):

        start_hover_fade(self, 0.0)
        super().leaveEvent(event)

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        h = self.hover
        down = self.isDown()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        painter.setPen(QPen(lerp_color(QColor("#5c5a4f"), QColor("#a9a287"), h), 1))
        painter.setBrush(QColor(0, 0, 0, 120 if down else 70))
        painter.drawRoundedRect(rect, 3, 3)

        painter.translate(0, 1 if down else 0)
        painter.setFont(stencil_font(7))
        painter.setPen(lerp_color(QColor("#8f8a74"), QColor("#e2dbbd"), h))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "[?] KEYS")

        painter.translate(0, -1 if down else 0)
        panel_dim(painter, rect, 3)


class HelpOverlay(QWidget):

    """
    core terminal command reference card. Lives under the CRT overlay so it
    gets the scanlines and flicker; any key or click dismisses it. The
    whole card is pre-rendered once per size, so the 60 fps CRT repaints
    only cost a blit while it is open.
    """

    GREEN = QColor(125, 255, 140)
    DIM = QColor(78, 190, 96)
    KEY = QColor(205, 255, 200)

    def __init__(self, host):

        super().__init__(host)

        self.host = host
        self._cache = None
        self._key = None
        self.opened_count = 0

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()

    # --------------------------------------------------------

    def open(self):

        self.setGeometry(self.host.rect())
        self.show()
        self.raise_()

        overlay = getattr(self.host, "crt_overlay", None)
        if overlay is not None:
            overlay.raise_()

        try:
            self.host.raise_()
            self.host.activateWindow()
        except Exception:
            pass

        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.grabKeyboard()
        self.opened_count += 1
        play_sound("click")

    def dismiss(self):

        if not self.isVisible():
            return

        self.releaseKeyboard()
        self.hide()
        play_sound("click")

        try:
            self.host.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:
            pass

    # --------------------------------------------------------

    def event(self, event):

        # swallow every shortcut while open: the key goes to keyPressEvent
        if event.type() == QEvent.Type.ShortcutOverride:
            event.accept()
            return True

        return super().event(event)

    def keyPressEvent(self, event):

        event.accept()

        if event.key() in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return          # wait for the real key of a combination

        self.dismiss()

    def mousePressEvent(self, event):

        event.accept()
        self.dismiss()

    def mouseDoubleClickEvent(self, event):

        event.accept()

    def resizeEvent(self, event):

        super().resizeEvent(event)
        self._cache = None

    def hideEvent(self, event):

        self.releaseKeyboard()
        super().hideEvent(event)

    # --------------------------------------------------------

    def card_rect(self):

        rows = sum(len(items) for _, items in HELP_SECTIONS)
        height = 40 + 48 + len(HELP_SECTIONS) * 26 + rows * 21 + 50
        width = 620

        w = min(width, self.width() - 40)
        h = min(height, self.height() - 40)

        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def build(self, dpr):

        W, H = self.width(), self.height()

        img = new_layer(W, H, dpr)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # dim the console behind the card
        p.fillRect(QRectF(0, 0, W, H), QColor(0, 0, 0, 170))

        card = self.card_rect()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawRoundedRect(card.adjusted(-2, 0, 6, 9), 12, 12)

        bezel = QLinearGradient(card.topLeft(), card.bottomLeft())
        bezel.setColorAt(0.0, QColor("#403f38"))
        bezel.setColorAt(0.5, QColor("#25251f"))
        bezel.setColorAt(1.0, QColor("#121210"))
        p.setBrush(QBrush(bezel))
        p.setPen(QPen(QColor("#77735f"), 1.5))
        p.drawRoundedRect(card, 11, 11)

        for sx, sy in ((card.left() + 10, card.top() + 10), (card.right() - 10, card.top() + 10),
                       (card.left() + 10, card.bottom() - 10), (card.right() - 10, card.bottom() - 10)):
            draw_screw(p, sx, sy, 3.6, 0.7)

        glass = card.adjusted(20, 20, -20, -20)

        screen = QRadialGradient(glass.center(), glass.width() * 0.62)
        screen.setColorAt(0.0, QColor("#0c2111"))
        screen.setColorAt(0.75, QColor("#061209"))
        screen.setColorAt(1.0, QColor("#020604"))
        p.setBrush(QBrush(screen))
        p.setPen(QPen(QColor(0, 0, 0, 220), 2))
        p.drawRoundedRect(glass, 8, 8)

        # text on its own layer so it can glow
        text = new_layer(W, H, dpr)
        q = QPainter(text)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        x0 = glass.left() + 22
        x1 = glass.right() - 22
        y = glass.top() + 14

        head = QFont("Consolas", 11)
        head.setBold(True)
        q.setFont(head)
        q.setPen(self.KEY)
        q.drawText(QRectF(x0, y, x1 - x0, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "OMORTSON CORE 6100  //  COMMAND REFERENCE")
        small = QFont("Consolas", 8)
        q.setFont(small)
        q.setPen(self.DIM)
        q.drawText(QRectF(x0, y, x1 - x0, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   "OPERATOR LINK")
        y += 26
        q.setPen(QPen(QColor(110, 230, 120, 110), 1))
        q.drawLine(QPointF(x0, y), QPointF(x1, y))
        y += 8

        body = QFont("Consolas", 9)
        bold = QFont("Consolas", 9)
        bold.setBold(True)
        key_w = 150

        for title, items in HELP_SECTIONS:

            q.setFont(small)
            q.setPen(QColor(232, 190, 92))
            q.drawText(QRectF(x0, y + 6, x1 - x0, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "// " + title)
            y += 26

            for key, desc in items:

                box = QRectF(x0 + 8, y + 1, key_w - 20, 17)
                q.setPen(QPen(QColor(125, 255, 140, 120), 1))
                q.setBrush(QColor(125, 255, 140, 22))
                q.drawRoundedRect(box, 3, 3)
                q.setFont(bold)
                q.setPen(self.KEY)
                q.drawText(box, Qt.AlignmentFlag.AlignCenter, key)

                q.setFont(body)
                q.setPen(self.GREEN)
                q.drawText(QRectF(x0 + key_w, y, x1 - x0 - key_w, 19),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, desc)
                y += 21

        y = glass.bottom() - 30
        q.setPen(QPen(QColor(110, 230, 120, 70), 1))
        q.drawLine(QPointF(x0, y), QPointF(x1, y))
        q.setFont(body)
        q.setPen(self.GREEN)
        q.drawText(QRectF(x0, y + 4, x1 - x0, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "> PRESS ANY KEY OR CLICK TO RETURN \u2588")
        q.end()

        # phosphor bloom: a soft, half-res copy of the text underneath
        bloom = text.scaled(
            max(1, text.width() // 3), max(1, text.height() // 3),
            Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setOpacity(0.85)
        p.drawImage(QRectF(0, 0, W, H), bloom)
        p.setOpacity(1.0)
        p.drawImage(QRectF(0, 0, W, H), text)

        # glass glare
        glare = QLinearGradient(glass.topLeft(), glass.bottomLeft())
        glare.setColorAt(0.0, QColor(255, 255, 255, 14))
        glare.setColorAt(0.3, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glare))
        p.drawRoundedRect(glass.adjusted(3, 3, -3, -3), 7, 7)

        p.end()

        pixmap = QPixmap.fromImage(img)
        pixmap.setDevicePixelRatio(dpr)

        return pixmap

    def paintEvent(self, event):

        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)

        if self._cache is None or self._key != key:
            self._cache = self.build(dpr)
            self._key = key

        painter = QPainter(self)
        r = event.rect()
        painter.drawPixmap(
            QRectF(r), self._cache,
            QRectF(r.x() * dpr, r.y() * dpr, r.width() * dpr, r.height() * dpr)
        )


class OmortsonMonitor(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Omortson"
        )

        self.setMinimumSize(
            1250,
            900
        )

        # ----------------------------------------------------
        # ADLX
        # ----------------------------------------------------

        self.adlx = None
        self.adlx_system = None
        self.gpu = None
        self.performance = None

        try:

            from adlx import ADLX

            self.adlx = (
                ADLX.ADLXHelper()
            )

            result = (
                self.adlx.Initialize()
            )

            if (
                result ==
                ADLX.ADLX_RESULT.ADLX_OK
            ):

                self.adlx_system = (
                    self.adlx.GetSystemServices()
                )

                gpus = (
                    self.adlx_system.GetGPUs()
                )

                if gpus:

                    self.gpu = gpus[0]

                    self.performance = (
                        self.adlx_system
                        .GetPerformanceMonitoringServices()
                    )

        except Exception:

            self.adlx = None
            self.adlx_system = None
            self.gpu = None
            self.performance = None

        # Cache static GPU info once instead of every tick

        self.gpu_name = "GPU NOT DETECTED"
        self.gpu_total_vram = 0

        if self.gpu is not None:

            try:
                self.gpu_name = self.gpu.Name()
            except Exception:
                self.gpu_name = "AMD GPU"

            try:
                self.gpu_total_vram = int(
                    self.gpu.TotalVRAM()
                )
            except Exception:
                self.gpu_total_vram = 0

        # ----------------------------------------------------
        # HISTORY
        # ----------------------------------------------------

        self.history_length = 60

        self.cpu_history = deque(
            [0.0] * self.history_length,
            maxlen=self.history_length
        )

        self.ram_history = deque(
            [0.0] * self.history_length,
            maxlen=self.history_length
        )

        self.gpu_history = deque(
            [0.0] * self.history_length,
            maxlen=self.history_length
        )

        self.temp_history = deque(
            [0.0] * self.history_length,
            maxlen=self.history_length
        )

        self.disk_read_history = deque(
            [0.0] * self.history_length,
            maxlen=self.history_length
        )

        self.disk_write_history = deque(
            [0.0] * self.history_length,
            maxlen=self.history_length
        )

        self.network_download_history = deque(
            [0.0] * self.history_length,
            maxlen=self.history_length
        )

        self.network_upload_history = deque(
            [0.0] * self.history_length,
            maxlen=self.history_length
        )

        # ----------------------------------------------------
        # GAUGES
        # ----------------------------------------------------

        self.cpu_gauge = AnalogGauge(
            "CPU LOAD"
        )

        self.ram_gauge = AnalogGauge(
            "MEMORY"
        )

        self.gpu_gauge = AnalogGauge(
            "GPU LOAD"
        )

        self.temp_gauge = AnalogGauge(
            "GPU TEMP",
            unit="°C",
            warning_start=80,
            compact=True
        )

        # ----------------------------------------------------
        # INFO PANEL
        # ----------------------------------------------------

        self.info_panel = InfoPanel(
            self
        )

        # ----------------------------------------------------
        # LAYOUT
        # ----------------------------------------------------

        main_layout = QHBoxLayout(
            self
        )

        self.main_layout = main_layout
        self.immersion_box = None

        main_layout.setContentsMargins(
            16,
            16,
            16,
            16
        )

        main_layout.setSpacing(
            14
        )

        gauge_layout = QGridLayout()

        gauge_layout.setSpacing(
            10
        )

        gauge_layout.addWidget(
            self.cpu_gauge,
            0,
            0
        )

        gauge_layout.addWidget(
            self.ram_gauge,
            0,
            1
        )

        gauge_layout.addWidget(
            self.gpu_gauge,
            1,
            0
        )

        gauge_layout.addWidget(
            self.temp_gauge,
            1,
            1
        )

        # Console strip: warning lamps, emblem plate, knobs, SLEEP switch

        self.console_strip = ConsoleStrip()

        # Bottom band: core terminal strip + net radar

        self.terminal = CoreTerminal()

        self.tracker = NetRadar(self)

        band = QHBoxLayout()
        band.setContentsMargins(0, 0, 0, 0)
        band.setSpacing(10)
        band.addWidget(self.terminal, 1)
        band.addWidget(self.tracker, 0)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(12)
        left_column.addLayout(gauge_layout, 1)
        left_column.addWidget(self.console_strip, 0)
        left_column.addLayout(band, 0)

        main_layout.addLayout(
            left_column,
            4
        )

        main_layout.addWidget(
            self.info_panel,
            1
        )

        # ----------------------------------------------------
        # GPU THREAD
        # ----------------------------------------------------

        self.gpu_usage = 0.0

        self.gpu_monitor = None

        if self.performance is None:

            # Fallback only: spawning PowerShell is slow (~1.5 s per sample)

            self.gpu_monitor = (
                WindowsGPUMonitor()
            )

            self.gpu_monitor.usage_updated.connect(
                self.receive_gpu_usage
            )

            self.gpu_monitor.start()

        # ----------------------------------------------------
        # SPEED BASELINES
        # ----------------------------------------------------

        disk_io = psutil.disk_io_counters()

        self.previous_disk_read = (
            disk_io.read_bytes if disk_io else 0
        )
        self.previous_disk_write = (
            disk_io.write_bytes if disk_io else 0
        )

        network = psutil.net_io_counters()

        self.previous_network_sent = network.bytes_sent
        self.previous_network_received = network.bytes_recv

        # First cpu_percent() call always returns 0.0; prime it

        psutil.cpu_percent(interval=None)

        self.last_speed_time = (
            time.time()
        )

        # ----------------------------------------------------
        # TIMER
        # ----------------------------------------------------

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_stats
        )

        self.timer.start(
            1000
        )

        # ----------------------------------------------------
        # STYLE
        # ----------------------------------------------------

        self.setStyleSheet("""
            QWidget {
                background-color: #0b0b0a;
                color: #b8b29a;
            }
        """)

        # ----------------------------------------------------
        # RETRO FX: SOUND, CRT OVERLAY, TOGGLES, ALARMS
        # ----------------------------------------------------

        self.setup_fx()

    # ========================================================
    # RETRO FX
    # ========================================================

    ALARM_SECONDS = 5
    ALARM_COOLDOWN = 60.0
    ALARM_PULSE_PERIOD = 1.25       # seconds -> 0.8 Hz, smooth sine
    IDLE_SECONDS = 120.0
    IDLE_DIM = 0.18
    STATUS_INTERVAL = 14            # seconds between routine status lines

    ALARM_TEXT = {
        "cpu": "WARNING: CPU LOAD CRITICAL  {v:.0f}%",
        "ram": "WARNING: MEMORY RESERVES CRITICAL  {v:.0f}%",
        "gpu_temp": "WARNING: CORE TEMPERATURE CRITICAL  {v:.0f}°C",
    }

    CLEAR_TEXT = {
        "cpu": "CPU LOAD NORMALIZED",
        "ram": "MEMORY RESERVES NORMALIZED",
        "gpu_temp": "CORE TEMPERATURE NORMALIZED",
    }

    def gauges(self):

        return [self.cpu_gauge, self.ram_gauge, self.gpu_gauge, self.temp_gauge]

    # --------------------------------------------------------

    def setup_fx(self):

        self.settings = QSettings(
            "Omortson",
            "Omortson"
        )
        try:
            self.tracker.set_ping_enabled(self.read_setting("radar_ping", True), save=False)
        except Exception:
            pass

        self.forced_mute = env_flag("OMORTSON_MUTE")

        self.sound_enabled = self.read_setting("sound", True)
        self.ambient_enabled = self.read_setting("ambient", False)
        self.crt_enabled = self.read_setting("crt", True)
        self.boot_enabled = self.read_setting("boot", True)
        self.fullscreen_wanted = self.read_setting("fullscreen", False)

        self.startup_played = False
        self.ambient_ready = False
        self.idle_dimmed = False
        self.boot = None
        self._bg = None
        self._bg_key = None

        hub = fx_hub()

        try:
            self.sounds = SoundBank(SOUND_DIR, self)
        except Exception:
            self.sounds = SoundBank(os.devnull, self)

        hub.sounds = self.sounds
        hub.terminal = self.terminal

        hub.set_enabled(self.crt_enabled)

        self.crt_overlay = decorate_window(
            self,
            close_sound=False,
            overlay_cls=FXOverlay
        )

        self.apply_sound_state()

        # Toggles reflect saved settings without re-saving them

        panel = self.info_panel

        for toggle, state in (
            (panel.mute_toggle, not self.sound_enabled),
            (panel.ambient_toggle, self.ambient_enabled),
            (panel.crt_toggle, self.crt_enabled),
            (panel.boot_toggle, self.boot_enabled),
        ):
            toggle.blockSignals(True)
            toggle.setChecked(state)
            toggle.blockSignals(False)

        if self.forced_mute:
            panel.mute_toggle.set_override_text("ENV")

        panel.mute_toggle.toggled.connect(self.on_mute_toggled)
        panel.ambient_toggle.toggled.connect(self.on_ambient_toggled)
        panel.crt_toggle.toggled.connect(self.on_crt_toggled)
        panel.boot_toggle.toggled.connect(self.on_boot_toggled)

        # Keyboard shortcuts work from any Omortson window

        self.shortcuts = []

        for key, slot in (
            ("M", panel.mute_toggle.click),
            ("H", panel.ambient_toggle.click),
            ("C", panel.crt_toggle.click),
            ("B", panel.boot_toggle.click),
            ("P", self.cycle_palette),
            ("Ctrl+Shift+A", self.preview_alarm),
            ("Ctrl+Shift+Q", self.force_quote),
            ("S", self.console_strip.sleep_toggle.click),
            ("Z", self.sleep_now),
            ("Ctrl+Shift+J", self.summon_cat),
        ):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(slot)
            self.shortcuts.append(shortcut)

        # Immersive fullscreen: F11 toggles, Esc leaves (only while fullscreen)
        self.fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        self.fullscreen_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.escape_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.escape_shortcut.activated.connect(self.exit_fullscreen)
        self.escape_shortcut.setEnabled(False)

        self.shortcuts += [self.fullscreen_shortcut, self.escape_shortcut]

        # Command reference: F1 / ? / the [?] KEYS tab
        self.help_overlay = HelpOverlay(self)
        self.help_hint_posted = False

        for key in (QKeySequence(Qt.Key.Key_F1), QKeySequence("?")):
            shortcut = QShortcut(key, self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(self.show_help)
            self.shortcuts.append(shortcut)

        panel.keys_button.clicked.connect(self.show_help)

        # Gauge face palette (persisted, cycled with P)

        self.palette_name = self.read_text("palette", DEFAULT_PALETTE)

        if self.palette_name not in GAUGE_PALETTES:
            self.palette_name = DEFAULT_PALETTE

        self.apply_palette(self.palette_name)

        # Double-click a gauge -> its diagnostic screen (GPU via the panel's own function)

        self.cpu_gauge.activated.connect(panel.open_cpu_window)
        self.ram_gauge.activated.connect(panel.open_memory_window)
        self.gpu_gauge.activated.connect(panel.open_gpu_diagnostics)
        self.temp_gauge.activated.connect(panel.open_gpu_diagnostics)

        # Oscilloscope listens to the sound bank's virtual mixer

        panel.scope.attach(self.sounds)

        # Terminal transmissions

        self.quote_bag = []
        self.last_quote = None
        self.quotes_shown = 0
        self.schedule_quote()

        # Sustained-overload alarms (GPU load deliberately excluded)

        self.alarm_targets = {
            "cpu": (90.0, self.cpu_gauge, panel.cpu_button),
            "ram": (90.0, self.ram_gauge, panel.memory_button),
            "gpu_temp": (85.0, self.temp_gauge, panel.temp_button),
        }

        self.alarm_counts = {key: 0 for key in self.alarm_targets}
        self.alarm_last = {key: None for key in self.alarm_targets}
        self.alarm_active = set()
        self.alarm_trigger_count = 0
        self.alarm_preview_until = 0.0
        self.alarm_phase_start = time.monotonic()
        self.alarm_level = 0.0
        self.last_warning_line = 0.0

        self.alarm_timer = ManagedTimer(self, 50, self.pulse_alarms)

        # Idle low-power dimming + boot skip input watcher

        self.activity = ActivityWatcher(self)
        QApplication.instance().installEventFilter(self.activity)

        self.idle_timer = ManagedTimer(self, 1000, self.check_idle)
        self.idle_timer.run()

        # Console hardware: knobs, lamps, deepsleep, ambient noises, side bays, glitches

        self.setup_console()

        self.boot = BootSequence(self)

        # Terminal status chatter

        self.status_counter = 0
        self.status_index = 0
        self.prev_cpu = None
        self.net_average = None
        self.last_spike = {}
        self.latest = {}

    # --------------------------------------------------------

    def read_setting(self, key, default):

        try:
            return bool(
                self.settings.value(key, default, type=bool)
            )
        except Exception:
            return default

    def write_setting(self, key, value):

        try:
            self.settings.setValue(key, bool(value))
            self.settings.sync()
        except Exception:
            pass

    def read_text(self, key, default):

        try:
            value = self.settings.value(key, default)
            return str(value) if value is not None else default
        except Exception:
            return default

    def write_text(self, key, value):

        try:
            self.settings.setValue(key, str(value))
            self.settings.sync()
        except Exception:
            pass

    # --------------------------------------------------------
    # gauge face palettes

    def apply_palette(self, name):

        PALETTE_STATE["name"] = name
        self.palette_name = name

        for gauge in self.gauges():
            gauge.palette_changed()

        try:
            self.info_panel.vu.palette_changed()
        except Exception:
            pass

    def set_palette(self, name, announce=True, persist=True):

        if name not in GAUGE_PALETTES:
            return

        self.apply_palette(name)

        if persist:
            self.write_text("palette", name)

        if announce:
            terminal_post(f"GAUGE PALETTE: {name}", "event")

    def cycle_palette(self):

        try:
            index = PALETTE_ORDER.index(self.palette_name)
        except ValueError:
            index = -1

        play_sound("click")

        self.set_palette(PALETTE_ORDER[(index + 1) % len(PALETTE_ORDER)])

    # --------------------------------------------------------
    # terminal transmissions: one random line every 3-6 minutes,
    # only when the terminal is quiet, no repeats until the pool is used up

    QUOTE_MIN = 180.0
    QUOTE_MAX = 360.0

    def schedule_quote(self):

        self.quote_due = time.monotonic() + random.uniform(self.QUOTE_MIN, self.QUOTE_MAX)

    def next_quote(self):

        if not self.quote_bag:
            self.quote_bag = list(QUOTES)
            random.shuffle(self.quote_bag)
            # no back-to-back repeat across a refill
            if len(self.quote_bag) > 1 and self.quote_bag[-1] == self.last_quote:
                self.quote_bag[0], self.quote_bag[-1] = self.quote_bag[-1], self.quote_bag[0]

        self.last_quote = self.quote_bag.pop()

        return self.last_quote

    def post_quote(self):

        terminal_post(self.next_quote(), "quote")
        self.quotes_shown += 1
        self.schedule_quote()

    def maybe_quote(self, now=None, booting=False):

        now = time.monotonic() if now is None else now

        if now < self.quote_due:
            return

        busy = (
            booting
            or self.alarm_active
            or fx_hub().paused
            or not self.terminal.idle()
        )

        if busy:
            self.quote_due = now + 10.0     # try again shortly, never interrupt
            return

        self.post_quote()

    def force_quote(self):

        self.post_quote()

    # --------------------------------------------------------

    def apply_sound_state(self):

        try:
            self.sounds.set_muted(
                self.forced_mute or not self.sound_enabled
            )
            self.sounds.set_loop(
                self.ambient_enabled and self.ambient_ready
            )
        except Exception:
            pass

        try:
            self.info_panel.scope.refresh()
        except Exception:
            pass

    def on_mute_toggled(self, checked):

        self.sound_enabled = not checked
        self.write_setting("sound", self.sound_enabled)
        self.apply_sound_state()

        terminal_post(
            "AUDIO OUTPUT RESTORED" if self.sound_enabled else "AUDIO OUTPUT MUTED",
            "event"
        )

    def on_ambient_toggled(self, checked):

        self.ambient_enabled = bool(checked)
        self.write_setting("ambient", self.ambient_enabled)
        self.apply_sound_state()

        terminal_post(
            "AMBIENT HUM ENGAGED" if self.ambient_enabled else "AMBIENT HUM DISENGAGED",
            "event"
        )

    def on_crt_toggled(self, checked):

        self.crt_enabled = bool(checked)
        self.write_setting("crt", self.crt_enabled)
        fx_hub().set_enabled(self.crt_enabled)

        terminal_post(
            "CRT FILTER ONLINE" if self.crt_enabled else "CRT FILTER OFFLINE",
            "event"
        )

    def on_boot_toggled(self, checked):

        self.boot_enabled = bool(checked)
        self.write_setting("boot", self.boot_enabled)

        terminal_post(
            "BOOT SEQUENCE ENABLED" if self.boot_enabled else "BOOT SEQUENCE DISABLED",
            "event"
        )

    # --------------------------------------------------------
    # show / hide / minimize: animations only run while visible

    def showEvent(self, event):

        super().showEvent(event)

        self.refresh_pause()

        if not self.startup_played:

            self.startup_played = True

            if self.boot_enabled and os.environ.get("OMORTSON_BOOT", "1") != "0":

                QTimer.singleShot(0, self.boot.start)

            else:

                QTimer.singleShot(150, lambda: play_sound("startup"))
                QTimer.singleShot(300, lambda: terminal_post("OPERATOR LINK READY  //  AWAITING INQUIRY", "event"))
                QTimer.singleShot(320, self.post_help_hint)

            # Ambient hum (if enabled) fades in after the power-up
            QTimer.singleShot(3600, self.enable_ambient_after_startup)

    def hideEvent(self, event):

        super().hideEvent(event)

        fx_hub().set_paused(True)

        try:
            self.sleep_screen.set_running(False)
        except Exception:
            pass

    def changeEvent(self, event):

        try:
            if event.type() == QEvent.Type.WindowStateChange:
                self.refresh_pause()
                self.on_window_state()
        except Exception:
            pass

        super().changeEvent(event)

    # --------------------------------------------------------
    # immersive fullscreen (F11 / Esc / maximize button / double-click metal)

    ASPECT_MIN = 1.35
    ASPECT_MAX = 1.62

    def show_help(self):

        if self.help_overlay.isVisible():
            self.help_overlay.dismiss()
        else:
            self.help_overlay.open()

    def post_help_hint(self):

        if not self.help_hint_posted:
            self.help_hint_posted = True
            terminal_post("PRESS F1 FOR COMMAND REFERENCE", "info")

    def show_restored(self):

        """Startup: come back in the display mode the user left."""

        if self.fullscreen_wanted:
            self.showFullScreen()
        else:
            self.show()

    def toggle_fullscreen(self):

        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self, announce=True):

        if self.isFullScreen():
            return

        self.showFullScreen()
        self.fullscreen_wanted = True
        self.write_setting("fullscreen", True)

        if announce:
            terminal_post("DISPLAY MODE: FULL IMMERSION", "event")

    def exit_fullscreen(self, announce=True):

        if not self.isFullScreen():
            return

        self.showNormal()
        self.fullscreen_wanted = False
        self.write_setting("fullscreen", False)

        if announce:
            terminal_post("DISPLAY MODE: WINDOWED", "event")

    def on_window_state(self):

        full = self.isFullScreen()

        self.escape_shortcut.setEnabled(full)

        # the maximize button means "make it big": give it true fullscreen
        if (
            not full
            and self.isMaximized()
            and not getattr(self, "_entering_fullscreen", False)
        ):
            self._entering_fullscreen = True
            QTimer.singleShot(0, self._maximize_to_fullscreen)

        self.update_immersion_layout()

    def _maximize_to_fullscreen(self):

        self._entering_fullscreen = False

        if self.isMaximized() and not self.isFullScreen():
            self.enter_fullscreen()

    def update_immersion_layout(self):

        """
        Fullscreen keeps the windowed proportions: the console is centred
        in a bay with panel metal around it, so nothing gets stretched.
        """

        margin = 16
        box = None

        if self.isFullScreen():

            W, H = self.width(), self.height()

            ng = self.normalGeometry()
            aspect = ng.width() / ng.height() if ng.height() > 0 else 1250 / 860
            aspect = min(max(aspect, self.ASPECT_MIN), self.ASPECT_MAX)

            pad = max(8, int(min(W, H) * 0.018))
            aw, ah = W - 2 * pad, H - 2 * pad

            if aw / max(1, ah) > aspect:
                bw, bh = ah * aspect, ah
            else:
                bw, bh = aw, aw / aspect

            bw = max(bw, min(aw, self.minimumWidth()))
            bh = max(bh, min(ah, self.minimumHeight()))

            x = int((W - bw) / 2)
            y = int((H - bh) / 2)
            box = QRectF(x, y, int(bw), int(bh))

        if box is None:
            margins = (margin, margin, margin, margin)
        else:
            margins = (
                int(box.left()) + margin,
                int(box.top()) + margin,
                self.width() - int(box.right()) + margin,
                self.height() - int(box.bottom()) + margin,
            )

        current = self.main_layout.contentsMargins()

        if (current.left(), current.top(), current.right(), current.bottom()) != margins:
            self.main_layout.setContentsMargins(*margins)

        if box != self.immersion_box:
            self.immersion_box = box
            self._bg = None
            self.update()

    def resizeEvent(self, event):

        super().resizeEvent(event)

        try:
            self.update_immersion_layout()
        except Exception:
            pass

        try:
            if self.help_overlay.isVisible():
                self.help_overlay.setGeometry(self.rect())
        except Exception:
            pass

        try:
            if self.sleep_screen.isVisible():
                self.sleep_screen.setGeometry(self.rect())
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):

        """Double-click bare panel metal (not a control) toggles fullscreen."""

        try:

            if event.button() == Qt.MouseButton.LeftButton:

                child = self.childAt(event.position().toPoint())

                if child is None or child is self.info_panel or child is self.console_strip or child in self.gauges():
                    self.toggle_fullscreen()
                    event.accept()
                    return

        except Exception:
            pass

        super().mouseDoubleClickEvent(event)

    def enable_ambient_after_startup(self):

        self.ambient_ready = True
        self.apply_sound_state()

    # --------------------------------------------------------
    # panel background (pre-rendered brushed metal, plates, stencils)

    def paintEvent(self, event):

        try:

            dpr = self.devicePixelRatioF()

            key = (
                self.width(), self.height(), dpr,
                tuple(
                    (w.x(), w.y(), w.width(), w.height())
                    for w in self.gauges() + [self.info_panel, self.terminal, self.tracker, self.console_strip]
                )
            )

            if self._bg is None or self._bg_key != key:
                self._bg = build_panel_background(self, dpr)
                self._bg_key = key

            painter = QPainter(self)
            r = event.rect()

            painter.drawPixmap(
                QRectF(r),
                self._bg,
                QRectF(r.x() * dpr, r.y() * dpr, r.width() * dpr, r.height() * dpr)
            )

            self.paint_bay_lamps(painter, r, dpr)

        except Exception:
            pass

    # --------------------------------------------------------
    # idle low-power dimming

    def check_idle(self):

        idle = time.monotonic() - self.activity.last_input

        if (
            not self.idle_dimmed
            and idle >= self.IDLE_SECONDS
            and not (self.boot is not None and self.boot.active)
        ):
            self.idle_dimmed = True
            self.crt_overlay.set_dim_target(self.IDLE_DIM)
            terminal_post("LOW POWER MODE  //  DISPLAY DIMMED", "info")

        if (
            self.deepsleep_enabled
            and not self.asleep
            and idle >= self.DEEPSLEEP_SECONDS
        ):
            self.enter_deepsleep("idle")

    def wake_from_idle(self):

        if self.idle_dimmed:
            self.idle_dimmed = False
            self.crt_overlay.set_dim_target(0.0)
            terminal_post("OPERATOR PRESENCE DETECTED", "event")

    # ========================================================
    # CONSOLE HARDWARE (round 6)
    # ========================================================

    DEEPSLEEP_SECONDS = 600.0
    AMBIENT_MIN = 90.0
    AMBIENT_MAX = 300.0
    LINK_IDLE_SECONDS = 60.0
    BAY_BLINK_MS = 250

    AMBIENT_LINES = {
        "door_open": ("DECK B: HATCH SERVO CYCLED", "AIRLOCK 2: INNER DOOR OPEN"),
        "door_close": ("DECK B: HATCH SERVO CYCLED", "AIRLOCK 2: INNER DOOR SEALED"),
        "steam": ("DECK C: PRESSURE VENT CYCLED", "COOLANT LOOP: PRESSURE EQUALIZED"),
        "cat_meow": ("MOTION: STATION CAT",),
        "cat_purr": ("MOTION: STATION CAT",),
        "cat_hiss": ("MOTION: STATION CAT  //  AGITATED",),
    }

    def read_int(self, key, default, lo, hi):

        try:
            value = int(float(self.settings.value(key, default)))
        except Exception:
            value = default

        return max(lo, min(hi, value))

    def setup_console(self):

        strip = self.console_strip

        self.asleep = False
        self.sleep_count = 0
        self.sleep_cursor = None
        self.sleep_started = 0.0
        self.last_wake_reason = None
        self.sleep_screen = SleepScreen(self)

        self.deepsleep_enabled = self.read_setting("deepsleep", True)

        strip.sleep_toggle.blockSignals(True)
        strip.sleep_toggle.setChecked(self.deepsleep_enabled)
        strip.sleep_toggle.blockSignals(False)
        strip.sleep_toggle.toggled.connect(self.on_sleep_toggled)

        # knobs: restore, apply live while turning, persist on release
        self.knob_keys = {
            strip.volume_knob: "volume",
            strip.crt_knob: "crt_intensity",
            strip.range_knob: "tracker_range",
        }

        for knob, key in self.knob_keys.items():
            knob.set_value(self.read_int(key, knob.default, knob.lo, knob.hi), emit=False, sound=False)
            knob.value_changed.connect(lambda v, k=knob: self.apply_knob(k, v))
            knob.committed.connect(lambda v, k=knob: self.commit_knob(k, v))
            self.apply_knob(knob, knob.value)

        # warning lamps + link watch
        self.link_up = True
        self.link_checks = 0
        self.last_traffic = time.monotonic()

        # ambient station noises
        self.ambient_events = []
        self.schedule_ambient()

        # fullscreen side bays (sparse blinking lamps)
        self.bay_lamps = []
        self.bay_lit = set()
        self.bay_changes = 0
        self.bay_ticks = 0
        self._bay_sprites = {}
        self.bay_timer = ManagedTimer(self, self.BAY_BLINK_MS, self._bay_tick)

        if self.crt_overlay is not None:
            self.crt_overlay.setup_glitches()

    # --------------------------------------------------------
    # knobs

    def apply_knob(self, knob, value):

        strip = self.console_strip

        if knob is strip.volume_knob:
            self.sounds.set_master(value / 100.0)
        elif knob is strip.crt_knob:
            fx_hub().set_intensity(value / 100.0)
        elif knob is strip.range_knob:
            self.tracker.set_range(value)

    def commit_knob(self, knob, value):

        key = self.knob_keys.get(knob)

        if key is None:
            return

        if self.read_int(key, knob.default, knob.lo, knob.hi) == value and self.settings.contains(key):
            return

        self.write_text(key, int(value))

        names = {"volume": "MASTER VOLUME", "crt_intensity": "CRT INTENSITY", "tracker_range": "RADAR RANGE"}
        terminal_post(f"{names[key]}: {knob.text()}", "event")

    def on_sleep_toggled(self, checked):

        self.deepsleep_enabled = bool(checked)
        self.write_setting("deepsleep", self.deepsleep_enabled)

        terminal_post(
            "AUTO-SLEEP ARMED  //  10 MIN" if self.deepsleep_enabled else "AUTO-SLEEP DISARMED",
            "event"
        )

    # --------------------------------------------------------
    # pause: minimized, hidden or in deepsleep

    def refresh_pause(self):

        hidden = self.isMinimized() or not self.isVisible()

        fx_hub().set_paused(hidden or self.asleep)

        try:
            if self.asleep:
                self.sleep_screen.set_running(not hidden)
        except Exception:
            pass

    # --------------------------------------------------------
    # deepsleep

    def sleep_now(self):

        self.enter_deepsleep("manual")

    def enter_deepsleep(self, reason="idle"):

        if self.asleep:
            return False

        if (self.boot is not None and self.boot.active) or self.active_alarm_keys():
            return False

        try:
            if self.help_overlay.isVisible():
                self.help_overlay.dismiss()
        except Exception:
            pass

        self.asleep = True
        self.sleep_count += 1
        self.sleep_started = time.monotonic()

        try:
            self.sleep_cursor = QCursor.pos()
        except Exception:
            self.sleep_cursor = None

        ov = self.crt_overlay

        if ov is not None:
            ov.cancel_glitch()
            fx_hub().clock60.remove((id(ov), "dim"))
            ov.dim = 0.0
            ov.dim_target = 0.0

        self.idle_dimmed = False

        self.info_panel.vu.rest()
        self.sleep_screen.start()
        self.refresh_pause()

        return True

    def wake_from_deepsleep(self, reason="input"):

        if not self.asleep:
            return False

        self.asleep = False
        self.last_wake_reason = reason
        self.activity.last_input = time.monotonic()

        self.sleep_screen.stop()
        self.refresh_pause()

        if self.crt_overlay is not None:
            self.crt_overlay.refresh_visibility()
            self.crt_overlay.update()

        if reason == "alarm":
            terminal_post("DEEP SLEEP ABORTED  //  ALARM CONDITION", "alert")
        else:
            self.stir_gauges()
            terminal_post("SYSTEM RESUMED  //  SLEEP CYCLE TERMINATED", "event")

        return True

    def stir_gauges(self):

        """Wake-up: the gauges come back with a short boot sweep, one after another."""

        for i, gauge in enumerate(self.gauges()):
            gauge.boot_dark()
            QTimer.singleShot(90 + i * 140, gauge.boot_power_on)

    def sleep_input_wakes(self, event):

        """Mouse moves only count when the pointer really moved (no synthetic jitter)."""

        if time.monotonic() - self.sleep_started < 0.6:
            return False

        if event.type() == QEvent.Type.MouseMove and self.sleep_cursor is not None:
            try:
                gp = event.globalPosition().toPoint()
                d = gp - self.sleep_cursor
                if abs(d.x()) + abs(d.y()) < 4:
                    return False
            except Exception:
                pass

        return True

    # --------------------------------------------------------
    # warning lamps

    @staticmethod
    def lamp_colour(value, amber, red):

        if value >= red:
            return "red"
        if value >= amber:
            return "amber"
        return None

    def check_link(self):

        try:
            for name, st in psutil.net_if_stats().items():
                low = name.lower()
                if st.isup and "loopback" not in low and low not in ("lo", "lo0"):
                    return True
            return False
        except Exception:
            return True

    def update_lamps(self, s, now):

        lamps = self.console_strip.lamps

        lamps.set_state("THERMAL", self.lamp_colour(s["gpu_temp"], 75.0, 85.0))
        lamps.set_state("CORE", self.lamp_colour(s["cpu"], 75.0, 90.0))
        lamps.set_state("MEM", self.lamp_colour(s["ram"], 80.0, 90.0))

        if self.link_checks % 10 == 0:
            self.link_up = self.check_link()
        self.link_checks += 1

        if s["down"] + s["up"] > 256:
            self.last_traffic = now

        if not self.link_up:
            link = "red"
        elif now - self.last_traffic >= self.LINK_IDLE_SECONDS:
            link = "amber"
        else:
            link = "green"

        lamps.set_state("LINK", link)

    # --------------------------------------------------------
    # ambient station noises (only with AMBIENT on and sound on)

    def schedule_ambient(self, now=None):

        now = time.monotonic() if now is None else now
        self.ambient_due = now + random.uniform(self.AMBIENT_MIN, self.AMBIENT_MAX)

    def ambient_playing(self):

        try:
            return any(v[0] in AMBIENT_EVENTS for v in self.sounds.active_voices())
        except Exception:
            return False

    def ambient_blocked(self):

        snd = self.sounds

        return (
            snd is None
            or snd.muted
            or snd.suspended
            or snd.master <= 0.001
            or self.asleep
            or fx_hub().paused
            or bool(self.alarm_active)
            or time.monotonic() < self.alarm_preview_until
            or (self.boot is not None and self.boot.active)
            or any(v[0] in AMBIENT_EVENTS or v[0] == "warning" for v in snd.active_voices())
        )

    def maybe_ambient(self, now):

        if not self.ambient_enabled:
            if now >= self.ambient_due:
                self.schedule_ambient(now)
            return

        if now < self.ambient_due:
            return

        if self.ambient_blocked():
            self.ambient_due = now + 20.0
            return

        self.play_ambient_event()
        self.schedule_ambient(now)

    def pick_ambient(self, kind=None):

        r = random.random()

        if kind == "cat" or (kind is None and r < 0.16):
            c = random.random()
            return "cat_meow" if c < 0.6 else ("cat_purr" if c < 0.9 else "cat_hiss")

        if kind == "steam" or (kind is None and r < 0.58):
            return "steam"

        return random.choice(("door_open", "door_close"))

    def play_ambient_event(self, kind=None, log=None):

        name = self.pick_ambient(kind)

        play_sound(name)

        self.ambient_events.append(name)

        if log or (log is None and random.random() < 0.4):
            terminal_post(random.choice(self.AMBIENT_LINES[name]), "info")

        return name

    def summon_cat(self):

        """Ctrl+Shift+J: the station cat makes itself known (obeys MUTE)."""

        if self.ambient_playing() or self.active_alarm_keys():
            return None

        return self.play_ambient_event("cat", log=True)

    def silence_ambient_events(self):

        if self.ambient_playing():
            for name in AMBIENT_EVENTS:
                self.sounds.stop(name)

    def console_stats_tick(self, s, now):

        try:
            self.update_lamps(s, now)
        except Exception:
            pass

        try:
            self.maybe_ambient(now)
        except Exception:
            pass

    # --------------------------------------------------------
    # fullscreen side bays: a few lamps blink, sparsely, at <= 4 fps

    def bays_rebuilt(self, lamps):

        self.bay_lamps = list(lamps)
        rnd = random.Random(426)
        self.bay_lit = {i for i in range(len(self.bay_lamps)) if rnd.random() < 0.3}

        if self.bay_lamps:
            self.bay_timer.run()
        else:
            self.bay_timer.halt()

    def bay_lamp_rect(self, i):

        c = self.bay_lamps[i][0]
        h = BAY_HALO

        return QRectF(c.x() - h, c.y() - h, 2 * h, 2 * h).toAlignedRect().adjusted(-1, -1, 1, 1)

    def bay_sprites(self, dpr):

        if self._bay_sprites.get("dpr") != dpr:
            self._bay_sprites = {"dpr": dpr}
            for colour in LAMP_RGB:
                self._bay_sprites[colour] = lamp_sprite(colour, BAY_LAMP_R, BAY_HALO, dpr, True)

        return self._bay_sprites

    def _bay_tick(self):

        if not self.bay_lamps or self.immersion_box is None:
            self.bay_timer.halt()
            return

        self.bay_ticks += 1

        if random.random() < 0.45:
            return                   # mostly quiet: the computer "thinks" in sparse bursts

        n = len(self.bay_lamps)

        for _ in range(1 if random.random() < 0.75 else 2):

            lit = len(self.bay_lit)

            if lit > n * 0.34:
                i = random.choice(tuple(self.bay_lit))
            elif lit < n * 0.22:
                i = random.choice([k for k in range(n) if k not in self.bay_lit])
            else:
                i = random.randrange(n)

            self.bay_lit ^= {i}
            self.bay_changes += 1
            self.update(self.bay_lamp_rect(i))

    def paint_bay_lamps(self, painter, r, dpr):

        if not self.bay_lit or self.immersion_box is None:
            return

        sprites = self.bay_sprites(dpr)

        for i in self.bay_lit:
            if i < len(self.bay_lamps) and self.bay_lamp_rect(i).intersects(r):
                c, colour = self.bay_lamps[i]
                blit_centred(painter, sprites[colour], c)

    def shutdown_console_fx(self):

        try:
            self.sleep_screen.stop()
            self.bay_timer.halt()
            self.console_strip.lamps.flicker_timer.halt()
            if self.crt_overlay is not None:
                self.crt_overlay.glitch_timer.halt()
                self.crt_overlay.cancel_glitch()
        except Exception:
            pass


    # --------------------------------------------------------
    # alarms / self-destruct mode

    def check_alarms(self, cpu, ram, gpu_temp):

        values = {
            "cpu": cpu,
            "ram": ram,
            "gpu_temp": gpu_temp,
        }

        now = time.monotonic()

        for key, (threshold, gauge, button) in self.alarm_targets.items():

            if values[key] >= threshold:
                self.alarm_counts[key] += 1
            else:
                self.alarm_counts[key] = 0

            sustained = (
                self.alarm_counts[key] >= self.ALARM_SECONDS
            )

            if sustained:

                last = self.alarm_last[key]

                if last is None or now - last >= self.ALARM_COOLDOWN:

                    self.alarm_last[key] = now
                    self.alarm_trigger_count += 1

                    play_sound("warning")
                    self.post_alarm_lines(key, values[key])

                self.alarm_active.add(key)

            elif key in self.alarm_active:

                self.alarm_active.discard(key)

                gauge.set_alarm(0.0)
                button.set_alarm(0.0)

                terminal_post(self.CLEAR_TEXT[key], "event")

        self.update_alarm_mode()

    def post_alarm_lines(self, key, value):

        terminal_post(self.ALARM_TEXT[key].format(v=value), "alert")

        if random.random() < 0.12:
            terminal_post("OVERRIDE LOCKED  //  OPERATOR EYES ONLY", "warn")
            terminal_post("STAND BY FOR INSTRUCTIONS", "alert")

        self.last_warning_line = time.monotonic()

    def active_alarm_keys(self):

        keys = set(self.alarm_active)

        if time.monotonic() < self.alarm_preview_until:
            keys.add("cpu")

        return keys

    def update_alarm_mode(self):

        keys = self.active_alarm_keys()

        if keys:
            if self.asleep:
                self.wake_from_deepsleep("alarm")
            self.silence_ambient_events()

        if keys and not self.alarm_timer.wanted:
            self.alarm_phase_start = time.monotonic()
            self.alarm_timer.run()
        elif not keys and self.alarm_timer.wanted:
            self.alarm_timer.halt()
            self.clear_alarm_visuals()

    def pulse_alarms(self):

        keys = self.active_alarm_keys()

        if not keys:
            self.alarm_timer.halt()
            self.clear_alarm_visuals()
            return

        t = time.monotonic() - self.alarm_phase_start

        # smooth 0.8 Hz sine: no hard edges, no strobing
        level = 0.5 - 0.5 * math.cos(2 * math.pi * t / self.ALARM_PULSE_PERIOD)
        self.alarm_level = level

        for key, (_, gauge, button) in self.alarm_targets.items():
            on = key in keys
            gauge.set_alarm(level if on else 0.0)
            button.set_alarm(level if on else 0.0)

        envelope = min(1.0, t / 0.6)

        if self.crt_overlay is not None:
            self.crt_overlay.set_alarm(envelope * (0.2 + 0.8 * level))

        real = keys & set(self.alarm_active)

        if real and time.monotonic() - self.last_warning_line >= 20:
            key = sorted(real)[0]
            self.post_alarm_lines(key, self.latest.get(key, 0.0))

    def clear_alarm_visuals(self):

        self.alarm_level = 0.0

        for _, gauge, button in self.alarm_targets.values():
            gauge.set_alarm(0.0)
            button.set_alarm(0.0)

        if self.crt_overlay is not None:
            self.crt_overlay.set_alarm(0.0)

    def preview_alarm(self):

        """Ctrl+Shift+A: 10 s simulated alarm (klaxon obeys MUTE)."""

        self.alarm_preview_until = time.monotonic() + 10.0

        play_sound("warning")

        terminal_post("SIMULATED ALARM  //  SELF-DESTRUCT DRILL", "alert")
        terminal_post("PRIORITY OVERRIDE", "warn")

        self.update_alarm_mode()

    # --------------------------------------------------------
    # stats -> terminal / tracker

    def fx_stats_tick(self, **s):

        s["gpu_temp_key"] = s.get("gpu_temp", 0.0)

        self.latest = {
            "cpu": s["cpu"],
            "ram": s["ram"],
            "gpu_temp": s["gpu_temp"],
        }
        self.latest_full = s

        self.tracker.feed(s["down"], s["up"])

        booting = self.boot is not None and self.boot.active
        now = time.monotonic()

        # spike detection
        if self.prev_cpu is not None and s["cpu"] - self.prev_cpu >= 40 and s["cpu"] >= 60:
            if now - self.last_spike.get("cpu", 0) > 20:
                self.last_spike["cpu"] = now
                terminal_post(f"CPU SPIKE DETECTED  {s['cpu']:.0f}%", "warn")

        self.prev_cpu = s["cpu"]

        net = s["down"] + s["up"]

        if self.net_average is None:
            self.net_average = net
        else:
            if net > 2 * 1024 * 1024 and net > 6 * max(self.net_average, 1.0):
                if now - self.last_spike.get("net", 0) > 30:
                    self.last_spike["net"] = now
                    terminal_post(
                        f"NETWORK SURGE  ↓ {self.format_speed(s['down'])}  ↑ {self.format_speed(s['up'])}",
                        "warn"
                    )
            self.net_average = self.net_average * 0.9 + net * 0.1

        self.status_counter += 1

        if not booting and self.status_counter % self.STATUS_INTERVAL == 0:
            terminal_post(self.next_status_line(s), "info")

        self.maybe_quote(now, booting)

        self.console_stats_tick(s, now)

    def next_status_line(self, s):

        lines = []

        lines.append(f"CPU LOAD {s['cpu']:.0f}%  ·  {psutil.cpu_count(logical=True)} THREADS")

        memory = s["memory"]
        lines.append(
            f"MEMORY {s['ram']:.0f}%  ·  {memory.used / 1024 ** 3:.1f} / {memory.total / 1024 ** 3:.1f} GB"
        )

        temp = s["gpu_temp"]

        if temp <= 0:
            lines.append("THERMAL PROBE: NO SIGNAL")
        elif temp < 70:
            lines.append(f"THERMAL: NOMINAL  ·  CORE {temp:.0f}°C")
        elif temp < 85:
            lines.append(f"THERMAL: ELEVATED  ·  CORE {temp:.0f}°C")
        else:
            lines.append(f"THERMAL: CRITICAL  ·  CORE {temp:.0f}°C")

        up = s["uptime"]
        lines.append(f"UPTIME {up // 86400}D {(up % 86400) // 3600:02d}H {(up % 3600) // 60:02d}M")

        net = s["down"] + s["up"]

        if net < 1024 * 1024:
            lines.append("NETWORK TRAFFIC NOMINAL")
        else:
            lines.append(f"NETWORK TRAFFIC HIGH  ↓ {self.format_speed(s['down'])}  ↑ {self.format_speed(s['up'])}")

        lines.append(f"GPU LOAD {s['gpu_load']:.0f}%  ·  VRAM {s['gpu_vram']} MB")

        lines.append("OPERATOR LINK READY  //  AWAITING INQUIRY")

        lines.append("ALL SYSTEMS NOMINAL" if not self.alarm_active else "SYSTEM STATUS: ALERT")

        line = lines[self.status_index % len(lines)]
        self.status_index += 1

        return line

    # ========================================================
    # GPU USAGE
    # ========================================================

    def receive_gpu_usage(
        self,
        value
    ):

        self.gpu_usage = value

    # ========================================================
    # SPEED FORMAT
    # ========================================================

    def format_speed(
        self,
        bytes_per_second
    ):

        if bytes_per_second < 1024:

            return (
                f"{bytes_per_second:.0f} B/s"
            )

        if (
            bytes_per_second <
            1024 * 1024
        ):

            return (
                f"{bytes_per_second / 1024:.1f} KB/s"
            )

        if (
            bytes_per_second <
            1024 * 1024 * 1024
        ):

            return (
                f"{bytes_per_second / (1024 * 1024):.1f} MB/s"
            )

        return (
            f"{bytes_per_second / (1024 * 1024 * 1024):.1f} GB/s"
        )

    # ========================================================
    # UPDATE STATS
    # ========================================================

    def update_stats(self):

        now = time.time()

        elapsed = (
            now -
            self.last_speed_time
        )

        if elapsed <= 0:
            elapsed = 1

        self.last_speed_time = now

        # ----------------------------------------------------
        # CPU
        # ----------------------------------------------------

        cpu = psutil.cpu_percent(
            interval=None
        )

        self.cpu_gauge.setValue(
            cpu
        )

        # ----------------------------------------------------
        # RAM
        # ----------------------------------------------------

        ram = (
            psutil.virtual_memory()
            .percent
        )

        self.ram_gauge.setValue(
            ram
        )

        memory = psutil.virtual_memory()

        self.info_panel.cpu_button.set_value(
            f"{cpu:.1f}%  ·  "
            f"{psutil.cpu_count(logical=True)} THREADS"
        )

        self.info_panel.memory_button.set_value(
            f"{memory.used / 1024 ** 3:.1f} / "
            f"{memory.total / 1024 ** 3:.1f} GB"
        )

        # ----------------------------------------------------
        # GPU
        # ----------------------------------------------------

        # ----------------------------------------------------
        # ADLX GPU DATA
        # ----------------------------------------------------

        gpu_temp = 0.0
        gpu_vram = 0

        if self.performance is not None:

            try:

                metrics = (
                    self.performance
                    .GetCurrentGPUMetrics(
                        self.gpu
                    )
                )

                usage = metrics.GPUUsage()

                if usage is not None:
                    self.gpu_usage = float(usage)

                temp = metrics.GPUTemperature()

                if temp is not None:
                    gpu_temp = float(temp)

                vram = metrics.GPUVRAM()

                if vram is not None:
                    gpu_vram = int(vram)

            except Exception:
                pass

        gpu_load = (
            self.gpu_usage
        )

        self.gpu_gauge.setValue(
            gpu_load
        )

        self.temp_gauge.setValue(
            gpu_temp
        )

        # ----------------------------------------------------
        # GPU NAME
        # ----------------------------------------------------

        self.info_panel.gpu_button.set_value(
            self.gpu_name
        )

        # ----------------------------------------------------
        # VRAM
        # ----------------------------------------------------

        if self.gpu_total_vram:

            self.info_panel.vram_button.set_value(
                f"{gpu_vram} / {self.gpu_total_vram} MB"
            )

        else:

            self.info_panel.vram_button.set_value(
                f"{gpu_vram} MB"
            )

        # ----------------------------------------------------
        # TEMP
        # ----------------------------------------------------

        self.info_panel.temp_button.set_value(
            f"{gpu_temp:.1f} °C"
        )

        # ----------------------------------------------------
        # OS
        # ----------------------------------------------------

        self.info_panel.os_button.set_value(
            platform.system() +
            " " +
            platform.release()
        )

        # ----------------------------------------------------
        # UPTIME
        # ----------------------------------------------------

        uptime_seconds = (
            time.time() -
            psutil.boot_time()
        )

        uptime = int(
            uptime_seconds
        )

        days = (
            uptime // 86400
        )

        hours = (
            uptime % 86400
        ) // 3600

        minutes = (
            uptime % 3600
        ) // 60

        seconds = (
            uptime % 60
        )

        self.info_panel.uptime_button.set_value(
            f"{days}d "
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

        # ----------------------------------------------------
        # DISK
        # ----------------------------------------------------

        disk_io = (
            psutil.disk_io_counters()
        )

        if disk_io:

            read_speed = (
                disk_io.read_bytes -
                self.previous_disk_read
            ) / elapsed

            write_speed = (
                disk_io.write_bytes -
                self.previous_disk_write
            ) / elapsed

            self.previous_disk_read = (
                disk_io.read_bytes
            )

            self.previous_disk_write = (
                disk_io.write_bytes
            )

        else:

            read_speed = 0
            write_speed = 0

        self.info_panel.disk_button.set_value(
            f"R {self.format_speed(read_speed)}\n"
            f"W {self.format_speed(write_speed)}"
        )

        # ----------------------------------------------------
        # NETWORK
        # ----------------------------------------------------

        network = (
            psutil.net_io_counters()
        )

        download_speed = (
            network.bytes_recv -
            self.previous_network_received
        ) / elapsed

        upload_speed = (
            network.bytes_sent -
            self.previous_network_sent
        ) / elapsed

        self.previous_network_received = (
            network.bytes_recv
        )

        self.previous_network_sent = (
            network.bytes_sent
        )

        self.info_panel.network_button.set_value(
            f"↓ {self.format_speed(download_speed)}\n"
            f"↑ {self.format_speed(upload_speed)}"
        )

        # ----------------------------------------------------
        # HISTORY
        # ----------------------------------------------------

        self.cpu_history.append(
            cpu
        )

        self.ram_history.append(
            ram
        )

        self.gpu_history.append(
            gpu_load
        )

        self.temp_history.append(
            gpu_temp
        )

        self.disk_read_history.append(
            read_speed
        )

        self.disk_write_history.append(
            write_speed
        )

        self.network_download_history.append(
            download_speed
        )

        self.network_upload_history.append(
            upload_speed
        )

        # ----------------------------------------------------
        # ALARMS
        # ----------------------------------------------------

        try:
            self.check_alarms(cpu, ram, gpu_temp)
        except Exception:
            pass

        try:
            self.fx_stats_tick(
                cpu=cpu, ram=ram, memory=memory,
                gpu_load=gpu_load, gpu_temp=gpu_temp, gpu_vram=gpu_vram,
                uptime=uptime, down=download_speed, up=upload_speed,
                read=read_speed, write=write_speed
            )
        except Exception:
            pass

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        self.timer.stop()

        # Silence FX first so closing windows doesn't chatter

        try:
            self.alarm_timer.halt()
            self.idle_timer.halt()
            self.info_panel.scope.timer.halt()
            self.shutdown_console_fx()
            if self.boot is not None and self.boot.active:
                self.boot.finish()
            QApplication.instance().removeEventFilter(self.activity)
            self.sounds.shutdown()
            fx_hub().stop()
            fx_hub().set_paused(True)
        except Exception:
            pass

        self.info_panel.close_all_windows()

        if (
            self.gpu_monitor is not None
            and self.gpu_monitor.isRunning()
        ):

            self.gpu_monitor.requestInterruption()

            self.gpu_monitor.wait(
                3000
            )

        # Release ADLX interfaces before terminating, or the
        # process crashes with an access violation on exit

        self.performance = None
        self.gpu = None
        self.adlx_system = None

        try:

            if self.adlx:

                self.adlx.Terminate()

        except Exception:
            pass

        self.adlx = None

        event.accept()


# ============================================================
# APPLICATION
# ============================================================

if __name__ == "__main__":

    # Own taskbar identity so Windows shows the Omortson icon
    # instead of the generic Python one.
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Omortson.SystemMonitor"
        )
    except Exception:
        pass

    app = QApplication(
        sys.argv
    )

    try:
        from PySide6.QtGui import QIcon
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Omortson.ico"
        )
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Omortson.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass

    window = OmortsonMonitor()

    window.show_restored()

    sys.exit(
        app.exec()
    )