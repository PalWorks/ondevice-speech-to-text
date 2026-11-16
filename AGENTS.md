# AGENTS.md

Last updated: 2026-11-16T14:13:16+00:00

The behaviour contract for AI agents (Claude Code and others) working on this project. `CLAUDE.md` points here. Read this file first, then `README.md`, then the document the task needs (map in README, Documentation).

## What this project is

On-device dictation for one person's XFCE (X11) laptop. F9 starts a session, speech is cut into phrases at pauses and typed into the window where F9 was pressed, and a session turns into a meeting transcript with speaker labels when a second voice is heard. Everything runs locally. It is **in production**: F9 runs `bin/dictate-live` from this folder every day, so any edit to that file is live on the next key press.

## Roles

| Role | Who | Does |
|---|---|---|
| Owner | The laptop's user | Decides behaviour, design and priorities; approves box (overlay) design changes and key bindings |
| Builder agent | Claude Code session in this folder | Implements, tests on a hidden display, keeps the docs current |
| Reviewer agent | Optional second session | Reviews a change against this file and `docs/TESTING.md` before the owner relies on it |

## Allowed without asking

- Read anything in this folder except the private files listed under Restricted areas (read those only when a task needs them, and never print their content).
- Edit code, config comments and docs, then test as `docs/TESTING.md` describes.
- Run `./install.sh --check`, `dictate-stats`, and tests on a private Xvfb display.
- Add or update docs, timestamped (see Conventions).

## Ask the owner first

- Any change to how the box looks or what it shows (show a preview: ASCII mockup or a screenshot from the test display). Exception: the owner said "build it straight away" for that change.
- Rebinding F9 or adding a key binding.
- Changing default behaviour a user would notice (where text goes, when meetings start, what is recorded).
- Downloading a new model or adding a dependency.
- Deleting anything in `data/`, `transcripts/` or `models/`.

## Restricted areas

| Path | Rule |
|---|---|
| `data/dictations.txt`, `data/live/`, `transcripts/` | The owner's spoken words and other people's. Private, mode 600 (folders 700). Never copy, upload, paste into chat or include in a report. Tests must never write here (use a scratch copy) |
| `data/sessions.jsonl` | Usage numbers and app names only; never add dictated text to it (owner, 2026-10-20) |
| `models/` | The only place models live; other locations are symlinks. Keep `install.sh` MODEL_LIST and `docs/REPLICATE.md` checksums in sync with it |
| `.venv/` | Rebuilt by `install.sh`; do not edit by hand |
| `~/.local/bin/dictate*`, XFCE F9 shortcut | System links into this folder; change only with the owner's approval |

## Safety constraints

1. **Never type into the owner's windows or move their pointer during tests.** Use the scratch-copy method in `docs/TESTING.md` (Xvfb on `:99`, shims for `arecord`, `pactl`, `parec`, `paplay`, `notify-send`). Check no old Xvfb is running before a test (`pgrep -x Xvfb`) and stop yours afterwards: a stray one made test windows answer from an earlier run (2026-11-16).
2. **Never steal focus** on the owner's desktop. Anything that needs a focused window runs on the test display.
3. **Text always goes to the window focused at the first F9 press** (activate, paste, return focus). Never type into whatever window is in front later: in a browser, typed letters fire single-key shortcuts (the 2026-11-16 Gmail incident, `docs/DECISIONS.md` D-07).
4. **Never switch focus per phrase** to insert while the owner is in another window; hold the text and insert on return (D-09).
5. **Never drop audio unless it is clearly background.** Uncertain chunks go to the engine.
6. **Backgrounded children in `bin/dictate` must not inherit fd 9** (start them with `9>&-`); otherwise the next press is ignored.
7. **The project is a public git repository** (github.com/PalWorks/ondevice-speech-to-text). Commit each tested change; before committing, run the key and personal-data scan in `docs/SECURITY.md` and check `git status` shows no private file.

## Conventions

- Everything for this project lives in this folder (code, config, models, data, docs, venv). The rest of the system only points in through symlinks and the F9 binding.
- Python for `bin/dictate-live` and `bin/dictate-stats` runs on `/usr/bin/python3` (it has the GTK bindings; Homebrew's Python does not). `lib/speakers.py` runs only on `.venv/bin/python`.
- Match the surrounding code: standard library only in `bin/dictate-live`, short docstrings that say why, comments only where the reason is not obvious, no new dependencies without approval.
- External tools are called by name (`xdotool`, `xclip`, `pactl`, `parec`, `arecord`, `paplay`) and must exist in `/usr/bin` because the F9 hotkey runs with a minimal PATH. Homebrew tools use the absolute `BREW` path.
- Settings live in `config/dictate.conf`, each with a comment; new settings also get a default in `load_config()`.
- Docs: plain language, no em dashes, no emojis. Every table has a visible numbered name. Timestamps to the second in UTC from `date -u --iso-8601=seconds` (this is a public repository; no local offset). The local-only `docs/DISCUSSION.md` keeps local time.
- Source files start with `SPDX-License-Identifier: AGPL-3.0-only` (after the shebang). Commit with `TZ=UTC git commit` and the repository's noreply author identity; never commit `data/`, `transcripts/`, `models/`, `.venv/` or `docs/DISCUSSION.md` (`.gitignore`).

## Workflow for a change

1. Read `README.md`, the relevant doc, and `ROADMAP.md` for related rows.
2. Start from a clean `git status`.
3. Make the change. Run `/usr/bin/python3 -m py_compile bin/dictate-live` and `uvx pyflakes bin/dictate-live lib/speakers.py`.
4. Test on the hidden display (`docs/TESTING.md`): at least the dictation scenario, plus the meeting scenarios if anything near phrases, speakers or calls changed.
5. Run `./install.sh --check`; every line must be `[ok]`.
6. Update in the same session: `CHANGELOG.md` (newest first), `docs/DISCUSSION.md` (local only, git-ignored: what the owner asked and decided), `docs/DECISIONS.md` (if a decision was made), `ROADMAP.md` (rows opened, advanced or closed), `README.md` and `docs/ARCHITECTURE.md` (if behaviour or structure changed), `docs/ANALYTICS.md` (if log fields changed).
7. Report to the owner: what changed, how it was tested, what was not tested, and the next step.

## Review rules

A change is ready when:

- It compiles, lints clean, and the test scenarios it touches pass on the hidden display.
- `./install.sh --check` passes.
- Nothing was written to the owner's `data/` or `transcripts/` by tests, and no test display is left running.
- The docs listed in step 6 match the new behaviour.
- Anything untested is stated as untested.

## Rollback

Revert the commit (`git revert <sha>`) or restore a file (`git checkout <sha> -- <path>`), then run `./install.sh --check`. If F9 is broken and a fix is not quick, switch F9 to the basic mode, which does not depend on `bin/dictate-live`: `xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/F9 -s "$HOME/.local/bin/dictate"` (`docs/RUNBOOK.md`).
