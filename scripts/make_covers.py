"""High-CTR (Click-Through Rate) Prominent Cover Generator for anatomy_reel.

Design Philosophy:
- IMPORTANT INFORMATION AT THE ABSOLUTE FOCAL POINT (核心信息第一视线焦点).
- Giant High-Contrast Typography (超大冲击力字号，缩略图一眼看清).
- Engineering Visual Backdrop (等轴测机械解剖作为高质量质感托底).
- Zero Overlap, Zero Clutter, Zero Tofu Boxes (零文字重叠，零乱码).
"""
from __future__ import annotations

import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = r"d:\.aaaiduihua\体验skill\anatomy_reel"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from mg.core import Canvas, clip01, gauss
from mg.iso import (IsoCamera, slab, cylinder, dial_gauge, coil_spring, DEFAULT_PALETTE)

COVERS_DIR = os.path.join(ROOT_DIR, "covers")
os.makedirs(COVERS_DIR, exist_ok=True)

# Color Scheme: High-Contrast Industrial Impact
PAPER = (240, 242, 246)
DARK_INK = (15, 20, 28)           # Deep black-ink for maximum text contrast
ACCENT_ORANGE = (235, 80, 25)      # Safety punch orange
ACCENT_BG = (255, 243, 238)        # Warm subtle orange tint
SLATE_GREY = (75, 85, 100)
LINE_LO = (175, 185, 198)
LINE_FAINT = (220, 226, 234)
CARD_BG = (255, 255, 255)
CARD_BORDER = (205, 215, 226)

def load_font(font_name: str, size: int):
    win_font = os.path.join(r"C:\Windows\Fonts", font_name)
    if os.path.exists(win_font):
        try:
            return ImageFont.truetype(win_font, size)
        except Exception:
            pass
    return ImageFont.load_default()

# Huge Impact Fonts for Mobile Feed Readability
font_hero_xxl = load_font("msyhbd.ttc", 82)    # Giant Main Title
font_hero_xl  = load_font("msyhbd.ttc", 72)    # Horizontal Main Title
font_hero_lg  = load_font("msyhbd.ttc", 62)    # Punchy Question Subtitle
font_hero_md  = load_font("msyhbd.ttc", 52)    # Subtitle for 4:3
font_sub_bold = load_font("msyhbd.ttc", 36)    # Golden Insight
font_body_sm  = load_font("msyh.ttc", 24)      # Small detail
font_tag_pill = load_font("msyhbd.ttc", 22)    # Category badge
font_mono     = load_font("arialbd.ttf", 16)
font_mono_sm  = load_font("arialbd.ttf", 13)


def draw_grid_background(p, c: Canvas, w: int, h: int):
    """Draw clean drafting grid background."""
    c.clear(PAPER)
    # Ambient corner light
    c.add += (np.array([0.025, 0.03, 0.04], np.float32)
              * gauss(w, h, w * 0.8, h * 0.2, w * 0.6, h * 0.6)[..., None])

    step = 100
    for x in range(step, w, step):
        p.line([(x, 20), (x, h - 20)], color=LINE_FAINT, width=1.0, alpha=0.40)
    for y in range(step, h, step):
        p.line([(20, y), (w - 20, y)], color=LINE_FAINT, width=1.0, alpha=0.40)

    # Crosshairs
    m = 40
    for cx, cy in [(m, m), (w - m, m), (m, h - m), (w - m, h - m)]:
        p.line([(cx - 15, cy), (cx + 15, cy)], color=LINE_LO, width=1.2, alpha=0.7)
        p.line([(cx, cy - 15), (cx, cy + 15)], color=LINE_LO, width=1.2, alpha=0.7)


