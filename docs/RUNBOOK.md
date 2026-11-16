# Runbook

Last updated: 2026-11-16T12:52:17+00:00

What to do when F9 dictation misbehaves. Start with `./install.sh --check` from the project folder; it checks every dependency, link, model and the F9 binding.

## Where to look

**Table R1: Signals**

| Source | Shows |
|---|---|
| `tail -3 data/sessions.jsonl` | Outcome and numbers of the last sessions (`docs/ANALYTICS.md` explains each field) |
| `dictate-stats --days 7` | Outcomes, speed, apps, trends |
| `ls data/live/` | A file here means a session crashed; it holds that session's text |
| `data/dictations.txt` | The last 20 sessions' text, newest first |
| `transcripts/` | Meeting transcripts |
| `$XDG_RUNTIME_DIR/dictate-live/session.pid` | Present while a session runs |
| `pgrep -af dictate-live; pgrep -af whisper-server; pgrep -af speakers.py` | Running pieces |

## Common failures

**Table R2: Symptoms and fixes**

| Symptom | Likely cause | Fix |
|---|---|---|
| F9 does nothing | Dell media-key mode, or the binding was lost | Try Fn+F9 or toggle Fn Lock (Fn+Esc). Check: `xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/F9` should print `~/.local/bin/dictate-live` |
| Box stuck on screen | A crashed session | `pkill -f dictate-live; pkill -x whisper-server; pkill -f speakers.py`, then check `data/live/` for its text |
| "Microphone not available" | Input device busy or missing | Sound settings (`pavucontrol`), `arecord -l` |
| "Didn't catch that" | Only silence, or speech below the speech line | Open **Tune**, watch the level bar: raise **Sensitivity** until speech crosses the white line |
| Text never appears until F9 | Pauses not detected (background louder than the speech line expects) | **Tune**: lower Sensitivity if the bar never drops below the line between sentences; lower **Pause** if you speak with short pauses |
| Words cut or sentences split oddly | Sensitivity too low, or Pause too short | **Tune**: raise Sensitivity or Pause |
| "N phrases waiting" never clears | The origin window is not in front | Click into the window where you pressed F9; they go in within about 0.5 s |
| Text went nowhere | Origin window closed (outcome `origin_closed`) or insertion failed (`insert_failed`) | Ctrl+V: the text is on the clipboard; also in `data/dictations.txt` |
| A meeting started by mistake | Someone else spoke for 20 s, or speakers were confused | F9 to end; the text is in the transcript and in `data/dictations.txt`. If it repeats in monologues, report it (ROADMAP row 16) |
| A meeting did not start | Second voice under 20 s, or voices too similar | Click **Meeting** on the box to switch at once |
| Other call participants missing from the transcript | No call detected (no app recording the mic, no Meet/Zoom/Teams window) or headphones on a different output | Check `pactl -f json list source-outputs` during the call; computer sound is taken from the default output's monitor |
| Same line twice in a meeting transcript | Echo through speakers not recognised as echo | Use headphones for that call; report the case (ROADMAP row 16) |
| No speaker labels ("Speaker ?") | `.venv` or the speaker model missing | `./install.sh` recreates the venv and downloads the model |
| Phrases take 5 s or more | CPU busy (seen at load average 11 with Chrome) | Close heavy tabs; `phrase_latency_avg_s` in the log confirms |
| Box off screen after a monitor change | Saved position | `rm data/overlay-position.json` |
| Wrong words | Engine choice or vocabulary | `dictate-compare` on a sample; consider `final_engine = whisper` with `prompt` |

## Recovery

- **Lost text.** Look in this order: the clipboard, `data/live/` (crashed session), `data/dictations.txt`, `transcripts/`.
- **F9 broken after a code change.** Restore the previous version: `git log -- bin/dictate-live`, then `git checkout <sha> -- bin/dictate-live`. As a stopgap, put F9 on basic mode, which does not use `bin/dictate-live`: `xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/F9 -s "$HOME/.local/bin/dictate"`. Back to live: the same command with `dictate-live`.
- **Settings broken by Tune.** Edit `speech_ratio` (default 2.5) and `pause_ms` (default 700) in `config/dictate.conf`.
- **Fresh install or new laptop.** `docs/REPLICATE.md`.
