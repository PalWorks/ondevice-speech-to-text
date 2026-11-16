# Analytics

Last updated: 2026-11-16T02:02:31+00:00

Purpose: learn your own dictation patterns (where, when, how much, how fast) and tune the setup with real numbers. Local only; nothing is sent anywhere.

## What is logged

One JSON line per session in `data/sessions.jsonl`.

**Table N1: Fields**

| Field | Modes | Meaning |
|---|---|---|
| `ts` | both | Session end, ISO 8601 with offset |
| `mode` | both | `basic` or `live` |
| `outcome` | both | `typed`, `typed_preview_fallback`, `empty`, `cancelled`, `mic_error`, `origin_closed`, `insert_failed`, and `window_changed` (only in rows from 2026-11-16 02:03 to 02:28 UTC, when switching windows blocked insertion) (last three live only) |
| `app` | both | WM_CLASS of the window focused at the first press (e.g. `Google-chrome`, `Code`) |
| `language` | both | Whisper language code |
| `audio_s` | both | Seconds recorded |
| `words`, `chars` | both | Size of the typed text |
| `wpm` | both | Words per minute of speaking time |
| `final_latency_s` | both | Wait between the second press and the text (live mode: just the last phrase) |
| `final_model` | both | Model that produced the typed text |
| `first_preview_s` | live | Time from first press to the first live words |
| `preview_updates` | live | Number of preview refreshes |
| `preview_latency_avg_s` | live | Average preview refresh time |
| `preview_model` | live | Model behind the overlay text |
| `phrases` | live | Phrases transcribed (one per pause) |
| `phrase_fallbacks` | live | Phrases where the accurate engine failed and the preview text was used |
| `live_inserts`, `held_flushes` | live | Insertions while the original window was in front, and insertions of held phrases on returning to it |
| `insert_failures` | live | Insertions that failed during the session |
| `phrase_latency_avg_s` | live | Average time from a pause to its text being ready |
| `meeting`, `speakers` | live | Whether the session became a meeting; speakers after the final regrouping |
| `meeting_manual` | live | The Meeting button was used (rather than the automatic switch) |
| `call_phrases`, `call_audio_s`, `echo_dropped` | live | Phrases and seconds from the computer's sound during calls; mic phrases dropped as echo |
| `insert_method` | live | `type` (xdotool keystrokes), `paste` (long text in terminals, or any text when focus had moved), `clipboard_only` (origin window closed), `activate_failed` |
| `insert_rc` | live | xdotool exit status; non-zero means `insert_failed` |
| `insert_s` | live | Seconds spent inserting |
| `window_changed` | live | Focus had moved away from the origin window by the second press (text still goes to the origin) |
| `insert_app` | live | WM_CLASS of the window focused at the second press |
| `text` | both, only if `log_text = true` | The typed text (off) |
| `preview_text` | live, only if `log_text = true` | Last preview text (off) |

Dictated text itself is kept separately in `data/dictations.txt` (last 20, mode 600; owner's request 2026-11-16T02:02:31+00:00; `backup_text = false` turns it off).

**Numbers only** (owner's choice, 2026-10-20T13:23:54+00:00): `log_text = false`, and the text fields of earlier sessions were removed from the log. Turn all logging off with `log_sessions = false`. With text off, Table S6 (words) and the preview-vs-final comparison in S2 show nothing.

## Reading the report

`dictate-stats` (or `--days N`, `--json`) prints:

- **S1 Overview**: sessions, outcomes, words, speaking time, speed, estimated time saved against typing at 40 wpm.
- **S2 Speed**: p50/p90 wait after the second press, time to first live words, preview refresh, and how often the final text differed from the preview.
- **S3 Where**: apps you dictate into most.
- **S4 When**: hour of day.
- **S5 Daily trend**: last 14 days.
- **S6 Words**: most used words (stopwords removed), useful for spotting names or jargon worth a bigger model.

## What to act on

| Signal | Action |
|---|---|
| `phrase_latency_avg_s` above 3 s | CPU busy (check load), or switch `final_engine` back to `parakeet` if on whisper |
| Few `phrases` per minute of `audio_s` | Pauses not detected: lower Sensitivity in the box (raises `speech_ratio`) |
| Many `held_flushes` | You often dictate while in other windows; expected, nothing to fix |
| `echo_dropped` high and lines missing from transcripts | The echo rule is too strict; report (ROADMAP row 16) |
| Final often differs from preview | Expected for names; if constant, try `preview_model = ggml-small.en.bin` |
| Many `empty` outcomes | Mic level or distance; check input volume |
| Many `cancelled` | Overlay or flow friction; revisit the design |
| Any `mic_error` | Capture device problem; check Sound settings and `arecord -l` |
| Meetings started by mistake (`meeting` true, `meeting_manual` false, one real speaker) | Raise `meeting_min_seconds`; report (ROADMAP row 16) |

The test sessions run during setup were removed, so the log starts clean from 2026-10-20T12:33:11+00:00.
