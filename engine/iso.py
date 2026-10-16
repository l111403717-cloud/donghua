"""Isometric Machinery & Anatomy drawing primitives for donghua engine.

Adapted from the craft principles of wheresryan22/anatomy:
- 45°/30° true isometric projection model with depth calculation for Painter's order.
- Four-tone industrial metal shading (tone0: shadow, tone1: ambient, tone2: lit side, tone3: top).
- Precise physical parts: base slab with feet, bevels, cylinders, coil springs, dial gauges,
  machined ruler strips, knurling textures, and exploded view assembly support.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# --------------------------------------------------------------------------
# Projection & Camera
# --------------------------------------------------------------------------
AZIMUTH = 45.0      # Azimuth angle (degrees)
ELEVATION = 30.0    # Elevation angle (degrees)


class IsoCamera:
    """Isometric Camera with Painter's depth sorting and coordinate projection."""

    def __init__(self, cx: float, cy: float, scale: float = 1.0,
                 azimuth: float = AZIMUTH, elevation: float = ELEVATION):
        self.cx = float(cx)
        self.cy = float(cy)
        self.scale = float(scale)
        self.azimuth = float(azimuth)
        self.elevation = float(elevation)

        a = math.radians(azimuth)
        e = math.radians(elevation)
        self.sinA = math.sin(a)
        self.cosA = math.cos(a)
        self.sinE = math.sin(e)
        self.cosE = math.cos(e)
        self.unit = math.sqrt(1.6)

    def project(self, x: float, y: float, z: float) -> Tuple[float, float]:
        """Project world coordinate (x: width, y: depth, z: up) to 2D screen coordinate."""
        k = self.scale * self.unit
        sx = self.cx + (x * self.sinA - y * self.cosA) * k
        sy = self.cy + ((x * self.cosA + y * self.sinA) * self.sinE - z * self.cosE) * k
        return (sx, sy)

    def depth_of(self, x: float, y: float, z: float) -> float:
        """Calculate Painter's depth (smaller value = further from camera = draw earlier)."""
        return (x * self.cosA + y * self.sinA) * self.cosE + z * self.sinE


# --------------------------------------------------------------------------
# Default Industrial Color Palette
# --------------------------------------------------------------------------
DEFAULT_PALETTE: Dict[str, Tuple[int, int, int]] = {
    "paper": (238, 240, 244),      # Plate background (light cool gray)
    "tone0": (125, 134, 146),      # Darkest shadow face
    "tone1": (168, 177, 188),      # Ambient lit side face
    "tone2": (208, 215, 222),      # Key lit side face
    "tone3": (246, 248, 251),      # Top face (brightest)
    "faint": (192, 199, 208),      # Inset grooves, seams, minor marks
    "line_lo": (135, 144, 155),    # Subtle structural outlines
    "line_mid": (65, 75, 88),      # Primary boundary line
    "line_hi": (22, 28, 36),       # Indicator needle, critical markers
    "accent": (238, 92, 38),       # Industrial safety orange accent
    "accent_hi": (255, 130, 75),   # Highlighted orange
    "accent_lo": (175, 55, 18),    # Shadowed accent
    "dark_paper": (22, 24, 28),    # Dark theme fallback
}


# --------------------------------------------------------------------------
# Part Primitives
# --------------------------------------------------------------------------
def slab(p: Any, cam: IsoCamera, x: float, y: float, z: float,
         w: float, d: float, h: float, r: float = 0.0,
         palette: Dict[str, Tuple[int, int, int]] = DEFAULT_PALETTE,
         lit: bool = False, explode: Tuple[float, float, float] = (0.0, 0.0, 0.0),
         line_width: float = 1.0, alpha: float = 1.0, bevel: bool = True) -> None:
    """Draw a solid isometric slab (base plate, chassis or carriage block)."""
    ex, ey, ez = explode
    x0, y0, z0 = x + ex, y + ey, z + ez
    x1, y1, z1 = x0 + w, y0 + d, z0 + h

    # 8 vertices
    # Bottom:
    b0 = cam.project(x0, y0, z0)
    b1 = cam.project(x1, y0, z0)
    b2 = cam.project(x1, y1, z0)
    b3 = cam.project(x0, y1, z0)

    # Top:
    t0 = cam.project(x0, y0, z1)
    t1 = cam.project(x1, y0, z1)
    t2 = cam.project(x1, y1, z1)
    t3 = cam.project(x0, y1, z1)

    t0_col = palette["tone0"]
    t1_col = palette["tone1"]
    t2_col = palette["tone2"]
    t3_col = palette["accent"] if lit else palette["tone3"]
    line_col = palette["line_mid"]
    faint_col = palette["faint"]

    # In 45° azimuth / 30° elevation isometric camera:
    # Front-right face (from y0 to y1 at x1):
    p.poly([b1, b2, t2, t1], color=t1_col, alpha=alpha)
    p.path([b1, b2, t2, t1], color=line_col, width=line_width, alpha=alpha, closed=True)

    # Front-left face (from x0 to x1 at y1):
    p.poly([b3, b2, t2, t3], color=t2_col, alpha=alpha)
    p.path([b3, b2, t2, t3], color=line_col, width=line_width, alpha=alpha, closed=True)

    # Top face:
    p.poly([t0, t1, t2, t3], color=t3_col, alpha=alpha)
    p.path([t0, t1, t2, t3], color=line_col, width=line_width, alpha=alpha, closed=True)

    # Bevel highlight on the front-top edge if enabled:
    if bevel and h > 2.0:
        p.line([t3, t2], color=palette.get("accent_hi", (255, 255, 255)) if lit else (255, 255, 255),
               width=max(1.0, line_width * 0.8), alpha=alpha * 0.8)


