# Roadmap & Backlog: OnDevice Speech To Text

> **The single source of truth for forward-looking work.** Anything not shipped lives here. If an
> item needs more than a paragraph, write a detail file under `docs/` and link it from its row.
> Shipped history is in [CHANGELOG.md](CHANGELOG.md), rationale in [docs/DECISIONS.md](docs/DECISIONS.md),
> system design in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
>
> **Start at §0.** It lists every open item, one row each. §2.2 is the ledger: the same open rows
> plus every closed one.
>
> Timestamps are ISO 8601 to the second, in UTC. Git history starts at the first public commit
> (2026-11-16), so Raised dates for earlier items come from CHANGELOG.md.
>
> _Last updated: 2026-11-16T14:13:16+00:00 (row 17 closed, row 22 added: published as a public repository)._

## 0. North star: every open item, one row each

Grouped by state (Open, Decision, Waiting, Blocked, Deferred, Recurring), then by priority.
`#` is the ledger number and never changes.

| # | Bucket | Priority | State | Size | Impact | Raised | Problem | Solution or next step |
|---|---|---|---|---|---|---|---|---|
| 16 | §3.1 | P2 | **Open** | S | M | 2026-11-16 | Meeting mode, call audio, echo dropping and pause detection were tested only with synthetic voices on a hidden display; real voices, a real call and the owner's loud mic background are untested. | Owner runs one real call and one in-room conversation; the agent reviews the transcripts and `dictate-stats`, then tunes `speech_ratio`, the 0.56 and 0.55 speaker thresholds and the echo rule. [§8.1](#81-row-16-real-world-validation) |
| 18 | §3.3 | P2 | **Open** | M | M | 2026-11-16 | The hidden-display test harness (shims, clips, scenarios) exists only in a session scratchpad, so every future change rebuilds it by hand and regressions can slip through. | Commit it as `tests/` (shims, clip builder, five scenarios, one runner) following docs/TESTING.md; no owner data involved. |
| 19 | §3.2 | P3 | **Deferred** | L | L | 2026-11-16 | When two people speak within one phrase (no 0.7 s pause), the whole phrase gets one speaker label. | Brought back if real transcripts show mixed turns: add speaker-change segmentation inside phrases (pyannote segmentation 3.0 via sherpa-onnx). |
| 20 | §3.2 | P3 | **Deferred** | M | L | 2026-11-16 | Phrases held while the owner is in another window are transcribed one by one, so words cut at pause boundaries may be less accurate than one pass. | Brought back if held text shows boundary errors: re-run held phrases' audio as one piece before inserting. |
| 21 | §3.1 | P3 | **Deferred** | ? | L | 2026-10-20 | `xdotool type` can mistype some non-ASCII characters in a few apps (noted in ANALYSIS, Known limits); terminals already get long text by paste. | Brought back if a mistyped character is seen: paste all phrases containing non-ASCII characters instead of typing them. |

**Reading the narrow columns.** Bucket is the §3 area: 3.1 Reliability, 3.2 Features, 3.3 Engineering.
Size: T trivial, S small, M medium, L large, ? unknown. Impact: H high, M medium, L low. A long-form
note for a row is in §8, linked from the end of its solution cell.

### Legend

**Priority** (how much it hurts):

| Priority | Means |
|---|---|
| **P0** | A live customer is losing something today |
| **P1** | Costs a support ticket, real money or a release every time it happens |
| **P2** | The product is measurably worse without it |
| **P3** | Worth doing; nothing breaks if it waits |

An empty P0 is good news. Never inflate an item to fill it. Here, "customer" means the owner using F9.

**Impact** (what it costs not to do):

| Impact | Means |
|---|---|
| **High** | Costs activations, refunds, revenue, or a customer meeting a defect |
| **Medium** | Costs support hours, or blocks something High |
| **Low** | Real, and nobody is bleeding |

Priority, Size and Impact are separate columns because they answer separate questions: how much it hurts, what it costs to do, and what it costs not to do.

**State** (closed vocabulary; use no other word):

