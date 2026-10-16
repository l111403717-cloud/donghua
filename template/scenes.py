"""Scenes definition for motion reels.

Implements the Scene base class with enter()/exit() lifecycle hooks,
momentum preservation, and strict typographical restraint.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple, List

import numpy as np

try:
    from mg import fonts as F
    from mg import anim as A
    from mg.core import clip01, gauss, radial, rgb01, Canvas
    from mg.transitions import (Transition, Slide, Wipe, ZoomThrough, ChannelSnap,
                            IrisShutter, FlashBurst, CurtainSplit)
    from mg.timeline import RenderContext
except ImportError:
    from engine import fonts as F
    from engine import anim as A
    from engine.core import clip01, gauss, radial, rgb01, Canvas
    from engine.transitions import (Transition, Slide, Wipe, ZoomThrough, ChannelSnap,
                                IrisShutter, FlashBurst, CurtainSplit)
    from engine.timeline import RenderContext

from . import theme as T

W, H = T.W, T.H
CX, CY = W / 2.0, H / 2.0


# --------------------------------------------------------------------------
# Lifecycle FX & Scene Base Class
# --------------------------------------------------------------------------
@dataclass
class FX:
    """Scene entrance / exit state."""
    alpha: float = 1.0
    dx: float = 0.0
    dy: float = 0.0
    scale: float = 1.0
    blur: float = 0.0
    stagger: float = 0.0


class Scene:
    """Base class for all choreographed motion scenes."""
    duration: float = 3.0
    in_dur: float = 0.6
    out_dur: float = 0.6

    def enter(self, p: float, ctx: RenderContext) -> FX:
        """p: 0 -> 1. Default: Slide in along momentum vector + fade in."""
        e = 1.0 - (1.0 - p) ** 3  # cubic out
        mx, my = ctx.momentum_in if ctx else (0.0, 0.0)
        return FX(alpha=float(e), dx=float((1.0 - e) * 120.0 * mx), dy=float((1.0 - e) * 120.0 * my))

    def exit(self, p: float, ctx: RenderContext) -> FX:
        """p: 0 -> 1. Default: Slide out along momentum vector + fade out."""
        e = p ** 3  # cubic in
        mx, my = ctx.momentum_out if ctx else (0.0, 0.0)
        return FX(alpha=float(1.0 - e), dx=float(e * 120.0 * mx), dy=float(e * 120.0 * my))

    def draw(self, c: Canvas, t: float, fx: FX, ctx: RenderContext):
        """Draw scene content in steady state. fx applies enter/exit transforms."""
        raise NotImplementedError

    def render(self, c: Canvas, t_local: float, ctx: RenderContext | None = None):
        if ctx is None:
            ctx = RenderContext()
        if t_local < self.in_dur:
            p = np.clip(t_local / max(1e-4, self.in_dur), 0.0, 1.0)
            fx = self.enter(float(p), ctx)
        elif t_local > self.duration - self.out_dur:
            p = np.clip((t_local - (self.duration - self.out_dur)) / max(1e-4, self.out_dur), 0.0, 1.0)
            fx = self.exit(float(p), ctx)
        else:
            fx = FX()
        self.draw(c, t_local, fx, ctx)
        return c


# --------------------------------------------------------------------------
# Five Clean Choreographed Scenes (Compliant with Typography & Transition rules)
# --------------------------------------------------------------------------
class Scene01_Opening(Scene):
    """01 / Opening: Calm horizon, generous breathing space, Hero statement."""
    duration = 3.2
    in_dur = 0.6
    out_dur = 0.5

    def draw(self, c: Canvas, t: float, fx: FX, ctx: RenderContext):
        c.clear(T.INK)
        # Gentle drifting background ambient glow
        pulse = 1.0 + 0.08 * np.sin(t * 1.6)
        c.add += (np.array([0.02, 0.08, 0.05], np.float32)
                  * gauss(W, H, CX, CY + 30, 520, 140 * pulse)[..., None])

        p = c.pass_()
        # Subtle horizontal axis guide line
        p.line([(CX - 280, CY + 40), (CX + 280, CY + 40)], T.ACCENT_DK, width=1.0, alpha=0.35 * fx.alpha)

        # L1 Hero Text: <= 12 chars Chinese or <= 5 words English
        title = getattr(T, "BRAND", "LAST MEETING")
        p.text(CX + fx.dx, CY - 20 + fx.dy, title, F.display(76), T.WHITE,
               anchor="mm", alpha=fx.alpha, level=1)
        c.commit()


class Scene02_Kinetic(Scene):
    """02 / Kinetic Momentum: Directional slide, typography in motion."""
    duration = 2.8
    in_dur = 0.5
    out_dur = 0.5

    def draw(self, c: Canvas, t: float, fx: FX, ctx: RenderContext):
        c.clear(T.INK)
        drift_x = CX + (t - 1.4) * 40.0
        c.add += (np.array([0.03, 0.06, 0.10], np.float32)
                  * gauss(W, H, drift_x, CY, 460, 200)[..., None])

        p = c.pass_()
        # L1 Hero Statement
        word = getattr(T, "TAGLINE", "BEFORE THE END")
        p.text(CX + fx.dx, CY + fx.dy, word, F.display(84), T.ACCENT_BR,
               anchor="mm", alpha=fx.alpha, level=1)
        c.commit()


class Scene03_Breathing(Scene):
    """03 / Pure Visual Breathing: Zero text! 100% graphic space & flow."""
    duration = 2.6
    in_dur = 0.6
    out_dur = 0.6

    def draw(self, c: Canvas, t: float, fx: FX, ctx: RenderContext):
        c.clear(T.INK)
        # Multi-layered concentric orbital geometry
        r_base = 120.0 + 35.0 * np.sin(t * 2.2)
        c.add += (np.array([0.06, 0.08, 0.12], np.float32)
                  * radial(W, H, CX, CY, r_base * 2.2, r_base * 1.5)[..., None])

        p = c.pass_()
        # Geometric orbits
        for i, rad_mult in enumerate([0.7, 1.0, 1.35]):
            rad = r_base * rad_mult
            rot = t * (0.8 if i % 2 == 0 else -0.6)
            p.arc(CX, CY, rad, rad, rot, rot + 4.2, T.ACCENT_LT,
                  width=1.5, alpha=0.45 * fx.alpha)
            # Satellite beacon
            bx = CX + rad * np.cos(rot)
            by = CY + rad * np.sin(rot)
            p.dot(bx, by, 3.5, T.WHITE, alpha=0.85 * fx.alpha)

        c.commit()


class Scene04_Statement(Scene):
    """04 / Proposition: L1 Core Insight + L2 Sub-sentence."""
    duration = 3.2
    in_dur = 0.5
    out_dur = 0.5

    def draw(self, c: Canvas, t: float, fx: FX, ctx: RenderContext):
        c.clear(T.INK)
        c.add += (np.array([0.05, 0.04, 0.08], np.float32)
                  * gauss(W, H, CX, CY, 580, 220)[..., None])

        p = c.pass_()
        # L1 Hero (<= 12 chars)
        p.text(CX + fx.dx, CY - 24 + fx.dy, "EVERY MEETING ENDS", F.display(72), T.WHITE,
               anchor="mm", alpha=fx.alpha, level=1)

        # L2 Sub-clause (<= 20 chars, font size <= 40% of L1)
        # 72 * 0.38 = ~27
        p.text(CX + fx.dx, CY + 42 + fx.dy, "YET THE ECHO LINGERS FOREVER", F.mono(22), T.GREY,
               track=2.0, anchor="mm", alpha=fx.alpha * 0.85, level=2)
        c.commit()


class Scene05_Signoff(Scene):
    """05 / Sign-off: Final branded lockup with momentum landing."""
    duration = 3.0
    in_dur = 0.6
    out_dur = 0.6

    def draw(self, c: Canvas, t: float, fx: FX, ctx: RenderContext):
        c.clear(T.INK)
        c.add += (np.array([0.02, 0.09, 0.06], np.float32)
                  * gauss(W, H, CX, CY, 420, 180)[..., None])

        p = c.pass_()
        # Brand lockup center
        brand = getattr(T, "BRAND", "STUDIO")
        domain = getattr(T, "DOMAIN", "STUDIO.DEV")
        p.text(CX + fx.dx, CY - 18 + fx.dy, brand, F.display(80), T.ACCENT_BR,
               anchor="mm", alpha=fx.alpha, level=1)
        p.text(CX + fx.dx, CY + 48 + fx.dy, domain, F.mono(20), T.SLATE if hasattr(T, "SLATE") else T.GREY,
               track=3.0, anchor="mm", alpha=fx.alpha * 0.75, level=2)
        c.commit()


# --------------------------------------------------------------------------
# Timeline Registry & Transition Plan
# --------------------------------------------------------------------------
SCENES = [
    Scene01_Opening(),
    Scene02_Kinetic(),
    Scene03_Breathing(),
    Scene04_Statement(),
    Scene05_Signoff(),
]

TRANSITION_PLAN = [
    Slide(direction="left", overlap=0.5, why="承接左向水平动量"),
    Wipe(direction="left", softness=0.08, overlap=0.6, why="走纸擦除推开文字进入纯视觉"),
    ZoomThrough(center=(0.5, 0.5), overlap=0.5, strength=1.8, why="从光环中心穿梭浮出核心论点"),
    ChannelSnap(max_shift=32, overlap=0.45, why="RGB色版错位归位锁定终章"),
]
