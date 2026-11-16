#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""End-to-end tests for bin/dictate-live on a private X display.

Run through tests/run.sh, which starts this under its own D-Bus session. Every test
uses a scratch copy of the code, the real speech engines, and recorded speech played
as if from the microphone, so the user's screen, windows, data and running F9
session are never touched (docs/TESTING.md).

Test speech: whisper.cpp's public sample clip (samples/jfk.wav), downloaded once and
checksummed. Voices B and C are pitch-shifted copies, which the speaker model scores
as different people (similarity about 0.3 to the original).
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CACHE = os.path.join(REPO, "tests", ".cache")
JFK_URL = "https://raw.githubusercontent.com/ggml-org/whisper.cpp/v1.7.5/samples/jfk.wav"
JFK_SHA256 = "59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e"
RATE = 16000
PILL = np.array([28, 28, 32])    # box background (docs/ARCHITECTURE.md, CSS)
BUTTON = np.array([46, 46, 50])  # button background over the box
WORDS = "country"                # appears twice in every copy of the clip


# Audio

def fetch_jfk():
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "jfk.wav")
    if not os.path.exists(path):
        urllib.request.urlretrieve(JFK_URL, path + ".part")
        os.replace(path + ".part", path)
    digest = subprocess.run(["sha256sum", path], capture_output=True, text=True).stdout.split()[0]
    if digest != JFK_SHA256:
        os.remove(path)
        sys.exit(f"checksum mismatch for {JFK_URL}")
    return path


def read_wav(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)


