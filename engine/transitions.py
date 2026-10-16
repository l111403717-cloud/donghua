"""Transitions library for motion reels.

Turns hard scene cuts into momentum-driven transitions:
- Wipe: paper conveyor wipe with soft edge
- Slide: continuous motion slide with optional parallax
- ZoomThrough: punch-through scale transition
- ChannelSnap: RGB misregistration snap
- IrisShutter: mechanical circular / iris aperture opening or closing
- FlashBurst: high-intensity optical energy burst for impacts/explosions
- CurtainSplit: bilateral blast door / mechanical sliding panel split
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

    if arr.dtype == np.uint8:
        im = Image.fromarray(arr)
    else:
        im = Image.fromarray((clip01(arr) * 255.0 + 0.5).astype(np.uint8))
    im_scaled = im.resize((nw, nh), Image.BILINEAR)

    # Re-crop or pad to original (w, h) about (cx, cy)
    new_cx = cx * scale
    new_cy = cy * scale

    x0 = int(round(new_cx - cx))
    y0 = int(round(new_cy - cy))

    out_im = Image.new("RGB", (w, h), (0, 0, 0))
    out_im.paste(im_scaled, (-x0, -y0))
    return np.asarray(out_im, np.uint8)


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
        res = A_frame.astype(np.float32) * (1.0 - mask) + B_frame.astype(np.float32) * mask
        return np.clip(res, 0.0, 255.0).astype(np.uint8)


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

        a = _zoom(A_frame, scale_a, self.center).astype(np.float32)
        b = _zoom(B_frame, scale_b, self.center).astype(np.float32)

        mix = np.clip((p - 0.35) / 0.30, 0.0, 1.0)
        mix = mix * mix * (3.0 - 2.0 * mix)
        res = a * (1.0 - mix) + b * mix
        return np.clip(res, 0.0, 255.0).astype(np.uint8)


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


class IrisShutter(Transition):
    """机械光圈快门：圆形精密机械孔径由内向外绽开或收拢。"""

    def __init__(self, mode="open", center=(0.5, 0.5), softness=0.04, overlap=0.7, why=""):
        self.mode = mode
        self.center = center
        self.softness = softness
        self.overlap = overlap
        self.why = why or f"IrisShutter {mode}"
        self.momentum = (0.0, 0.0)

    def apply(self, A_frame: np.ndarray, B_frame: np.ndarray, p: float) -> np.ndarray:
        p = self.ease(p)
        h, w = A_frame.shape[:2]
        cx, cy = self.center[0] * w, self.center[1] * h
        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.float32)
        max_dist = np.sqrt(max(cx, w - cx) ** 2 + max(cy, h - cy) ** 2)

        r_curr = max_dist * p if self.mode == "open" else max_dist * (1.0 - p)
        s_px = max(1.0, max_dist * self.softness)
        mask = np.clip((dist - r_curr) / (2.0 * s_px) + 0.5, 0.0, 1.0)
        if self.mode == "open":
            mask = 1.0 - mask
        mask = mask[:, :, None]
        res = A_frame.astype(np.float32) * (1.0 - mask) + B_frame.astype(np.float32) * mask
        return np.clip(res, 0.0, 255.0).astype(np.uint8)


class FlashBurst(Transition):
    """能量暴击耀斑：在转场中点爆发出高光耀斑（适用于碰撞与大爆炸瞬间）。"""

    def __init__(self, overlap=0.6, peak=0.88, color=(255, 245, 230), why=""):
        self.overlap = overlap
        self.peak = peak
        self.flash_col = np.array(color, dtype=np.float32)
        self.why = why or "FlashBurst"
        self.momentum = (0.0, 0.0)

    def apply(self, A_frame: np.ndarray, B_frame: np.ndarray, p: float) -> np.ndarray:
        pe = self.ease(p)
        base = A_frame.astype(np.float32) * (1.0 - pe) + B_frame.astype(np.float32) * pe
        flash_k = float(np.exp(-((p - 0.5) / 0.18) ** 2) * self.peak)
        res = base * (1.0 - flash_k) + self.flash_col * flash_k
        return np.clip(res, 0.0, 255.0).astype(np.uint8)


class CurtainSplit(Transition):
    """机械双移门：左右对称推开揭示下一幕。"""

    def __init__(self, overlap=0.7, softness=0.03, why=""):
        self.overlap = overlap
        self.softness = softness
        self.why = why or "CurtainSplit"
        self.momentum = (0.0, 0.0)

    def apply(self, A_frame: np.ndarray, B_frame: np.ndarray, p: float) -> np.ndarray:
        p = self.ease(p)
        h, w = A_frame.shape[:2]
        x = np.linspace(-1.0, 1.0, w, dtype=np.float32)
        dist = np.abs(x)
        s = max(0.01, self.softness)
        mask = np.clip((dist - p) / s + 0.5, 0.0, 1.0)[None, :, None]
        res = B_frame.astype(np.float32) * (1.0 - mask) + A_frame.astype(np.float32) * mask
        return np.clip(res, 0.0, 255.0).astype(np.uint8)
