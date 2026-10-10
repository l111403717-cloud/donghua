#!/usr/bin/env python3
"""Xiaomi MiMo TTS voiceover synthesizer.

Usage:
    py -3 tts_voice.py --text "人生中很多最后一面，往往发生在一个极其普通的午后。" --out assets/voice.wav
    py -3 tts_voice.py --file script.txt --style "语速慢、温柔叙事、深沉感伤" --out assets/voice.wav
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error

DEFAULT_API_KEY = "sk-c4cebl17h20cecdg4rdrgldzjr0l592jgw8r4x5bkuv9dz9x"
ENDPOINT = "https://api.xiaomimimo.com/v1/chat/completions"
MODEL = "mimo-v2.5-tts"


def synthesize(text: str, out_path: str, style: str = "", api_key: str = DEFAULT_API_KEY) -> str:
    """Call Xiaomi MiMo TTS to generate voice audio file."""
    if style:
        content = f"<style>{style}</style>{text}"
    else:
        content = text

    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "assistant", "content": content}],
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
            with open(out_abs, "wb") as f:
                f.write(raw)
            print(f"✓ Generated TTS audio: {out_abs} ({len(raw)} bytes)")
            return out_abs
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        print(f"HTTP Error {e.code}: {err_msg}", file=sys.stderr)
        raise


def main():
    ap = argparse.ArgumentParser(description="Generate voiceover using Xiaomi TTS")
    ap.add_argument("--text", default="", help="Voiceover text string")
    ap.add_argument("--file", default="", help="File containing voiceover text")
    ap.add_argument("--style", default="", help="Style tag e.g. '语速慢、温柔叙事、深沉感伤'")
    ap.add_argument("--out", default="assets/voice.wav", help="Output wav audio path")
    ap.add_argument("--key", default=DEFAULT_API_KEY, help="Xiaomi TTS API key")
    args = ap.parse_args()

    content = args.text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read().strip()

    if not content:
        ap.error("Must provide either --text or --file")

    synthesize(content, args.out, style=args.style, api_key=args.key)


if __name__ == "__main__":
    main()
