# Changelog

## 2026-11-16T14:13:33+00:00

- **Published** as a public repository, github.com/PalWorks/ondevice-speech-to-text, dual-licensed: AGPL 3.0 (`LICENSE`, unmodified text from gnu.org) plus a commercial licence (`COMMERCIAL-LICENSE.md`; enquiries through GitHub issues, no personal contact published). `SPDX-License-Identifier: AGPL-3.0-only` added to every source file.
- Pre-publication audit: no keys, tokens or personal addresses in code or docs; models, `.venv/`, `data/`, `transcripts/` and the private conversation log (`docs/DISCUSSION.md`) are git-ignored. Doc timestamps converted to UTC. The live-window trade-off tables moved from the private log into docs/DECISIONS.md D-09. Owner-specific wording neutralised; README gained clone instructions, contribution terms for a dual-licensed project, and model licences (models are downloaded, not redistributed).
- `bin/dictate-live` module docstring rewritten to describe the current behaviour.
- AGENTS.md: commit rules (UTC, noreply identity, pre-commit scan), git-based rollback; docs/SECURITY.md: pre-commit checklist; docs/RUNBOOK.md: git-based recovery. ROADMAP row 17 closed, row 22 added.

## 2026-11-16T12:52:17+00:00

- **Documentation set** per the maintainer's documentation guidelines (judgement: the files a single-owner, in-production, local tool needs). New: `AGENTS.md` (agent contract; `CLAUDE.md` now points to it), `ROADMAP.md` (roadmap guide structure, 21 ledger rows), `docs/DOMAIN.md`, `docs/DECISIONS.md` (D-01 to D-15), `docs/TESTING.md`, `docs/RUNBOOK.md`, `docs/SECURITY.md`. Rewritten: `README.md` (full structure: overview, features, architecture, stack, install, all settings, commands, structure, testing, deployment, limitations, docs map) and `docs/ARCHITECTURE.md` (diagram, threads, files, dependencies, scaling). Updated: `docs/REPLICATE.md` (uv, `.venv` and private folders excluded from copies), `docs/ANALYTICS.md` (what to act on), `docs/ANALYSIS.md` (pointer to current limits), `docs/overlay-preview.png` (current box: dictating, Tune open, meeting).
- Not created, by judgement: PROMPTS, SKILLS, MEMORY (DECISIONS covers it), PLAYBOOK (in AGENTS.md), TASKS (ROADMAP covers it), CONTRIBUTING and CODE_STYLE (single owner; conventions in AGENTS.md), DATA_MODEL (ANALYTICS and DOMAIN cover the files), API (no API), DEPLOYMENT (README section), OBSERVABILITY (RUNBOOK and ANALYTICS), INCIDENTS (the one incident is D-07 and ROADMAP §7).
- Fix found while documenting: the per-phrase clip given to the speaker helper (`$XDG_RUNTIME_DIR/dictate-live/speaker-<pid>.wav`) was overwritten but never deleted, so the last phrase's audio stayed in RAM-backed tmpfs after a session. It is now deleted right after use, matching the privacy rule that audio is never kept.

## 2026-11-16T11:13:52+00:00

- **Meeting button** on the box (owner asked to build it straight away): switches to meeting mode at once instead of waiting for 20 s of a second voice; hidden once in a meeting. Logged as `meeting_manual`. Phrases not yet inserted when you click go to the transcript.
- The box shows consecutive phrases of one speaker as one turn (one S1 label, not one per phrase).
- Transcript writes recreate `transcripts/` if needed and never crash the session (the live file still has every phrase); meeting end works without the speaker helper (labels then read Speaker ?).
- Tested on a private Xvfb display: clicked Meeting 4 s in, nothing typed into the window, transcript written live, F9 saved it with final labels (1 speaker), focus never left the target window; automatic switch re-tested with two voices. A stray Xvfb left from an earlier test run had been answering some test windows; removed, and the earlier odd Tune-test result traced to it.

## 2026-11-16T10:40:41+00:00

