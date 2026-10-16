"""Build a reel: timeline compositor, typographic lint, frame render, encode, mux.

    python3 -m <pkg>.build                      full reel
    python3 -m <pkg>.build --chrome gallery     override chrome style
    python3 -m <pkg>.build --at 1.5             one full-resolution frame at 1.5s
    python3 -m <pkg>.build --stills 7           render 7 contact sheet stills
    python3 -m <pkg>.build --skip-lint          bypass typographic budget lint
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import subprocess
import tempfile
import shutil
import time
from typing import List

import numpy as np
from PIL import Image

try:
    from mg.timeline import Timeline
    from mg.budget import TextBudget, set_budget
    from mg.core import Canvas
    from mg.transitions import Slide
except ImportError:
    from engine.timeline import Timeline
    from engine.budget import TextBudget, set_budget
    from engine.core import Canvas
    from engine.transitions import Slide

from . import chrome
from . import scenes as SC
from . import theme as T

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
FRAMES = os.path.join(OUT, "frames")


def get_timeline() -> Timeline:
    scenes = SC.SCENES
    transitions = getattr(SC, "TRANSITION_PLAN", None)
    if not transitions:
        transitions = [Slide(overlap=0.5, direction="left") for _ in range(len(scenes) - 1)]
    return Timeline(scenes, transitions)


def lint_reel(tl: Timeline):
    """Enforce typographic restraint rules before committing to full render."""
    print("Linting reel against typographic restraint rules...")
    budget = TextBudget(T.W, T.H)
    set_budget(budget)
    # Sample every 0.1s
    sample_ts = np.linspace(0.0, tl.total, max(10, int(tl.total * 10)))
    for t in sample_ts:
        tl.render_frame(float(t), lambda: Canvas(T.W, T.H, ss=1, out=(T.OUT_W, T.OUT_H)))
    errs = budget.violations
    set_budget(None)
    if errs:
        print("\n" + "=" * 64)
        print("❌ [LINT FAILURE] Typographic Restraint Rules Violated:")
        for e in errs:
            print(f"  • {e}")
        print("=" * 64 + "\n")
        raise SystemExit(1)
    print("✓ [LINT PASS] Single screen levels <= 2, text area <= 12%")


def _render_chunk(args) -> int:
    f0, f1, chrome_style, ss = args
    tl = get_timeline()
    os.makedirs(FRAMES, exist_ok=True)
    for f in range(f0, f1):
        t = f / float(T.FPS)
        raw = tl.render_frame(t, lambda: Canvas(T.W, T.H, ss=ss, out=(T.OUT_W, T.OUT_H)))
        final = chrome.apply_chrome(raw, t, tl.total, style=chrome_style)
        Image.fromarray(final).save(os.path.join(FRAMES, f"f{f:04d}.png"))
    return f1 - f0


def render_at(t: float, chrome_style: str | None = None, ss: int = 2, name: str | None = None) -> str:
    tl = get_timeline()
    os.makedirs(OUT, exist_ok=True)
    raw = tl.render_frame(t, lambda: Canvas(T.W, T.H, ss=ss, out=(T.OUT_W, T.OUT_H)))
    final = chrome.apply_chrome(raw, t, tl.total, style=chrome_style)
    path = os.path.join(OUT, name or f"at_{t:.3f}.png")
    Image.fromarray(final).save(path)
    return path


def render_still(n_stills: int = 7, chrome_style: str | None = None, ss: int = 2, tag: str = "") -> str:
    tl = get_timeline()
    os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)
    ts = np.linspace(0.2, max(0.2, tl.total - 0.2), n_stills)
    rows = []
    for k, t in enumerate(ts):
        raw = tl.render_frame(float(t), lambda: Canvas(T.W, T.H, ss=ss, out=(T.OUT_W, T.OUT_H)))
        final = chrome.apply_chrome(raw, float(t), tl.total, style=chrome_style)
        img = Image.fromarray(final)
        img.save(os.path.join(OUT, f"stills/s_{k}_{t:.2f}{tag}.png"))
        rows.append(img)
    sheet = Image.new("RGB", (rows[0].width, rows[0].height * len(rows)), (0, 0, 0))
    for k, im in enumerate(rows):
        sheet.paste(im, (0, k * im.height))
    sp = os.path.join(OUT, f"sheet{tag}.jpg")
    sheet.resize((sheet.width * 3 // 5, sheet.height * 3 // 5), Image.LANCZOS).save(sp, quality=88)
    return sp


def build_audio() -> str:
    from . import audio as A

    os.makedirs(OUT, exist_ok=True)
    st, sr = A.build()
    A.write_wav(os.path.join(OUT, "track.wav"), st, sr)
    wave, spec = A.analyse(st, sr, fps=T.FPS)
    np.save(os.path.join(OUT, "wave.npy"), wave)
    np.save(os.path.join(OUT, "spec.npy"), spec)
    return os.path.join(OUT, "track.wav")


NVENC = ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr",
         "-cq", "19", "-b:v", "0", "-spatial_aq", "1", "-temporal_aq", "1",
         "-aq-strength", "12", "-bf", "3", "-pix_fmt", "yuv420p"]
X264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p"]


_ASCII_BASE = "C:\\mreel_tmp"


def find_ffmpeg() -> str:
    candidates = [
        r"D:\github\ffm\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe",
        "ffmpeg",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "ffmpeg"


FFMPEG = find_ffmpeg()


def _short_root(path):
    r"""给 ffmpeg 一个纯 ASCII 的等价路径（Windows）。

    这个用户名是中文（C:\Users\张宝玉\...），全片渲染的帧目录正好在它下面。
    实测：PATH 上那份 ffmpeg **连一个确定存在的 PNG 都读不到**，报
    "Could find no file with path ..."；把同样的帧放到 C:\pgtest\ 就正常。
    根因是非 ASCII 路径，不是 -start_number。

    做法：把路径里**第一个非 ASCII 的那一层目录**做成 ASCII 名的 junction
    （junction 不需要管理员权限），再拼回 ASCII 的余下部分。
    任何一步失败就原样返回 —— 行为与打补丁前完全一致。
    """
    try:
        p = os.path.abspath(path)
        parts = p.split(os.sep)
        idx = next((i for i, c in enumerate(parts) if c and not c.isascii()), None)
        if idx is None:
            return p                      # 整条路径本来就是 ASCII
        rest = [c for c in parts[idx + 1:] if c]
        if any(not c.isascii() for c in rest):
            return p                      # 不止一层非 ASCII，别硬来
        target = os.sep.join(parts[:idx + 1])
        if not os.path.isdir(target):
            return p
        os.makedirs(_ASCII_BASE, exist_ok=True)
        junc = os.path.join(_ASCII_BASE, "j%08x" % (abs(hash(target)) & 0xFFFFFFFF))
        if not os.path.exists(junc):
            r = subprocess.run(["cmd", "/c", "mklink", "/J", junc, target],
                               capture_output=True, text=True, encoding="gbk", errors="ignore")
            if r.returncode != 0 or not os.path.exists(junc):
                return p
        out = os.path.join(junc, *rest) if rest else junc
        return out if out.isascii() else p
    except Exception:
        return os.path.abspath(path)


def _has_nvenc() -> bool:
    try:
        out = subprocess.run([FFMPEG, "-hide_banner", "-encoders"],
                             capture_output=True, text=True).stdout
    except OSError:
        return False
    return "h264_nvenc" in out


def _encode_frames(dst: str, enc: List[str]) -> int:
    return subprocess.run([
        FFMPEG, "-y", "-v", "error", "-framerate", str(T.FPS),
        # 显式声明从 f0000.png 起（渲染就是 0-based），别依赖各版本默认值。
        # 真正的坑是 _short_root()：ffmpeg 读不了非 ASCII 路径。
        "-start_number", "0", "-i", os.path.join(_short_root(FRAMES), "f%04d.png"), *enc,
        "-movflags", "+faststart", dst,
    ]).returncode


def encode(name: str = "reel") -> str:
    silent = os.path.join(OUT, f"{name}_silent.mp4")
    for e, enc in enumerate([NVENC, X264] if _has_nvenc() else [X264]):
        if _encode_frames(silent, enc) == 0:
            break
        if e == 0:
            print("  nvenc present but failed, falling back to libx264")
    else:
        raise SystemExit("neither h264_nvenc nor libx264 could encode")
    final = os.path.join(OUT, f"{name}.mp4")
    wav = os.path.join(OUT, "track.wav")
    if os.path.exists(wav):
        # 384k 是默认头等目标；但某些环境里的 ffmpeg 用旧版 aac 编码器，
        # 会直接拒绝（"Too many bits per frame requested"）。逐档往下退，
        # 而不是在这里断掉已经渲好的整片。
        last_err = ""
        for rate in ("384k", "256k", "192k", "128k"):
            p = subprocess.run([
                FFMPEG, "-y", "-v", "error",
                "-i", _short_root(silent), "-i", _short_root(wav),
                "-c:v", "copy", "-c:a", "aac", "-strict", "-2", "-b:a", rate, "-shortest",
                "-movflags", "+faststart", _short_root(final),
            ], capture_output=True, text=True)
            if p.returncode == 0:
                if rate != "384k":
                    print(f"  aac {rate} used (384k rejected by this ffmpeg)")
                break
            last_err = (p.stderr or "").strip()
        else:
            raise SystemExit("audio mux failed at every bitrate; last error:\n" + last_err)
        try:
            os.remove(silent)
        except OSError:
            pass
        return final
    return silent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome", default=None, choices=["none", "gallery", "hud"],
                    help="override CHROME_STYLE in theme.py")
    ap.add_argument("--at", type=float, default=None, help="render single frame at timestamp t")
    ap.add_argument("--stills", type=int, default=None, help="render N preview stills")
    ap.add_argument("--ss", type=int, default=2, help="supersampling factor (default: 2)")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--skip-lint", action="store_true", help="bypass typographic lint")
    ap.add_argument("--skip-frames", action="store_true")
    ap.add_argument("--jobs", type=int, default=0)
    args = ap.parse_args()

    tl = get_timeline()
    chrome_style = args.chrome or getattr(T, "CHROME_STYLE", "gallery")

    if args.at is not None:
        p = render_at(args.at, chrome_style=chrome_style, ss=args.ss)
        print("Rendered frame:", p)
        return

    if args.stills is not None:
        p = render_still(args.stills, chrome_style=chrome_style, ss=args.ss)
        print("Rendered sheet:", p)
        return

    # 1. Preflight typographic lint
    if not args.skip_lint:
        lint_reel(tl)

    os.makedirs(OUT, exist_ok=True)
    if not args.no_audio:
        t0 = time.time()
        build_audio()
        print(f"audio  {time.time() - t0:.1f}s")

    total_frames = int(round(tl.total * T.FPS))
    if not args.skip_frames:
        t0 = time.time()
        want = args.jobs or max(1, (os.cpu_count() or 4) // 2)
        # Partition frames into chunks
        chunk_size = max(15, total_frames // (want * 2))
        chunks = []
        cur = 0
        while cur < total_frames:
            nxt = min(total_frames, cur + chunk_size)
            chunks.append((cur, nxt, chrome_style, args.ss))
            cur = nxt

        print(f"rendering {total_frames} frames ({tl.total:.2f}s) with {want} workers...")
        with mp.Pool(want) as pool:
            counts = pool.map(_render_chunk, chunks)
        print(f"frames {sum(counts)} in {time.time() - t0:.1f}s")

    out_file = encode()
    print("out:", out_file)


if __name__ == "__main__":
    main()
