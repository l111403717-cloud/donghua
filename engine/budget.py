"""Text budget & linting for motion graphics reels.

Enforces typographic restraint at build time:
- Max levels <= 2 (L1 Hero, L2 Support)
- Text bounding box area <= 12% of total frame area
- Rejects clutter and unreadable micro-copy
"""
from __future__ import annotations

from typing import List, Tuple, Set


class TextBudget:
    MAX_LEVELS = 2
    MAX_AREA_RATIO = 0.12

    def __init__(self, w: int = 1920, h: int = 1080):
        self.w = w
        self.h = h
        self.area = float(w * h)
        self.items: List[Tuple[int, Tuple[float, float, float, float], str]] = []
        self._all_violations: List[str] = []

    def reset(self):
        self.items = []

    def record(self, level: int, bbox: Tuple[float, float, float, float], text: str):
        """Record a rendered text block.
        level: 1 (Hero/L1) or 2 (Sub/L2)
        bbox: (x0, y0, x1, y1) in canvas coordinates
        """
        self.items.append((int(level), bbox, str(text)))

    def check(self, t: float) -> List[str]:
        """Validate the active frame against typographic restraint rules."""
        errs = []
        if not self.items:
            return errs

        levels: Set[int] = {lv for lv, _, _ in self.items}
        if len(levels) > self.MAX_LEVELS:
            errs.append(
                f"[Lint Error] t={t:.2f}s: 文字层级过多 (存在 {len(levels)} 层 > 上限 {self.MAX_LEVELS} 层). "
                f"请削减至最多 L1(主标题) + L2(副标/字幕) 两层。"
            )

        total_text_area = 0.0
        for _, (x0, y0, x1, y1), _ in self.items:
            bw = max(0.0, x1 - x0)
            bh = max(0.0, y1 - y0)
            total_text_area += bw * bh

        ratio = total_text_area / max(1.0, self.area)
        if ratio > self.MAX_AREA_RATIO:
            errs.append(
                f"[Lint Error] t={t:.2f}s: 文字面积占比超标 ({ratio:.1%} > 上限 {self.MAX_AREA_RATIO:.1%}). "
                f"画面留白不足，请缩减字数或放大留白区域。"
            )

        self._all_violations.extend(errs)
        return errs

    @property
    def violations(self) -> List[str]:
        return list(dict.fromkeys(self._all_violations))


# Global budget instance attached to active render pipeline
_CURRENT_BUDGET: TextBudget | None = None


def get_budget() -> TextBudget | None:
    return _CURRENT_BUDGET


def set_budget(b: TextBudget | None):
    global _CURRENT_BUDGET
    _CURRENT_BUDGET = b