| State | Means |
|---|---|
| **Open** | Not started or partly done; nothing stops it but a decision to begin |
| **Blocked** | Cannot proceed until someone outside the project acts or changes a policy; the row names who |
| **Waiting** | Ready, and deliberately held until a named date (a measurement window, a staged rollout) |
| **Deferred** | Could proceed, and the owner has chosen not to yet (usually new spend, or no demand); the row says what would bring it back |
| **Decision** | An answer from the owner is needed first; the row carries a recommendation |
| **Recurring** | A procedure that runs again every release or on a date; the row records the last run |
| **Done** | Closed, with the date and the size it turned out to be (ledger only) |

## How to keep this file current

| When | Do this |
|---|---|
| An item closes | Move its ledger row to the Done block with `**Done** <date>` and `Was <size>`, remove it from §0, delete its §8 subsection. Never delete the ledger row |
| An item is found | Add it to §0 and the ledger with the next unused number, and to its §3 area if it needs context |
| The owner answers a Decision | Update the §0 row and the ledger row the same day |
| A state changes | Change it in §0 and the ledger together |
| A release or milestone ships | Update §2.1, close the rows it shipped, update §1 |
| Anything above happens | Update the header's `_Last updated_` line with the timestamp and what changed |

---

## 1. Shipped capabilities

| Capability | Since |
|---|---|
| F9 dictation, fully on-device (basic mode) | 2026-10-20 |
| Live box with preview text; Parakeet final engine; F9 on live mode | 2026-10-20 |
| `install.sh` with self-check; `docs/REPLICATE.md` | 2026-10-20 |
| Text always into the window where F9 was pressed; private text backup | 2026-11-16 |
| Text inserted at each pause; held while away; no length limit | 2026-11-16 |
| Meetings: automatic switch, Meeting button, speaker labels, call audio with echo dropping | 2026-11-16 |
| Tune panel in the box | 2026-11-16 |

## 2. Next up

### 2.1 Status: public, waiting for real-world use (updated 2026-11-16T14:13:33+00:00)

Published at github.com/PalWorks/ondevice-speech-to-text under AGPL 3.0 plus a commercial licence. The next step is row 16: one real call and one in-room conversation, then tuning.

### 2.2 The ledger: every backlog item, pending first, done at the bottom

**The ledger is authoritative for STATE; §3 and §8 are authoritative for REASONING.** Open rows
repeat §0 in one line; §0 holds the problem and solution. Closed rows keep only their date and size.

| # | Item | Section | State | Size | Impact |
|---|---|---|---|---|---|
| 16 | Real-world validation and tuning of meetings, calls and pause detection | §3.1 | **Open**: waiting for the owner's first real call | S | M |
| 18 | Commit the hidden-display test harness as `tests/` | §3.3 | **Open** | M | M |
| 19 | Speaker changes inside one phrase | §3.2 | **Deferred** | L | L |
| 20 | Re-transcribe held phrases as one piece | §3.2 | **Deferred** | M | L |
| 21 | Non-ASCII characters mistyped by `xdotool type` | §3.1 | **Deferred** | ? | L |
| 1 | Basic F9 dictation (whisper.cpp, small.en) | §3.2 | **Done** 2026-10-20 | Was Medium | H |
| 2 | Live preview box | §3.2 | **Done** 2026-10-20 | Was Medium | M |
| 3 | Live-mode accuracy: beam search, Parakeet as default | §3.1 | **Done** 2026-10-20 | Was Medium | H |
| 4 | Pre-production audit, `install.sh`, F9 to live mode | §3.3 | **Done** 2026-10-20 | Was Medium | M |
| 5 | Remove the old Homebrew `openai-whisper` | §3.3 | **Done** 2026-10-20 | Was Trivial | L |
| 6 | Text typed into the wrong window (Gmail incident) | §3.1 | **Done** 2026-11-16 | Was Small | H |
| 7 | Text always into the origin window | §3.1 | **Done** 2026-11-16: superseded the clipboard fix in row 6 | Was Small | H |
| 8 | Private backup of dictated text | §3.1 | **Done** 2026-11-16 | Was Small | M |
| 9 | Phrases typed on pause (option 3) | §3.2 | **Done** 2026-11-16 | Was Medium | H |
| 10 | No 5-minute cutoff | §3.2 | **Done** 2026-11-16 | Was Small | M |
| 11 | Meeting mode with speaker labels | §3.2 | **Done** 2026-11-16 | Was Large | M |
| 12 | Call audio with echo dropping | §3.2 | **Done** 2026-11-16 | Was Medium | M |
| 13 | Tune panel in the box | §3.2 | **Done** 2026-11-16 | Was Small | M |
| 14 | Meeting button | §3.2 | **Done** 2026-11-16 | Was Small | M |
| 15 | Documentation set (README, AGENTS, ROADMAP, docs) | §3.3 | **Done** 2026-11-16 | Was Medium | M |
| 17 | Put the project under version control | §3.3 | **Done** 2026-11-16: public repo chosen instead of private (row 22) | Was Trivial | M |
| 22 | Publish as a public repository, AGPL 3.0 plus commercial licence | §3.3 | **Done** 2026-11-16 | Was Small | M |

