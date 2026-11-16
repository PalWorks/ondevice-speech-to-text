# Decisions

Last updated: 2026-11-16T12:52:17+00:00

Architecture decision records: why the system is the way it is. Each record is short; benchmarks are in [ANALYSIS.md](ANALYSIS.md). The maintainer's conversation log behind these records is kept privately and is not part of the repository. A record is never deleted; a later record supersedes it and says so.

**Table D0: Index**

| # | Date | Decision | Status |
|---|---|---|---|
| D-01 | 2026-10-20 | Local whisper.cpp stack with an F9 hotkey, not SpeechNote or a cloud service | Active |
| D-02 | 2026-10-20 | Two engines: fast preview, accurate final; only final text is inserted | Active |
| D-03 | 2026-10-20 | Parakeet TDT 0.6b v3 as the default final engine | Active |
| D-04 | 2026-10-20 | Everything in one project folder; the system only links in | Active |
| D-05 | 2026-10-20 | Analytics are numbers only | Active, amended by D-08 |
| D-06 | 2026-10-20 | Box is a non-focusable GTK POPUP, draggable, anchored at its bottom edge | Active |
| D-07 | 2026-11-16 | Text always goes to the window where F9 was first pressed | Active, supersedes the earlier same-day "clipboard on window switch" behaviour |
| D-08 | 2026-11-16 | Keep a private backup of dictated text | Active |
| D-09 | 2026-11-16 | Insert at each pause; hold while away; insert on return | Active |
| D-10 | 2026-11-16 | Pause detection by loudness against a moving background, never dropping uncertain audio | Active |
| D-11 | 2026-11-16 | No length limit while speaking | Active |
| D-12 | 2026-11-16 | Meetings switch on automatically inside F9, plus a Meeting button | Active |
| D-13 | 2026-11-16 | Speaker labels per phrase with sherpa-onnx TitaNet small in a project venv | Active |
| D-14 | 2026-11-16 | Computer sound only while a call is open; echo dropped by word overlap | Active |
| D-15 | 2026-11-16 | Tuning controls in the box, folded behind a Tune button | Active |

---

## D-01 Local whisper.cpp stack with an F9 hotkey

- **Context.** The owner wanted macOS-style dictation: press F9 anywhere, speak, text appears at the cursor. A Homebrew `openai-whisper` install existed but was command-line only.
- **Decision.** Build on whisper.cpp (Homebrew), `arecord`, `xdotool` and an XFCE custom shortcut. SpeechNote was judged heavier for the same result. Nothing leaves the laptop.
- **Consequences.** X11 only (`xdotool`). Models are downloaded once (1.9 GB). The old `openai-whisper` was removed later the same day.

## D-02 Two engines, only final text inserted

- **Context.** Live text while speaking needs a fast model; accurate text needs a slower one.
- **Decision.** A fast whisper `base.en` server gives the grey preview; the final engine's text is the only text inserted. Inserted text is never corrected afterwards.
- **Consequences.** No synthetic backspaces (they misbehave in editors, terminals and chat boxes). The preview may differ from what is inserted.

## D-03 Parakeet as the default final engine

- **Context.** Live mode v1 was less accurate than basic mode: whisper-server's greedy decoding versus whisper-cli's beam search (ANALYSIS A5).
- **Decision.** NVIDIA Parakeet TDT 0.6b v3 (`parakeet-cli`) as the default final engine, about 1 to 2 s per phrase; whisper large-v3-turbo with beam 5 and a vocabulary prompt one setting away (`final_engine = whisper`). The owner judged Parakeet "much much better".
- **Consequences.** English and European languages by default; Indian languages need the whisper setting. Parakeet ignores the vocabulary prompt.

## D-04 One project folder

- **Context.** Owner's request (2026-10-20): every artifact for this project in one folder, documented well enough to rebuild on another laptop.
- **Decision.** Code, config, models, data, docs and the venv live in this folder; `~/.local/bin/dictate*`, `~/.local/share/whisper-cpp/models` and the F9 binding point in. `install.sh` rebuilds the links.
- **Consequences.** The folder can move (scripts use `realpath`). Models stay in `models/` only.

## D-05 Analytics are numbers only

- **Context.** The owner wanted to learn their dictation patterns without storing what they say.
- **Decision.** `data/sessions.jsonl` holds counts, timings and app names; `log_text = false`. Text fields were removed from early rows.
- **Consequences.** `dictate-stats` cannot show word tables. Amended by D-08: dictated text is kept separately, not in the log.

## D-06 Box design

- **Context.** The box must never steal the cursor from the app being dictated into.
- **Decision.** GTK `POPUP` window with `accept_focus = False`; buttons are not focusable. Drag to move; the position is saved as left x and bottom y, so the box grows upwards; clamped to the screen.
- **Consequences.** Clicking the box (Meeting, Tune, Cancel) is safe mid-dictation. Any change to the box's design needs the owner's approval of a preview.

## D-07 Text always goes to the origin window

- **Context.** 2026-11-16: a 549-character dictation started in a terminal was typed into Gmail because the owner clicked over to Chrome before the second F9. Gmail treated the letters as shortcuts (`?` opened the shortcut list). A first fix the same day refused to type after a window switch and used the clipboard; the owner said dictating means moving between windows, so text must still reach the origin.
- **Decision.** At the end, if focus moved, activate the origin window, paste, and return focus to where the owner was. If the origin window is closed, use the clipboard.
- **Consequences.** A short, deliberate focus detour at the end of a session only. Tested on xfwm4 with terminals and a GTK window.

## D-08 Private backup of dictated text