def cylinder(p: Any, cam: IsoCamera, cx: float, cy: float, z: float,
             r: float, h: float, steps: int = 36,
             palette: Dict[str, Tuple[int, int, int]] = DEFAULT_PALETTE,
             knurl: bool = False, explode: Tuple[float, float, float] = (0.0, 0.0, 0.0),
             line_width: float = 1.0, alpha: float = 1.0, lit: bool = False) -> None:
    """Draw a vertical solid cylinder (post, collar, bezel or knob)."""
    ex, ey, ez = explode
    ccx, ccy, z0 = cx + ex, cy + ey, z + ez
    z1 = z0 + h

    angles = np.linspace(0, 2 * np.pi, steps, endpoint=False)
    pts_bot = [cam.project(ccx + r * math.cos(a), ccy + r * math.sin(a), z0) for a in angles]
    pts_top = [cam.project(ccx + r * math.cos(a), ccy + r * math.sin(a), z1) for a in angles]

    # Find silhouette edges facing camera
    # Light direction in XY plane:
    lx, ly = -0.5, 0.8
    t1_col = palette["tone1"]
    t2_col = palette["tone2"]
    t0_col = palette["tone0"]
    top_col = palette["accent"] if lit else palette["tone3"]

    # Side facets
    for i in range(steps):
        next_i = (i + 1) % steps
        mid_a = (angles[i] + angles[next_i]) / 2.0
        # Normal
        nx, ny = math.cos(mid_a), math.sin(mid_a)
        # Dot product with camera view (facing check)
        cam_dot = nx * cam.cosA + ny * cam.sinA
        if cam_dot > -0.05:  # Facing camera
            # Shading by light dot product
            lum = nx * lx + ny * ly
            if lum > 0.4:
                col = t2_col
            elif lum > -0.2:
                col = t1_col
            else:
                col = t0_col
            quad = [pts_bot[i], pts_bot[next_i], pts_top[next_i], pts_top[i]]
            p.poly(quad, color=col, alpha=alpha)

    # Bottom visible curve & top visible curve
    p.path(pts_top, color=top_col, alpha=alpha, closed=True)
    p.poly(pts_top, color=top_col, alpha=alpha)
    p.path(pts_top, color=palette["line_mid"], width=line_width, alpha=alpha, closed=True)

    # Optional knurling (vertical textured micro-stripes around bezel)
    if knurl and h >= 3.0:
        for i in range(0, steps, 2):
            nx, ny = math.cos(angles[i]), math.sin(angles[i])
            if nx * cam.cosA + ny * cam.sinA > 0.05:
                p.line([pts_bot[i], pts_top[i]], color=palette["line_lo"],
                       width=max(1.0, line_width * 0.6), alpha=alpha * 0.6)


def dial_gauge(p: Any, cam: IsoCamera, cx: float, cy: float, z: float,
               r: float = 28.0, h: float = 8.0, value_ratio: float = 0.5,
               palette: Dict[str, Tuple[int, int, int]] = DEFAULT_PALETTE,
               explode: Tuple[float, float, float] = (0.0, 0.0, 0.0),
               label: str = "", line_width: float = 1.0, alpha: float = 1.0) -> None:
    """Draw an industrial dial gauge with knurled bezel, tick marks, and moving needle."""
    # 1. Base outer bezel puck
    cylinder(p, cam, cx, cy, z, r, h, steps=48, palette=palette, knurl=True,
             explode=explode, line_width=line_width, alpha=alpha)

    ex, ey, ez = explode
    top_z = z + ez + h + 0.1
    ccx, ccy = cx + ex, cy + ey

    # 2. Recessed dial face (slightly smaller radius)
    inner_r = r * 0.82
    angles = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    inner_pts = [cam.project(ccx + inner_r * math.cos(a), ccy + inner_r * math.sin(a), top_z) for a in angles]
    p.poly(inner_pts, color=palette["tone3"], alpha=alpha)
    p.path(inner_pts, color=palette["faint"], width=1.0, alpha=alpha, closed=True)

    # 3. Radial tick marks (from 135° to 405° = 270° sweep)
    tick_start = math.radians(135)
    tick_sweep = math.radians(270)
    num_ticks = 24
    for i in range(num_ticks + 1):
        ang = tick_start + (i / num_ticks) * tick_sweep
        is_major = (i % 6 == 0)
        len_r = 4.2 if is_major else 2.2
        col = palette["line_hi"] if is_major else palette["line_lo"]
        w_px = max(1.0, line_width * (1.2 if is_major else 0.8))

        p_out = cam.project(ccx + (inner_r - 1.5) * math.cos(ang),
                            ccy + (inner_r - 1.5) * math.sin(ang), top_z)
        p_in = cam.project(ccx + (inner_r - 1.5 - len_r) * math.cos(ang),
                           ccy + (inner_r - 1.5 - len_r) * math.sin(ang), top_z)
        p.line([p_out, p_in], color=col, width=w_px, alpha=alpha)

    # 4. Center hub
    hub_pts = [cam.project(ccx + 2.5 * math.cos(a), ccy + 2.5 * math.sin(a), top_z + 0.4)
               for a in np.linspace(0, 2 * math.pi, 16)]
    p.poly(hub_pts, color=palette["line_hi"], alpha=alpha)

    # 5. Deflection needle
    needle_ang = tick_start + max(0.0, min(1.0, value_ratio)) * tick_sweep
    needle_len = inner_r - 3.5
    needle_tip = cam.project(ccx + needle_len * math.cos(needle_ang),
                             ccy + needle_len * math.sin(needle_ang), top_z + 0.5)
    needle_tail = cam.project(ccx - 4.0 * math.cos(needle_ang),
                              ccy - 4.0 * math.sin(needle_ang), top_z + 0.5)
    p.line([needle_tail, needle_tip], color=palette["accent"], width=max(1.5, line_width * 1.6), alpha=alpha)