---

## 3. Backlog by area

### 3.1 Reliability

Rows 16 and 21. Row 16 matters most: every Phase 2 threshold was chosen on test clips (docs/DECISIONS.md D-10, D-13, D-14).

### 3.2 Features

Rows 19 and 20. Both are improvements to work already shipped, held until real use shows the need.

### 3.3 Engineering

Row 18. With the git repository (rows 17, 22) it makes changes to the production F9 script safe to undo and quick to verify.

## 4. Deferred: decided, waiting on something

| Item | Waiting on | Detail |
|---|---|---|
| Speaker changes inside one phrase | Real transcripts showing mixed turns | Row 19 |
| Re-transcribe held phrases as one piece | Held text showing boundary errors | Row 20 |
| Non-ASCII mistyping | A seen occurrence | Row 21 |

## 5. Not doing: decided against, with the reason

| Item | Why |
|---|---|
| Switch focus to the origin window for every phrase while the owner is elsewhere | Steals keystrokes (a stray Enter in a terminal runs a command), closes menus, flickers, churns the clipboard (owner chose hold and insert on return, 2026-11-16; D-09) |
| Type into a window that is not in front (X synthetic events) or inject into a terminal's input | Tested: ignored by xfce4-terminal and GTK apps; blocked by the kernel (`dev.tty.legacy_tiocsti = 0`) |
| Correct already-inserted text when the final engine disagrees with the preview | Needs synthetic backspaces, which misbehave in editors, terminals and chat boxes (D-02) |
| A separate hotkey for meeting mode | Owner chose the automatic switch inside F9 plus the Meeting button (2026-11-16; D-12) |
| Wayland support | The reference machine runs X11; porting notes are in docs/REPLICATE.md §4. Reports from Wayland users are welcome as issues |
| SpeechNote | Heavier for the same result (2026-10-20; D-01) |

## 6. Where the detail lives

One detail document:

| Document | Covers |
|---|---|
| [docs/TESTING.md](docs/TESTING.md) | The hidden-display harness that row 18 commits |

## 7. Closed, kept for the reasoning

- **Row 6, the Gmail incident.** Text typed into whatever window was in front at the second F9 fired Gmail's single-key shortcuts. **Rule: never type into any window except the origin window.**
- **Row 9, phrases on pause.** Built with the hold-while-away rule. **Rule: never take the keyboard from the owner while they are in another window.**

## 8. Open rows in full

### 8.1 Row 16: real-world validation

What to check after the owner's first real sessions:

1. `dictate-stats` and the last rows of `data/sessions.jsonl`: `phrases` per minute of `audio_s` (too few means pauses are not detected: raise Sensitivity or lower `speech_ratio`), `phrase_latency_avg_s` (expected 1 to 2 s on an idle laptop; 6 s was seen while Chrome loaded the CPU), `echo_dropped` and `call_phrases` for calls.
2. The meeting transcript: speaker count against the real number of people, mixed turns (row 19), duplicate lines (echo rule), missing lines (echo rule too strict).
3. Whether the automatic switch fired, how late, and whether a monologue ever switched by mistake.

Tune one thing at a time and record each change in CHANGELOG.md and, if it is a decision, docs/DECISIONS.md.
