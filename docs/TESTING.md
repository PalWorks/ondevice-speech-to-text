# Testing

Last updated: 2026-11-16T12:52:17+00:00

How to test changes without touching the owner's desktop, data or F9 session. There is no committed test suite yet (ROADMAP row 18); this file is the procedure the harness follows.

## Principles

1. **Never touch the owner's screen.** No typing into their windows, no pointer moves, no focus changes. Everything visual runs on a private X display (`Xvfb :99`) with its own window manager.
2. **Never touch the owner's data.** Run a scratch copy of the code, so `data/`, `transcripts/` and the live F9 session (`$XDG_RUNTIME_DIR/dictate-live/session.pid`) are untouched.
3. **Use the real engines.** whisper-server, Parakeet and the speaker helper run for real; only audio capture, call detection and notifications are faked.
4. **Leave nothing running.** Check `pgrep -x Xvfb` before and after. A stray Xvfb from an earlier run once answered a later test's windows and produced a false failure (2026-11-16).

## Static checks (every change)

```bash
cd ~/Documents/"OnDevice Speech To Text"
/usr/bin/python3 -m py_compile bin/dictate-live bin/dictate-stats
uvx pyflakes bin/dictate-live lib/speakers.py
./install.sh --check            # every line [ok]
rm -rf bin/__pycache__ lib/__pycache__
```

## The scratch copy

```bash
S=<session scratchpad>/e2e                      # never inside the project folder
P=~/Documents/"OnDevice Speech To Text"
mkdir -p "$S"/{proj/bin,proj/data,shim,run}
cp "$P/bin/dictate-live" "$S/proj/bin/"
cp -r "$P/config" "$P/lib" "$S/proj/"
ln -sfn "$P/models" "$S/proj/models"
ln -sfn "$P/.venv"  "$S/proj/.venv"
```

`bin/dictate-live` finds its project through `realpath`, so the copy writes `data/` and `transcripts/` inside `$S/proj`. Set `XDG_RUNTIME_DIR=$S/run` so its pidfile never meets the owner's session.

## Shims (first on PATH)

**Table X1: Shims**

| Tool | Replaced by | Why |
|---|---|---|
| `arecord` | `exec ffmpeg -v quiet -re -i <clip.wav> -f s16le -ac 1 -ar 16000 -` | Plays a known clip in real time. Add trailing silence to the clip instead of looping; never use `apad` (faster than real time). For call tests, also write `date +%s.%N` to a file so `parec` can start at the same offset |
| `parec` | `ffmpeg -re -ss <seconds since arecord started> -i call.wav ...` | The other side of a call, aligned with the mic clip |
| `pactl` | Prints `[]`, or for a call a fake source-output: `[{"index":9,"source":1,"properties":{"application.process.binary":"chrome","application.process.id":"4242"}}]`, and for `list sources` a mic plus a `.monitor` source | Controls whether a call looks open |
| `paplay` | `exit 0` | No sounds |
| `notify-send` | Appends its arguments to a file | Checks notifications without showing them |

`xdotool` and `xclip` run for real, on display `:99` only.

## The test display

```bash
cat > "$S/run-scenario.sh" <<'EOF'
#!/bin/bash
export DISPLAY=:99 XDG_RUNTIME_DIR=$S/run PATH=$S/shim:$PATH
Xvfb :99 -screen 0 1280x800x24 >/dev/null 2>&1 & sleep 1
xfwm4 --display=:99 --compositor=off --sm-client-disable >/dev/null 2>&1 & sleep 2
xfce4-terminal --disable-server --title=termA -x sh -c "stty -icanon -echo; cat > $S/a.txt" >/dev/null 2>&1 &
xfce4-terminal --disable-server --title=termB -x sh -c "stty -icanon -echo; cat > $S/b.txt" >/dev/null 2>&1 &
sleep 3
A=$(xdotool search --onlyvisible --name termA | head -1)
xdotool windowactivate --sync "$A"
/usr/bin/python3 "$S/proj/bin/dictate-live" 2>"$S/err.log" & DL=$!
# ... scenario steps: xdotool windowactivate, sleeps, screenshots ...
/usr/bin/python3 "$S/proj/bin/dictate-live"      # the second F9 press
wait $DL
kill $(jobs -p) 2>/dev/null
EOF
dbus-run-session -- bash "$S/run-scenario.sh"
```

