"""Overlapping timeline compositor for motion reels.

Manages scenes with transition overlaps:
- Scenes run as pure functions: t_local -> frame
- Overlap intervals: B starts before A finishes
- Transition objects blend overlapping frames
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Callable
import numpy as np

from .transitions import Transition
from .budget import TextBudget, get_budget


@dataclass
class RenderContext:
    momentum_in: Tuple[float, float] = (0.0, 0.0)
    momentum_out: Tuple[float, float] = (0.0, 0.0)
    role: str = "solo"   # "solo" | "in" | "out"
    center: Tuple[float, float] = (960.0, 540.0)


class Timeline:
    def __init__(self, scenes: list, transitions: List[Transition]):
        if len(transitions) != len(scenes) - 1:
            raise ValueError(
                f"Number of transitions ({len(transitions)}) must be len(scenes) - 1 ({len(scenes) - 1})"
            )

        self.scenes = scenes
        self.transitions = transitions
        self.starts: List[float] = []

        cur_t = 0.0
        for i, s in enumerate(scenes):
            self.starts.append(cur_t)
            ov = transitions[i].overlap if i < len(transitions) else 0.0
            if hasattr(s, "out_dur") and s.out_dur < ov:
                s.out_dur = ov
            if i + 1 < len(scenes) and hasattr(scenes[i + 1], "in_dur") and scenes[i + 1].in_dur < ov:
                scenes[i + 1].in_dur = ov
            cur_t += s.duration - ov

        self.total = self.starts[-1] + scenes[-1].duration

    def _ctx(self, scene_i: int, tr: Transition | None = None, role: str = "solo") -> RenderContext:
        mx_in, my_in = (0.0, 0.0)
        mx_out, my_out = (0.0, 0.0)

        if scene_i > 0:
            mx_in, my_in = self.transitions[scene_i - 1].momentum
        if scene_i < len(self.transitions):
            mx_out, my_out = self.transitions[scene_i].momentum

        return RenderContext(
            momentum_in=(mx_in, my_in),
            momentum_out=(mx_out, my_out),
            role=role,
            center=(960.0, 540.0),
        )

    def render_frame(self, t: float, make_canvas: Callable) -> np.ndarray:
        budget = get_budget()
        if budget:
            budget.reset()

        # 1. Check if t is within an overlap window between scene i and scene i+1
        for i, tr in enumerate(self.transitions):
            a_end = self.starts[i] + self.scenes[i].duration
            b_start = self.starts[i + 1]

            if b_start <= t <= a_end:
                dur_ov = max(1e-4, a_end - b_start)
                p = np.clip((t - b_start) / dur_ov, 0.0, 1.0)

                ctx_a = self._ctx(i, tr, role="out")
                ctx_b = self._ctx(i + 1, tr, role="in")

                cA = make_canvas()
                self.scenes[i].render(cA, t - self.starts[i], ctx_a)
                arrA = cA.to_array()

                cB = make_canvas()
                self.scenes[i + 1].render(cB, t - b_start, ctx_b)
                arrB = cB.to_array()

                out_arr = tr.apply(arrA, arrB, float(p))
                if budget:
                    budget.check(t)
                return out_arr

        # 2. Solo scene
        active_i = 0
        for j, st in enumerate(self.starts):
            if st <= t:
                active_i = j

        ctx = self._ctx(active_i, role="solo")
        c = make_canvas()
        self.scenes[active_i].render(c, t - self.starts[active_i], ctx)
        out_arr = c.to_array()

        if budget:
            budget.check(t)
        return out_arr
