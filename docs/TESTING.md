# Testing

Last updated: 2026-11-16T14:43:54+00:00

How to test changes without touching the user's desktop, data or running F9 session. The suite is in `tests/`.

## Run it

```bash
tests/run.sh                    # static checks, speaker helper, 7 scenarios (about 7 minutes)
tests/run.sh --static           # static checks and the speaker helper only (seconds)
tests/run.sh dictation tune     # static checks plus named scenarios
tests/run.sh --slow             # also the 2.5-minute monologue
tests/run.sh --keep             # keep the work folder (clips, scratch project, logs) for inspection
./install.sh --check            # always, after any change
```

Exit code 0 means everything passed. Set `TMPDIR` to choose where the work folder goes. The first run downloads the test speech (about 350 kB) into `tests/.cache/` (git-ignored).

Requirements on top of a normal install: `Xvfb`, `xfwm4`, `xfce4-terminal`, `dbus-run-session`, `ffmpeg` and numpy for `/usr/bin/python3`; `uvx` for pyflakes (skipped if missing).

## Principles

1. **Never touch the user's screen.** No typing into their windows, no pointer moves, no focus changes. Everything visual runs on a private X display (the first free number from `:99`) with its own window manager (xfwm4), under its own D-Bus session.
2. **Never touch the user's data.** Each run works on a scratch copy of `bin/dictate-live`, `config/` and `lib/` (with `models/` and `.venv/` linked), and its own `XDG_RUNTIME_DIR`, so `data/`, `transcripts/` and the live F9 session's pidfile are untouched.
3. **Use the real engines.** whisper-server, Parakeet and the speaker helper run for real; only audio capture, call detection, sounds and notifications are faked.
4. **Leave nothing running.** The runner stops the display and every process it started, even after a failure.

## What `tests/run.sh` does

**Table X1: Steps**

| Step | Checks |
|---|---|
| Static | Python compiles (system Python and `.venv`), shell syntax, pyflakes, an `SPDX-License-Identifier: AGPL-3.0-only` header in every source file |
| Speaker helper | Three phrases from two voices through `lib/speakers.py`: the helper survives a new speaker, and the final regrouping finds exactly 2 speakers with the first and third phrase together |
| Scenarios | `tests/e2e.py` under `dbus-run-session`, below |

## Test speech

whisper.cpp's public sample `samples/jfk.wav` (11 s, 16 kHz; pinned to tag v1.7.5 and checked by SHA-256). The word "country" appears twice in it, so counting it tells how much text arrived. A second voice is the same clip pitch-shifted to 0.80 (same words and speed); the speaker model scores it about 0.3 similar to the original, well under the 0.56 new-speaker threshold.

**Table X2: Clips built for each run**

| Clip | Content |
|---|---|
| `dictation` | Four copies of voice A with 1.5 s gaps, 15 s of trailing silence |
| `noisy` | The same plus a stationary rumble at about 650 RMS, the background measured on the reference mic |
| `silence` | 20 s of silence |
| `room` | A, B, A, B, A |
| `call_mic` and `call_side` | A on the mic; B only on the computer's sound, and also on the mic at a third of the volume 50 ms late (laptop speakers), plus light noise |
| `monologue` | Twelve copies of A |

## Shims

**Table X3: Fakes, first on PATH**

| Tool | Replaced by |
|---|---|
| `arecord` | ffmpeg playing the scenario's clip in real time (`-re`); records its start time |
| `parec` | ffmpeg playing `call_side` from the same moment as the mic clip |
| `pactl` | A fake source-output from "chrome" when the scenario says a call is open, otherwise none |
| `paplay` | Nothing |
| `notify-send` | Appends to a file |

`xdotool` and `xclip` run for real, on the private display only. Box buttons are found by colour in a screenshot (button background over the box), so clicks do not depend on exact positions.

## Scenarios

**Table X4: Scenarios and pass criteria**

| Scenario | Steps | Pass when |
|---|---|---|
| `dictation` | Dictation clip in termA; switch to termB at 15 s, back at 30 s, to termB at 44 s; second F9 at 57 s | Outcome `typed`, all 8 "country" in termA, termB empty, focus ends on termB, `held_flushes` ≥ 1 |
| `noisy` | Same with the noisy clip | As above, at least 7 of 8 |
| `empty-cancel` | Silence, F9 at 5 s; then dictation, SIGTERM at 20 s | `empty`; then `cancelled` with the inserted text kept and no file left in `data/live` |
| `room-meeting` | Room clip, F9 at 65 s | Outcome `meeting`, 2 speakers, "Speaker 2" in the transcript |
| `call-echo` | Call clips with a call open, F9 at 92 s | Outcome `meeting`, `call_phrases` ≥ 3, `echo_dropped` ≥ 2, at most 4 "country" typed (voice A before the switch), 12 to 14 in the transcript (no duplicates) |
| `meeting-button` | Dictation clip, click Meeting at 4 s, F9 at 40 s | `meeting_manual` true, nothing typed into termA, transcript has the text, focus stayed on termA |
| `tune` | Click Tune, then Sensitivity + and Pause + | Focus stayed on termA; the scratch config shows `speech_ratio = 2.25` and `pause_ms = 800` |
| `monologue` (`--slow`) | Monologue clip, F9 at 165 s | Outcome `typed`, no meeting |

Each line of output reads `PASS` or `FAIL`, the scenario, its duration and the measured values. A failing `tune` saves `tune-fail.png` in the work folder (use `--keep`).

## Last full run

2026-11-16 on the reference machine: all static checks, the speaker helper and 8 of 8 scenarios passed (`monologue` run separately). Phrase latency 0.6 to 1.1 s at load average 4; about 2.9 s at load average 12.

## Adding a scenario

1. Build its clip in `build_audio()` from voice A, voice B or silence; keep "country" counts predictable.
2. Write `s_<name>(r)`: `r.setup(clip, call=...)`, `r.start()`, `r.at(seconds)` for timed steps, `r.press()` for the second F9; read `r.row()` (last log line), `r.text(r.out_a)`, `r.transcript()`.
3. Return `(passed, detail)`, with the measured values in `detail`. Register it in `SCENARIOS` (and `SLOW` if it takes over two minutes).
4. Update Table X4.
