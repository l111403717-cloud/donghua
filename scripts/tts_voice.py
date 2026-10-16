#!/usr/bin/env python3
"""Xiaomi MiMo TTS voiceover synthesizer.

Defaults to the signature Taiwanese emotional female voice:
"一位20多岁纯正台湾国语年轻女生，地道台湾腔极其明显。声调感情非常足，语调忽高忽低、尾音自然上扬带情绪，有典型台湾女生急躁吵架、心急跺脚的语调起伏。感情非常饱满，既有恨铁不成钢的气恼，又有真情实感的痛心质问。"

Usage:
    py -3 tts_voice.py --text "吼！你真的很奇怪耶！" --out assets/voice.wav
    py -3 tts_voice.py --file script.txt --out assets/voice.wav
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

DEFAULT_API_KEY = "sk-c4cebl17h20cecdg4rdrgldzjr0l592jgw8r4x5bkuv9dz9x"
ENDPOINT = "https://api.xiaomimimo.com/v1/chat/completions"
MODEL = "mimo-v2.5-tts-voicedesign"

# 内置默认音色：地道台湾腔 · 急躁动情声调版（用户定调专属音色）
DEFAULT_PROMPT = (
    "一位20多岁纯正台湾国语年轻女生，地道台湾腔极其明显。"
    "声调感情非常足，语调忽高忽低、尾音自然上扬带情绪，有典型台湾女生急躁吵架、心急跺脚的语调起伏。"
    "感情非常饱满，既有恨铁不成钢的气恼，又有真情实感的痛心质问。"
)

FFMPEG_CANDIDATES = [
    r"D:\github\ffm\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe",
    "ffmpeg",
]


def find_ffmpeg() -> str:
    for c in FFMPEG_CANDIDATES:
        if os.path.exists(c):
            return c
    return "ffmpeg"


def synthesize(text: str, out_path: str, prompt: str = DEFAULT_PROMPT,
               gain: float = 1.8, api_key: str = DEFAULT_API_KEY) -> str:
    """Call Xiaomi MiMo VoiceDesign TTS to generate voice audio file."""
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": text}
        ],
        "audio": {"format": "wav"},
        "stream": False
    }).encode("utf-8")

    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Content-Type": "application/json",
        "api-key": api_key
    })

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            b64_audio = data.get("choices", [{}])[0].get("message", {}).get("audio", {}).get("data")
            if not b64_audio:
                raise RuntimeError(f"No audio returned in response: {data}")
            raw = base64.b64decode(b64_audio)
            out_abs = os.path.abspath(out_path)
            os.makedirs(os.path.dirname(out_abs), exist_ok=True)

            if gain > 1.01 or gain < 0.99:
                tmp_raw = out_abs + ".raw.tmp.wav"
                with open(tmp_raw, "wb") as f:
                    f.write(raw)
                ffmpeg_bin = find_ffmpeg()
                cmd = [ffmpeg_bin, "-y", "-i", tmp_raw, "-filter:a", f"volume={gain:.2f}", out_abs]
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    if os.path.exists(tmp_raw):
                        os.remove(tmp_raw)
                except OSError:
                    pass
                if res.returncode != 0:
                    # Fallback to saving raw if ffmpeg failed
                    with open(out_abs, "wb") as f:
                        f.write(raw)
            else:
                with open(out_abs, "wb") as f:
                    f.write(raw)

            size = os.path.getsize(out_abs)
            print(f"✓ Generated TTS audio (Taiwanese Emotional Voice): {out_abs} ({size} bytes)")
            return out_abs
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        print(f"HTTP Error {e.code}: {err_msg}", file=sys.stderr)
        raise


def main():
    ap = argparse.ArgumentParser(description="Generate voiceover using Xiaomi VoiceDesign TTS")
    ap.add_argument("--text", default="", help="Voiceover text string")
    ap.add_argument("--file", default="", help="File containing voiceover text")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT, help="Persona/timbre prompt (defaults to Taiwanese emotional voice)")
    ap.add_argument("--style", default="", help="Additional style description (appends to prompt)")
    ap.add_argument("--gain", type=float, default=1.8, help="Output volume gain factor (default: 1.8)")
    ap.add_argument("--out", default="assets/voice.wav", help="Output wav audio path")
    ap.add_argument("--key", default=DEFAULT_API_KEY, help="Xiaomi TTS API key")
    args = ap.parse_args()

    content = args.text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read().strip()

    if not content:
        ap.error("Must provide either --text or --file")

    active_prompt = args.prompt
    if args.style:
        active_prompt = f"{active_prompt} {args.style}"

    synthesize(content, args.out, prompt=active_prompt, gain=args.gain, api_key=args.key)


if __name__ == "__main__":
    main()
