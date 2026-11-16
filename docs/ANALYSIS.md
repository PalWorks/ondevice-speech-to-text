# Analysis and decisions

Last updated: 2026-10-20T16:53:54+00:00

## Starting point (audit, 2026-10-20)

**Table A1: Speech software found on the system**

| Item | Status | Notes |
|---|---|---|
| `openai-whisper` (Homebrew, Python) | Installed 2026-02-21, version 20250625_3; **uninstalled 2026-10-20T16:53:54+00:00** | Only had the `tiny` model (`~/.cache/whisper/tiny.pt`, also deleted). Replaced by whisper.cpp |
| VS Code Speech extension 0.16.0 | Installed | Dictation inside VS Code only |
| Edge on-device speech model | Bundled with the browser | Browser only |
| SpeechNote | Not installed | Only cached screenshots from the Mint Software Manager |
| pocketsphinx, speech-dispatcher | System libraries | speech-dispatcher is text to speech |

## Engine choice

whisper.cpp (C++) over the Python `openai-whisper`: same models, much faster on CPU, starts in a fraction of a second, ships a ready HTTP server (`whisper-server`) that keeps a model in memory.

## Benchmarks (i7-11390H, 4 cores / 8 threads, 16 GB RAM)

Test clip: 7.7 s English sentence with background noise.

**Table A2: whisper-cli per run (includes model load)**

| Model | 4 threads | 8 threads | Transcript |
|---|---|---|---|
| base.en | 0.89 s | 0.89 s | correct |
| small.en | 2.24 s | 2.19 s | correct |
| large-v3-turbo q5_0 | 3.97 s | 4.21 s | correct |

8 threads gives no gain (hyper-threads), so everything uses 4.

**Table A3: whisper-server (model already loaded)**

| Model | Load | 3 s clip | 8 s clip |
|---|---|---|---|
| tiny.en | 0.18 s | 0.30 s | 0.31 s |
| base.en | 0.24 s | 0.42 s | 0.60 s |
| small.en + VAD | n/a | n/a | 1.63 to 1.82 s |
| small.en + VAD, silence only | n/a | 0.01 s, empty | n/a |

## Live text options (2026-10-20)

**Table A4: Ways to show text while speaking**

| Option | Experience | Trade-off |
|---|---|---|
| 1. Type each phrase on pause | Phrases land about 1 to 2 s after each pause | Whisper accuracy, no corrections, not word by word |
| 2. Live preview overlay + final typing | Words in a floating box as you speak; accurate text typed at the end | Looks like claude.ai; text lands in the window only at the end |
| 3. Options 1 and 2 together | Live box plus phrases typed as you pause | Best feel, most work |
| 4. Streaming engine (Vosk, sherpa-onnx) | True word by word into the window | Lower accuracy, weaker on Indian accents |
| 5. Cloud streaming (Deepgram, Google) | Fast and accurate | Audio leaves the machine, API key, cost, needs internet |

Typing interim text into another app and then correcting it needs synthetic backspaces into the focused window, which breaks in editors with autocomplete, terminals and chat boxes. That is why options 1 to 3 never type text that may later change.

**Chosen: option 2** (owner, 2026-10-20). Fallback plan if it does not work well: build option 3.

## SpeechNote vs this setup

[Unverified: SpeechNote was not installed for a hands-on comparison.] SpeechNote (Flatpak `net.mkiol.SpeechNote`) is a GUI app with more languages, translation and an "insert into active window" action. It would cost well over 1 GB with its Flatpak runtime before models, uses the same Whisper model family, and needs its own shortcut setup. This setup does exactly the requested F9 behaviour with less overhead, so SpeechNote was not adopted.

## Preview model choice

base.en for the preview: about 0.4 s per refresh, accurate enough to read along. tiny.en is faster (0.3 s) but made more visible mistakes; it is downloaded as an alternative (`preview_model = ggml-tiny.en.bin`). The preview only needs to be readable; the typed text always comes from the final engine.

## Accuracy drop in live mode v1 (2026-10-20T13:23:54+00:00)

Owner reported live mode was less accurate than basic F9.

Root cause: both used small.en, but basic mode ran `whisper-cli`, which defaults to beam search (beam 5, best of 5), while live mode ran `whisper-server`, which defaults to greedy decoding (beam -1, best of 2). Owner's real sessions showed greedy errors such as "I, Claude, are able to listen to me".

**Table A5: Final-pass options, server warm, Iris Xe Vulkan** (8 s and 23 s clips)

| Engine / settings | 8 s | 23 s | Notes |
|---|---|---|---|
| small.en greedy (live v1) | 1.8 s | 4.2 s | the less accurate setting |
| small.en beam 5 | 3.0 s | 6.9 s | parity with basic F9 v1; slow decoder on long text |
| large-v3-turbo q5_0 beam 5 | 4.7 s | 5.9 s | stronger model; fixed 30 s encoder cost dominates |
| large-v3-turbo q8_0 beam 5 | 5.3 s | 6.8 s | slower than q5_0 on this GPU; deleted |
| large-v3-turbo q5_0, audio_ctx 768 | 2.3 s | 4.4 s | rejected: drops audio beyond about 15 s per window |
| large-v3-turbo q5_0 beam 5, CPU only | 14.7 s | 16.8 s | the GPU is already doing most of the work |
| **parakeet tdt 0.6b v3 q8_0** (parakeet-cli, cold load each call) | **1.2 s** | **2.1 s** | non-autoregressive; chosen |

**Table A6: Why Parakeet**

| | Parakeet TDT 0.6b v3 | whisper large-v3-turbo |
|---|---|---|
| Wait after second press | 1 to 2 s | about 5 s |
| English accuracy | [Unverified, from public Open ASR leaderboard reporting] ranks above whisper large-v3 | strong |
| Indian English accent | Not measured on the owner's voice yet | Not measured either |
| Vocabulary prompt | No | Yes (`prompt`) |
| Languages | English + 24 European | 99, including Hindi, Tamil |

Decision: Parakeet as default final engine, whisper large-v3-turbo kept one setting away. `dictate-compare` runs one clip of the owner's voice through every engine so the choice can be confirmed on real speech rather than benchmarks.

Also fixed: whisper sometimes prefixes a line with a dialogue dash ("- Hi"); the cleaner strips it.

## Known limits

As of 2026-10-20. Current limits: README.md, Known limitations (updated 2026-11-16T12:52:17+00:00); since 2026-11-16 each phrase gets its own final pass instead of one pass over the full audio.

- English by default. Indian languages need `final_engine = whisper` with `large-v3-turbo`, which is slower.
- Parakeet ignores the vocabulary `prompt`; only the whisper preview and whisper final use it.
- The preview re-reads only the last 28 s (whisper's window is 30 s), so long dictations show "…" plus the tail. The final pass uses the full audio.
- X11 only (`xdotool`).
- `xdotool type` can mistype some non-ASCII characters in a few apps.