def render_mechanism(p, cam: IsoCamera, explode_ratio: float = 0.9):
    """Render high-craft exploded mechanism parts."""
    pal = DEFAULT_PALETTE
    exp = explode_ratio

    # Four base blocks
    dist = 58.0 + 36.0 * exp
    slab(p, cam, -dist - 20, -dist - 20, 0, 40, 40, 14, palette=pal, bevel=True)
    slab(p, cam, dist - 20, -dist - 20, 0, 40, 40, 14, palette=pal, bevel=True)
    slab(p, cam, -dist - 20, dist - 20, 0, 40, 40, 14, palette=pal, bevel=True)
    slab(p, cam, dist - 20, dist - 20, 0, 40, 40, 14, palette=pal, lit=True, bevel=True)

    # Springs
    spr_len = 16.0 + 34.0 * exp
    coil_spring(p, cam, (-14, 0, 20), (-spr_len, 0, 20), radius=7.0, turns=5, palette=pal)
    coil_spring(p, cam, (14, 0, 20), (spr_len, 0, 20), radius=7.0, turns=5, palette=pal)
    coil_spring(p, cam, (0, -14, 20), (0, -spr_len, 20), radius=7.0, turns=5, palette=pal)
    coil_spring(p, cam, (0, 14, 20), (0, spr_len, 20), radius=7.0, turns=5, palette=pal)

    # Double knurled hub
    hub_z = 22.0 + 48.0 * exp
    cylinder(p, cam, -10, 0, hub_z, r=24, h=12, steps=36, knurl=True, palette=pal)
    cylinder(p, cam, 12, 0, hub_z + 8, r=24, h=12, steps=36, knurl=True, palette=pal, lit=True)

    # Elevated dial gauge
    zenith_z = hub_z + 58.0 * exp + 15.0
    dial_gauge(p, cam, 0, 0, zenith_z, r=38, h=10, value_ratio=0.92, palette=pal)