- **Context.** The Gmail incident lost the text for good. The owner asked for a copy to paste into other tools.
- **Decision.** Each phrase is appended to `data/live/<start>.txt` during a session; at the end the session's text moves to `data/dictations.txt` (last 20, newest first). Files mode 600, folders 700.
- **Consequences.** Spoken words now exist on disk; agents must treat these files as private (AGENTS.md).

## D-09 Insert at pauses; hold while away

- **Context.** The owner wanted text to appear while speaking (like the VS Code Claude Code extension) and asked whether phrases could keep going into the origin window while another window is in front.
- **Decision.** Insert each phrase when ready if the origin window is in front; otherwise hold it and insert once the origin window has been back in front for about 0.5 s. Rejected: switching focus for every phrase. Tested first: typing into a window that is not in front is ignored by xfce4-terminal and GTK, and the kernel blocks terminal input injection (`dev.tty.legacy_tiocsti = 0`), so a focus switch per phrase would have been the only way.
- **Consequences.** No stolen keystrokes, no flicker, no clipboard churn while the owner works elsewhere. The trade-offs:

  Tested first on a hidden Xvfb display: typing into a window that is not in front (`xdotool type --window`, X synthetic events) is ignored by both xfce4-terminal and GTK apps, and injecting into a terminal's input is blocked by the kernel (`dev.tty.legacy_tiocsti = 0`). The only working way to insert while away would be to focus the origin window for each phrase, paste, and focus back.

**Table D-I1: Insert live while away (focus switch per phrase), rejected**

| | Detail |
|---|---|
| Advantage | Text lands in the original window as you speak, nothing waits |
| Drawback 1: stray keys | For about 0.6 s per phrase the original window has the keyboard. Anything typed then goes there; in a terminal, Enter runs the half-typed line (in an AI coding agent's prompt, that sends a half-finished prompt) |
| Drawback 2: interruptions | Each switch closes open menus, dropdowns, autocomplete lists and browser address bar suggestions, and can break a click or drag |
| Drawback 3: flicker | The original window flashes to the front and back every few seconds |
| Drawback 4: clipboard | The clipboard is replaced and restored every phrase; a copy or paste at that moment can pick up the wrong text |

**Table D-I2: Hold while away, insert on return, chosen**

| | Detail |
|---|---|
| Advantage | Nothing takes your keyboard or flickers; work in other windows is untouched; held text goes in as one clean block |
| Possible advantage | Held phrases could be re-transcribed as one piece for better accuracy at pause boundaries (not built; ROADMAP row 20) |
| Drawback | Text is not visible in the original window until you return; the box and the live file show it meanwhile |

## D-10 Pause detection by loudness

- **Context.** Phrases need a pause detector that runs on the system Python with nothing new installed, and a 3-second check of the owner's mic showed a loud background.
- **Decision.** Loudness per 100 ms chunk against the 10th percentile of the last 10 s; speech when above `speech_ratio` × background and `speech_min_rms`. Only clearly quiet audio is dropped; uncertain audio goes to the engine.
- **Consequences.** In a very noisy test no words were lost, but one sentence was split at an odd point. Tunable from the box (D-15).

## D-11 No length limit while speaking

- **Context.** The owner asked about a 1-hour monologue and said a single speaker must not be cut off after 5 minutes.
- **Decision.** Sessions end only after `silence_stop_seconds` (600) without speech or at `max_seconds` (14400, a safety limit). Only the current phrase is kept in memory.
- **Consequences.** Basic mode keeps its 5-minute limit.

## D-12 Meetings switch automatically, plus a button

- **Context.** The owner chose no new hotkey: F9 should become a meeting when a second person speaks. The automatic switch types the other person's first 20 s into the window, so the owner asked for a button too.
- **Decision.** Switch when a second voice has spoken 20 s over at least 2 phrases, confirmed by regrouping all fingerprints; the Meeting button switches at once. After the switch, text goes only to `transcripts/`.
- **Consequences.** Text already inserted stays in the window. Phrases held at a manual switch go to the transcript.

## D-13 Speaker labels with sherpa-onnx

- **Context.** Meetings need "Speaker 1, 2, 3" labels, on-device.
- **Decision.** NeMo TitaNet small (40 MB) through sherpa-onnx 2.0.1 in a project venv, run as a helper process (`lib/speakers.py`). Live label per phrase (new speaker below 0.56 similarity); average-linkage regrouping (merge above 0.55) to confirm meetings and correct labels at the end. Thresholds from test clips: same voice 0.61 to 0.84, different voices 0.23 to 0.54.
- **Consequences.** Labels are per phrase: two people inside one phrase get one label (ROADMAP row 19). Without the venv or model, dictation works and meetings stay off.

## D-14 Computer sound only during calls

- **Context.** Remote participants are not heard by the mic when the owner wears headphones. The owner uses both headphones and speakers.
- **Decision.** Record the speaker monitor (`parec`) only while a call is open: another app is recording the mic, or a Meet, Zoom or Teams window shows. Mic phrases during a call wait up to 4 s for the call's copy; 60% of words matching in order means echo, dropped. During a call, only the call's own copy counts towards meeting detection.
- **Consequences.** A video playing during dictation is not transcribed. Call speech is never inserted into a window.

## D-15 Tuning in the box

- **Context.** The owner said editing the config file during a call is impractical.
- **Decision.** A Tune button folds open a mic level bar with the speech line, Sensitivity −/+ and Pause −/+. Chosen from three previews (owner, 2026-11-16).
- **Consequences.** Changes apply at once and are written to `config/dictate.conf`, keeping its comments.
