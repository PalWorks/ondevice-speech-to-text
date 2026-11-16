# Security and privacy

Last updated: 2026-11-16T12:52:17+00:00

This project records speech, including other people's in meetings. Its security model is simple: nothing leaves the laptop, and the files holding words are readable only by the owner.

## Network

- **Runtime: no network.** Transcription, speaker labels and the box all run locally. whisper-server binds to `127.0.0.1` on a free port per session.
- **Install time only:** `install.sh` downloads models over HTTPS from Hugging Face and the sherpa-onnx GitHub releases and verifies each SHA-256 (`MODEL_LIST`); `uv` installs `sherpa-onnx==2.0.1` and `numpy` from PyPI into `.venv`.
- **No accounts, keys or tokens** are used anywhere in the project.

## Data at rest

**Table P1: What is stored**

| Data | Where | Protection | Kept |
|---|---|---|---|
| Audio | Memory; `$XDG_RUNTIME_DIR/dictate-live/*.wav` for about a second per phrase | Per-user tmpfs (RAM), deleted after use | Never kept |
| Phrase text during a session | `data/live/<start>.txt` | File 600, folder 700 | Until the session ends |
| Session text | `data/dictations.txt` | 600 | Last 20 sessions |
| Meeting transcripts | `transcripts/*.md` | File 600, folder 700 | Until deleted by the owner |
| Usage numbers and app names | `data/sessions.jsonl` | Owner's home folder | Permanent; no words (D-05) |
| Box position, settings | `data/overlay-position.json`, `config/dictate.conf` | Owner's home folder | Permanent |

To stop keeping text: `backup_text = false` in `config/dictate.conf` (meeting transcripts are still written, since they are the point of a meeting). To delete it: remove `data/dictations.txt`, `data/live/` and the transcripts.

## Recording other people

- During a call the computer's sound is recorded, so remote participants are transcribed. This happens only while a call is detected (D-14).
- In a room, the mic picks up everyone nearby; the session switches to a meeting transcript when a second voice is heard.
- **Tell people they are being recorded.** Consent rules depend on where the participants are; the software does not ask for consent.

## Clipboard and focus

- Pasting borrows the clipboard for about 0.5 s and then restores the previous text clipboard. Non-text clipboard content (an image) is not restored after a paste.
- When text has nowhere to go (origin window closed, insertion failed) it is left on the clipboard, where any app can read it.
- At the end of a session the origin window may be focused for under a second to paste, then focus returns (D-07). No focus change happens mid-session.

## Rules for agents

- Never read out, copy, upload or paste into chat the content of `data/dictations.txt`, `data/live/` or `transcripts/` (AGENTS.md, Restricted areas).
- Tests use a scratch copy and never write to the owner's data (docs/TESTING.md).
- The public repository never contains `data/`, `transcripts/`, `models/`, `.venv/` or the private conversation log (`.gitignore`). Check `git status` before every commit.

## Before every commit

The repository is public. Run from the project folder:

```bash
git status --short                       # no data/, transcripts/, models/, .venv/, docs/DISCUSSION.md
git diff --cached | grep -nE 'AIza|sk-[A-Za-z0-9]|ghp_|xox[bp]|eyJ[A-Za-z0-9]|BEGIN [A-Z ]*PRIVATE|@[a-z0-9-]+\.(com|in|org)' \
  && echo 'STOP: possible key or address in the commit'
```

Commit with `TZ=UTC` and the noreply author identity configured in the repository (`git config user.email`), so no personal address or local time zone is published.

## Reporting a problem

Report a security or privacy problem through a GitHub issue on the repository; do not include recordings, transcripts or dictated text in it.
