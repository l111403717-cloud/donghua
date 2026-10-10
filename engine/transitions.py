"""Transitions library for motion reels.

Turns hard scene cuts into momentum-driven transitions:
- Wipe: paper conveyor wipe with soft edge
- Slide: continuous motion slide with optional parallax
- ZoomThrough: punch-through scale transition
- ChannelSnap: RGB misregistration snap
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from . import anim as A
from .core import clip01


def _ease_in_out(p: float) -> float:
    p = float(np.clip(p, 0.0, 1.0))
    return float(p * p * (3.0 - 2.0 * p))


def _paste(dst: np.ndarray, src: np.ndarray, ox: int, oy: int):
    """Paste src into dst at pixel offset (ox, oy) with boundary clipping."""
    h, w = dst.shape[:2]
    sh, sw = src.shape[:2]

    dx0, dx1 = max(0, ox), min(w, ox + sw)
    dy0, dy1 = max(0, oy), min(h, oy + sh)
    if dx0 >= dx1 or dy0 >= dy1:
        return

    sx0, sx1 = dx0 - ox, dx0 - ox + (dx1 - dx0)
    sy0, sy1 = dy0 - oy, dy0 - oy + (dy1 - dy0)

    dst[dy0:dy1, dx0:dx1] = src[sy0:sy1, sx0:sx1]


def _zoom(arr: np.ndarray, scale: float, center=(0.5, 0.5)) -> np.ndarray:
    """Zoom arr about normalized center coordinate."""
    if abs(scale - 1.0) < 0.001:
        return arr
    h, w = arr.shape[:2]
    cx = float(center[0]) * w
    cy = float(center[1]) * h

    nw = max(2, int(round(w * scale)))
    nh = max(2, int(round(h * scale)))

    im = Image.fromarray((clip01(arr) * 255.0 + 0.5).astype(np.uint8))
    im_scaled = im.resize((nw, nh), Image.BILINEAR)

    # Re-crop or pad to original (w, h) about (cx, cy)
    new_cx = cx * scale
    new_cy = cy * scale

    x0 = int(round(new_cx - cx))
    y0 = int(round(new_cy - cy))

    out_im = Image.new("RGB", (w, h), (0, 0, 0))
    out_im.paste(im_scaled, (-x0, -y0))
    return np.asarray(out_im, np.float32) / 255.0


class Transition:
    overlap: float = 0.6
    ease = staticmethod(_ease_in_out)
    momentum: tuple[float, float] = (1.0, 0.0)
    why: str = "Transition"

    def apply(self, A_frame: np.ndarray, B_frame: np.ndarray, p: float) -> np.ndarray:
        raise NotImplementedError


class Wipe(Transition):
    """走纸擦除：一条带软边的横向或纵向遮罩扫过。"""

    def __init__(self, direction="left", softness=0.08, overlap=0.7, why=""):
        self.direction = direction
        self.softness = softness
        self.overlap = overlap
        self.why = why or f"Wipe {direction}"
        self.momentum = {
            "left": (-1.0, 0.0),
            "right": (1.0, 0.0),
            "up": (0.0, -1.0),
            "down": (0.0, 1.0),
        }[direction]

    def apply(self, A_frame: np.ndarray, B_frame: np.ndarray, p: float) -> np.ndarray:
        p = self.ease(p)
        h, w = A_frame.shape[:2]
        axis = np.linspace(0.0, 1.0, w if self.direction in ("left", "right") else h, dtype=np.float32)
        if self.direction in ("right", "down"):
            axis = 1.0 - axis

        edge = p * (1.0 + 2.0 * self.softness) - self.softness
        mask = np.clip((edge - axis) / (2.0 * self.softness) + 0.5, 0.0, 1.0)
        mask = mask[None, :, None] if self.direction in ("left", "right") else mask[:, None, None]
        return A_frame * (1.0 - mask) + B_frame * mask


class Slide(Transition):
    """动量平移：A 被推出，B 被带入，两者同向同速。"""

    def __init__(self, direction="left", overlap=0.7, parallax=0.0, why=""):
        self.direction = direction
        self.overlap = overlap
        self.parallax = parallax
        self.why = why or f"Slide {direction}"
        self.momentum = {
            "left": (-1.0, 0.0),
            "right": (1.0, 0.0),
            "up": (0.0, -1.0),
            "down": (0.0, 1.0),
        }[direction]

    def apply(self, A_frame: np.ndarray, B_frame: np.ndarray, p: float) -> np.ndarray:
        p = self.ease(p)
        h, w = A_frame.shape[:2]
        mx, my = self.momentum
        out = np.zeros_like(A_frame)

        ox = int(round(mx * w * p))
        oy = int(round(my * h * p))

        bx = int(round(ox - mx * w))
        by = int(round(oy - my * h))

        _paste(out, A_frame, ox, oy)
        _paste(out, B_frame, bx + int(round(mx * w * self.parallax * (1.0 - p))), by)
        return out


class ZoomThrough(Transition):
    """缩放穿梭：A 放大冲出画面，B 从深处放大归位。"""

    def __init__(self, center=(0.5, 0.5), overlap=0.8, strength=2.2, why=""):
        self.center = center
        self.overlap = overlap
        self.strength = strength
        self.why = why or "ZoomThrough center"
        self.momentum = (0.0, 0.0)

    def apply(self, A_frame: np.ndarray, B_frame: np.ndarray, p: float) -> np.ndarray:
        p = float(self.ease(p))
        scale_a = 1.0 + p * (self.strength - 1.0)
        scale_b = 1.0 / self.strength + (1.0 - 1.0 / self.strength) * p

        a = _zoom(A_frame, scale_a, self.center)
        b = _zoom(B_frame, scale_b, self.center)

        # 中段平滑交叉淡化
        mix = np.clip((p - 0.35) / 0.30, 0.0, 1.0)
        mix = mix * mix * (3.0 - 2.0 * mix)
        return a * (1.0 - mix) + b * mix


class ChannelSnap(Transition):
    """色版错位归位：各色彩通道分离，在转场中点剧烈错位，两端对齐。"""

    def __init__(self, max_shift=40, overlap=0.5, why=""):
        self.max_shift = max_shift
        self.overlap = overlap
        self.why = why or "ChannelSnap"
        self.momentum = (1.0, 0.0)

    def apply(self, A_frame: np.ndarray, B_frame: np.ndarray, p: float) -> np.ndarray:
        base = A_frame if p < 0.5 else B_frame
        k = abs(1.0 - 2.0 * self.ease(p)) ** 2
        out = base.copy()
        for c, sgn in zip(range(3), (-1, 0, 1)):
            shift_amt = int(round(sgn * self.max_shift * k))
            if shift_amt != 0:
                out[..., c] = np.roll(base[..., c], shift_amt, axis=1)
        return out