- **Meetings (Phase 2).** Every phrase gets a voice fingerprint (NeMo TitaNet small, sherpa-onnx 2.0.1, in a project venv; helper `lib/speakers.py`). When a voice other than the dictating person's has spoken for `meeting_min_seconds` (20) over at least 2 phrases, confirmed by regrouping all fingerprints, the session becomes a meeting: text goes to `transcripts/<date time> meeting.md` (mode 600) with timestamps and speaker labels, updated live. At F9 all fingerprints are regrouped (average-linkage clustering) to correct the labels, the transcript is rewritten, a notification shows and the path is copied.
- **Call audio.** While a call is open (another app records the mic, or a Meet, Zoom or Teams window shows), the computer's sound is recorded as a second stream (`parec` on the default monitor) and cut into phrases the same way. It counts towards meeting detection and goes into the transcript, never into the window. Mic phrases that repeat the call's words at the same moment (laptop speakers) are dropped (`similar()`, 60% of words in order). Stops 15 s after the call ends.
- **Tune panel** in the box (approved layout): Tune button next to Cancel opens a mic level bar with the speech line, Sensitivity −/+ (1 to 10, maps to `speech_ratio` 4.0 to 1.75) and Pause −/+ (0.3 to 2.0 s); changes apply at once and are saved to `config/dictate.conf`.
- Box text is trimmed to about three lines so the ellipsis always sits at the start; end messages hide the buttons and shrink the box.
- New settings `meetings`, `meeting_min_seconds`, `call_audio`; new log fields `meeting`, `speakers`, `echo_dropped`, `call_phrases`, `call_audio_s`; outcome `meeting`.
- `install.sh`: speaker model in MODEL_LIST, creates `.venv` with `uv`, checks the venv and `parec`/`pactl`.
- Tested on a private Xvfb display with real models: (1) four-phrase dictation with window switches, unchanged behaviour; (2) 2.5-minute single-voice monologue, no false meeting; (3) two voices in the room, meeting after the second voice's third phrase, transcript labelled correctly; (4) call with the other voice on the computer sound and an echo through the speakers: 3 echo copies dropped, call speech never typed into the window, meeting detected, transcript correct; (5) Tune panel: clicks kept focus on the target window, settings saved.

## 2026-11-16T08:47:52+00:00

- **Text goes in as you talk.** Live mode cuts the audio into phrases at pauses (0.7 s) and transcribes each with the accurate engine (Parakeet) straight away; each phrase is inserted into the original window about 1 to 2 s after the pause (test average 1.1 to 1.8 s). Replaces the single pass over the whole recording at the end; closes the open decision on option 3 (phrases typed on pause).
- While the original window is not in front, phrases are held and shown as waiting, then inserted once it has been back in front for about 0.5 s. The second F9 inserts anything still held by the focus, paste, return method. Decision and trade-offs: docs/DECISIONS.md D-09.
- No 5-minute cutoff: sessions end after `silence_stop_seconds` (600) without speech or at `max_seconds` (now 14400, 4 hours). Only the current phrase is kept in memory.
- Speech detection by loudness against the room's background level (10th percentile of the last 10 s); new settings `pause_ms`, `max_phrase_seconds`, `speech_min_rms`, `speech_ratio`. Audio is dropped only when clearly background, so soft words reach the engine. Phrases over 25 s are cut at their quietest moment.
- Each phrase is appended to `data/live/<start>.txt` (mode 600) during the session and moved into `data/dictations.txt` at the end.
- Box: finished phrases in white, the phrase being spoken in grey, hint names the target window and counts waiting phrases; timer shows hours. Fixed: the live text never had its `live` style class, so its colour followed the GTK theme (dark grey on the dark box under a light theme).
- Cancel keeps phrases already inserted and drops the rest.
- New log fields: `phrases`, `phrase_fallbacks`, `live_inserts`, `held_flushes`, `insert_failures`, `phrase_latency_avg_s`. `final_latency_s` is now the wait after the second press for the last phrase.
- Tested on a private Xvfb display under xfwm4 with real whisper-server and Parakeet: four-phrase clip with switches away and back and the second F9 pressed from another window; all text reached the original window in order, none reached the other window, focus returned. Same with heavy background noise (no words lost; one word split across a phrase boundary). Empty session and Cancel also checked.

## 2026-11-16T02:28:40+00:00

