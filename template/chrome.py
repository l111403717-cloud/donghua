"""Chrome overlay and post-processing finishing.

Provides three chrome presentation styles:
- none: Raw composited frames, zero overlay.
- gallery: High-end 1px hairline inner frame (inset ~48px, alpha ~0.18) + subtle vignette.
           Default is purely visual with zero text clutter.
- hud: Legacy tactical engineering HUD (brackets, timecode, status dots).

Also exports `apply_chrome(frame, t, total)` for pipeline integration.
"""
from __future__ import annotations

import numpy as np

try:
    from mg import fonts as F
    from mg.core import corner_brackets, Canvas
except ImportError:
    from engine import fonts as F
    from engine.core import corner_brackets, Canvas

from . import theme as T

W, H = T.W, T.H
DOT_X, DOT_Y = W / 2.0, 604.0
BAR_Y = H - 4.0


def _tc(t):
    fr = int(round(t * T.FPS))
    return "TC %02d:%02d:%02d" % (fr // (T.FPS * 3600) % 100, fr // T.FPS % 60, fr % T.FPS)


def _edge_alpha(t: float, total: float, fade: float = 0.6, hold: float = 1.0) -> float:
    """Fade-in and fade-out envelope near video start and finish."""
    if t < fade:
        return t / fade
    if t < fade + hold:
        return 1.0
    if t < fade * 2 + hold:
        return max(0.0, 1.0 - (t - (fade + hold)) / fade)
    t_end = total - t
    if t_end < fade:
        return max(0.0, t_end / fade)
    if t_end < fade + hold:
        return 1.0
    if t_end < fade * 2 + hold:
        return max(0.0, 1.0 - (t_end - (fade + hold)) / fade)
    return 0.0


def draw(p, t, scene_i=0, light=False, total=None):
    """Draw tactical HUD vector furniture."""
    ink = T.INK if light else T.GREY
    dim = T.SLATE if light else T.GREY_D
    acc = T.ACCENT if light else T.ACCENT_BR
    allow_text = getattr(T, "CHROME_TEXT", False)
    dur = total or getattr(T, "DUR", 15.0)

    # --- brand bug, top left: the mark plus the domain
    p.rect(T.HUD_M, T.HUD_TOP - 5.5, 9, 9, acc, 0.95)
    p.rect(T.HUD_M + 3.0, T.HUD_TOP - 2.5, 3, 3, T.PAPER if light else T.INK, 0.95)
    if allow_text:
        p.text(T.HUD_M + 17, T.HUD_TOP, f"{T.DOMAIN} — {T.STUDIO}", F.mono(T.S_HUD), ink,
               T.TRACK_HUD, level=2)

    # --- product reel title, top right
    if allow_text:
        p.text(W - T.HUD_M, T.HUD_TOP, "PRODUCT REEL // 15 SEC", F.mono(T.S_HUD), ink,
               T.TRACK_HUD, anchor="rs", level=2)

    # --- timecode, bottom left
    if allow_text:
        p.text(T.HUD_M, T.HUD_BOT, _tc(t), F.mono(T.S_HUD), ink, T.TRACK_HUD, level=2)

    # --- scene name, bottom right
    if allow_text and hasattr(T, "SCENES") and scene_i < len(T.SCENES):
        sid, sname = T.SCENES[scene_i][0], T.SCENES[scene_i][1]
        wlab = p.text(W - T.HUD_M, T.HUD_BOT, f"SCENE {sid} / {sname}", F.mono(T.S_HUD),
                      ink, T.TRACK_HUD, anchor="rs", level=2)
        p.rect(W - T.HUD_M - wlab - 11, T.HUD_BOT - 3.0, 5, 5, acc, 0.9)

    # --- eight-dot indicator
    bars = getattr(T, "BARS", 8)
    gap = 15.0
    x0 = DOT_X - gap * (bars - 1) / 2.0
    for i in range(bars):
        cx = x0 + i * gap
        if i == scene_i:
            p.rect(cx - 6.5, DOT_Y - 1.6, 13, 3.2, acc, 1.0, radius=1.6)
        elif i < scene_i:
            p.dot(cx, DOT_Y, 2.0, ink, 0.62)
        else:
            p.dot(cx, DOT_Y, 2.0, dim, 0.55)

    corner_brackets(p, W, H, acc, 26, 15, 0.34 if not light else 0.30)

    # --- progress bar
    p.rect(0, BAR_Y, W, 3.0, dim, 0.30)
    prog = np.clip(t / max(1e-3, dur), 0.0, 1.0)
    p.rect(0, BAR_Y, W * prog, 3.0, acc, 0.95)
    p.rect(W * prog - 1.5, BAR_Y - 1.0, 3.0, 5.0, T.WHITE if not light else T.INK, 0.85)

    # --- live status chip, bottom-centre-left
    up = min(1.0, t / 0.35)
    if up > 0.01:
        p.dot(T.HUD_M + 4, T.HUD_BOT - 14, 3.0, T.ACCENT_BR,
              up * (0.55 + 0.45 * np.sin(t * 4.6)))
        if allow_text:
            p.text(T.HUD_M + 13, T.HUD_BOT - 11, "ONLINE", F.mono(8.5), T.ACCENT_LT,
                   T.TRACK_HUD, alpha=up * 0.9, level=2)


def _gallery(frame: np.ndarray, t: float, total: float) -> np.ndarray:
    cv = Canvas.from_array(frame)
    inset = getattr(T, "GALLERY_INSET", 48)
    fg = getattr(T, "WHITE", (240, 245, 240))
    p = cv.pass_()

    # 1px hairline border
    p.line([(inset, inset), (cv.w - inset, inset)], fg, width=1.0, alpha=0.18)
    p.line([(cv.w - inset, inset), (cv.w - inset, cv.h - inset)], fg, width=1.0, alpha=0.18)
    p.line([(cv.w - inset, cv.h - inset), (inset, cv.h - inset)], fg, width=1.0, alpha=0.18)
    p.line([(inset, cv.h - inset), (inset, inset)], fg, width=1.0, alpha=0.18)

    # Optional Title (only when CHROME_TEXT is true)
    if getattr(T, "CHROME_TEXT", False) and getattr(T, "TITLE", None):
        a = _edge_alpha(t, total, fade=0.6, hold=1.0)
        if a > 0.01:
            p.text(inset + 24, cv.h - inset - 20, T.TITLE, F.mono(14), fg,
                   anchor="ls", alpha=a * 0.5, level=2)

    cv.commit()
    cv.vignette(amount=0.12, power=1.6)
    return cv.to_array()


def _hud(frame: np.ndarray, t: float, total: float) -> np.ndarray:
    cv = Canvas.from_array(frame)
    p = cv.pass_()
    # Estimate scene index from time
    bar = getattr(T, "BAR", 1.875)
    scene_i = min(getattr(T, "BARS", 8) - 1, int(t // max(1e-4, bar)))
    draw(p, t, scene_i=scene_i, total=total)
    cv.commit()
    return cv.to_array()


def apply_chrome(frame: np.ndarray, t: float, total: float, style: str | None = None) -> np.ndarray:
    """Apply the active chrome post-processing style onto a composited frame."""
    mode = style or getattr(T, "CHROME_STYLE", "gallery")
    if mode == "none":
        return frame
    if mode == "gallery":
        return _gallery(frame, t, total)
    if mode == "hud":
        return _hud(frame, t, total)
    return frame


# --------------------------------------------------------------------------
# finishing — per-scene post-processing
# --------------------------------------------------------------------------
POST = {
    0: dict(bloom=(0.70, 0.24), chroma=1.4, vig=0.44, grain=0.0120, scan=0.014, white=1.16),
    1: dict(bloom=(0.68, 0.26), chroma=1.8, vig=0.46, grain=0.0140, scan=0.016, white=1.16),
    2: dict(bloom=(0.70, 0.26), chroma=1.3, vig=0.54, grain=0.0125, scan=0.016, white=1.16),
    3: dict(bloom=(0.66, 0.28), chroma=1.3, vig=0.50, grain=0.0130, scan=0.016, white=1.18),
    4: dict(bloom=(0.60, 0.30), chroma=1.2, vig=0.54, grain=0.0135, scan=0.016, white=1.20),
    5: dict(bloom=(0.95, 0.26), chroma=0.9, vig=0.16, grain=0.0060, scan=0.000, white=1.00,
            light=True),
    6: dict(bloom=(0.64, 0.28), chroma=2.2, vig=0.52, grain=0.0150, scan=0.018, white=1.16),
    7: dict(bloom=(0.70, 0.26), chroma=1.5, vig=0.44, grain=0.0125, scan=0.014, white=1.16),
}


def finish(c, t, scene_i):
    q = dict(POST.get(scene_i, POST[0]))
    q.update(getattr(c, "post_override", None) or {})

    c.bloom(thr=q["bloom"][0], knee=q["bloom"][1])
    c.chroma(q["chroma"])

    if q.get("light"):
        c.rgb = np.clip(c.rgb, 0.0, 1.0)
        c.vignette(q["vig"], 2.0)
    else:
        c.rgb = c.rgb * np.asarray((1.0, 1.02, 1.03), np.float32).reshape(1, 1, 3)
        c.rgb = c.rgb + np.asarray((0.004, 0.010, 0.018), np.float32).reshape(1, 1, 3)
        l = c.rgb.mean(axis=2, keepdims=True)
        c.rgb = np.clip(l + (c.rgb - l) * 1.07, 0.0, 1.0)
        c.vignette(q["vig"], 1.7)

    tl = t % getattr(T, "BAR", 1.875)
    k = 1.00 if scene_i == 0 else (0.72 if scene_i == 1 else 0.58)
    if scene_i in (4, 7):
        k = 0.72
    if scene_i == 2:
        k = 0.40
    flash = k * np.exp(-tl / 0.055)
    if scene_i == 5:
        flash = 0.90 * np.exp(-tl / 0.10)
    if flash > 0.004:
        c.add += flash * np.asarray((0.86, 1.0, 0.90), np.float32).reshape(1, 1, 3)

    if q.get("scan", 0):
        c.scanlines(q["scan"], 3)
    c.grain(q["grain"])
    c.tonemap(0.80 if not q.get("light") else 0.86)
    return c