- `dbus-run-session` keeps xfwm4's session bus away from the owner's.
- The terminals write what they receive to `a.txt` and `b.txt` (`-icanon` so nothing waits for Enter).
- Screenshot: `ffmpeg -v quiet -y -f x11grab -video_size 1280x800 -i :99 -frames:v 1 shot.png`.
- Clicking a box button: find the box's top edge in a raw screenshot (first row of colour (28, 28, 32) in column x=330), then `xdotool mousemove <x> <top+33> click 1`. Buttons in the top row, left to right: Meeting, Tune, Cancel.

## Test audio

Speech clips with known content, joined with silences by ffmpeg (`concat` filter) or numpy:

- **Dictation clip**: four phrases of one voice with 1.5 s gaps and 15 s of trailing silence.
- **Noisy clip**: the same mixed with pink noise at about 650 RMS (`anoisesrc=c=pink:a=0.11`, `amix ... normalize=0`), close to the owner's measured background.
- **Room meeting clip**: voice A and voice B alternating, B reaching 23 s over three phrases.
- **Call pair**: `mic_call.wav` (voice A, plus voice B at 0.35 volume 50 ms late, as through laptop speakers, plus light noise) and `call.wav` (voice B alone at the same times).
- **Monologue**: one voice for 2.5 minutes.

## Scenarios

**Table X2: Scenarios and expected results**

| # | Scenario | Pass when |
|---|---|---|
| 1 | Dictation clip; switch to termB at 11 s, back at 23 s, to termB at 32 s, F9 at 39 s | All four phrases reach `a.txt` in order, `b.txt` empty, focus ends on termB; log: `typed`, `held_flushes` ≥ 1 |
| 2 | Noisy clip, same steps | No words missing in `a.txt` (a sentence may be split) |
| 3 | Silence only, F9 at 4 s; then Cancel (SIGTERM) mid-speech | `empty`; then `cancelled` with inserted phrases kept and `data/live` empty |
| 4 | Room meeting clip | Outcome `meeting`, 2 speakers, transcript turns alternate correctly; before the switch, text typed into termA |
| 5 | Call pair with the call `pactl` shim | `echo_dropped` = number of B phrases, `call_phrases` = the same, nothing of B in `a.txt`, transcript has each B line once |
| 6 | Monologue | No meeting; every phrase typed |
| 7 | Click Meeting 4 s in, F9 at 45 s | `a.txt` empty, `meeting_manual` true, transcript saved, "Transcript saved" shown |
| 8 | Click Tune, then Sensitivity + and Pause + | Focus stays on termA; the copy's `config/dictate.conf` shows the new `speech_ratio` and `pause_ms` |

Read results from `$S/proj/data/sessions.jsonl` (last line), `$S/a.txt`, `$S/b.txt`, `$S/proj/transcripts/` and `$S/err.log` (must have no traceback).

## Unit-level checks

- Speaker helper: pipe `{"cmd":"assign",...}` lines for three clips and `{"cmd":"final"}` into `.venv/bin/python -I lib/speakers.py models/nemo_en_titanet_small.onnx`; a new voice must get a new label without the helper dying.
- Regrouping speed: 800 random 192-dimension vectors cluster in under a second (`final_labels`).
- Insertion paths without a display: import `bin/dictate-live` with `SourceFileLoader`, point `PROJECT` and `BACKUP_FILE` at the scratch folder, and drive `_insert_final` with a shimmed `xdotool`.
- Call detection on the real desktop is read-only and safe: `call_open(set())` should be `False` with no call open.

## Afterwards

- `pgrep -x Xvfb` prints nothing.
- The owner's `data/` and `transcripts/` are unchanged (compare `ls -la` before and after).
- `bin/__pycache__` and `lib/__pycache__` removed.
