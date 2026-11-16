# Domain: words this project uses

Last updated: 2026-11-16T12:52:17+00:00

The terms below have a precise meaning in the code (`bin/dictate-live`, `lib/speakers.py`), the log (`data/sessions.jsonl`) and the docs. Use them the same way.

## Sessions and modes

**Table T1: Sessions**

| Term | Meaning |
|---|---|
| Session | Everything between the first F9 press and the end (second F9, Cancel, 10 minutes without speech, or 4 hours). One `dictate-live` process per session |
| Live mode | `bin/dictate-live`, bound to F9: the box, phrases inserted as you talk, meetings |
| Basic mode | `bin/dictate`: fallback command. Records until the second press, transcribes once, types the text. No box, no phrases, 5-minute limit |
| Dictation | A live session that has not become a meeting: text goes into the origin window |
| Meeting | A live session after the switch: text goes to a transcript file with speaker labels, nothing more is inserted into a window |
| Box (overlay) | The floating dark window showing status, text, Meeting, Tune and Cancel. It never takes keyboard focus |
| Tune panel | The part of the box opened by Tune: mic level bar with the speech line, Sensitivity −/+, Pause −/+ |

## Audio and phrases

**Table T2: Audio**

| Term | Meaning |
|---|---|
| Stream | One audio source cut into phrases: the **mic stream** (`arecord`) and, during a call, the **call stream** (`parec` on the speaker monitor) |
| Chunk | 100 ms of 16 kHz mono 16-bit audio, the unit of loudness measurement |
| Loudness (RMS) | Root mean square of a chunk's samples |
| Background level (floor) | 10th percentile of the last 10 s of chunk loudness; follows fans and hum, even while someone talks |
| Speech line (threshold) | Loudness above which a chunk counts as speech: the larger of `speech_min_rms` and `speech_ratio` × background |
| Clearly quiet | Below 1.5 × background (or half of `speech_min_rms`). Only clearly quiet audio is ever dropped |
| Sensitivity | The box's 1 to 10 scale for `speech_ratio` (1 = 4.0, least sensitive; 10 = 1.75, most sensitive) |
| Pause | `pause_ms` of non-speech after speech; ends a phrase |
| Phrase | The audio between pauses (at most `max_phrase_seconds`, then cut at its quietest chunk). The unit that is transcribed, inserted, labelled and logged |

## Transcription

**Table T3: Engines**

| Term | Meaning |
|---|---|
| Preview | Fast, rough text of the phrase still being spoken (whisper `base.en` via `whisper-server`), shown in grey in the box. Never inserted |
| Final engine | The accurate engine whose text is inserted: Parakeet TDT 0.6b v3 (`parakeet-cli`, default) or whisper large-v3-turbo (`final_engine = whisper`) |
| Phrase latency | Time from a pause being detected to that phrase's final text being ready |
| Fallback | A phrase whose final engine call failed; the preview text is used instead (`phrase_fallbacks`) |

## Inserting text

**Table T4: Insertion**

| Term | Meaning |
|---|---|
| Origin window | The window focused at the first F9 press. All dictated text goes there, never anywhere else |
| In front | The origin window is the active window (`xdotool getactivewindow`) |
| Live insert | A phrase typed into the origin window as soon as it is ready, because the origin window is in front |
| Held phrase | A phrase ready while another window is in front. Shown as "N phrases waiting" |
| Flush | Inserting held phrases once the origin window has been back in front for two checks (about 0.5 s) |
| Final insert | At the end of a session, held text goes into the origin window wherever focus is: activate it, paste, return focus |
| Type / paste | `xdotool type` key by key, or clipboard plus Ctrl+V (Ctrl+Shift+V in terminals). Long text in terminals and any final insert after a window switch are pasted; the previous clipboard text is restored |
| Origin closed | The origin window no longer exists at the end; text goes to the clipboard |

## Meetings and speakers

**Table T5: Speakers**

| Term | Meaning |
|---|---|
| Voice fingerprint (embedding) | A 192-number vector per phrase from NeMo TitaNet small (sherpa-onnx); similar voices give similar vectors (cosine similarity) |
| Live label | Speaker number given as each phrase arrives: nearest running-average voice, or a new speaker below 0.56 similarity |
| Regroup (final labels) | Average-linkage clustering of every fingerprint so far, merging groups above 0.55. Used to confirm a meeting and to correct labels at the end |
| Primary speaker | The voice of the first accepted mic phrase: the person dictating |
| Second voice | Any other voice with at least `meeting_min_seconds` (20 s) over at least 2 phrases, after regrouping |
| Automatic switch | Dictation becomes a meeting when a second voice is confirmed |
| Manual switch | The box's Meeting button: becomes a meeting at once (`meeting_manual`) |
| Call open | Another app is recording the mic (per `pactl`), or a Meet, Zoom or Teams window is showing. Starts the call stream; it stops 15 s after the call ends |
| Echo | The call's audio heard again by the mic through laptop speakers. A mic phrase is dropped as echo when 60% of its words appear, in order, in call phrases within 1 s of it (`echo_dropped`) |
| Transcript | `transcripts/<YYYY-MM-DD HHMM> meeting.md`: timestamps, `Speaker N` labels, one paragraph per speaker turn |

## Outcomes (the `outcome` log field)

**Table T6: Outcomes**

| Outcome | Meaning |
|---|---|
| `typed` | Dictation finished and all text was inserted |
| `typed_preview_fallback` | As `typed`, but at least one phrase used preview text |
| `meeting` | Session ended as a meeting; transcript saved |
| `origin_closed` | Origin window gone at the end; text on the clipboard |
| `insert_failed` | An insertion failed; text on the clipboard and in the backup |
| `empty` | Nothing recognised |
| `cancelled` | Cancel button or SIGTERM; inserted text stays |
| `mic_error` | The microphone stream ended unexpectedly |
| `window_changed` | Historical only (2026-11-16 02:03 to 02:28 UTC), when a window switch blocked insertion |

## Files that hold words

**Table T7: Text stores**

| File | Holds | Kept |
|---|---|---|
| `data/live/<start>.txt` | Each phrase as it arrives (call phrases prefixed `[call]`) | Until the session ends; a leftover file means a crash |
| `data/dictations.txt` | Whole-session text, newest first | Last 20 sessions (`backup_keep`) |
| `transcripts/*.md` | Meeting transcripts | Until the owner deletes them |
| `data/sessions.jsonl` | Numbers only, no words | Permanent |
