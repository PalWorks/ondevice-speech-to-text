# Pre-production audit

Audit date: 2026-10-20T13:39:54+00:00. Scope: every script in `bin/` and `lib/`, the config, the system bindings, and the docs, before switching F9 to live mode.

## Findings and fixes

**Table U1: Findings**

| # | Severity | Finding | Fix | Verified by |
|---|---|---|---|---|
| 1 | High | A stale `session.pid` (after a crash) could point at a reused PID; the next F9 would send SIGUSR1 to an unrelated process, whose default action is to terminate | `running_pid()` now also checks `/proc/<pid>/cmdline` contains `dictate-live` | Test: pidfile pointed at a `sleep` process; F9 started a fresh session and the `sleep` survived |
| 2 | High | Basic mode: the sound-cue helper ran `[ ... ] && paplay ... &`, so the backgrounded subshell inherited the lock fd and the next press could be ignored (same class as the original bug) | `cue()` returns early when sounds are off and backgrounds `paplay ... 9>&-` directly | Test: two full start/stop cycles 3 s apart both typed |
| 3 | Medium | Live mode had no handling for a dead microphone: the box would say "Start speaking…" forever | `_read_audio` detects arecord exiting early; box shows "Microphone not available", session logged as `mic_error` | Test: arecord shim that exits immediately |
| 4 | Medium | No cap on the in-memory audio buffer; a misbehaving capture source could grow it without bound (found when a test shim produced audio faster than real time: 6 hours of audio in 3 minutes) | Buffer capped at `max_seconds`; the timer still ends the session | Code review; normal sessions unaffected |
| 5 | Medium | Basic mode passed the dictated text to the logger as a command-line argument, visible briefly in process listings | Text now goes in on stdin | Test: basic session logged correctly |
| 6 | Low | Basic mode started Python five times per press to read settings (about 250 ms) | One Python call emits all settings | Measured stop-to-typed 1.55 s total including Parakeet |
| 7 | Low | `paplay` was called from Homebrew; on a fresh laptop it would not exist | Uses the system `paplay` from `pulseaudio-utils` | `install.sh --check` |
| 8 | Low | Homebrew prefix hard-coded in live mode | `HOMEBREW_PREFIX` honoured, default `/home/linuxbrew/.linuxbrew` | Code review |
| 9 | Low | Stats overview ignored the new `mic_error` outcome | Added to Table S1 | `dictate-stats` |
| 10 | Info | Accuracy drop from whisper-server's greedy default (found earlier) | Beam 5 on whisper finals; Parakeet default | docs/ANALYSIS.md A5 |

## Checks that passed without changes

- Overlay never takes focus (POPUP, `accept_focus = False`, Cancel not focusable).
- Typed text is only ever the final engine's output; preview text is display only, except the documented `typed_preview_fallback` when the final engine errors.
- whisper-server binds to 127.0.0.1 on a random free port and is stopped at the end of every session, including Cancel and errors; no orphaned servers after the test runs.
- No audio is written to disk in live mode except a temporary WAV for Parakeet in `$XDG_RUNTIME_DIR`, deleted right after.
- Analytics hold numbers only (`log_text = false`); the two earlier rows with text were scrubbed.
- Test sessions were removed from `data/sessions.jsonl` after every test run; the owner's real sessions were kept.

## Known limits accepted

- Two F9 presses within about 100 ms of the very first press can start two sessions (pidfile written after start-up). Not reachable by normal use.
- If Parakeet fails, the fallback types the last preview text, which covers only the last 28 s of a longer dictation.
- X11 only.

## Production switch

2026-10-20T13:37:45+00:00: F9 moved from `dictate` to `dictate-live`; the Shift+F9 trial binding removed; `hotkey_label = F9`. `./install.sh --check`: all checks passed, GPU in use.
