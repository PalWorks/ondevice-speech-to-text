# SPDX-License-Identifier: AGPL-3.0-only
"""Append one basic-mode session to data/sessions.jsonl.

Usage: printf %s "$text" | log_session.py MODE OUTCOME APP AUDIO_BYTES FINAL_LATENCY_S
(text on stdin, so it never appears in a process listing)
Called by bin/dictate. bin/dictate-live writes its own (richer) entries in the
same format; see docs/ANALYTICS.md for the schema.
"""
import configparser
import datetime
import json
import os
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def main():
    mode, outcome, app, audio_bytes, latency = sys.argv[1:6]
    text = sys.stdin.read()
    cfg = configparser.ConfigParser()
    cfg.read_dict({"dictate": {"log_sessions": "true", "log_text": "false", "language": "en"}})
    cfg.read(os.path.join(PROJECT, "config", "dictate.conf"))
    c = cfg["dictate"]
    if not c.getboolean("log_sessions"):
        return
    audio_s = max(int(audio_bytes) - 44, 0) / 32000  # 16 kHz mono s16 WAV
    words = len(text.split())
    entry = {
        "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": mode,
        "outcome": outcome,
        "app": app or "unknown",
        "language": os.environ.get("DICTATE_LANG", "en"),
        "audio_s": round(audio_s, 2),
        "words": words,
        "chars": len(text),
        "wpm": round(words / (audio_s / 60), 1) if audio_s > 1 and words else None,
        "final_latency_s": round(float(latency), 2),
        "final_model": os.path.basename(os.environ.get("DICTATE_MODEL", c.get("final_model", "ggml-small.en.bin"))),
    }
    if c.getboolean("log_text"):
        entry["text"] = text
    os.makedirs(os.path.join(PROJECT, "data"), exist_ok=True)
    with open(os.path.join(PROJECT, "data", "sessions.jsonl"), "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