- Text now always goes to the window where F9 was first pressed (owner's request: dictating often means moving between windows). If focus moved, that window is activated, the text pasted (Ctrl+V, or Ctrl+Shift+V in terminals), and focus returned to the window you were on; the clipboard is restored. Replaces the earlier "Not inserted: you switched windows" behaviour from the same day.
- If the original window was closed, the text goes to the clipboard and the box says so (outcome `origin_closed`). If activation or pasting fails: `insert_failed`, clipboard, notification.
- Tested on a private Xvfb display under xfwm4 with two xfce4-terminals and a GTK text window: text reached the origin window every time, nothing reached the other windows, focus returned, clipboard restored.

## 2026-11-16T02:02:31+00:00

- Fixed: text was typed into whatever window had focus at the second press. A 549-character dictation started in the terminal was typed into Gmail in Chrome, where the letters fired keyboard shortcuts (the shortcut list appeared) and nothing reached the terminal. Now, if the focused window changed since the first press, nothing is typed: the text goes to the clipboard and the box says so (outcome `window_changed`).
- Terminals: text of `terminal_paste_min_chars` (100) or more is pasted with Ctrl+Shift+V instead of typed key by key; the previous text clipboard is restored after 0.5 s.
- Backup: every dictation is saved to `data/dictations.txt` (last `backup_keep` = 20, newest first, mode 600). Owner asked for this so failed text can be recovered; `backup_text = false` turns it off. Analytics in `sessions.jsonl` stay numbers only.
- Diagnostics in `sessions.jsonl`: `insert_method` (`type`, `paste`, `clipboard_only`), `insert_rc`, `insert_s`, `window_changed`, `insert_app`. A non-zero xdotool exit is logged as `insert_failed`, the text goes to the clipboard and a notification appears.
- `dictate-stats` counts not-inserted sessions; `install.sh` installs `xclip`.

## 2026-10-20T16:53:54+00:00

- Removed the unused Homebrew `openai-whisper` (Python) and its `~/.cache/whisper/tiny.pt` model; Homebrew also removed dependencies nothing else needed (including eigen and abseil). `./install.sh --check` passes afterwards.

## 2026-10-20T13:39:54+00:00

- **Production:** F9 now runs `dictate-live` (switched 2026-10-20T13:37:45+00:00); Shift+F9 trial binding removed; `hotkey_label = F9`.
- Overlay can be dragged anywhere; position saved in `data/overlay-position.json`, clamped to the screen, bottom edge anchored.
- Audit fixes (docs/AUDIT.md): pidfile checked against `/proc/<pid>/cmdline` before signalling; basic-mode sound cue no longer holds the lock; microphone failure shown in the box and logged as `mic_error`; audio buffer capped at `max_seconds`; basic-mode text passed to the logger on stdin; settings read with one Python call; system `paplay`; `HOMEBREW_PREFIX` honoured; stats count `mic_error`.
- Added `install.sh` (idempotent install, `--check` self-test including GPU detection).
- Documentation sweep: README rewritten for production; new docs/REPLICATE.md and docs/AUDIT.md; ARCHITECTURE, ANALYTICS, DISCUSSION, CLAUDE.md updated.

## 2026-10-20T13:23:54+00:00

- Fixed live-mode accuracy: whisper finals now use beam search (`-bs 5 -bo 5`); the server's greedy default caused the drop.
- New default final engine for both modes: NVIDIA Parakeet TDT 0.6b v3 (`parakeet-cli`), about 1 to 2 s. `final_engine = whisper` switches to large-v3-turbo with beam 5.
- Downloaded `ggml-parakeet-tdt-0.6b-v3-q8_0.bin`. Tried and deleted `ggml-large-v3-turbo-q8_0.bin` (slower than q5_0 here).
- Added `bin/dictate-compare` (one clip through every engine) and `prompt` (vocabulary hint for whisper).
- Basic mode now reads engine, model, beam, prompt and language from `config/dictate.conf`.
- Analytics are numbers only: `log_text = false` by default; text fields removed from existing log rows.
- Cleaner strips whisper's leading dialogue dash.

## 2026-10-20T12:33:11+00:00

- Added `bin/dictate-live`: live preview overlay (base.en via whisper-server) with the accurate small.en text typed on the second press. Bound to Shift+F9 for trial.
- Added `bin/dictate-stats` and per-session logging to `data/sessions.jsonl` for both modes.
- Added `config/dictate.conf` (models, language, analytics, sounds, hotkey label).
- Downloaded `ggml-tiny.en.bin` as an optional faster preview model.
- Moved the project into `~/Documents/OnDevice Speech To Text`: models moved to `models/` with `~/.local/share/whisper-cpp/models` symlinked to it; `~/.local/bin/dictate` and `dictate-live` are symlinks into `bin/`.
- Basic `dictate` now reads models from the project folder and logs sessions.
- Documentation: README, ANALYSIS, ARCHITECTURE, ANALYTICS, DISCUSSION, CLAUDE.md.

## 2026-10-20T11:41:01+00:00

- Installed whisper.cpp 1.9.5 (Homebrew).
- Downloaded base.en, small.en, large-v3-turbo-q5_0 and Silero VAD models.
- Added `dictate` (basic mode): F9 toggles recording, whisper-cli small.en transcribes, xdotool types into the focused window.
- Fixed: the sound cue process inherited the lock, so every second press was ignored.