# --------------------------------------------------------------------------
# 1. 9:16 Vertical Cover (1080x1920) - 抖音/快手/视频号移动第一流
# --------------------------------------------------------------------------
def make_cover_9x16():
    w, h = 1080, 1920
    c = Canvas(w, h)
    p = c.pass_()
    draw_grid_background(p, c, w, h)

    # Place Mechanism in lower-middle background as visual anchor
    cam = IsoCamera(540, 1420, scale=2.4)
    render_mechanism(p, cam, explode_ratio=0.95)
    c.commit()

    img = c.image()
    draw = ImageDraw.Draw(img)
    cx = w // 2

    # --- TOP PROMINENT HERO CARD (最显眼的核心信息超级视觉焦点) ---
    # Centered in the top-to-middle golden reading zone (y: 180 ~ 950)
    card_margin = 48
    card_top = 180
    card_w = w - card_margin * 2
    card_h = 720
    card_rect = [card_margin, card_top, card_margin + card_w, card_top + card_h]

    # Solid High-End White Architectural Plate with Double Layer Shadow/Border
    draw.rounded_rectangle(card_rect, radius=24, fill=CARD_BG, outline=CARD_BORDER, width=2)
    # Top Industrial Safety Orange Highlight Accent Bar
    draw.rounded_rectangle([card_margin, card_top, card_margin + card_w, card_top + 10],
                           radius=5, fill=ACCENT_ORANGE)

    # 1. Category Tag Pill inside Card
    tag_y = card_top + 45
    tag_text = "● 情绪动力学 · 深度解剖实验报告"
    t_bbox = font_tag_pill.getbbox(tag_text)
    tw, th = t_bbox[2] - t_bbox[0], t_bbox[3] - t_bbox[1]
    draw.rounded_rectangle([cx - tw // 2 - 20, tag_y, cx + tw // 2 + 20, tag_y + th + 14],
                           radius=8, fill=ACCENT_BG, outline=ACCENT_ORANGE, width=1)
    draw.text((cx, tag_y + 6), tag_text, font=font_tag_pill, fill=ACCENT_ORANGE, anchor="mt")

    # 2. GIANT MAIN TITLE (超级大字，第一眼抓住眼球)
    t1_y = tag_y + 75
    draw.text((cx, t1_y), "微信拉黑了", font=font_hero_xxl, fill=DARK_INK, anchor="mt")
    t1_2_y = t1_y + 98
    draw.text((cx, t1_2_y), "合照也删光了", font=font_hero_xxl, fill=DARK_INK, anchor="mt")

    # 3. PUNCHY ORANGE QUESTION (最具冲击力的痛点提问，超大字号)
    t2_y = t1_2_y + 115
    draw.text((cx, t2_y), "可为什么，你还是忘不掉？", font=font_hero_lg, fill=ACCENT_ORANGE, anchor="mt")

    # Decorative Technical Divider Line
    div_y = t2_y + 90
    draw.line([(card_margin + 50, div_y), (card_margin + card_w - 50, div_y)], fill=LINE_FAINT, width=2)
    draw.ellipse([cx - 5, div_y - 5, cx + 5, div_y + 5], fill=ACCENT_ORANGE)

    # 4. GOLDEN CONCLUSION (核心反常识解答，加粗显眼)
    ans_y = div_y + 35
    draw.text((cx, ans_y), "“ 他早就把你的生活习惯，", font=font_sub_bold, fill=DARK_INK, anchor="mt")
    draw.text((cx, ans_y + 48), "重新装配了一遍。”", font=font_sub_bold, fill=DARK_INK, anchor="mt")

    # Technical sub-caption
    draw.text((cx, ans_y + 105), "身体记住的每一道刻度 · 你来过 · 我再也变不回从前",
              font=font_body_sm, fill=SLATE_GREY, anchor="mt")

    # --- BOTTOM FLOATING SPEC BADGE ---
    bot_y = h - 120
    draw.text((cx, bot_y), "SCALE 1:1.0 · EXPLODED ANATOMY · 44S NARRATIVE",
              font=font_mono, fill=SLATE_GREY, anchor="mt")
    draw.text((cx, bot_y + 26), "DONGHUA SKILL · ISOMETRIC ANATOMY SYSTEM",
              font=font_mono_sm, fill=LINE_LO, anchor="mt")

    out_file = os.path.join(COVERS_DIR, "cover_9x16_1080x1920.png")
    img.save(out_file, quality=96)
    print("Exported 9:16 High-CTR Cover:", out_file)


# --------------------------------------------------------------------------
# 2. 3:4 Vertical Cover (1080x1440) - 小红书 Feed 封面（信息极度显眼）
# --------------------------------------------------------------------------
def make_cover_3x4():
    w, h = 1080, 1440
    c = Canvas(w, h)
    p = c.pass_()
    draw_grid_background(p, c, w, h)

    # Place Mechanism in bottom area with clear breathing margin
    cam = IsoCamera(540, 1120, scale=2.10)
    render_mechanism(p, cam, explode_ratio=0.88)
    c.commit()

    img = c.image()
    draw = ImageDraw.Draw(img)
    cx = w // 2

    # Prominent Hero Card for 3:4 (紧凑且极度显眼)
    card_margin = 44
    card_top = 90
    card_w = w - card_margin * 2
    card_h = 490
    card_rect = [card_margin, card_top, card_margin + card_w, card_top + card_h]

    draw.rounded_rectangle(card_rect, radius=20, fill=CARD_BG, outline=CARD_BORDER, width=2)
    draw.rounded_rectangle([card_margin, card_top, card_margin + card_w, card_top + 8],
                           radius=4, fill=ACCENT_ORANGE)

    # 1. Tag
    tag_y = card_top + 32
    tag_text = "● 情绪机械解剖 · 44秒深度叙事"
    draw.text((cx, tag_y), tag_text, font=font_tag_pill, fill=ACCENT_ORANGE, anchor="mt")

    # 2. Giant Title
    t1_y = tag_y + 52
    draw.text((cx, t1_y), "微信拉黑了，合照删光了", font=font_hero_xl, fill=DARK_INK, anchor="mt")

    # 3. Punchy Question
    t2_y = t1_y + 86
    draw.text((cx, t2_y), "可为什么，你还是忘不掉？", font=font_hero_lg, fill=ACCENT_ORANGE, anchor="mt")

    # Divider
    div_y = t2_y + 78
    draw.line([(card_margin + 40, div_y), (card_margin + card_w - 40, div_y)], fill=LINE_FAINT, width=2)

    # 4. Answer
    ans_y = div_y + 26
    draw.text((cx, ans_y), "“ 他早就把你的生活习惯，重新装配了一遍 ”",
              font=font_sub_bold, fill=DARK_INK, anchor="mt")
    draw.text((cx, ans_y + 48), "散场的是两个人 · 留下的是被重塑的你",
              font=font_body_sm, fill=SLATE_GREY, anchor="mt")

    # Bottom Callout
    draw.text((cx, h - 60), "ISOMETRIC ANATOMY · EXPLODED VIEW", font=font_mono, fill=SLATE_GREY, anchor="mt")

    out_file = os.path.join(COVERS_DIR, "cover_3x4_1080x1440.png")
    img.save(out_file, quality=96)
    print("Exported 3:4 High-CTR Cover:", out_file)


# --------------------------------------------------------------------------
# 3. 16:9 Landscape Cover (1920x1080) - B站 / 视频号 / 横屏极显眼大字
# --------------------------------------------------------------------------
def make_cover_16x9():
    w, h = 1920, 1080
    c = Canvas(w, h)
    p = c.pass_()
    draw_grid_background(p, c, w, h)

    # Place Giant Exploded Mechanism on Right
    cam = IsoCamera(1490, 600, scale=2.50)
    render_mechanism(p, cam, explode_ratio=0.98)
    c.commit()

    img = c.image()
    draw = ImageDraw.Draw(img)

    # --- LEFT HERO INFORMATION BOARD (占画面左侧超大面积，视线第一落点) ---
    left_x = 90
    top_y = 100
    board_w = 900
    board_h = 880

    # Clean Architectural Card Plate with Orange Indicator Bar
    draw.rounded_rectangle([left_x, top_y, left_x + board_w, top_y + board_h],
                           radius=24, fill=CARD_BG, outline=CARD_BORDER, width=2)
    # Left Vertical Orange Highlight Strip
    draw.rounded_rectangle([left_x, top_y, left_x + 12, top_y + board_h],
                           radius=6, fill=ACCENT_ORANGE)

    content_x = left_x + 55

    # 1. Category Tag Pill
    tag_y = top_y + 60
    tag_text = "● ISOMETRIC ANATOMY · 情绪机械解剖实验报告"
    t_bbox = font_tag_pill.getbbox(tag_text)
    tw, th = t_bbox[2] - t_bbox[0], t_bbox[3] - t_bbox[1]
    draw.rounded_rectangle([content_x, tag_y, content_x + tw + 32, tag_y + th + 16],
                           radius=8, fill=ACCENT_BG, outline=ACCENT_ORANGE, width=1)
    draw.text((content_x + 16, tag_y + 7), tag_text, font=font_tag_pill, fill=ACCENT_ORANGE)

    # 2. GIANT MAIN TITLE (82px 极粗黑体，第一视觉冲击)
    t1_y = tag_y + 75
    draw.text((content_x, t1_y), "微信拉黑了，", font=font_hero_xxl, fill=DARK_INK)
    draw.text((content_x, t1_y + 98), "合照删光了。", font=font_hero_xxl, fill=DARK_INK)

    # 3. PUNCHY ORANGE QUESTION (72px 亮橙色超大字号提问)
    t2_y = t1_y + 215
    draw.text((content_x, t2_y), "可为什么，你还是忘不掉？", font=font_hero_xl, fill=ACCENT_ORANGE)

    # Divider Line
    div_y = t2_y + 110
    draw.line([(content_x, div_y), (content_x + board_w - 90, div_y)], fill=LINE_FAINT, width=2)

    # 4. CORE INSIGHT QUOTE (核心反常识解答金句)
    ans_y = div_y + 40
    draw.text((content_x, ans_y), "“ 他早就把你的生活习惯，重新装配了一遍。”",
              font=font_sub_bold, fill=DARK_INK)
    draw.text((content_x, ans_y + 55), "身体记住的每一道刻度 / 你来过 / 我再也变不回从前",
              font=font_body_sm, fill=SLATE_GREY)

    # 5. Technical Spec
    spec_y = top_y + board_h - 75
    draw.text((content_x, spec_y), "FIG 04. EXPLODED DYNAMICS / 44.0S DEEP NARRATIVE / 96 BPM",
              font=font_mono, fill=SLATE_GREY)

    out_file = os.path.join(COVERS_DIR, "cover_16x9_1920x1080.png")
    img.save(out_file, quality=96)
    print("Exported 16:9 High-CTR Cover:", out_file)


# --------------------------------------------------------------------------
# 4. 4:3 Landscape Cover (1440x1080) - iPad / 网页通栏
# --------------------------------------------------------------------------
def make_cover_4x3():
    w, h = 1440, 1080
    c = Canvas(w, h)
    p = c.pass_()
    draw_grid_background(p, c, w, h)

    cam = IsoCamera(1100, 600, scale=2.15)
    render_mechanism(p, cam, explode_ratio=0.92)
    c.commit()

    img = c.image()
    draw = ImageDraw.Draw(img)

    left_x = 65
    top_y = 90
    board_w = 760
    board_h = 900

    draw.rounded_rectangle([left_x, top_y, left_x + board_w, top_y + board_h],
                           radius=22, fill=CARD_BG, outline=CARD_BORDER, width=2)
    draw.rounded_rectangle([left_x, top_y, left_x + 10, top_y + board_h],
                           radius=5, fill=ACCENT_ORANGE)

    content_x = left_x + 45

    # Tag
    tag_y = top_y + 50
    draw.text((content_x, tag_y), "● ISOMETRIC ANATOMY · 情绪机械解剖",
              font=font_tag_pill, fill=ACCENT_ORANGE)

    # Title
    t1_y = tag_y + 65
    draw.text((content_x, t1_y), "微信拉黑了", font=font_hero_xl, fill=DARK_INK)
    draw.text((content_x, t1_y + 86), "合照删光了", font=font_hero_xl, fill=DARK_INK)

    # Question
    t2_y = t1_y + 190
    draw.text((content_x, t2_y), "可为什么，你还是忘不掉？", font=font_hero_md, fill=ACCENT_ORANGE)

    # Divider
    div_y = t2_y + 90
    draw.line([(content_x, div_y), (content_x + board_w - 90, div_y)], fill=LINE_FAINT, width=2)

    # Quote
    ans_y = div_y + 35
    draw.text((content_x, ans_y), "“ 他早就把你的生活习惯，", font=font_sub_bold, fill=DARK_INK)
    draw.text((content_x, ans_y + 46), "重新装配了一遍。”", font=font_sub_bold, fill=DARK_INK)

    draw.text((content_x, ans_y + 105), "散场的是两个人 · 留下的是被重塑的你",
              font=font_body_sm, fill=SLATE_GREY)

    out_file = os.path.join(COVERS_DIR, "cover_4x3_1440x1080.png")
    img.save(out_file, quality=96)
    print("Exported 4:3 High-CTR Cover:", out_file)


def main():
    print("=== Generating High-CTR Covers with Prominent Information Hierarchy ===")
    make_cover_9x16()
    make_cover_3x4()
    make_cover_16x9()
    make_cover_4x3()
    print("=== All 4 Prominent High-CTR Covers Successfully Generated! ===")


if __name__ == "__main__":
    main()