def coil_spring(p: Any, cam: IsoCamera, p0: Tuple[float, float, float],
                p1: Tuple[float, float, float], radius: float = 5.0,
                turns: int = 6, palette: Dict[str, Tuple[int, int, int]] = DEFAULT_PALETTE,
                half: str = "both", explode: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                line_width: float = 1.2, alpha: float = 1.0) -> None:
    """Draw a spiral coil spring along a vector, split into back/front for Painter's ordering."""
    ex, ey, ez = explode
    x0, y0, z0 = p0[0] + ex, p0[1] + ey, p0[2] + ez
    x1, y1, z1 = p1[0] + ex, p1[1] + ey, p1[2] + ez

    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    length = math.hypot(dx, dy, dz)
    if length < 1e-4:
        return

    total_steps = turns * 24
    pts_3d = []
    for step in range(total_steps + 1):
        t = step / float(total_steps)
        curr_x = x0 + dx * t
        curr_y = y0 + dy * t
        curr_z = z0 + dz * t

        ang = 2 * math.pi * turns * t
        # Normal vectors perpendicular to the spring axis
        if abs(dz) > 0.9 * length:
            ox = radius * math.cos(ang)
            oy = radius * math.sin(ang)
            oz = 0.0
        else:
            ox = 0.0
            oy = radius * math.cos(ang)
            oz = radius * math.sin(ang)

        pts_3d.append((curr_x + ox, curr_y + oy, curr_z + oz, math.sin(ang)))

    col_front = palette["line_hi"]
    col_back = palette["tone1"]

    for i in range(len(pts_3d) - 1):
        pt_a = pts_3d[i]
        pt_b = pts_3d[i + 1]
        is_front = (pt_a[3] + pt_b[3]) >= 0.0

        if half == "front" and not is_front:
            continue
        if half == "back" and is_front:
            continue

        sa = cam.project(pt_a[0], pt_a[1], pt_a[2])
        sb = cam.project(pt_b[0], pt_b[1], pt_b[2])
        col = col_front if is_front else col_back
        w = line_width if is_front else line_width * 0.75
        p.line([sa, sb], color=col, width=w, alpha=alpha)


def ruler_strip(p: Any, cam: IsoCamera, x: float, y: float, z: float,
                length: float, width: float = 6.0, axis: str = "x",
                ticks_count: int = 20, major_interval: int = 5,
                palette: Dict[str, Tuple[int, int, int]] = DEFAULT_PALETTE,
                explode: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                line_width: float = 1.0, alpha: float = 1.0) -> None:
    """Draw a metal ruler strip with millimeter tick marks and engraved scale."""
    ex, ey, ez = explode
    w = length if axis == "x" else width
    d = width if axis == "x" else length
    slab(p, cam, x, y, z, w, d, h=0.8, palette=palette, explode=explode,
         line_width=line_width, alpha=alpha, bevel=False)

    top_z = z + ez + 0.82
    for i in range(ticks_count + 1):
        ratio = i / float(ticks_count)
        is_major = (i % major_interval == 0)
        t_len = width * (0.65 if is_major else 0.35)
        col = palette["line_mid"] if is_major else palette["line_lo"]

        if axis == "x":
            tx = x + ex + ratio * length
            p0 = cam.project(tx, y + ey + d, top_z)
            p1 = cam.project(tx, y + ey + d - t_len, top_z)
        else:
            ty = y + ey + ratio * length
            p0 = cam.project(x + ex + w, ty, top_z)
            p1 = cam.project(x + ex + w - t_len, ty, top_z)

        p.line([p0, p1], color=col, width=max(1.0, line_width * 0.7), alpha=alpha)