def write_wav(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(np.clip(samples, -32768, 32767).astype(np.int16).tobytes())


def shifted(src, ratio, dst):
    """Same words and speed, different pitch: reads as another speaker."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                    f"asetrate={RATE}*{ratio},aresample={RATE},atempo={1 / ratio}",
                    "-ac", "1", "-ar", str(RATE), dst], check=True)
    return read_wav(dst)


def sequence(parts, gap=1.5, lead=1.0, tail=15.0):
    """Join clips with silences; returns the audio and each clip's start time."""
    out, starts, t = [np.zeros(int(lead * RATE), np.float32)], [], lead
    for clip in parts:
        starts.append(t)
        out += [clip, np.zeros(int(gap * RATE), np.float32)]
        t += len(clip) / RATE + gap
    out.append(np.zeros(int(tail * RATE), np.float32))
    return np.concatenate(out), starts


def build_audio(work):
    a = read_wav(fetch_jfk())
    b = shifted(os.path.join(CACHE, "jfk.wav"), 0.80, os.path.join(work, "voice_b.wav"))
    clips = {}
    clips["dictation"], _ = sequence([a, a, a, a])
    rng = np.random.default_rng(1)
    pink = np.cumsum(rng.normal(0, 1, len(clips["dictation"])))  # brown-ish rumble, made stationary
    pink -= np.convolve(pink, np.ones(400) / 400, mode="same")
    noise = pink / np.std(pink) * 650  # about the loud background measured on the reference mic
    clips["noisy"] = clips["dictation"] + noise.astype(np.float32)
    clips["silence"] = np.zeros(20 * RATE, np.float32)
    clips["room"], _ = sequence([a, b, a, b, a])
    clips["monologue"], _ = sequence([a] * 12)
    # A call: A on the mic; B only on the computer's sound, and heard again by the mic
    # through the speakers at a third of the volume, 50 ms late.
    mic, starts = sequence([a, b, a, b, a, b, a])
    call = np.zeros_like(mic)
    for i, t in enumerate(starts):
        if i % 2:
            s = int(t * RATE)
            mic[s:s + len(b)] = 0
            call[s:s + len(b)] += b
            mic[s + 800:s + 800 + len(b)] += 0.35 * b
    clips["call_mic"] = mic + rng.normal(0, 60, len(mic)).astype(np.float32)
    clips["call_side"] = call
    for name, samples in clips.items():
        write_wav(os.path.join(work, f"{name}.wav"), samples)


# Scratch project and shims

def make_project(work):
    proj = os.path.join(work, "proj")
    os.makedirs(os.path.join(proj, "bin"))
    os.makedirs(os.path.join(proj, "data"))
    shutil.copy(os.path.join(REPO, "bin", "dictate-live"), os.path.join(proj, "bin"))
    shutil.copytree(os.path.join(REPO, "config"), os.path.join(proj, "config"))
    shutil.copytree(os.path.join(REPO, "lib"), os.path.join(proj, "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("models", ".venv"):
        os.symlink(os.path.join(REPO, name), os.path.join(proj, name))
    return proj


SHIMS = {
    # The microphone: plays the clip named in $WORK/mic in real time.
    "arecord": '#!/bin/bash\ndate +%s.%N > "$E2E_WORK/mic_started"\n'
               'exec ffmpeg -v quiet -re -i "$E2E_WORK/$(cat "$E2E_WORK/mic").wav" -f s16le -ac 1 -ar 16000 -\n',
    # The computer's sound during a call, aligned with the microphone clip.
    "parec": '#!/bin/bash\noff=$(python3 -c "import time; print(max(0, time.time() - float(open(\'$E2E_WORK/mic_started\').read())))")\n'
             'exec ffmpeg -v quiet -re -ss "$off" -i "$E2E_WORK/call_side.wav" -f s16le -ac 1 -ar 16000 -\n',
    # Is a call open? $WORK/call contains "yes" or "no".
    "pactl": '#!/bin/bash\ncase "$*" in\n'
             ' *"list sources"*) echo \'[{"index":1,"name":"mic"},{"index":2,"name":"speaker.monitor"}]\';;\n'
             ' *"list source-outputs"*) if [ "$(cat "$E2E_WORK/call")" = yes ]; then\n'
             '   echo \'[{"index":9,"source":1,"properties":{"application.process.binary":"chrome","application.process.id":"4242"}}]\';\n'
             '   else echo "[]"; fi;;\n'
             ' *) echo "[]";;\nesac\n',
    "paplay": "#!/bin/bash\nexit 0\n",
    "notify-send": '#!/bin/bash\necho "$*" >> "$E2E_WORK/notifications"\n',
}


def make_shims(work):
    shim = os.path.join(work, "shim")
    os.makedirs(shim)
    for name, body in SHIMS.items():
        path = os.path.join(shim, name)
        with open(path, "w") as f:
            f.write(body)
        os.chmod(path, 0o755)
    return shim


# The private display

class Display:
    def __init__(self, work, shim):
        self.num = next(n for n in range(99, 140) if not os.path.exists(f"/tmp/.X{n}-lock"))
        self.env = dict(os.environ, DISPLAY=f":{self.num}", XDG_RUNTIME_DIR=os.path.join(work, "run"),
                        E2E_WORK=work, PATH=shim + os.pathsep + os.environ["PATH"])
        os.makedirs(self.env["XDG_RUNTIME_DIR"], mode=0o700)
        self.procs = []
        self.spawn(["Xvfb", f":{self.num}", "-screen", "0", "1280x800x24"])
        time.sleep(1)
        self.spawn(["xfwm4", f"--display=:{self.num}", "--compositor=off", "--sm-client-disable"])
        time.sleep(2)

    def spawn(self, cmd, **kw):
        kw.setdefault("stdout", subprocess.DEVNULL)
        kw.setdefault("stderr", subprocess.DEVNULL)
        p = subprocess.Popen(cmd, env=self.env, **kw)
        self.procs.append(p)
        return p

    def run(self, *cmd):
        return subprocess.run(cmd, env=self.env, capture_output=True, text=True).stdout.strip()

    def terminal(self, title, out):
        p = self.spawn(["xfce4-terminal", "--disable-server", f"--title={title}", "-x", "sh", "-c",
                        f"stty -icanon -echo; cat > '{out}'"])
        for _ in range(50):
            wid = self.run("xdotool", "search", "--onlyvisible", "--name", title).split()
            if wid:
                return p, wid[0]
            time.sleep(0.2)
        raise RuntimeError(f"terminal {title} did not appear")

    def activate(self, wid):
        self.run("xdotool", "windowactivate", "--sync", wid)
        time.sleep(0.3)

    def active(self):
        return self.run("xdotool", "getactivewindow")

    def screen(self):
        raw = subprocess.run(["ffmpeg", "-v", "quiet", "-f", "x11grab", "-video_size", "1280x800",
                              "-i", f":{self.num}", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             env=self.env, capture_output=True).stdout
        return np.frombuffer(raw, np.uint8).reshape(800, 1280, 3).astype(int)

    def buttons(self):
        """Box buttons as rows of (x, y) centres, found by colour, top row first.
        Scanlines with button-coloured runs are grouped; each group is one row."""
        self.run("xdotool", "mousemove", "1270", "10")  # no hover highlight
        time.sleep(0.3)
        img = self.screen()
        groups = []  # [first y, last y, runs at the middle]
        for y in range(300, 800):
            mask = np.abs(img[y, 300:980] - BUTTON).max(axis=1) < 7
            spans, start = [], None
            for x, on in enumerate(list(mask) + [False]):
                if on and start is None:
                    start = x
                elif not on and start is not None:
                    if x - start < 3:  # anti-aliased edge pixels, not a button
                        pass
                    elif spans and start - spans[-1][1] <= 12:  # a glyph splits the button: rejoin
                        spans[-1][1] = x
                    else:
                        spans.append([start, x])
                    start = None
            runs = [300 + (a + b) // 2 for a, b in spans if 25 <= b - a <= 200]  # buttons, not the meter bar
            if not runs:
                continue
            if groups and y - groups[-1][1] <= 2 and len(runs) == len(groups[-1][2]):
                groups[-1][1] = y
            else:
                groups.append([y, y, runs])
        return [[(x, (y0 + y1) // 2) for x in runs] for y0, y1, runs in groups if y1 - y0 >= 10]

    def click(self, x, y):
        self.run("xdotool", "mousemove", str(x), str(y), "click", "1")
        time.sleep(0.4)

    def close(self):
        for p in reversed(self.procs):
            if p.poll() is None:
                p.terminate()
        for p in self.procs:
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()


# Scenarios

class Run:
    def __init__(self, args):
        self.work = tempfile.mkdtemp(prefix="dictate-e2e-")
        self.keep = args.keep
        print(f"work folder: {self.work}")
        build_audio(self.work)
        self.proj = make_project(self.work)
        self.shim = make_shims(self.work)
        self.d = Display(self.work, self.shim)

    def setup(self, mic, call="no"):
        for name, value in (("mic", mic), ("call", call)):
            with open(os.path.join(self.work, name), "w") as f:
                f.write(value)
        shutil.rmtree(os.path.join(self.proj, "transcripts"), ignore_errors=True)
        self.out_a = os.path.join(self.work, "a.txt")
        self.out_b = os.path.join(self.work, "b.txt")
        self.ta, self.a = self.d.terminal("termA", self.out_a)
        self.tb, self.b = self.d.terminal("termB", self.out_b)
        self.d.activate(self.a)

    def start(self):
        self.session = self.d.spawn(["/usr/bin/python3", os.path.join(self.proj, "bin", "dictate-live")],
                                    stderr=open(os.path.join(self.work, "err.log"), "a"))
        self.t0 = time.time()

    def at(self, seconds):
        time.sleep(max(0, self.t0 + seconds - time.time()))

    def press(self):
        """The second F9 press: a second process that signals the first."""
        subprocess.run(["/usr/bin/python3", os.path.join(self.proj, "bin", "dictate-live")], env=self.d.env)
        self.session.wait(120)

    def finish(self):
        for p in (self.ta, self.tb):
            p.terminate()
        time.sleep(0.5)

    def row(self):
        with open(os.path.join(self.proj, "data", "sessions.jsonl")) as f:
            return json.loads(f.readlines()[-1])

    def text(self, path):
        try:
            with open(path) as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def transcript(self):
        folder = os.path.join(self.proj, "transcripts")
        names = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
        return self.text(os.path.join(folder, names[-1])) if names else ""

    def close(self):
        self.d.close()
        if not self.keep:
            shutil.rmtree(self.work, ignore_errors=True)


def s_dictation(r, clip="dictation", need=8):
    """Four copies of the clip; leave for termB, come back, leave again, press F9 from termB."""
    r.setup(clip)
    r.start()
    r.at(15); r.d.activate(r.b)
    r.at(30); r.d.activate(r.a)
    r.at(44); r.d.activate(r.b)
    r.at(57); r.press()
    row, a, b = r.row(), r.text(r.out_a), r.text(r.out_b)
    ok = (row["outcome"] == "typed" and a.lower().count(WORDS) >= need and not b.strip()
          and r.d.active() == r.b and row.get("held_flushes", 0) >= 1)
    return ok, (f"outcome {row['outcome']}, '{WORDS}' x{a.lower().count(WORDS)} in A (need {need}), "
                f"B {'empty' if not b.strip() else 'NOT empty'}, held_flushes {row.get('held_flushes')}, "
                f"phrase latency {row.get('phrase_latency_avg_s')} s")


def s_noisy(r):
    return s_dictation(r, "noisy", need=7)


def s_empty_cancel(r):
    r.setup("silence")
    r.start()
    r.at(5); r.press()
    empty = r.row()["outcome"] == "empty"
    r.finish()
    r.setup("dictation")
    r.start()
    r.at(20)
    r.session.send_signal(signal.SIGTERM)
    r.session.wait(30)
    row, a = r.row(), r.text(r.out_a)
    live = os.path.join(r.proj, "data", "live")
    leftovers = os.listdir(live) if os.path.isdir(live) else []
    ok = empty and row["outcome"] == "cancelled" and WORDS in a.lower() and not leftovers
    return ok, f"silence -> {'empty' if empty else 'NOT empty'}; cancel -> {row['outcome']}, inserted text kept: {WORDS in a.lower()}, live files left: {len(leftovers)}"


def s_room_meeting(r):
    r.setup("room")
    r.start()
    r.at(65); r.press()
    row, t = r.row(), r.transcript()
    ok = row["outcome"] == "meeting" and row.get("speakers") == 2 and "Speaker 2" in t
    return ok, f"outcome {row['outcome']}, speakers {row.get('speakers')}, transcript {'has' if 'Speaker 2' in t else 'LACKS'} Speaker 2"


def s_call_echo(r):
    r.setup("call_mic", call="yes")
    r.start()
    r.at(92); r.press()
    row, a, t = r.row(), r.text(r.out_a), r.transcript()
    a_count = a.lower().count(WORDS)
    t_count = t.lower().count(WORDS)
    ok = (row["outcome"] == "meeting" and row.get("echo_dropped", 0) >= 2 and row.get("call_phrases", 0) >= 3
          and a_count <= 4 and 12 <= t_count <= 14)
    return ok, (f"outcome {row['outcome']}, call_phrases {row.get('call_phrases')}, echo_dropped {row.get('echo_dropped')}, "
                f"'{WORDS}' x{a_count} typed (voice A before the switch: at most 4), x{t_count} in transcript (12 to 14, no duplicates)")


def s_monologue(r):
    r.setup("monologue")
    r.start()
    r.at(165); r.press()
    row = r.row()
    ok = row["outcome"] == "typed" and not row.get("meeting")
    return ok, f"outcome {row['outcome']}, meeting {row.get('meeting')}, phrases {row.get('phrases')}"


def s_meeting_button(r):
    r.setup("dictation")
    r.start()
    r.at(4)
    rows = r.d.buttons()
    if not rows or len(rows[0]) != 3:
        return False, f"could not find the three box buttons (found {rows[:1]})"
    r.d.click(*rows[0][0])  # Meeting, Tune, Cancel: Meeting is leftmost
    focus = r.d.active() == r.a
    r.at(40); r.press()
    row, a, t = r.row(), r.text(r.out_a), r.transcript()
    ok = row.get("meeting_manual") and not a.strip() and WORDS in t.lower() and focus
    return ok, f"meeting_manual {row.get('meeting_manual')}, typed into window: {len(a.strip())} chars, transcript has text: {WORDS in t.lower()}, focus kept: {focus}"


def s_tune(r):
    conf = os.path.join(r.proj, "config", "dictate.conf")
    before = open(conf).read()
    r.setup("dictation")
    r.start()
    r.at(4)
    rows = r.d.buttons()
    r.d.click(*rows[0][1])  # Tune
    rows = r.d.buttons()
    small = next((row for row in rows[1:] if len(row) == 4), None)
    if not small:
        subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-f", "x11grab", "-video_size", "1280x800", "-i",
                        f":{r.d.num}", "-frames:v", "1", os.path.join(r.work, "tune-fail.png")], env=r.d.env)
        r.press()
        return False, f"Tune panel buttons not found (rows: {[len(x) for x in rows]}; screenshot tune-fail.png)"
    r.d.click(*small[1])  # Sensitivity +
    r.d.click(*small[3])  # Pause +
    focus = r.d.active() == r.a
    after = open(conf).read()
    r.at(12); r.press()
    with open(conf, "w") as f:
        f.write(before)
    ok = focus and "speech_ratio = 2.25" in after and "pause_ms = 800" in after
    return ok, f"focus kept: {focus}, speech_ratio 2.5 -> 2.25: {'speech_ratio = 2.25' in after}, pause 700 -> 800: {'pause_ms = 800' in after}"


SCENARIOS = {
    "dictation": s_dictation, "noisy": s_noisy, "empty-cancel": s_empty_cancel,
    "room-meeting": s_room_meeting, "call-echo": s_call_echo, "meeting-button": s_meeting_button,
    "tune": s_tune, "monologue": s_monologue,
}
SLOW = {"monologue"}


def main():
    ap = argparse.ArgumentParser(description="End-to-end tests on a private display.")
    ap.add_argument("scenarios", nargs="*", help=f"any of: {', '.join(SCENARIOS)} (default: all but the slow ones)")
    ap.add_argument("--slow", action="store_true", help="also run the 2.5-minute monologue")
    ap.add_argument("--keep", action="store_true", help="keep the work folder for inspection")
    args = ap.parse_args()
    names = args.scenarios or [n for n in SCENARIOS if args.slow or n not in SLOW]
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        sys.exit(f"unknown scenario: {', '.join(unknown)}")
    r = Run(args)
    results = []
    try:
        for name in names:
            started = time.time()
            try:
                ok, detail = SCENARIOS[name](r)
            except Exception as e:  # a broken scenario must not stop the others
                ok, detail = False, f"error: {e!r}"
            if getattr(r, "session", None) and r.session.poll() is None:
                r.session.kill()
            r.finish()
            results.append((name, ok, detail, time.time() - started))
            print(f"{'PASS' if ok else 'FAIL'}  {name:15s} {time.time() - started:5.0f} s  {detail}", flush=True)
    finally:
        r.close()
    failed = [n for n, ok, _, _ in results if not ok]
    print(f"\n{len(results) - len(failed)} of {len(results)} passed" + (f"; failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
